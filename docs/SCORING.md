# Scoring — FlowJoy Lead Finder

## Score Rubric (20 pts base + bonuses)

| Signal | Points | Detection |
|---|---|---|
| Seed or Series A funding | **10** | jev `funding_stage` choice (or recent batch verification) |
| No GTM engineer / Head of Sales / RevOps | **5** | jev `has_gtm_hire` boolean + job title scan |
| B2B product / SaaS | **5** | jev `is_b2b` boolean + tag detection |

### Bonus Signals (tie-break, up to 4 pts)

| Signal | +pts | Detection |
|---|---|---|
| Verified email found via treg | **+2** | `treg.people.email.find` |
| Team size 5–50 | **+1** | `team_size` field |
| Technical founder (ex-FAANG, PhD, CTO) | **+1** | founder bio keyword match |
| Open eng roles with zero sales roles | **+1** | job posting analysis |

**Max score: 24 pts**

---

## jev Question Specification

Evaluated via Vercel AI Gateway:
```
POST https://ai-gateway.vercel.sh/v4/ai/evaluation-model
Headers:
  Authorization: Bearer $AI_GATEWAY_API_KEY
  ai-model-id: typesafe-ai/jev
  ai-evaluation-model-specification-version: 4
  ai-gateway-protocol-version: 0.0.1
```

### Tier 1 — Fast Filter (Per Company)

```json
{
  "is_b2b": {
    "type": "boolean",
    "instructions": "Is this a B2B company (sells products or services to businesses or developers)?"
  },
  "has_gtm_hire": {
    "type": "boolean",
    "instructions": "Does this company currently have a GTM engineer, Head of Sales, VP Sales, RevOps, or Growth Lead?"
  },
  "funding_stage": {
    "type": "choice",
    "instructions": "What is the most likely funding stage of this company?",
    "criteria": {
      "seed": "Seed round, pre-product-market-fit",
      "series_a": "Series A, early revenue scaling",
      "series_b_plus": "Series B or later scaling",
      "pre_seed": "Pre-seed or bootstrapped",
      "unknown": "Cannot determine"
    }
  }
}
```

### Tier 3 — Final Score (Per Lead with Contact State)

```json
{
  "fit": {
    "type": "score",
    "instructions": "Score this lead's fit as a FlowJoy prospect from 0 to 20.",
    "criteria": [
      {"level": 0, "description": "Consumer, pre-revenue, or clearly not a match"},
      {"level": 5, "description": "B2B but large/mature, already has full GTM team"},
      {"level": 10, "description": "B2B, Seed/SeriesA, may have some sales capacity"},
      {"level": 15, "description": "B2B, Seed/SeriesA, no GTM hire, technical founder"},
      {"level": 20, "description": "All signals: seed/A, B2B, no GTM, eng-heavy, email found"}
    ]
  }
}
```

---

## Calibrated Heuristic Fallback

When `AI_GATEWAY_API_KEY` is not present, unverified, or experiences rate limits / downtime:
`scorer.py` evaluates the signals deterministically using the exact same schema and probability distributions. Zero external LLM calls, zero rate-limit errors, and zero API token cost.
