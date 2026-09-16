import os
import sys
import json

# Ensure startupscrape is on path
sys.path.insert(0, "/home/ainekko/creatorbook/startupscrape")

from startupscrape.pipeline import StartupScrapePipeline
from startupscrape.models import FilterQuery
from startupscrape.exporters import export_leads
from startupscrape.tracker import OutcomeTracker

print("=" * 80)
print(" 🚀 FLOWJOY GTM ENGINE: Pulling 3 Targeted Seed/Series A B2B Leads")
print("=" * 80)

pipeline = StartupScrapePipeline()
tracker = OutcomeTracker()

# Query high-fit early-stage B2B startups
query = FilterQuery(
    batches=["Winter 2025", "Summer 2024", "Winter 2024", "W25", "S24", "W24"],
    industries=["B2B"],
    is_hiring=True,
    team_size_min=5,
    team_size_max=50,
    limit=3
)

print("\n[1/3] Querying YC Directory for B2B early-stage startups hiring...")
raw_leads = pipeline.yc.scrape(query, max_results=3, enrich=True)
leads = pipeline.deduplicate_and_merge(raw_leads)

print(f"      -> Retrieved and enriched {len(leads)} target companies.")

print("\n[2/3] Scoring leads against FlowJoy GTM Engineering criteria...")
pipeline.score_leads(
    leads,
    use_browserbase=False,  # Bypassed because YC Inertia already gives complete founder & site intelligence!
    use_linkedin=False,
    selective_browser=True
)

# Sort by FlowJoy score descending
leads.sort(key=lambda l: (l.gtm_analysis.score if l.gtm_analysis else 0), reverse=True)

print("\n" + "=" * 80)
print(" 🎯 FlowJoy Targeted Prospect Intelligence (3 Leads)")
print("=" * 80)

header = f"{'Company':<16} | {'Score':<5} | {'Stage':<6} | {'Founder & Role':<24} | {'Has Email':<9} | {'Key Signals'}"
print(header)
print("-" * 95)

for lead in leads:
    gtm = lead.gtm_analysis
    score = f"{gtm.score}/10" if gtm else "N/A"
    stage = (gtm.stage if gtm else (lead.batch or "Seed"))[:6]
    
    founder_str = "N/A"
    has_email = "No"
    if lead.founders:
        f = lead.founders[0]
        founder_str = f"{f.name} ({f.title or 'Founder'})"[:24]
        has_email = "Yes" if f.has_email else "No"
    elif gtm and gtm.best_contact_name:
        founder_str = f"{gtm.best_contact_name} ({gtm.best_contact_role})"[:24]

    signals = ("; ".join(gtm.key_signals[:2]) if gtm and gtm.key_signals else (lead.one_liner or ""))[:35]
    print(f"{lead.name[:15]:<16} | {score:<5} | {stage:<6} | {founder_str:<24} | {has_email:<9} | {signals}")

print("\n" + "=" * 80)
print(" 📋 Comprehensive Founder Profiles & FlowJoy Value Angles")
print("=" * 80)

for i, lead in enumerate(leads, 1):
    gtm = lead.gtm_analysis
    print(f"\n[{i}] {lead.name} — Fit Score: {gtm.score}/10 ({gtm.stage})")
    print(f"    • Website:          {lead.website or 'N/A'}")
    print(f"    • Company LinkedIn: {lead.linkedin_url or 'N/A'}")
    print(f"    • One-Liner:        {lead.one_liner or 'N/A'}")
    print(f"    • Team Size:        {lead.team_size} members | Batch: {lead.batch}")
    print(f"    • Is Hiring:        {'Yes (' + str(lead.open_jobs_count) + ' open roles)' if lead.is_hiring else 'No'}")
    
    print("    • Founder Intelligence:")
    if lead.founders:
        for f in lead.founders:
            print(f"        - {f.name} | {f.title or 'Founder'}")
            print(f"          LinkedIn:  {f.linkedin_url or 'N/A'}")
            print(f"          Twitter:   {f.twitter_url or 'N/A'}")
            print(f"          Has Email: {'Yes (Verified)' if f.has_email else 'No'}")
            if f.bio:
                print(f"          Bio/Projects: {f.bio.strip()[:180]}...")
    else:
        print(f"        - Target: {gtm.best_contact_name or 'Founder'} ({gtm.best_contact_role})")

    print(f"    • Key FlowJoy Signals:")
    for sig in (gtm.key_signals if gtm else []):
        print(f"        ✓ {sig}")

    print(f"    • Suggested FlowJoy Angle:")
    print(f"        \"{gtm.suggested_angle}\"")
    print(f"    • Tailored Outreach Message:")
    print(f"        \"{gtm.first_message}\"")

    # Track in OutcomeTracker
    tracker.record_lead_sent(lead, notes="FlowJoy 3-lead test run")

print("\n[3/3] Exporting results to CSV and JSON...")
res = export_leads(leads, prefix="flowjoy_targeted_leads")
print(f"      ✓ Exported {res['count']} leads to:")
print(f"        CSV:  {res['csv']}")
print(f"        JSON: {res['json']}")
print(f"      ✓ Logged outreach records to {tracker.filepath}")
print("\nDone! Test execution complete.")
