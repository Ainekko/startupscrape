# Signal Playbook: B2B GTM Outbound Signals

This playbook documents the key growth and hiring signals monitored by `startupscrape`, their operational meaning, and the recommended outreach angles.

---

## 1. Core Signals Monitored

| Signal Name | Trigger Keywords / Criteria | Operational Meaning | Suggested Value Angle |
|-------------|----------------------------|---------------------|-----------------------|
| **Founding Account Executive** | `Founding AE`, `Founding Account Executive`, `First Sales Hire` | Transitioning from founder-led sales to their first dedicated closer. High urgency; founders often lack structured playbooks, SDR pipeline, or onboarding collateral. | Providing qualified pipeline, outbound systems, or RevOps scaffolding to ensure their first sales hire succeeds immediately. |
| **Sales Leadership** | `Head of Sales`, `VP Sales`, `Director of Sales` | Ready to build a repeatable sales engine. Company has initial product-market fit and is standardizing deal stages, ICP criteria, and outbound quota. | Strategic pipeline scaling, market testing, account intelligence enrichment, and outbound automation. |
| **Revenue Operations** | `RevOps`, `Revenue Operations`, `CRM Lead` | Tech stack complexity bottleneck. Transitioning from spreadsheets to HubSpot/Salesforce, needing data hygiene, automated routing, and attribution. | Data enrichment, CRM integration, lead routing, and pipeline visibility. |
| **Outbound SDR / BDR** | `SDR`, `BDR`, `Sales Development Representative` | Building dedicated cold outbound infrastructure. Struggling with email deliverability, list building, and personalization at scale. | Pre-qualified account targeting, verified contact intelligence, and automated signal tracking. |
| **Growth / GTM Lead** | `Head of Growth`, `GTM Lead`, `Growth Marketing` | Moving beyond word-of-mouth. Looking for multi-channel acquisition (LinkedIn, outbound, content). | Account-based outbound, signal-triggered prospecting, and ICP discovery. |
| **Recent Tier-1 Batch** | `W25`, `S25`, `W26`, `Winter 2025`, etc. | Recently raised institutional Seed capital ($500k–$3M). Capitalized and under high investor pressure to demonstrate initial revenue traction. | Speed to first 10 enterprise/mid-market design partners or customers. |
| **Optimal Scaling Size** | `Team Size 5 - 50` | Past the core product-building phase; building early commercial operations. Big enough to pay, small enough that decisions happen in days. | Agility, founder direct access, low procurement friction. |
| **Founder Bottleneck Pain** | *"founder-led sales"*, *"repeatable outbound"*, *"first sales process"* | Explicitly self-identifying GTM pains in public company descriptions or job postings. | Direct solution to the exact bottleneck articulated by the leadership team. |

---

## 2. Priority Scoring Matrix

`startupscrape` uses a two-tier scoring system:

1. **Heuristic Pre-Score (1-10)**:
   - Evaluated locally in <1ms without API calls.
   - Used to gate browser sessions and filter out low-intent accounts.
2. **Gemini GTM Score (1-10)**:
   - Evaluates full context (job descriptions, team composition, website copy).
   - Generates the customized sales hook and tailored 3-sentence outreach draft.

### Priority Action Buckets:
- **Tier 1: High Priority (Score 8–10)**:
  - Immediate outreach.
  - Personalized multichannel sequence (Email + Founder LinkedIn connect + Twitter interaction).
  - Use Browserbase/LinkedIn to verify executive name if missing.
- **Tier 2: Medium Priority (Score 6–7)**:
  - Standard automated sequence.
  - Enrich via HTTP only; no browser sessions.
- **Tier 3: Low Priority (Score 1–5)**:
  - Nurture or disqualify (e.g. non-commercial, late growth, or inactive).
