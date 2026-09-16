# Browserbase Strategy & Anti-Detection Best Practices

Headless browser automation is powerful but expensive and fragile. This guide details how `startupscrape` uses Browserbase responsibly.

---

## 1. The Selective Gating Policy

To prevent burning cloud browser credits and protecting LinkedIn session integrity, Browserbase is executed **only when both criteria are met**:

1. **Lead Score $\ge 7/10$**: High-intent account with verified growth or hiring signals.
2. **Critical Data Missing**: The account lacks founder names, verified LinkedIn profile, or website text that could NOT be obtained from Algolia or HTTP requests.

### What Algolia & HTTP Already Provide (Zero Browser Needed):
- Company Name, Slug, YC URL, WAAS URL
- High-level Batch, Industry, Subindustry
- Job listings (Titles, locations, salary, equity)
- Verified Website URL (via YC Inertia JSON)
- Company LinkedIn URL (via YC Inertia JSON)
- Company Twitter handle (via YC Inertia JSON)

### What Browserbase is Exclusively Reserved For:
- Mining specific executive names from `/company/<slug>/people/` when no founders are listed in YC.
- Extracting rendered JavaScript content from SPA websites with Cloudflare/bot challenges.
- Verifying exact headcount and recent hiring posts directly from LinkedIn.

---

## 2. Session Management & Concurrency Controls

- **Serial Execution (`browserbase_workers=1`)**: LinkedIn strictly monitors concurrent requests from different IPs. `startupscrape` serializes LinkedIn sessions to 1 worker by default.
- **Context Persistence**: The context ID generated via `setup_linkedin_context.py` contains valid cookies and local storage tokens.
- **Automatic Session Release**: All Browserbase sessions run inside `try...finally` blocks with explicit `stop_session` calls (`REQUEST_RELEASE`) to avoid hanging sessions and unexpected billing.

---

## 3. LinkedIn Context Setup Workflow

1. Run the setup script:
   ```bash
   python3 setup_linkedin_context.py
   ```
2. Open the printed Browserbase Live View URL in your browser.
3. Log in with your LinkedIn credentials and complete any 2FA challenge.
4. Return to the terminal and press Enter.
5. The persistent context ID will be saved to your `.env` file as `BROWSERBASE_LINKEDIN_CONTEXT_ID`.
