import argparse
import sys
from .pipeline import StartupScrapePipeline
from .exporters import export_leads


def main():
    parser = argparse.ArgumentParser(
        description="StartupScrape - Scrape startup leads from Y Combinator & Work at a Startup"
    )
    parser.add_argument(
        "--url",
        "-u",
        action="append",
        dest="urls",
        help="Directory URL or company page URL (e.g. https://www.ycombinator.com/companies/oklo)",
    )
    parser.add_argument(
        "--limit",
        "-l",
        type=int,
        default=25,
        help="Maximum results to return per source (default: 25)",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default="startup_leads",
        help="Output file prefix (default: startup_leads)",
    )
    parser.add_argument(
        "--no-enrich",
        action="store_true",
        help="Disable automatic enrichment with website, LinkedIn, and Twitter",
    )

    args = parser.parse_args()

    if not args.urls:
        print("Please provide at least one target URL with --url or -u")
        sys.exit(1)

    enrich = not args.no_enrich
    print(f"Starting scrape for {len(args.urls)} target URL(s) (Enrichment: {'ON' if enrich else 'OFF'})...")
    pipeline = StartupScrapePipeline()
    leads = pipeline.scrape_from_urls(args.urls, max_per_source=args.limit, enrich=enrich)

    print(f"Successfully scraped {len(leads)} unique startup lead(s)!")
    for lead in leads:
        print(f"  - {lead.name} | Website: {lead.website} | LinkedIn: {lead.linkedin_url} | Twitter: {lead.twitter_url}")

    res = export_leads(leads, prefix=args.output)
    print(f"Saved CSV:  {res['csv']}")
    print(f"Saved JSON: {res['json']}")


if __name__ == "__main__":
    main()
