#!/usr/bin/env python3
"""
spy_linkedin.py — Cheap & Reliable LinkedIn Spying CLI Tool
===========================================================
Executes lightning-fast, micro-metered LinkedIn intelligence gathering:
- Active hiring & open roles (sales, revops, leadership, engineering)
- Key decision-makers & founders on LinkedIn
- Why-Now timing triggers & urgency scoring
- Cost tracking (< $0.0008 per scan)

Usage:
  # Spy on a single company
  python spy_linkedin.py --company "Ramp"

  # Include domain
  python spy_linkedin.py --company "Clay" --domain "clay.com"

  # Output as JSON
  python spy_linkedin.py --company "Cursor" --json

  # Scan top leads from latest Verve run file
  python spy_linkedin.py --latest --limit 3
"""

from __future__ import annotations

import argparse
import asyncio
import glob
import json
import logging
import os
import sys
from pathlib import Path

# Add backend directory to sys.path so app imports work seamlessly
backend_dir = Path(__file__).resolve().parent / "backend"
sys.path.insert(0, str(backend_dir))

from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent / ".env")
load_dotenv(backend_dir / ".env")

from app.trigger_engine.linkedin_spy import LinkedInSpyService
from app.trigger_engine.treg_client import TregClient

logging.basicConfig(level=logging.WARNING)


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


def print_spy_report(res: dict):
    print("=" * 70)
    print(f"🎯 LINKEDIN SPY REPORT: {res['company_name']} (Brand: {res['clean_name']})")
    print("=" * 70)
    print(f"🔥 Urgency Score: {res['urgency_score']}/10")
    print(f"💡 Angle:         {res['angle']}")
    print(f"⚡ Timing Hook:   {res['timing_hook']}")
    print(f"💰 Treg Spend:    ${res['cost_usd']:.6f} USD")
    print(f"📡 Sources Used:  {', '.join(res['sources_used']) or 'none'}")
    print("-" * 70)

    jobs = res.get("jobs_found", [])
    print(f"💼 Open Jobs Detected ({len(jobs)}):")
    if not jobs:
        print("   (No open job postings detected via live search or indexed SERP)")
    else:
        for idx, j in enumerate(jobs, 1):
            cat_badge = f"[{j['category'].upper()}]"
            print(f"   {idx}. {cat_badge:<18} {j['title']}")
            print(f"      Company: {j['company']} | Location: {j.get('location', 'Remote')}")
            if j.get("url"):
                print(f"      URL:     {j['url']}")

    print("-" * 70)
    people = res.get("people_found", [])
    print(f"👥 Key People & Leadership Detected ({len(people)}):")
    if not people:
        print("   (No indexed executive profiles found)")
    else:
        for idx, p in enumerate(people, 1):
            role_badge = f"[{p['role_type'].upper()}]"
            print(f"   {idx}. {role_badge:<16} {p['name']} — {p['title']}")
            print(f"      LinkedIn: {p['url']}")

    print("=" * 70 + "\n")


async def main_async(args):
    treg = TregClient(per_call_cap=0.01)
    spy_service = LinkedInSpyService(treg_client=treg)

    targets = []
    if args.company:
        targets.append({"company_name": args.company, "domain": args.domain})
    elif args.latest or args.input:
        in_path = Path(args.input) if args.input else find_latest_verve_file()
        if not in_path or not in_path.exists():
            print("Error: No valid Verve input file found.", file=sys.stderr)
            sys.exit(1)
        with open(in_path, "r", encoding="utf-8") as f:
            raw = json.load(f)
        leads = raw if isinstance(raw, list) else raw.get("leads", [])
        for l in leads[:args.limit]:
            targets.append({
                "company_name": l.get("company_name") or l.get("name"),
                "domain": l.get("website"),
            })
    else:
        print("Error: Must specify --company, --latest, or --input.", file=sys.stderr)
        sys.exit(1)

    all_results = []
    for target in targets:
        name = target.get("company_name") or ""
        if not name:
            continue
        resp = await spy_service.spy(
            company_name=name,
            domain=target.get("domain"),
            include_people=not args.no_people,
        )
        res_dict = resp.model_dump()
        all_results.append(res_dict)

        if not args.json:
            print_spy_report(res_dict)

    if args.json:
        if len(all_results) == 1:
            print(json.dumps(all_results[0], indent=2, default=str))
        else:
            print(json.dumps(all_results, indent=2, default=str))


def main():
    parser = argparse.ArgumentParser(description="Cheap & Reliable LinkedIn Spying CLI")
    parser.add_argument("--company", "-c", type=str, help="Company name to spy on")
    parser.add_argument("--domain", "-d", type=str, help="Company website domain")
    parser.add_argument("--latest", action="store_true", help="Scan top leads from latest Verve run file")
    parser.add_argument("--input", "-i", type=str, help="Path to Verve leads JSON file")
    parser.add_argument("--limit", "-l", type=int, default=3, help="Max leads to scan from file")
    parser.add_argument("--no-people", action="store_true", help="Skip people / leadership search")
    parser.add_argument("--json", action="store_true", help="Output machine-readable JSON only")

    args = parser.parse_args()
    asyncio.run(main_async(args))


if __name__ == "__main__":
    main()

