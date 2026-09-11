# StartupScrape

A lightweight, robust lead generation engine for small businesses and agencies targeting startups across startup directories like **Y Combinator** and **Work at a Startup**.

Instead of fragile DOM web scraping that breaks or gets blocked, `startupscrape` interfaces directly with the underlying Algolia search APIs that power both YC and Work at a Startup, returning structured data in milliseconds.

## Features

- **Direct Algolia Integration**: High-speed, rate-limit friendly, structured JSON data.
- **URL Filter Parsing**: Paste search URLs directly from your browser with whatever filters you have selected (batches, industries, team size, hiring status, visa sponsorship, locations).
- **Multi-Directory Support**:
  - Y Combinator Directory (`ycombinator.com/companies`)
  - Work at a Startup (`workatastartup.com/companies`)
- **Lead Deduplication & Merging**: Companies appearing across both sources are automatically merged by normalized domain and company name.
- **Exporting**: Auto-exports to clean CSV and JSON files ready for CRM import (HubSpot, Apollo, Google Sheets).

## Installation

```bash
cd startupscrape
pip install -e .
# or uv:
uv sync
```

## Running the Demo

```bash
python3 demo.py
```

## CLI Usage

```bash
# Scrape YC directory URL
python3 -m startupscrape.cli --url "https://www.ycombinator.com/companies/?industry=B2B&isHiring=true" --limit 50

# Scrape Work at a Startup directory URL
python3 -m startupscrape.cli --url "https://www.workatastartup.com/companies?locations=DE&usVisaNotRequired=true" --limit 50
```
