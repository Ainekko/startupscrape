import json
from startupscrape.pipeline import StartupScrapePipeline
from startupscrape.exporters import export_leads

pipeline = StartupScrapePipeline()

print("=" * 80)
print(" 🚀 Finding 3 Early-Stage Prospects & Enriching with Browserbase + Gemini GTM")
print("=" * 80)

# Pull 3 leads, score one at a time to respect concurrency cap of 3
leads = pipeline.pull_early_stage_gtm_leads(
    limit=3,
    min_score=1,
    use_browserbase=True,
    use_linkedin=True,
    browserbase_workers=1    # serialize sessions — one at a time
)

print(f"\nSuccessfully evaluated {len(leads)} prospect(s):\n")

header = f"{'Company':<16} | {'Score':<5} | {'Stage':<8} | {'Best Contact':<22} | {'Key Signals'}"
print(header)
print("-" * 90)

for lead in leads:
    gtm = lead.gtm_analysis
    score = f"{gtm.score}/10" if gtm else "N/A"
    stage = (gtm.stage if gtm else (lead.batch or "Seed"))[:8]
    contact = (f"{gtm.best_contact_role}" if gtm else "Founder / CEO")[:22]
    signals = ("; ".join(gtm.key_signals[:2]) if gtm and gtm.key_signals else (lead.one_liner or ""))[:45]
    print(f"{lead.name[:15]:<16} | {score:<5} | {stage:<8} | {contact:<22} | {signals}")

print("\n" + "=" * 80)
print(" Detailed Prospect Profiles & GTM Angles:")
print("=" * 80)

for i, lead in enumerate(leads, 1):
    gtm = lead.gtm_analysis
    print(f"\n[{i}] {lead.name} (Score: {gtm.score}/10 | {gtm.stage})")
    print(f"    Website:      {lead.website or 'N/A'}")
    print(f"    LinkedIn:     {lead.linkedin_url or 'N/A'}")
    print(f"    Twitter:      {lead.twitter_url or 'N/A'}")
    print(f"    Target:       {gtm.best_contact_role} {f'({gtm.best_contact_name})' if gtm.best_contact_name else ''}")
    print("    Key Signals:")
    for sig in gtm.key_signals:
        print(f"      • {sig}")
    print(f"    Suggested Hook:  {gtm.suggested_angle}")
    print(f"    Draft Message:   \"{gtm.first_message}\"")

res = export_leads(leads, prefix="prospects_bb_3")
print(f"\nExported → CSV: {res['csv']}")
print(f"           JSON: {res['json']}")
