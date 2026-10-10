"""
scripts/linkedin_pilot.py — End-to-end LinkedIn intel pilot on real tracked accounts
====================================================================================
Runs the real pipeline (TriggerEngineService.scan_account with the `linkedin_activity`
detector → live treg calls → qualifier → outreach briefs → DB persistence) for N Verve
leads and dumps everything to backend/pilot_runs/<timestamp>/:

  raw_calls.json             every treg call: endpoint, params, status, cost, raw response
  <lead_id>.report.json      persisted LinkedInIntelReport (snapshot read back from DB)
  <lead_id>.scan.json        scan_account result (signals, evaluations, briefs)
  summary.json / summary.md  per-account metrics + totals

Usage (from backend/):
  uv run python scripts/linkedin_pilot.py                 # top-2 leads with LinkedIn URLs
  uv run python scripts/linkedin_pilot.py --limit 3
  uv run python scripts/linkedin_pilot.py --lead-ids a b
  uv run python scripts/linkedin_pilot.py --no-db --company "Acme" --company-url URL --founder-url URL
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from sqlalchemy import or_  # noqa: E402
from sqlmodel import select  # noqa: E402

from app.config import get_settings  # noqa: E402,F401  (loads .env)
from app.db import get_session_context, init_db  # noqa: E402
from app.models import Lead  # noqa: E402
from app.trigger_engine.detectors.linkedin_activity import LinkedInActivityDetector  # noqa: E402
from app.trigger_engine.linkedin_intel import IntelOptions, load_latest_snapshot  # noqa: E402
from app.trigger_engine.routes import _lead_to_account  # noqa: E402
from app.trigger_engine.service import TriggerEngineService  # noqa: E402
from app.trigger_engine.treg_client import TregClient  # noqa: E402


class RecordingTreg(TregClient):
    """TregClient that keeps a full log of every call (inputs, status, cost, raw body)."""

    def __init__(self) -> None:
        super().__init__()
        self.log: list[dict[str, Any]] = []
        self.current_account: Optional[str] = None

    async def call(self, endpoint_id: str, **kwargs: Any) -> dict[str, Any]:  # type: ignore[override]
        t0 = time.monotonic()
        res = await super().call(endpoint_id, **kwargs)
        self.log.append({
            "account": self.current_account,
            "endpoint_id": endpoint_id,
            "method": kwargs.get("method"),
            "params": kwargs.get("params"),
            "json": kwargs.get("json"),
            "max_cost": kwargs.get("max_cost"),
            "status_code": res.get("status_code"),
            "success": res.get("success"),
            "cost_usd": res.get("cost_usd"),
            "call_id": res.get("call_id"),
            "served_by": res.get("served_by"),
            "elapsed_s": round(time.monotonic() - t0, 2),
            "error": res.get("error"),
            "data": res.get("data"),
        })
        return res


def _dump(path: Path, obj: Any) -> None:
    path.write_text(json.dumps(obj, indent=2, default=str, ensure_ascii=False), encoding="utf-8")


async def _pick_leads(session, lead_ids: list[str], limit: int) -> list[Lead]:
    q = select(Lead)
    if lead_ids:
        q = q.where(Lead.id.in_(lead_ids))
    else:
        q = (
            q.where(or_(Lead.linkedin_url.is_not(None), Lead.founder_linkedin.is_not(None)))
            .order_by(Lead.final_score.desc())
            .limit(limit)
        )
    return list((await session.execute(q)).scalars().all())


def _account_metrics(report: dict[str, Any], scan: dict[str, Any], calls: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "lead_id": report.get("lead_id"),
        "company_name": report.get("company_name"),
        "company_linkedin_url": report.get("company_linkedin_url"),
        "founders": [f.get("name") or f.get("profile_url") for f in report.get("founders", [])],
        "company_posts": len(report.get("company_posts", [])),
        "founder_posts": len(report.get("founder_posts", [])),
        "post_comments": len(report.get("post_comments", [])),
        "founder_comments": len(report.get("founder_comments", [])),
        "signals": [f"{s['kind']}: {s['headline']}" for s in report.get("signals", [])],
        "engaged_people": [f"{p['name']} ({p['role']}, {p['comment_count']}x)" for p in report.get("engaged_people", [])[:8]],
        "topics": report.get("topics", []),
        "urgency_score": report.get("urgency_score"),
        "summary": report.get("summary"),
        "cost_usd": report.get("cost_usd"),
        "calls_made": report.get("calls_made"),
        "errors": report.get("errors", []),
        "scan_signals_found": scan.get("signals_found"),
        "scan_briefs_generated": scan.get("briefs_generated"),
        "treg_calls": [
            f"{c['endpoint_id']} -> {c['status_code']} ${c['cost_usd'] or 0:.4f} ({c['elapsed_s']}s)" for c in calls
        ],
    }


def _summary_md(metrics: list[dict[str, Any]], total_cost: float, out_dir: Path) -> str:
    lines = [f"# LinkedIn intel pilot — {out_dir.name}", "", f"Total treg spend: **${total_cost:.4f}**", ""]
    for m in metrics:
        lines += [
            f"## {m['company_name']} (`{m['lead_id']}`)",
            f"- Company page: {m['company_linkedin_url']}",
            f"- Founders: {', '.join(str(f) for f in m['founders']) or '—'}",
            f"- Posts: company {m['company_posts']}, founder {m['founder_posts']} · Comments: on posts {m['post_comments']}, by founders {m['founder_comments']}",
            f"- Urgency: {m['urgency_score']} · Cost: ${m['cost_usd']} · Calls: {m['calls_made']}",
            f"- Scan: {m['scan_signals_found']} signals → {m['scan_briefs_generated']} briefs",
            f"- Summary: {m['summary']}",
            "- Signals:",
            *[f"  - {s}" for s in m["signals"] or ["(none)"]],
            "- Engaged people:",
            *[f"  - {p}" for p in m["engaged_people"] or ["(none)"]],
            f"- Topics: {', '.join(m['topics']) or '—'}",
            "- treg calls:",
            *[f"  - {c}" for c in m["treg_calls"]],
        ]
        if m["errors"]:
            lines += ["- Errors:", *[f"  - {e}" for e in m["errors"]]]
        lines.append("")
    return "\n".join(lines)


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=2)
    ap.add_argument("--lead-ids", nargs="*", default=[])
    ap.add_argument("--max-cost", type=float, default=0.06, help="per-account treg budget (USD)")
    ap.add_argument("--no-db", action="store_true", help="skip DB; use --company/--company-url/--founder-url")
    ap.add_argument("--company")
    ap.add_argument("--company-url")
    ap.add_argument("--founder-url", action="append", default=[])
    args = ap.parse_args()

    out_dir = BACKEND_DIR / "pilot_runs" / datetime.now(timezone.utc).strftime("linkedin_%Y%m%d_%H%M%S")
    out_dir.mkdir(parents=True, exist_ok=True)

    treg = RecordingTreg()
    if not treg.token:
        raise SystemExit("TREG_TOKEN is not set")
    service = TriggerEngineService(treg_client=treg)
    service.detectors["linkedin_activity"] = LinkedInActivityDetector(IntelOptions(max_cost_usd=args.max_cost))

    metrics: list[dict[str, Any]] = []

    async def run_one(account: dict[str, Any], session) -> None:
        treg.current_account = str(account.get("id") or account.get("company_name"))
        print(f"→ {account.get('company_name')} ({treg.current_account})", flush=True)
        n_before = len(treg.log)
        scan = await service.scan_account(account, trigger_types=["linkedin_activity"], min_urgency=6, session=session)
        calls = treg.log[n_before:]
        report: dict[str, Any] = {}
        if session is not None:
            snap = await load_latest_snapshot(session, scan["lead_id"])
            report = snap.model_dump(mode="json") if snap else {}
        if not report:
            # no-DB path: re-run detector-free gather is wasteful; reconstruct from scan metadata
            report = {"lead_id": scan["lead_id"], "company_name": scan["company_name"]}
        _dump(out_dir / f"{scan['lead_id']}.report.json", report)
        _dump(out_dir / f"{scan['lead_id']}.scan.json", scan)
        m = _account_metrics(report, scan, calls)
        metrics.append(m)
        print(f"   urgency={m['urgency_score']} posts={m['company_posts']}+{m['founder_posts']} "
              f"comments={m['post_comments']}+{m['founder_comments']} signals={len(m['signals'])} "
              f"briefs={m['scan_briefs_generated']} cost=${m['cost_usd']}", flush=True)

    if args.no_db:
        if not args.company:
            raise SystemExit("--company is required with --no-db")
        account = {"company_name": args.company, "company_linkedin_url": args.company_url,
                   "founders": [{"linkedin_url": u} for u in args.founder_url]}
        await run_one(account, None)
    else:
        if not await init_db():
            raise SystemExit("DB init failed (check DATABASE_URL)")
        async with get_session_context() as session:
            leads = await _pick_leads(session, args.lead_ids, args.limit)
            if not leads:
                raise SystemExit("No matching leads")
            accounts = [_lead_to_account(l) for l in leads]
        for account in accounts:
            async with get_session_context() as session:
                await run_one(account, session)

    total = round(treg.total_cost_usd, 6)
    _dump(out_dir / "raw_calls.json", treg.log)
    _dump(out_dir / "summary.json", {"total_cost_usd": total, "accounts": metrics})
    (out_dir / "summary.md").write_text(_summary_md(metrics, total, out_dir), encoding="utf-8")
    print(f"\nTotal treg spend ${total:.4f} · results in {out_dir}")


if __name__ == "__main__":
    asyncio.run(main())

