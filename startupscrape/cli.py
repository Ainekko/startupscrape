import argparse
import sys
from .pipeline import StartupScrapePipeline
from .exporters import export_leads


def main():
    parser = argparse.ArgumentParser(
        description="StartupScrape - GTM Lead Generation Engine & Account Scorer"
    )
    parser.add_argument(
        "--url",
        "-u",
        action="append",
        dest="urls",
        help="Directory URL or company page URL (e.g. https://www.ycombinator.com/companies/oklo)",
    )
    parser.add_argument(
        "--early-stage",
        action="store_true",
        help="Automatically pull early-stage (Seed / Series A) companies actively hiring",
    )
    parser.add_argument(
        "--limit",
        "-l",
        type=int,
        default=10,
        help="Maximum results to return (default: 10)",
    )
    parser.add_argument(
        "--gtm",
        action="store_true",
        help="Run AI GTM scoring, signal extraction, and personalized outreach generation",
    )
    parser.add_argument(
        "--browserbase",
        action="store_true",
        help="Use Browserbase remote cloud browser for stealth scraping",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default="gtm_leads",
        help="Output file prefix (default: gtm_leads)",
    )

    args = parser.parse_args()

    pipeline = StartupScrapePipeline()

    if args.early_stage:
        print(f"Targeting early-stage (Seed/Series A) startups with hiring signals (Limit: {args.limit})...")
        leads = pipeline.pull_early_stage_gtm_leads(
            limit=args.limit,
            use_browserbase=args.browserbase
        )
    elif args.urls:
        print(f"Scraping {len(args.urls)} target URL(s)...")
        leads = pipeline.scrape_from_urls(
            args.urls,
            max_per_source=args.limit,
            enrich=True,
            score_gtm=args.gtm
        )
    else:
        print("Please provide target URLs with --url or use --early-stage")
        sys.exit(1)

    print(f"\nSuccessfully processed {len(leads)} lead(s)!\n")

    # Display Clean Output Table
    header = f"{'Company':<18} | {'Score':<5} | {'Stage':<8} | {'Best Contact':<22} | {'Key Signal'}"
    print(header)
    print("-" * 95)

    for lead in leads:
        gtm = lead.gtm_analysis
        score = str(gtm.score) if gtm else "N/A"
        stage = (gtm.stage if gtm else lead.batch or "Early")[:8]
        contact = (f"{gtm.best_contact_role}" if gtm else "Founder")[:22]
        signal = (gtm.key_signals[0] if gtm and gtm.key_signals else (lead.one_liner or ""))[:38]
        print(f"{lead.name[:18]:<18} | {score:<5} | {stage:<8} | {contact:<22} | {signal}")

    res = export_leads(leads, prefix=args.output)
    print(f"\nSaved CSV:  {res['csv']}")
    print(f"Saved JSON: {res['json']}")


if __name__ == "__main__":
    main()
