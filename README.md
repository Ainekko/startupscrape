# StartupScrape

StartupScrape is a startup sourcing and lead-enrichment pipeline for GTM teams, agencies, and outbound operators who want a fast way to find high-fit early-stage companies and the people behind them.

This repo is built to answer a simple question: which startups are worth reaching out to right now, and why?

It combines:
- direct startup-directory discovery from Y Combinator and Work at a Startup
- lightweight enrichment of company and founder metadata
- heuristic or AI-assisted scoring for GTM fit
- optional founder email lookup via treg
- exportable lead artifacts for outreach, case studies, and dashboard review

---

## What this project is for

This project is not a generic web scraper. It is a focused prospecting engine for early-stage B2B startups with a GTM problem.

Typical use cases:
- find Seed and Series A startups that are hiring but still under-optimized in GTM
- identify technical founders and signals that indicate a need for a GTM engineering or RevOps engagement
- generate a ranked list of outreach targets with company, founder, and message context
- turn those results into case-study-style narratives or sales narratives for a studio or agency

The core idea is to convert startup-directory data into a structured, scored opportunity list.

---

## The high-level workflow

1. Source startup records from directory backends
   - Y Combinator companies
   - Work at a Startup
   - filtered by stage, hiring, team size, and industry relevance

2. Enrich the records
   - company website
   - LinkedIn URL
   - founder names, titles, bios, and LinkedIn profiles
   - hiring and job-posting signals

3. Score for fit
   - early-stage startup signal
   - B2B SaaS relevance
   - absence of GTM headcount
   - technical founder signals
   - founder email reachability and relevance

4. Contact-enrich and export
   - verified founder emails where available
   - CSV and JSON exports for downstream tools
   - dashboard summaries for manual review

5. Build the narrative
   - explain why the startup is attractive
   - summarize team context and problem to solve
   - produce a case-study or outreach report from the scored data

---

## What a “case study” means in this repo

A case study here is usually a short, evidence-backed prospect brief built from one or more scored startup records.

Typical case-study structure:
- company overview and stage
- why this startup is a fit for GTM or outbound work
- hiring and team-signal evidence
- founder background and likely decision-maker
- suggested angle or problem statement
- exportable lead data for follow-up

This is the practical output of the pipeline: not just raw data, but a usable narrative from real startup metadata.

---

## Repository layout

```text
.
├── README.md                  # Project overview and agent handoff guide
├── demo.py                    # Basic startup-directory demo
├── run_prospects.py           # Browser-based prospecting run example
├── run_flowjoy_test.py        # Example FlowJoy-style targeted lead generation
├── pyproject.toml             # Python project config
├── data/                      # Generated JSON/CSV artifacts from runs
├── docs/                      # Architecture, scoring, sourcing, and strategy docs
├── startupscrape/             # Main package for scraping, scoring, and models
│   ├── cli.py                 # Command-line entry point
│   ├── config.py             # Config and environment settings
│   ├── exporters.py          # CSV/JSON export logic
│   ├── models.py             # Core Pydantic models
│   ├── pipeline.py           # Run orchestration and pipeline logic
│   ├── tracker.py            # Lead/outcome tracking
│   ├── enrichers.py         # Founder/company enrichment logic
│   ├── signals.py           # Signal extraction and heuristic rules
│   ├── scrapers/            # YC / Work at a Startup scraper clients
│   └── ...
├── pipeline/                  # Pipeline runner, scorer, and enrichment modules
├── web/                      # Flask dashboard and templates
├── backend/                  # Backend app for serving and storing run results
├── tests/                    # Automated tests for pipeline behavior
└── docs/                     # Additional project design docs
```

---

## Core parts of the system

### Source discovery
The repo queries startup directories directly instead of depending on slow browser automation where possible. This keeps runs faster and more reliable.

Relevant code:
- `startupscrape/scrapers/`
- `startupscrape/pipeline.py`
- `demo.py`

### Enrichment and scoring
Once a company is found, the system extracts founder and company signals, then scores the account for GTM fit based on stage, hiring, founder quality, and business relevance.

Relevant code:
- `pipeline/scorer.py`
- `startupscrape/signals.py`
- `startupscrape/enrichers.py`

### Contact discovery
If the repo is configured with a treg token, it can try to find founder emails and related contact reachability signals.

Relevant code:
- `pipeline/enricher.py`
- `startupscrape/tracker.py`

### Output
Saved run artifacts land in `data/` and are suitable for downstream analysis, outreach, or case-study generation.

Relevant code:
- `startupscrape/exporters.py`
- `web/app.py`

---

## Quick-start commands

### Basic demo
```bash
python demo.py
```
This runs a lightweight example that pulls a few startups and exports them.

### FlowJoy-style targeted run
```bash
python run_flowjoy_test.py
```
This is closer to a “case-study generation” workflow: it pulls highly relevant early-stage B2B leads, scores them, and prints founder and signal context.

### CLI pipeline run
```bash
python -m startupscrape.cli --early-stage --limit 10 --gtm
```
This is the direct command-line entry point for a scored lead list.

### Dashboard
```bash
python web/app.py
```
Then open:
- http://localhost:5001

---

## Typical output artifacts

Runs write data into the `data/` directory as JSON and CSV files. These are the raw material for:
- outreach lists
- ranked prospect tables
- founder data review
- case study summaries and narrative generation

Look for files like:
- `data/flowjoy_targeted_leads_*.csv`
- `data/flowjoy_targeted_leads_*.json`
- `data/prospects_*.json`
- `data/run_*.json`

---

## What makes this useful for agents

An agent can use this repo to do the following:
- identify promising startup targets from public directory data
- rank them by GTM fit with a consistent scoring model
- inspect founder and team metadata to support a narrative
- generate a case study or outreach brief from a list of scored leads
- export clean results for later analysis or human follow-up

The repo is most useful when treated as a pipeline for “target discovery + signal extraction + ranking + narrative generation,” not just scraping.

---

## Good starting questions to ask this repo

- Which startups are early-stage, B2B, and hiring right now?
- Which founders look like the right decision-maker for a GTM service engagement?
- Which companies have the strongest evidence of a GTM bottleneck?
- Which leads should be exported into a case study or outreach brief?

These are the questions the pipeline was designed to support.

---

## Project references

Further context is in the docs folder:
- `docs/ARCHITECTURE.md`
- `docs/PLAN.md`
- `docs/SCORING.md`
- `docs/SIGNAL_PLAYBOOK.md`
- `docs/FLOWJOY_WIKI.md`
- `docs/TREG.md`

These documents explain scoring logic, sourcing strategy, and the business use cases behind the project.

---

## Bottom line

StartupScrape turns startup directories into a structured, scored, and exportable market map of early-stage SaaS companies. It is designed to help an agent or operator quickly understand which startups are worth pursuing and why, and to turn those findings into actionable case studies or outreach flows.
