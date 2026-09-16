# StartupScrape: Optimization & Architecture Plan

## 1. Current State Evaluation

### Architecture Overview
The current repository is a lead generation and account intelligence engine targeting startup directories (Y Combinator & Work at a Startup) for B2B Go-To-Market (GTM) teams:
- **Scraping Layer (`scrapers/yc.py`, `scrapers/waas.py`)**: Interacts directly with Algolia backend search APIs via public API keys. Fast (<500ms), resilient to DOM changes, and provides rich initial metadata without headless browsers.
- **Enrichment Layer (`enrichers.py`)**: Parses YC company pages using lightweight HTTP `requests` and extracts website, company LinkedIn, and Twitter from embedded Inertia `data-page` JSON, with regex fallbacks.
- **Browser Automation Layer (`browserbase_client.py`, `linkedin_scraper.py`)**: Manages remote cloud browser sessions via Browserbase (CDP/Playwright). `linkedin_scraper.py` uses a persistent authenticated session (`setup_linkedin_context.py`) to scrape company pages and employee profiles (`/people/`).
- **Intelligence Layer (`gtm_scorer.py`)**: Sends aggregated account context (founders, jobs, descriptions, scraped site text) to Gemini 3.6 Flash to output an urgency score (1-10), stage, key signals, suggested angle, and draft message.
- **Pipeline & Deduplication (`pipeline.py`, `exporters.py`)**: Merges records across sources based on domain and company name normalization, exporting to CSV/JSON.

---

### Critical Bottlenecks & Weaknesses

1. **Unconstrained Browser Usage (Cost & Speed Bottleneck)**:
   - In `run_prospects.py` and `pipeline.py`, Browserbase and LinkedIn scrapers run indiscriminately across all leads (`use_browserbase=True, use_linkedin=True`).
   - Browserbase sessions take 15–35 seconds each and consume cloud browser minutes.
   - For early-stage startups where Algolia and the YC Inertia payload already provide the website, founders, and job listings, firing a headless browser is redundant.
   - Running LinkedIn automation on every lead puts the user's LinkedIn account at high risk of bot detection, captchas, and auth invalidation.

2. **Absence of Signal Prioritization & Gating**:
   - Scraping and AI scoring happen in an unoptimized sequence. All scraped leads are treated equally, regardless of whether they have a founding GTM role open or are a 1-person pre-product company.
   - There is no preliminary signal filter to rank leads *before* spending heavy resources.

3. **Zero Test Coverage**:
   - There are currently no automated unit or integration tests in the repository (`tests/` directory does not exist).
   - Core functions like Algolia query building, URL filter parsing, deduplication merging, and Inertia JSON extraction are unverified by automated suites.

4. **No Closed-Loop / Self-Improving Feedback System**:
   - There is no tracking mechanism for outreach outcomes (sent, opened, replied, meeting booked, disqualified).
   - The system cannot calibrate its scoring weights or learn which signals correlate with actual conversions.

5. **Lack of Internal Knowledge Base / Wikis**:
   - The repository only has a basic README. Operational knowledge regarding LinkedIn cookie persistence, Browserbase session concurrency, signal taxonomy, and ICP criteria is undocumented.

---

## 2. System Architecture: Tiered Enrichment & Feedback Loop

```
[ Tier 0: Algolia Directory Scrape (YC + WAAS) ]
                    │
                    ▼
[ Tier 1: Lightweight HTTP Enrichment (YC Inertia JSON / Direct Requests) ]
                    │
                    ▼
[ Tier 2: Heuristic Signal Detection & ICP Pre-Scoring ]
                    │
     ┌──────────────┴──────────────┐
     │                             │
Score < Threshold             Score >= Threshold (High-Value Lead)
(Low/Medium Fit)              AND Missing Critical Data (Founder/People/Context)
     │                             │
     ▼                             ▼
Skip Browser                  [ Tier 3: Selective Browserbase / LinkedIn Scrape ]
     │                             │
     └──────────────┬──────────────┘
                    ▼
[ Gemini GTM Analysis & Pitch Generation ]
                    │
                    ▼
[ CRM Export / Lead Delivery ]
                    │
                    ▼
[ Outcome Tracker & Self-Improving Calibration Loop ]
```

---

## 3. Implementation Roadmap

- **Step 1: Test Suite (`tests/`)**:
  - `test_models.py`
  - `test_pipeline.py`
  - `test_scrapers.py`
  - `test_enrichers.py`
  - `test_signals_and_gating.py`
  - `test_tracker.py`
  - `test_exporters.py`
- **Step 2: Signal Detection & Selective Browser Gating (`startupscrape/signals.py`, `pipeline.py`)**:
  - Heuristic signal scoring and `should_enrich_with_browser` gating.
  - Smart gating integration into `StartupScrapePipeline`.
- **Step 3: Outcome Tracking & Self-Improving Loop (`startupscrape/tracker.py`)**:
  - Outcome recording, signal performance aggregation, conversion calibration.
- **Step 4: Knowledge Base & Wikis (`docs/`)**:
  - `docs/ARCHITECTURE.md`
  - `docs/SIGNAL_PLAYBOOK.md`
  - `docs/BROWSER_STRATEGY.md`
  - `docs/SELF_IMPROVING_LOOP.md`
