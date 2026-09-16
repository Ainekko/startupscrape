# Architecture & System Design: StartupScrape

## 1. System Overview

`startupscrape` is an account intelligence and lead generation engine designed for B2B Go-To-Market (GTM) teams, agencies, and outbound operators targeting early-stage startups.

Traditional scraping tools break when frontend DOM structures change and consume excessive bandwidth with headless browsers. `startupscrape` avoids this by using direct API queries, lightweight HTTP payloads, heuristic pre-scoring, and selective cloud browser enrichment.

```
┌────────────────────────────────────────────────────────┐
│                   Data Sources                         │
│   Y Combinator Directory    Work at a Startup (WAAS)   │
└───────────────────┬───────────────────┬────────────────┘
                    │                   │
                    ▼                   ▼
┌────────────────────────────────────────────────────────┐
│                 Algolia Search Layer                   │
│   • Direct backend API queries                         │
│   • Millisecond response times, zero bot blocks        │
│   • Structured JSON (Batches, Roles, Headcount, URLs)  │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│             Deduplication & Field Merging              │
│   • Normalized domain & company name matching          │
│   • Merges multi-source jobs, socials, descriptions    │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│            Lightweight HTTP Enrichment                 │
│   • YC Inertia data-page extraction                    │
│   • Resolves website, LinkedIn URL, Twitter handle     │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│           Heuristic Signal & Gating Engine             │
│   • Detects GTM hiring (AE, Sales Lead, RevOps)        │
│   • Batch freshness & team size validation             │
│   • Computes pre-score (1-10)                          │
└───────────────┬────────────────────────┬───────────────┘
                │                        │
    Score < 7 OR Complete Data   Score >= 7 AND Missing Data
                │                        │
                ▼                        ▼
      [ Skip Browserbase ]     [ Selective Browserbase ]
                │                • Authenticated LinkedIn
                │                • People & contact mining
                │                • Dynamic site scrape
                └───────────┬────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│           Gemini 3.6 Flash Intelligence Layer          │
│   • Account readiness score (1-10)                     │
│   • Recommended target role & contact name             │
│   • Custom sales hook & personalized 1st message       │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│            CRM Exporters & Feedback Loop               │
│   • CSV & JSON Export (HubSpot, Apollo, Sheets)        │
│   • OutcomeTracker (open, reply, meeting conversion)   │
│   • Auto-calibration of scoring prompts                │
└────────────────────────────────────────────────────────┘
```

---

## 2. Component Reference

### 2.1 Algolia Search Clients (`scrapers/yc.py`, `scrapers/waas.py`)
- Interfaces with the Algolia indexes powering Y Combinator (`YCCompany_production`) and Work at a Startup (`Company_production`, `Job_production`).
- Features full query translation: translates frontend directory search URLs (including parameters like `batch`, `industry`, `team_size=[min,max]`, `isHiring`, `hasSalary`, `hasEquity`, `usVisaNotRequired`) directly into Algolia `facetFilters` and `numericFilters`.

### 2.2 YC Enrichment (`enrichers.py`)
- Employs Inertia.js JSON parsing. YC renders application state inside `<div id="app" data-page="...">`.
- The enricher pulls this state in a single standard HTTP `GET` request, cleanly extracting verified company website URLs, social profiles, and company summaries without spinning up Chromium.
- Includes regex fallback for non-Inertia legacy pages.

### 2.3 Signal Detection & Gating (`signals.py`)
- Inspects job postings and descriptions for high-intent GTM hiring signals:
  - Founding Account Executive
  - Head of Sales / VP Sales
  - RevOps / Revenue Operations
  - Outbound SDR / BDR
- Evaluates operational fit (team size 5–50, recent 2024–2026 batches).
- Evaluates `should_enrich_with_browser` to gate expensive browser sessions.

### 2.4 Browserbase Cloud Integration (`browserbase_client.py`, `linkedin_scraper.py`)
- Uses Browserbase CDP / Playwright infrastructure.
- Features persistent authenticated contexts: logs into LinkedIn once (`setup_linkedin_context.py`) and saves the session context ID in `.env` (`BROWSERBASE_LINKEDIN_CONTEXT_ID`).
- Subsequent runs reuse session auth cookies across headless instances without triggering SMS/email 2FA checkpoints.

### 2.5 Intelligence Engine (`gtm_scorer.py`)
- Leverages Google Gemini 3.6 Flash with structured JSON output schemas.
- Takes all lead metadata, open job titles, founder profiles, and scraped site text to evaluate GTM scalability bottlenecks and generate personalized outreach messages.

### 2.6 Outcome Tracker (`tracker.py`)
- Persists outreach outcomes to `data/outreach_outcomes.jsonl`.
- Aggregates reply rates and meeting conversion rates by signal and score bucket to enable continuous calibration.
