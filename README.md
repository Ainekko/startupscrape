# StartupScrape — Autonomous Account Intelligence & GTM Outbound Engine

> **A high-speed, signal-driven lead generation engine that combines direct Algolia search, deep Inertia founder intelligence, selective cloud browser automation, and closed-loop AI qualification for B2B Go-To-Market teams.**

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Target: Seed--Series A](https://img.shields.io/badge/ICP-Seed%20to%20Series%20A%20B2B-purple.svg)]()
[![Intelligence: Gemini 3.6 Flash](https://img.shields.io/badge/AI-Gemini%203.6%20Flash-orange.svg)]()

---

## 📖 Executive Summary & Case Study Context

Targeting early-stage startups for high-ticket B2B services (e.g., GTM engineering, outbound automation, RevOps scaffolding) is plagued by three fundamental inefficiencies:
1. **Fragile DOM Web Scraping**: Traditional web scrapers break on every CSS update, get rate-limited, and return incomplete snippets.
2. **Wasteful Headless Browser Execution**: Spinning up full headless Chromium browsers on every lead burns cloud browser minutes, takes 30+ seconds per account, and risks bot-detection or session loss on platforms like LinkedIn.
3. **Shallow, Actionless Leads**: Standard scraping tools output disconnected company names and generic info@ emails without personal founder profiles, past career achievements, hiring signals, or actionable value angles.

**StartupScrape solves this with a 4-Tier Architecture**:
- **Tier 0 (Algolia Direct Query)**: Queries backend search APIs directly in <500ms with zero bot detection.
- **Tier 1 (Lightweight Inertia Extraction)**: Extracts verified websites, company socials, open roles, and full founder profiles (personal LinkedIn URLs, bios, past projects, and verified email status) via raw HTTP without browsers.
- **Tier 2 (Heuristic Signal & ICP Gating)**: Deterministically scores accounts (1–10) based on stage, hiring triggers, and data completeness.
- **Tier 3 (Selective Browserbase / LinkedIn)**: Fires cloud browser sessions **only** for high-value targets ($\ge 7/10$) missing critical intelligence.
- **Tier 4 (Gemini GTM Intelligence & Pitch Generation)**: Uses Gemini to synthesize founder backgrounds and open roles into tailored value hooks and personalized first messages.
- **Self-Improving Feedback Loop**: Logs outreach outcomes (sent, opened, replied, meeting booked) into a ledger to continuously calibrate signal weights and prompt strategies.

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
│   • Structured filters: batch, industry, team size     │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│         Tier 1: Deep Inertia JSON Enrichment           │
│   • Company Website, LinkedIn, Twitter, GitHub         │
│   • Open Job Postings & Role Types                     │
│   • Complete Founder Profiles:                         │
│     - Personal LinkedIn & Twitter URLs                 │
│     - Founder Bio, Past Projects, University           │
│     - Verified Email Availability Flag (`has_email`)   │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│     Tier 2: Heuristic Signal Detection & Gating        │
│   • Hiring signals: Founding AE, Head of Sales, RevOps │
│   • Stage & size fit: Seed-Series A, 5-50 members      │
│   • Data completeness evaluation                       │
└───────────────┬────────────────────────┬───────────────┘
                │                        │
    Score < 7 OR Complete Data   Score >= 7 AND Missing Data
                │                        │
                ▼                        ▼
      [ Skip Browserbase ]     [ Tier 3: Selective Browserbase ]
       (Save $$$ & avoid         • Authenticated LinkedIn session
        rate limits)             • Deep people & contact search
                │                • Dynamic JavaScript site dump
                └───────────┬────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│        Tier 4: Gemini 3.6 Flash Intelligence           │
│   • FlowJoy GTM Engineering Fit Score (1-10)           │
│   • Identifies Best Contact (Name, Title, LinkedIn)    │
│   • Customized FlowJoy Value Hook                      │
│   • 2-3 sentence personalized outreach draft           │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│         CRM Delivery & Self-Improving Loop             │
│   • Flattened CSV & nested JSON exports                │
│   • OutcomeTracker ledger (reply rate, meeting rate)   │
│   • Real-time signal conversion calibration            │
└────────────────────────────────────────────────────────┘
```

---

## 🚀 Case Study in Production: FlowJoy GTM Engineering Studio

In this implementation, `startupscrape` is configured as the outbound prospecting engine for **FlowJoy** ([flowjoy.online](https://flowjoy.online)), a GTM Engineering Studio building custom revenue systems, data pipelines (Clay, Apollo, HubSpot), and autonomous outbound agents for Seed to Series A B2B startups.

### Core Value Positioning:
- *"Your GTM stack is powerful (Apollo, Clay, HubSpot). Your workflow isn't."*
- Core devs are swamped with product development and cannot build internal CRM syncs or scrapers.
- Hiring a full-time GTM Engineer costs **$180,000+/year**.
- FlowJoy ships production revenue systems directly to the client's GitHub repository in **2–4 weeks**.

### Verified Case Study Results:

Here is an actual sample run targeting early-stage B2B startups with complete founder intelligence:

| Company | Fit Score | Target Contact | Founder LinkedIn | Email | Projects & Background | FlowJoy Value Hook & Personalized Pitch |
| :--- | :---: | :--- | :--- | :---: | :--- | :--- |
| **[SAMMY Labs](https://www.sammylabs.com)** | **10/10** | Joe Savidge *(Founder/CEO)* | [LinkedIn](https://www.linkedin.com/in/josephsavidge) | **Yes** | Ex-Palantir pod lead, repeated founder. Building computational law for AI agents. | *"Instead of pulling ex-Palantir engineers off SAMMY's core product to build sales pipelines, FlowJoy ships production revenue systems directly to your GitHub in 2 weeks."* |
| **[Mercura](https://www.mercura.ai)** | **10/10** | Lukas Bock *(Founder/CEO)* | [LinkedIn](https://www.linkedin.com/in/lukas-bock-7636a0131) | **Yes** | Ex-Google X AI Engineer, former Allianz Data Scientist. Building AI order workflows. | *"Instead of pulling your core AI engineers off product to build internal CRM syncs, FlowJoy ships production GTM pipelines directly to your GitHub in a 2-4 week sprint."* |
| **[Browser Use](https://browser-use.com)** | **10/10** | Magnus Müller *(Founder/CEO)* | [LinkedIn](https://www.linkedin.com/in/magnus-mueller) | **Yes** | Repeated founder, ML researcher at ETH Zurich & Cambridge CARES. Built 110k+ star web agent. | *"Loved seeing browser-use blow up to 110k+ stars. While your team is 100% focused on scaling the core web agent engine, FlowJoy can ship your automated outbound pipelines and CRM architecture directly into your GitHub in a 2-week sprint."* |

---

## 🎯 Key Features & Modules

### 1. High-Precision Founder Intelligence (`models.py`, `enrichers.py`)
Rather than generic company summaries, the engine extracts:
- `Founder.name`: Verified full name
- `Founder.title`: Role (e.g. Founder/CEO, Co-founder/CTO)
- `Founder.linkedin_url`: Direct personal LinkedIn profile
- `Founder.twitter_url`: Personal Twitter / X account
- `Founder.bio`: Career highlights, past employers (Palantir, Google X, Bain), universities, and technical focus
- `Founder.has_email`: Verified email flag
- `Founder.projects`: Current or previous ventures

### 2. Self-Healing Algolia Integration (`config.py`, `scrapers/yc.py`, `scrapers/waas.py`)
- Algolia frontend search API keys rotate periodically.
- `startupscrape` includes automatic credential discovery: if an Algolia query receives a `403 Forbidden`, the client scrapes `window.AlgoliaOpts` from the live directory page, refreshes credentials, and retries seamlessly.

### 3. Selective Browser Gating (`signals.py`, `pipeline.py`)
- Gating policy guarantees that Browserbase and LinkedIn scrapers only run when an account is both **high-value** ($\ge 7/10$) AND **missing critical intelligence** that standard HTTP cannot resolve.
- Leads with complete Inertia data bypass the browser entirely, preserving 90%+ of cloud browser credits.

### 4. Outcome Tracking & Self-Improving Loop (`tracker.py`)
- Outreach outcomes are tracked in `data/outreach_outcomes.jsonl`:
  ```json
  {
    "lead_id": "sammy-labs",
    "company_name": "SAMMY Labs",
    "score": 10,
    "status": "meeting_booked",
    "contact_name": "Joe Savidge",
    "suggested_angle": "FlowJoy 2-week sprint for Palantir founders",
    "created_at": "2026-09-16T12:59:36"
  }
  ```
- Generates real-time conversion rates (`reply_rate`, `meeting_rate`) broken down by signal and score bucket.
- Outputs automated calibration recommendations (`recommended_boost`, `recommended_deprioritize`).

---

## 📦 Project Structure

```
startupscrape/
├── docs/                                # Comprehensive Wiki & Documentation
│   ├── ARCHITECTURE.md                  # System design, API layer & data flow
│   ├── FLOWJOY_WIKI.md                  # FlowJoy GTM Engineering Studio Playbook
│   ├── SIGNAL_PLAYBOOK.md               # GTM signal taxonomy & trigger hooks
│   ├── BROWSER_STRATEGY.md              # Browserbase gating & anti-detection guide
│   ├── SELF_IMPROVING_LOOP.md           # Outcome tracking & calibration architecture
│   └── PLAN.md                          # Optimization & implementation roadmap
├── startupscrape/
│   ├── scrapers/
│   │   ├── yc.py                        # Y Combinator Algolia client with auto-refresh
│   │   └── waas.py                      # Work at a Startup Algolia client
│   ├── enrichers.py                     # Inertia JSON parser for deep founder context
│   ├── signals.py                       # Heuristic signal detector & browser gating policy
│   ├── gtm_scorer.py                    # Gemini AI GTM analysis & pitch generator
│   ├── tracker.py                       # OutcomeTracker & conversion metrics engine
│   ├── browserbase_client.py            # Playwright / CDP cloud session manager
│   ├── linkedin_scraper.py              # Persistent context LinkedIn scraper
│   ├── models.py                        # Pydantic models (StartupLead, Founder, GTMAnalysis)
│   ├── pipeline.py                      # Unified pipeline coordinator
│   ├── exporters.py                     # CSV & JSON export utilities
│   ├── flowjoy_wiki.py                  # Embedded GTM knowledge base
│   └── config.py                        # Configuration & credentials
├── tests/                               # Comprehensive Pytest Suite
│   ├── test_models.py                   # Model validation & flat dictionary mapping
│   ├── test_pipeline.py                 # Normalization & deduplication logic
│   ├── test_scrapers.py                 # URL parsing & Algolia query builders
│   ├── test_enrichers.py                # Inertia parsing & regex fallbacks
│   ├── test_signals_and_gating.py       # Signal detection & browser gating
│   ├── test_tracker.py                  # Outcome tracking & calibration metrics
│   └── test_exporters.py                # CSV/JSON file generation tests
├── data/                                # Lead exports & outcome tracking ledgers
├── run_flowjoy_test.py                  # Live 3-lead targeted prospecting test
├── demo.py                              # Basic multi-directory demo script
├── setup_linkedin_context.py            # One-time authenticated session generator
└── pyproject.toml                       # Python package dependencies
```

---

## ⚡ Quickstart

### 1. Installation

```bash
git clone https://github.com/your-org/startupscrape.git
cd startupscrape
pip install -e .
```

### 2. Environment Setup

Create a `.env` file in the root directory:
```env
# Google Gemini API Key (for GTM scoring & personalized hooks)
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-3.6-flash

# Optional: Browserbase credentials (for selective deep scraping)
BROWSERBASE_API_KEY=your_browserbase_api_key
BROWSERBASE_PROJECT_ID=your_browserbase_project_id
BROWSERBASE_LINKEDIN_CONTEXT_ID=your_context_id
```

### 3. Run a Targeted Prospecting Sprint

To find and qualify targeted Seed/Series A B2B leads with full founder intelligence:

```bash
python3 run_flowjoy_test.py
```

### 4. Running the Unit Test Suite

```bash
python3 -m pytest tests/ -v
```

---

## 🛠️ Python SDK Usage

```python
from startupscrape.pipeline import StartupScrapePipeline
from startupscrape.models import FilterQuery
from startupscrape.tracker import OutcomeTracker
from startupscrape.exporters import export_leads

# 1. Initialize Pipeline
pipeline = StartupScrapePipeline()
tracker = OutcomeTracker()

# 2. Query Targeted Early-Stage B2B Startups
query = FilterQuery(
    batches=["Winter 2025", "Summer 2024", "Winter 2024"],
    industries=["B2B"],
    is_hiring=True,
    team_size_min=5,
    team_size_max=50,
    limit=5
)

# 3. Scrape & Enrich with Complete Founder Intelligence
leads = pipeline.yc.scrape(query, max_results=5, enrich=True)
leads = pipeline.deduplicate_and_merge(leads)

# 4. Score Leads against GTM Engineering Criteria
pipeline.score_leads(leads, selective_browser=True)

# 5. Inspect Results
for lead in leads:
    founder = lead.founders[0] if lead.founders else None
    print(f"Company: {lead.name} (Score: {lead.gtm_analysis.score}/10)")
    print(f"Founder: {founder.name} | LinkedIn: {founder.linkedin_url}")
    print(f"Hook:    {lead.gtm_analysis.suggested_angle}")
    print(f"Message: {lead.gtm_analysis.first_message}\n")
    
    # Track outreach attempt
    tracker.record_lead_sent(lead)

# 6. Export to CRM Format
res = export_leads(leads, prefix="gtm_campaign")
print(f"Exported to {res['csv']}")
```

---

## 📚 Knowledge Base & Wikis

Detailed operational playbooks and architecture guides are located in [`docs/`](docs/):
- **[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)**: Full system design, data models, Algolia integration, and pipeline lifecycle.
- **[`docs/FLOWJOY_WIKI.md`](docs/FLOWJOY_WIKI.md)**: FlowJoy GTM Engineering Studio positioning, value hooks, and ICP matrix.
- **[`docs/SIGNAL_PLAYBOOK.md`](docs/SIGNAL_PLAYBOOK.md)**: GTM signal triggers (Founding AE, Sales Leadership, RevOps, Batch freshness).
- **[`docs/BROWSER_STRATEGY.md`](docs/BROWSER_STRATEGY.md)**: Browserbase session persistence, gating rules, and anti-detection practices.
- **[`docs/SELF_IMPROVING_LOOP.md`](docs/SELF_IMPROVING_LOOP.md)**: Closed-loop outcome tracking, reply-rate analytics, and prompt calibration.
- **[`docs/PLAN.md`](docs/PLAN.md)**: System evolution roadmap and architectural decisions.

---

## 📄 License
MIT License. Created for B2B GTM teams and modern outbound engineering studios.


---

## 🔌 treg + jev Signal Pipeline (New)

A second, cost-first pipeline layer sits on top of the existing YC/WAAS scraper.
It uses **treg** (tool catalog — 3,600+ endpoints, one token) for email enrichment
and **jev** (Vercel AI Gateway evaluation model) for calibrated scoring.

### How it works

```
YC/WAAS Algolia (free, ~200 companies)
  │
  ▼ Tier 0 — free pre-filter (batch age, team size, B2B tags) → ~100
  ▼ Tier 1 — jev fast score: is_b2b / has_gtm_hire / funding_stage → keep top 60
  ▼ Tier 2 — treg email find (threaded, batch=10, checkpoint every batch) → 50 with email
  ▼ Tier 3 — jev final score (0-20 rubric) → ranked, written to data/run_<ts>.json
  ▼ Browse page — Flask app at localhost:5001
```

### Scoring rubric (20 pts max)

| Signal | Points |
|---|---|
| Seed or Series A funding | 10 |
| No GTM engineer / Head of Sales / RevOps | 5 |
| B2B product | 5 |
| Team 5–50 (bonus) | +1 |
| Technical founder (ex-FAANG, repeat, PhD) (bonus) | +1 |
| Engineering hiring, zero sales jobs (bonus) | +1 |
| Recent batch 2024–2026 (bonus) | +1 |

### Environment variables

```
TREG_TOKEN=<flowjoy team token>        # auto-set by treg login
AI_GATEWAY_API_KEY=<vercel key>        # optional — enables real jev; agent fallback if absent
TREG_PER_CALL_CAP_USD=0.05             # per-call ceiling sent as X-Treg-Route-Max-Cost
TREG_MAX_RUN_COST_USD=1.50             # run-level ceiling — stops new email batches when hit
```

### Run the pipeline

```bash
# One-shot from CLI
cd startupscrape/
python3 -c "from pipeline.runner import run; r = run(); print(r['funnel'])"

# Or via the browse page
python3 web/app.py        # → http://localhost:5001
# click "Run Pipeline"
```

### Browse page features

- **Funnel bar**: raw → pre-filter → jev Tier 1 → email found → final leads
- **Spend bar**: treg USD + jev judge (jev / agent)
- **Lead cards**: score ring (colour-coded), one-liner, batch, team size, funding stage prob
- **Inspector** (click card): signals, jev probability bars, contact box with email + provider + cost, links
- **Filters**: has email / score ≥ 15 / free search

### Failure safety

- Checkpoint JSON saved after every batch of 10 email finds
- On 402 (balance exhausted): stops email enrichment, scores what's found, writes full result
- On any exception: writes `data/run_<ts>_partial.json` (shown with ⚠️ PARTIAL badge)

### Cost per 50-lead run

| Step | Est. cost |
|---|---|
| YC/WAAS Algolia | $0 |
| jev scoring (100+60 items) | ~$0 (billed to AI Gateway quota) |
| treg email find (60 calls) | ~$0.20–$0.40 |
| **Total** | **≈ $0.20–$0.50** |

### Documentation

- [`docs/SCORING.md`](docs/SCORING.md) — jev question shapes and rubric
- [`docs/TREG.md`](docs/TREG.md) — treg endpoints, cost model, failure codes
