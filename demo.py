#!/usr/bin/env python3
"""
StartupScrape Demo
Demonstrates scraping filtered leads from Y Combinator and Work at a Startup
using the URLs specified by the user.
"""

import sys
from startupscrape.pipeline import StartupScrapePipeline
from startupscrape.exporters import export_leads

# URLs provided in the user prompt with active filters
YC_FILTERED_URL = (
    "https://www.ycombinator.com/companies/"
    "?batch=Winter%202027&batch=Fall%202026&batch=Spring%202026&batch=Summer%202026"
    "&industry=B2B&industry=Consumer&industry=Fintech&isHiring=true&nonprofit=true"
    "&regions=United%20States%20of%20America&regions=Canada&regions=United%20Kingdom&regions=Germany&regions=Latin%20America"
    "&team_size=%5B%221%22%2C%22250%22%5D"
)

WAAS_FILTERED_URL = (
    "https://www.workatastartup.com/companies"
    "?demographic=any&hasEquity=any&hasSalary=any&industry=any&interviewProcess=any"
    "&jobType=any&layout=list-compact&locations=DE&sortBy=created_desc&tab=any&usVisaNotRequired=true"
)


def run_demo():
    print("=" * 75)
    print(" 🚀 STARTUPSCRAPE: Startup Lead Generation Demo")
    print("=" * 75)

    pipeline = StartupScrapePipeline()

    print("\n[1/2] Scraping Work at a Startup (Germany / Visa-friendly)...")
    waas_leads = pipeline.waas.scrape_url(WAAS_FILTERED_URL, max_results=10)
    print(f"      -> Found {len(waas_leads)} companies from Work at a Startup.")

    print("\n[2/2] Scraping Y Combinator Directory (Recent Batches, B2B/Fintech/Consumer, Hiring)...")
    yc_leads = pipeline.yc.scrape_url(YC_FILTERED_URL, max_results=10)
    print(f"      -> Found {len(yc_leads)} companies from Y Combinator.")

    all_raw = waas_leads + yc_leads
    unique_leads = pipeline.deduplicate_and_merge(all_raw)
    print(f"\n[+] Total Unified & Deduplicated Leads: {len(unique_leads)}\n")

    # Display clean table
    header = f"{'Company':<22} | {'Batch':<10} | {'Industry':<15} | {'Team':<6} | {'Hiring':<7} | {'Website'}"
    print(header)
    print("-" * len(header))
    for lead in unique_leads[:15]:
        comp = lead.name[:20]
        batch = (lead.batch or "N/A")[:10]
        ind = (lead.industry or "N/A")[:15]
        team = str(lead.team_size or "N/A")[:6]
        hiring = "Yes" if lead.is_hiring else "No"
        website = (lead.website or lead.yc_url or lead.waas_url or "")[:35]
        print(f"{comp:<22} | {batch:<10} | {ind:<15} | {team:<6} | {hiring:<7} | {website}")

    # Export
    res = export_leads(unique_leads, prefix="startup_leads_demo")
    print("\n" + "=" * 75)
    print(f" Saved {res['count']} leads to:")
    print(f"  - CSV:  {res['csv']}")
    print(f"  - JSON: {res['json']}")
    print("=" * 75)


if __name__ == "__main__":
    run_demo()
