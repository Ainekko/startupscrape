# Architecture & System Design: StartupScrape

## 1. System Overview

`startupscrape` is a high-speed, signal-first lead generation and account intelligence engine designed for B2B Go-To-Market (GTM) teams, agencies, and outbound studios targeting early-stage startups.

### Core Pipeline Architecture:

```
┌─────────────────────────────────────────────────────────────┐
│                    Target Directories                       │
│    Y Combinator Directory     Work at a Startup (WAAS)      │
└──────────────────────┬──────────────────────┬───────────────┘
                       │                      │
                       ▼                      ▼
┌─────────────────────────────────────────────────────────────┐
│          Tier 0: Direct Algolia Backend Search API          │
│   • Direct backend search queries (no slow browser rendering)│
│   • Sub-second latency, zero bot blocks or rate limits       │
│   • Structured filtering: recent batches, tags, headcount    │
│   • Self-healing credentials (auto-refreshes keys on 403)    │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│           Lightweight YC HTML / Inertia Enrichment          │
│   • Single raw HTTP GET per company page                    │
│   • Extracts clean company domain and company LinkedIn URL  │
│   • Extracts full founder profiles: names, titles, bios,    │
│     personal LinkedIn URLs, and Twitter handles             │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│          Tier 1: Fast ICP Scoring (jev / Heuristics)        │
│   • Evaluates B2B model, funding stage, and GTM hiring status│
│   • Runs via Vercel AI Gateway (`typesafe-ai/jev`)          │
│   • Calibrated deterministic heuristic fallback             │
│   • Filters out low-fit accounts with zero token cost       │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│        Tier 2: treg Email Discovery (`treg.people.email.find`)│
│   • Cascades cheapest-first to find verified founder emails │
│   • ~$0.005 per verified email hit; misses cost nothing     │
│   • Enforces strict per-call ($0.05) and run-level caps     │
│   • Checkpoint saves after every batch of 10                │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│               Tier 3: Final Scoring & Ranking               │
│   • Final composite score (0–24 pts) with contact state     │
│   • Writes clean JSON run artifact to `data/run_<ts>.json`  │
│   • Served live via Flask browse dashboard (`localhost:5001`)│
└─────────────────────────────────────────────────────────────┘
```

---

## 2. Component Reference

### 2.1 Algolia Search Clients (`scrapers/yc.py`, `scrapers/waas.py`)
- **What Algolia does**: Algolia is the hosted search engine powering `ycombinator.com/companies` and `workatastartup.com/companies`.
- Rather than driving headless browsers through dynamic JavaScript web pages, our clients query Algolia's REST endpoints directly.
- Translates query parameters (batches, industries, team size bounds, hiring status) directly into Algolia `facetFilters` and `numericFilters`.
- Includes automatic key discovery: if an Algolia API key expires, it extracts `window.AlgoliaOpts` from the live site and re-authenticates automatically.

### 2.2 YC Enrichment (`enrichers.py`)
- Parses Inertia.js application state embedded in `<div id="app" data-page="...">`.
- Extracts company website, company LinkedIn URL, open job titles, and complete founder intelligence (name, title, bio, personal LinkedIn URL).
- Operates via raw HTTP requests in under 200ms per company without cloud browser overhead.

### 2.3 Evaluation & Scoring Engine (`pipeline/scorer.py`)
- Public function: `judge(state, questions) -> dict`.
- **jev Integration**: Calls `https://ai-gateway.vercel.sh/v4/ai/evaluation-model` with `ai-model-id: typesafe-ai/jev`.
  - Question types: `boolean` (instructions), `choice` (instructions + criteria record), `score` (instructions + ordered rubric array).
- **Calibrated Heuristic Fallback**: Evaluates the identical rubric deterministically from state metadata when `AI_GATEWAY_API_KEY` is absent or unverified, ensuring zero downtime, zero token rate limits, and instantaneous scoring.

### 2.4 treg Contact Enrichment (`pipeline/enricher.py`)
- Integrates `treg.people.email.find` via `https://treg.to/call/`.
- Authenticates using team token via `X-Treg-Token`.
- Enforces cost limits via `X-Treg-Route-Max-Cost` header ($0.05/call ceiling).
- Saves incremental checkpoint JSON files every 10 leads so no work is lost on network interruption.

### 2.5 Pipeline Orchestrator (`pipeline/runner.py`)
- Unified 4-tier pipeline runner:
  - Scrapes target directories (`_scrape`)
  - Applies fast pre-filters (`_prefilter`)
  - Enriches YC company metadata (`YCEnricher`)
  - Fast-scores leads (`_tier1_score`)
  - Enriches verified founder emails (`enrich_batch`)
  - Computes final rankings and writes results (`_tier3_score`)

### 2.6 Browse Dashboard (`web/app.py`, `web/templates/index.html`)
- Dark-mode responsive web interface running on port 5001.
- Features real-time run triggering, status polling, funnel analytics, lead cards with score badges, and interactive lead inspector.
