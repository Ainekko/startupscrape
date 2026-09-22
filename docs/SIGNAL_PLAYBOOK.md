# Signal Playbook: B2B GTM Outbound Signals

This playbook documents the key growth, funding, and hiring signals monitored by `startupscrape`, where each signal originates, how it is extracted, and how it informs the scoring engine.

---

## 1. Signal Taxonomy & Detection Sources

| Signal Name | Source | Detection Mechanism | Operational Meaning | Value Angle for FlowJoy |
|---|---|---|---|---|
| **Recent Seed / Series A Funding** | YC / WAAS Batches | Matches cohorts from 2023–2027 (`Winter 2023` through `Summer 2027`) | Institutional check ($500k–$3M) secured; under high investor pressure to accelerate commercial traction. | Speed to outbound revenue engine; building repeatability before burn runs out. |
| **No GTM Engineer / Sales Lead** | Job Postings & Team Titles | Absence of GTM keywords (`head of sales`, `vp sales`, `revops`, `growth lead`, `gtm engineer`) in headcount & job openings | Founder-led sales bottleneck. The founders are personally doing sales calls without structured pipeline scaffolding. | Providing turnkey automated outbound and CRM routing without hiring an expensive $180k/yr sales VP. |
| **Engineering Hiring, Zero Sales Roles** | YC Open Roles | Multiple open engineering roles (`engineer`, `developer`, `backend`, `ml`, `ai`) with zero open sales roles | Dev team is 100% absorbed by product; no internal dev capacity exists to build custom sales scrapers or CRM syncs. | FlowJoy ships production revenue infrastructure directly to their GitHub in 2–4 weeks. |
| **B2B / SaaS / DevTools Model** | Algolia Tags & Metadata | Positive match on `b2b`, `saas`, `enterprise`, `developer tools`, `infrastructure`, `ai`, `fintech`, `api` (and absence of pure consumer tags) | High ACV model ($10k–$100k+). A handful of closed enterprise deals pays for the entire sprint. | High-ROI outbound targeting for technical enterprise buyers. |
| **Technical Founder Pedigree** | YC Founder Bios | Keyword match on ex-FAANG (`Google`, `Meta`, `Apple`, `Palantir`, `Stripe`, `OpenAI`), `PhD`, top technical schools (`Stanford`, `MIT`, `ETH`) | Technical leadership values deterministic code and automated systems over manual spreadsheet busywork. | Code-first revenue systems, Git-based workflows, and technical credibility. |
| **Optimal Scaling Team Size** | WAAS / YC Directory | `team_size` between 5 and 50 employees (skips >150) | Past the prototype stage; large enough to feel serious pipeline pain, small enough to approve contracts in days. | Rapid decision-making without corporate procurement friction. |
| **Verified Direct Contact** | treg (`treg.people.email.find`) + YC Page | Domain extraction + full name query against treg cascades; personal & company LinkedIn URL extraction | Reachable directly in the founder's primary inbox and on LinkedIn. | Multi-channel sequence deliverability. |

---

## 2. Priority Scoring Matrix (0–24 Pts)

Scored via **`pipeline/scorer.py`** using **jev** (or calibrated local heuristics):

```
Base Signals (20 pts):
  ├── Seed or Series A Stage ...................... +10 pts
  ├── No GTM Engineer / Head of Sales in Headcount  +5 pts
  └── B2B Product / SaaS Model .................... +5 pts

Bonus Multipliers (up to 4 pts):
  ├── Verified Founder Email (treg) ............... +2 pts
  ├── Optimal Team Size (5–50) .................... +1 pt
  ├── Technical Founder (ex-FAANG/PhD) ............ +1 pt
  └── Active Engineering Hiring (no sales roles) .. +1 pt
```

### Priority Action Buckets:
- **Tier 1: High Priority (Score 18–24)**:
  - Immediate outreach.
  - Multi-channel approach: direct verified email + founder LinkedIn connect.
  - Custom value hook referencing their specific batch and product one-liner.
- **Tier 2: Solid Fit (Score 12–17)**:
  - Standard automated sequence.
  - Reference founder-led sales bottlenecks and automated outbound scaffolding.
- **Tier 3: Low Fit / Disqualified (Score < 12)**:
  - Consumer, large enterprise (>150 headcount), or already has a complete in-house sales team.
