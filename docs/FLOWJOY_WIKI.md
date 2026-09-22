# FlowJoy Knowledge Base & GTM Outbound Playbook

This wiki defines the core positioning, customer profile, signal mechanics, and scoring rubric for marketing **FlowJoy GTM Engineering Studio** to Seed and Series A B2B startups.

---

## 1. What is FlowJoy?

FlowJoy is a **GTM Engineering Studio** (v6 revenue systems).

- **Headline**: *"Your GTM Stack Is Powerful. Your Workflow Isn't."*
- **The Reality**: Modern B2B startups pay thousands per month for Clay, Apollo, HubSpot, and Slack. But their teams are still manually exporting CSVs, formatting lists, and copying data between tabs.
- **The Dilemma**:
  - Founders want automated pipeline.
  - Core software engineers are swamped with customer feature requests and cannot build internal GTM tooling.
  - Hiring a full-time GTM Engineer costs **$180,000+/year** plus equity and benefits.
- **FlowJoy's Solution**:
  - **Shipped in 2–4 weeks**: Production-grade data pipelines, deterministic CRM syncs, and autonomous outbound agents.
  - **100% Code Ownership**: Shipped directly to the client's GitHub repository.
  - **Zero Platform Lock-in**: Connects directly to their existing stack (Postgres, HubSpot, Slack, Apollo, Clay).

---

## 2. Ideal Customer Profile (ICP)

| Dimension | Target Profile | Why |
|-----------|----------------|-----|
| **Stage** | Seed to Series A ($1M–$6M raised) | Have budget, past product exploration, need repeatable outbound engine. |
| **Team Size** | 5 to 50 employees | Small enough to make fast decisions, large enough to have real pipeline pain. |
| **Model** | B2B SaaS / AI Infrastructure / DevTools | High ACV ($10k–$100k) where closing 2-3 extra deals pays for the entire FlowJoy sprint. |
| **GTM Gap** | No GTM Engineer / Head of Sales in headcount | Founder-led sales bottleneck; high urgency for structured outbound infrastructure. |
| **Engineering Trigger** | Hiring Engineers but ZERO sales postings | Proves core dev team is fully allocated to product and cannot build sales tooling. |

---

## 3. Signal-First Scoring Rubric (20 Pts Base + Bonuses)

Every startup is scored and ranked on an objective 24-point fit rubric evaluated via **jev** (or calibrated deterministic heuristics):

| Signal | Points | Detection / Source | Rationale |
|---|---|---|---|
| **Seed or Series A Stage** | **10** | YC/WAAS cohorts from 2023–2027 | Capitalized and under investor pressure to build outbound pipeline. |
| **No GTM Engineer / Head of Sales** | **5** | Job postings & founder titles | Confirms founder-led sales bottleneck; prime FlowJoy buyer. |
| **B2B SaaS / DevTools** | **5** | Algolia tags, industry, description | Fits FlowJoy's high-ACV engineering architecture. |
| **Verified Work Email** | **+2** | `treg.people.email.find` | Direct deliverability into founder's inbox. |
| **Team Size 5–50** | **+1** | Algolia / directory metadata | Sweet spot for fast procurement and high outbound need. |
| **Technical Founder** | **+1** | Founder bios (ex-FAANG, PhD, CTO) | Engineers respect engineering solutions shipped to GitHub. |
| **Eng Hiring without Sales Hiring** | **+1** | Open role titles | Proves dev capacity is saturated on core product. |

**Max possible score: 24 points.**

---

## 4. Signal Sourcing Waterfall

```
┌─────────────────────────────────────────────────────────────┐
│ 1. Algolia Backend Query (YC & WAAS directories)            │
│    • Slices thousands of startups in <500ms                 │
│    • Filters by batch freshness (Seed/Series A proxy)       │
│    • Pulls team size, B2B tags, and open job roles          │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. YC Company Page HTTP Extraction                          │
│    • Parses Inertia data-page in a single lightweight GET   │
│    • Extracts company domain, company LinkedIn URL          │
│    • Extracts founder names, titles, and personal LinkedIn  │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. jev / Heuristic Scoring                                  │
│    • Evaluates B2B, stage, and GTM hiring status            │
│    • Filters out low-fit accounts with zero token overhead  │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. treg Contact Enrichment (`treg.people.email.find`)       │
│    • Cascades cheapest-first to find verified work emails   │
│    • ~$0.005 per verified hit; misses are free              │
│    • Enforces strict per-call ($0.05) and run-level caps    │
└─────────────────────────────────────────────────────────────┘
```

---

## 5. FlowJoy Core Outreach Templates

### Angle 1: No Sales Lead / First Outbound Scaffolding
> *"Hi [Founder Name], saw [Company] is scaling engineering without a dedicated GTM engineer or Head of Sales yet. When technical founders reach this stage, they usually spend weekends stitching Apollo and Clay lists into spreadsheets instead of building product. At FlowJoy, we engineer automated revenue pipelines directly into your GitHub in a 2-week sprint so your outbound runs on autopilot. Worth a 10-minute chat?"*

### Angle 2: Devs Busy on Product
> *"Hi [Founder Name], loved what you and the team built with [Company One-Liner]. Most Seed B2B founders we speak with have their core engineers 100% focused on shipping features, leaving internal CRM syncs and lead routing under-engineered. FlowJoy acts as your dedicated GTM Engineering team — shipping production revenue pipelines directly to your repo in 2–4 weeks. Free for a quick architecture review?"*

### Angle 3: Free GTM Stack Teardown
> *"Hi [Founder Name], noticed [Company] is scaling past [Team Size] people. We put together 5-minute Loom teardowns for Seed-stage B2B founders showing where manual pipeline leaks are happening across Apollo/Clay/HubSpot. Mind if I record one for [Company]?"*
