# LinkedIn Deep Intel — Implementation Plan (Trigger Engine)

Goal: for every **tracked Verve account** (`startupscrape_leads`), gather as much LinkedIn intel as
possible — company posts, founder posts, **comments on those posts**, and **comments the founders
leave elsewhere** — turn it into timing signals, persist it, and feed it into the existing
Trigger Engine scan → qualifier → outreach-brief pipeline.

## Ban-safety decision (read first)

- **All LinkedIn data is fetched through treg.to catalog providers** (Fetchin, HarvestAPI, AnyAPI,
  TikHub …). They scrape on their own infrastructure. **No LinkedIn login, no cookies, no session of
  ours ever touches LinkedIn** → the user's LinkedIn account cannot be banned by this system.
- **No custom browser is built.** treg covers every capability we need (see table). The old
  `browserbase_*` settings stay unused. If a capability ever disappears from treg, the fallback is
  another treg provider for the same capability — never a logged-in browser.
- Spend is capped per call (`X-Treg-Route-Max-Cost`) and per account (`IntelBudget`).

## treg endpoints used

| Job | Endpoint id | Method | Input | ~Cost |
|---|---|---|---|---|
| Company posts | `harvestapi.linkedin.company.posts` | GET (strict query) | `companyUniversalName`, `page`, `scrapePostedLimit` | $0.004 |
| Founder posts | `treg.linkedin.user.posts` (routed) | POST json | `linkedin_url` / `linkedin_handle`, `limit` → `output.posts` | $0.0015–0.004 |
| Comments on a post | `treg.linkedin.post.comments` (routed) | POST json | `post_urn` / `post_id`, `limit` → `output.comments` | $0.0015 (cap 0.01) |
| Comments a founder made | `harvestapi.linkedin.user.comments` | GET (strict query) | `profile`, `postedLimit`, `page` | $0.004 |
| Resolve company slug / founder URL | `treg.google.serp.organic` | POST json | `q` | $0.00015 |

Real charge = response header `X-Treg-Cost-Micro` (micro-USD). Rows are **provider-native**, so all
parsing goes through tolerant normalizers.

## Architecture

```
routes.py  POST /api/triggers/linkedin/intel          (single account, cached 24h)
           GET  /api/triggers/linkedin/intel/{lead_id} (latest snapshot)
           POST /api/triggers/linkedin/intel/batch     (many accounts, total budget)
              │
              ▼
linkedin_intel.py  LinkedInIntelService.gather(account) -> LinkedInIntelReport
              │  ├─ resolve targets (company slug, founder profiles; SERP fallback)
              │  ├─ fetch company posts + founder posts (parallel)
              │  ├─ pick top-N recent posts → fetch comments (parallel, semaphore)
              │  ├─ fetch founder's own comments elsewhere
              │  └─ analyze → IntelSignal[], EngagedPerson[], topics
              ▼
linkedin_normalize.py  pure parsing helpers (urls, urns, dates, post/comment rows)
treg_client.py         TregClient.call(GET|POST, params|json) + header cost accounting
detectors/linkedin_activity.py  LinkedInActivityDetector → DetectedSignal[] (scan pipeline)
models.py              LinkedInIntelSnapshot table `trigengine_linkedin_intel` + schemas
```

## Steps (status)

1. [x] **TregClient upgrade** — generic `call()` supporting GET+query and POST+json, cost from
   `X-Treg-Cost-Micro` header (fallback to body), `call_id`/`served_by` captured, injectable
   `httpx` transport for tests. `call_endpoint()` kept backward compatible.
2. [x] **Normalizers** (`linkedin_normalize.py`) — company slug / profile handle / activity URN
   extraction, timestamp parsing (ISO, epoch s/ms, relative `3d`/`2w`/`1mo`, nested dicts),
   `find_rows()` to locate row lists in any provider envelope, `normalize_post()`,
   `normalize_comment()`.
3. [x] **Schemas + table** (`models.py`) — `LinkedInPost`, `LinkedInComment`, `IntelSignal`,
   `EngagedPerson`, `LinkedInIntelReport`, `LinkedInIntelRequest`, `LinkedInIntelBatchRequest`,
   table `LinkedInIntelSnapshot` (`trigengine_linkedin_intel`). Created automatically by
   `init_db()` (it imports `app.trigger_engine.models`).
4. [x] **Intel service** (`linkedin_intel.py`) — budgeted gathering + analysis:
   - post signals: hiring, funding, launch, gtm_pain, milestone, event
   - comment signals: buying intent / pain in comments, notable commenters (investors, sales
     leaders, founders), founder commenting on GTM topics elsewhere
   - engaged people aggregation (warm-intro + lookalike prospects), topics, founder last-active
5. [x] **Detector** (`detectors/linkedin_activity.py`) registered as `linkedin_activity` in
   `TriggerEngineService`; scan persists the snapshot too. Qualifier heuristic handles
   `founder_signal`.
6. [x] **Routes** — intel single / latest / batch; `/leads` now also returns
   `company_linkedin_url` + `founders`. Lead→account mapping factored into `_lead_to_account()`.
7. [x] **Tests** (`backend/tests/`, plain `pytest`, no async plugin needed — tests use
   `asyncio.run`): normalizers, treg client (httpx.MockTransport), intel service (fake treg),
   detector, routes (FastAPI TestClient + dependency overrides).
   ⚠️ Written but **not yet executed** (agent sandbox was down) — first run may need small
   assertion/fixture tweaks; fix the code, not the intent of the test.
8. [x] **Frontend client** — `api.triggers.linkedinIntel / getLinkedinIntel / linkedinIntelBatch`
   + TS types in `trig-engine/src/lib/{api,types}.ts`.
9. [ ] **UI** (design deferred by user) — show intel on the lead card (signals, hot comments,
   engaged people, founder last active). Use existing colors/typography only.
10. [ ] **Live smoke test** with a real `TREG_TOKEN` on 2–3 accounts; check provider row shapes
    against normalizers; tune keyword lists; review spend in `treg audit`.
11. [ ] **Scheduling** — daily batch refresh of top-N accounts (cron / background task), diff
    against previous snapshot to surface only *new* signals.
12. [ ] **LLM pass (optional)** — send top posts+comments to Gemini for a 3-bullet "what they care
    about right now" summary and a personalised opener; keep heuristic as fallback.

## Running tests

```
cd ~/creatorbook/startupscrape/backend
uv add --dev pytest      # once (pytest is the only extra dependency)
uv run pytest -q
```

## Config

- `TREG_TOKEN` (already used) — required for live calls.
- Defaults (overridable per request): `max_cost_usd=0.06` per account, `lookback_days=90`,
  `max_posts_for_comments=3`, `comments_per_post=25`, `max_founders=2`, cache TTL 24h.

## Notes for the next agent

- Provider row shapes are not contractually fixed. If a live run returns empty normalized posts
  while `raw` has data, extend the key candidate lists in `linkedin_normalize.py` and add a test
  with the real row (strip personal data).
- Never retry a 4xx on another provider (treg guidance); 429/5xx may fall back.
- Keep every LinkedIn fetch on treg. Do not add logged-in scraping.
