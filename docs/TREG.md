# treg — FlowJoy Lead Finder integration

## Token

Team: **flowjoy** (baked into `TREG_TOKEN` in `.env`).
Base URL: `https://treg.to`
Auth header: `X-Treg-Token: $TREG_TOKEN`

---

## Endpoints used

### `treg.people.email.find` (Tier 2)

Routed endpoint — tries providers cheapest-first; misses are free.

```
POST https://treg.to/call/treg.people.email.find
Headers:
  X-Treg-Token: $TREG_TOKEN
  X-Treg-Route-Max-Cost: 0.05       ← per-call ceiling; 402 if exceeded, no charge
Body:
  {"full_name": "...", "company_name": "...", "domain": "..."}
```

**Response headers to always read:**

| Header | Meaning |
|---|---|
| `X-Treg-Cost-Micro` | Actual charge in micro-USD (÷1,000,000 = USD) |
| `X-Treg-Call-Id` | Unique call ID for support / audit |
| `X-Treg-Served-By` | Which provider answered |
| `X-Treg-Cache` | `hit` = answered from cache at 10% price |

**Status codes:**

| Code | Meaning | Billed? |
|---|---|---|
| 200 + email | Hit | Yes |
| 200 + no email | Miss (no data) | No |
| 402 | Budget exhausted or per-call cap exceeded | No |
| 429 | Provider rate limit | No |
| 5xx | Provider/treg error | No |

---

## Cost model per run (50 leads)

| Step | Calls | Unit cost | Estimated total |
|---|---|---|---|
| YC/WAAS Algolia | — | free | $0 |
| jev Tier 1 (100 items) | via AI Gateway | ~$0 | $0 |
| treg email find (60 attempts) | 60 | ~$0.01/hit, miss=free | ~$0.20–$0.40 |
| jev Tier 3 (60 items) | via AI Gateway | ~$0 | $0 |
| **Total** | | | **≈ $0.20–$0.50** |

Run ceiling: `TREG_MAX_RUN_COST_USD=1.50` (env var). Stops new email batches if reached.
Per-call ceiling: `TREG_PER_CALL_CAP_USD=0.05` (env var, sent as `X-Treg-Route-Max-Cost`).

---

## Failure safety

1. **Checkpoint** saved after every batch of 10 email finds → `data/run_<ts>_partial.json`
2. **402 mid-run**: stops email enrichment, scores what's found, writes full result
3. **Any exception**: writes `data/run_<ts>_partial.json` before exit
4. **Idempotency**: re-running with the same inputs is safe; treg dedupes at provider level

---

## Check balance

```bash
treg balance
```

Or:
```
GET https://treg.to/balance   -H "X-Treg-Token: $TREG_TOKEN"
```

Top up: https://treg.to/dashboard → Team → Billing
