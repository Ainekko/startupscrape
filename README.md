# StartupScrape — FlowJoy Signal-First Lead Finder

> **A high-speed, signal-driven lead finder that combines direct Algolia directory search, lightweight founder intelligence, jev/heuristic ICP scoring, and treg email enrichment for B2B Go-To-Market teams.**

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![ICP: Seed--Series A B2B](https://img.shields.io/badge/ICP-Seed%20to%20Series%20A%20B2B-purple.svg)]()
[![Enrichment: treg.to](https://img.shields.io/badge/Enrichment-treg.to-emerald.svg)]()
[![Scoring: jev](https://img.shields.io/badge/Scoring-typesafe--ai%2Fjev-orange.svg)]()

---

## 📖 Executive Summary

Finding and qualifying early-stage B2B startups for high-ticket GTM services (e.g. GTM engineering studios, RevOps architecture, automated outbound) requires fresh signals and direct founder reachability without burning money on slow headless browsers.

**StartupScrape solves this with a 4-Tier Waterfall**:
1. **Tier 0 (Algolia Backend Query)**: Queries Y Combinator and Work at a Startup directory backends directly in <500ms with zero bot detection or browser overhead.
2. **Enrichment (Lightweight HTTP Extraction)**: Extracts company website, company LinkedIn URL, open job titles, and founder profiles (names, titles, bios, personal LinkedIn URLs) in a single fast HTTP GET request.
3. **Tier 1 & 3 (jev / Calibrated Heuristic Scoring)**: Evaluates accounts against a 24-point fit rubric (Seed/Series A stage, no GTM engineer in headcount, B2B SaaS focus, tech founder pedigree) via **jev** on Vercel AI Gateway with a local heuristic fallback.
4. **Tier 2 (treg Verified Email Discovery)**: Cascades across 89 providers via **treg** (`treg.people.email.find`) to find verified founder emails (~$0.005 per verified hit; misses are free).
5. **Browse Dashboard**: Dark-mode web interface (`localhost:5001`) with real-time status polling, funnel analytics, and interactive contact inspector.

---

## 🏗️ System Architecture

```
┌────────────────────────────────────────────────────────┐
│                   Target Directories                   │
│   Y Combinator Directory    Work at a Startup (WAAS)   │
└───────────────────┬───────────────────┬────────────────┘
                    │                   │
                    ▼                   ▼
┌────────────────────────────────────────────────────────┐
│       Tier 0: Direct Algolia Backend Search API        │
│   • Sub-second response times, zero bot blocks         │
│   • Auto-refreshing keys (self-healing on 403)         │
│   • Structured filters: recent batches, tags, size     │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│         Inertia HTML Enrichment (Lightweight HTTP)     │
│   • Company website & company LinkedIn profile         │
│   • Open job postings & engineering role scan          │
│   • Complete founder profiles & personal LinkedIn URLs │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│        Tier 1: Fast ICP Scoring (jev / Heuristics)     │
│   • Seed / Series A funding stage verification         │
│   • Detects absence of GTM engineer / Head of Sales    │
│   • Verifies B2B model; filters out consumer           │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│        Tier 2: treg Email Find (`treg.people.email`)   │
│   • Threaded cascading email search across providers   │
│   • ~$0.005 per verified hit, misses cost $0           │
│   • Per-call ($0.05) and run-level budget enforcement  │
│   • Checkpoints saved every 10 leads                   │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│         Tier 3: Final Scoring & Ranking (0–24 pts)     │
│   • Re-scores with contact reachability state          │
│   • Saves run results to `data/run_<ts>.json`          │
│   • Browse live at http://localhost:5001               │
└────────────────────────────────────────────────────────┘
```

---

## 🎯 Scoring Rubric (0–24 Pts)

Evaluated via **`pipeline/scorer.py`** using **jev** (or calibrated local heuristics):

| Signal | Points | Detection / Source |
|---|---|---|
| **Seed or Series A Stage** | **10** | YC/WAAS cohorts from 2023–2027 (`Winter 2023` to `Summer 2027`) |
| **No GTM Engineer / Head of Sales** | **5** | Absence of sales leadership in headcount & job postings |
| **B2B SaaS / DevTools** | **5** | Algolia tags, industry, and description |
| **Verified Founder Email** | **+2** | `treg.people.email.find` |
| **Optimal Team Size (5–50)** | **+1** | Algolia directory metadata |
| **Technical Founder** | **+1** | Founder bios (ex-FAANG, PhD, CTO) |
| **Eng Hiring without Sales Hiring** | **+1** | Open role titles |

---

## ⚡ Quickstart

### 1. Environment Setup

Configure `.env` in the project root:

```env
# treg — tool catalog token (https://treg.to)
TREG_TOKEN=eyJ1aW...
TREG_PER_CALL_CAP_USD=0.05
TREG_MAX_RUN_COST_USD=1.50

# Optional: Vercel AI Gateway key for live jev scoring (falls back to calibrated heuristics if absent)
AI_GATEWAY_API_KEY=vck_...
```

### 2. Run from the Web Dashboard

Start the Flask browse dashboard:

```bash
python3 web/app.py
```
Open **http://localhost:5001** and click **Run Pipeline**.

### 3. Run from CLI

Execute a targeted run directly:

```bash
python3 -c "from pipeline.runner import run; r = run(max_leads=10); print(r['funnel'])"
```

---

## 📦 Project Structure

```
startupscrape/
├── pipeline/
│   ├── runner.py               # 4-tier pipeline orchestrator
│   ├── scorer.py               # jev scoring wrapper & heuristic fallback
│   └── enricher.py             # treg email discovery cascade
├── web/
│   ├── app.py                  # Flask browse dashboard (port 5001)
│   └── templates/
│       └── index.html          # Dark-mode dashboard UI with funnel & inspector
├── startupscrape/
│   ├── scrapers/
│   │   ├── yc.py               # Y Combinator Algolia client with auto-refresh
│   │   └── waas.py             # Work at a Startup Algolia client
│   ├── enrichers.py            # YC HTML Inertia parser for founder intelligence
│   ├── signals.py              # Heuristic signal detector & title analyzer
│   ├── models.py               # Pydantic models (StartupLead, Founder, JobPosting)
│   └── config.py               # Central configuration & credentials
├── docs/                       # System Documentation & Wikis
│   ├── ARCHITECTURE.md         # System design, Algolia integration & data flow
│   ├── FLOWJOY_WIKI.md         # FlowJoy positioning, ICP & outreach angles
│   ├── SIGNAL_PLAYBOOK.md      # Signal taxonomy, trigger keywords & score matrix
│   ├── SCORING.md              # jev question specification & rubric
│   └── TREG.md                 # treg endpoints, pricing model & error codes
├── data/                       # Run output JSON files (e.g. run_<ts>.json)
└── pyproject.toml              # Package dependencies
```

---

## 📚 Knowledge Base & Wikis

- **[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)**: System design, Algolia backend mechanics, and pipeline lifecycle.
- **[`docs/FLOWJOY_WIKI.md`](docs/FLOWJOY_WIKI.md)**: FlowJoy GTM Engineering Studio positioning, ICP matrix, and outreach angles.
- **[`docs/SIGNAL_PLAYBOOK.md`](docs/SIGNAL_PLAYBOOK.md)**: Growth & hiring signals, detection logic, and value propositions.
- **[`docs/SCORING.md`](docs/SCORING.md)**: Complete jev question shapes and rubric evaluation rules.
- **[`docs/TREG.md`](docs/TREG.md)**: treg tool catalog integration and cost model.

---

## 📄 License
MIT License. Built for modern B2B GTM teams and outbound engineering studios.
