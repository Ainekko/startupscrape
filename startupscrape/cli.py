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
        help="Directory URL to scrape (e.g. from ycombinator.com or workatastartup.com with query filters)",
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

    args = parser.parse_args()

    if not args.urls:
        print("Please provide at least one directory URL with --url or -u")
        sys.exit(1)

    print(f"Starting scrape for {len(args.urls)} target URL(s)...")
    pipeline = StartupScrapePipeline()
    leads = pipeline.scrape_from_urls(args.urls, max_per_source=args.limit)

    print(f"Successfully scraped {len(leads)} unique startup lead(s)!")
    res = export_leads(leads, prefix=args.output)
    print(f"Saved CSV:  {res['csv']}")
    print(f"Saved JSON: {res['json']}")


if __name__ == "__main__":
    main()
