#!/usr/bin/env python3
"""
run_trigger_engine.py — CLI Runner for the Flowjoy Trigger-Based Outbound Engine
================================================================================
Takes Verve's qualified accounts and continuously scans for "Why Now?" timing triggers:
- Funding & capital rounds (Google News via treg)
- GTM / Sales hiring (LinkedIn Jobs via treg)
- Product launches & version releases
- Social / Reddit buying discussions
- Tech stack & tooling additions

Workflow:
  Verve accounts → Trigger Detectors (treg) → AI Qualifier → Outreach Engine → Output

Usage:
  # Scan top leads from latest Verve run file
  python run_trigger_engine.py --latest --limit 5

  # Scan specific Verve JSON file
  python run_trigger_engine.py --input data/flowjoy_targeted_leads_20260916_125936.json --limit 3

  # Scan directly from PostgreSQL database
  python run_trigger_engine.py --db --limit 10
"""

from __future__ import annotations

import argparse
import asyncio
import glob
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# Add backend to sys.path so app imports work
backend_dir = Path(__file__).resolve().parent / "backend"
sys.path.insert(0, str(backend_dir))

from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent / ".env")
load_dotenv(backend_dir / ".env")

from app.db import get_session_context, init_db
from app.models import Lead as VerveLead
from app.trigger_engine.models import TriggerRun
from app.trigger_engine.service import TriggerEngineService
from app.trigger_engine.treg_client import TregClient
from sqlalchemy import select

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("trigger_engine")


def find_latest_verve_file() -> Path | None:
    data_dir = Path(__file__).resolve().parent / "data"
    patterns = [
        str(data_dir / "flowjoy_targeted_leads_*.json"),
        str(data_dir / "run_*.json"),
    ]
    files = []
    for pat in patterns:
        files.extend(glob.glob(pat))
    if not files:
        return None
    files.sort(key=os.path.getmtime, reverse=True)
    return Path(files[0])


def load_leads_from_file(file_path: Path, limit: int) -> list[dict]:
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    leads = data if isinstance(data, list) else data.get("leads", [])
    return leads[:limit]


async def load_leads_from_db(limit: int) -> list[dict]:
    async with get_session_context() as session:
        if not session:
            logger.error("Database connection not available")
            return []
        query = select(VerveLead).order_by(VerveLead.final_score.desc()).limit(limit)
        result = await session.execute(query)
        verve_leads = list(result.scalars().all())

        lead_dicts = []
        for l in verve_leads:
            raw_founders = []
            if l.founders_json:
                try:
                    raw_founders = json.loads(l.founders_json)
                except Exception:
                    raw_founders = []
            lead_dicts.append({
                "id": l.id,
                "company_name": l.company_name,
                "website": l.website,
                "one_liner": l.one_liner,
                "batch": l.batch,
                "industry": l.industry,
                "team_size": l.team_size,
                "tags": l.tags.split(",") if l.tags else [],
                "founder_name": l.founder_name,
                "founder_title": l.founder_title,
                "founder_linkedin": l.founder_linkedin,
                "email": l.email,
                "founders": raw_founders,
                "yc_url": l.yc_url,
                "linkedin_url": l.linkedin_url,
            })
        return lead_dicts


async def main_async(args):
    print("=" * 70)
    print("🚀 FLOWJOY TRIGGER-BASED OUTBOUND ENGINE")
    print("   Evaluating 'Why Now?' timing triggers for qualified accounts")
    print("=" * 70)

    # 1. Load accounts
    leads: list[dict] = []
    source_desc = ""
    if args.db:
        await init_db()
        leads = await load_leads_from_db(args.limit)
        source_desc = f"PostgreSQL database (top {len(leads)} leads)"
    elif args.input:
        in_path = Path(args.input)
        if not in_path.exists():
            print(f"Error: input file {in_path} does not exist.")
            sys.exit(1)
        leads = load_leads_from_file(in_path, args.limit)
        source_desc = f"{in_path.name} ({len(leads)} leads)"
    else:
        latest = find_latest_verve_file()
        if not latest:
            print("Error: No Verve lead run files found in data/.")
            sys.exit(1)
        leads = load_leads_from_file(latest, args.limit)
        source_desc = f"Latest run file: {latest.name} ({len(leads)} leads)"

    print(f"\n📂 Source: {source_desc}")
    print(f"🎯 Target Accounts to Scan: {len(leads)}")
    print(f"⚙️  Min Urgency Threshold: {args.min_urgency}/10\n")

    treg_client = TregClient(per_call_cap=0.02)
    service = TriggerEngineService(treg_client=treg_client)

    # 2. Run scans
    all_results = []
    total_briefs = 0

    async with get_session_context() as session:
        for idx, lead in enumerate(leads, 1):
            name = lead.get("company_name") or lead.get("name") or "Unknown"
            print(f"\n[{idx}/{len(leads)}] Scanning account: {name}")

            res = await service.scan_account(
                account=lead,
                trigger_types=args.types,
                min_urgency=args.min_urgency,
                session=session,
            )
            all_results.append(res)

            print(f"  • Signals found: {res['signals_found']}")
            print(f"  • Briefs generated: {res['briefs_generated']}")

            for brief in res["briefs"]:
                total_briefs += 1
                print("\n  " + "─" * 60)
                print(f"  🔥 QUALIFIED BRIEF: {brief['company_name']} (Urgency: {brief['urgency_score']}/10)")
                print(f"     Angle: {brief['angle']}")
                print(f"     Why Now Hook: {brief['why_now_hook']}")
                print(f"     Contact: {brief['founder_name']} <{brief['founder_email'] or 'email not found'}>")
                print(f"     Subject: {brief['email_subject']}")
                print(f"     Slack Alert:\n       {brief['slack_preview']}")
                print("  " + "─" * 60)

    # 3. Export results to data directory
    data_dir = Path(__file__).resolve().parent / "data"
    data_dir.mkdir(exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    out_file = data_dir / f"trigger_run_{ts}.json"

    export_payload = {
        "timestamp": ts,
        "accounts_scanned": len(leads),
        "total_briefs_generated": total_briefs,
        "treg_spend_usd": round(treg_client.total_cost_usd, 6),
        "results": all_results,
    }

    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(export_payload, f, indent=2, default=str)

    print("\n" + "=" * 70)
    print("✅ TRIGGER SCAN COMPLETE")
    print(f"   Accounts Scanned: {len(leads)}")
    print(f"   Outreach Briefs Generated: {total_briefs}")
    print(f"   Total Treg Spend: ${treg_client.total_cost_usd:.4f}")
    print(f"   Export Artifact: {out_file}")
    print("=" * 70)


def main():
    parser = argparse.ArgumentParser(description="Flowjoy Trigger-Based Outbound Engine")
    parser.add_argument("--latest", action="store_true", help="Use latest Verve run file in data/")
    parser.add_argument("--input", type=str, help="Path to Verve leads JSON file")
    parser.add_argument("--db", action="store_true", help="Pull top leads directly from database")
    parser.add_argument("--limit", type=int, default=3, help="Max accounts to scan (default: 3)")
    parser.add_argument("--min-urgency", type=int, default=6, help="Min urgency score 1-10 (default: 6)")
    parser.add_argument(
        "--types",
        nargs="+",
        choices=["gtm_hiring", "funding", "product_launch", "social_discussion", "tech_stack"],
        help="Filter specific trigger types",
    )
    args = parser.parse_args()
    asyncio.run(main_async(args))


if __name__ == "__main__":
    main()

