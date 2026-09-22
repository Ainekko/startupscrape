import os
import re
import json
import logging
import requests
from dotenv import load_dotenv

logger = logging.getLogger(__name__)
load_dotenv()

# Y Combinator Algolia Search Config (Live validated keys)
YC_ALGOLIA_APP_ID = os.getenv("YC_ALGOLIA_APP_ID", "45BWZJ1SGC")
YC_ALGOLIA_API_KEY = os.getenv(
    "YC_ALGOLIA_API_KEY",
    "NzJmMWExZWYxYzY5OGYwN2VkYWM5YzRiM2VlNDFlM2I0ODU2YjQ2Yjg0MTFiNWE5NzY0NTMyZGI1OWEwMzVjY2FuYWx5dGljc1RhZ3M9eWNkYyZyZXN0cmljdEluZGljZXM9WUNDb21wYW55X3Byb2R1Y3Rpb24lMkNZQ0NvbXBhbnlfQnlfTGF1bmNoX0RhdGVfcHJvZHVjdGlvbiZ0YWdGaWx0ZXJzPSU1QiUyMnljZGNfcHVibGljJTIyJTVE"
)
YC_PRIMARY_INDEX = "YCCompany_production"
YC_LAUNCH_DATE_INDEX = "YCCompany_By_Launch_Date_production"

# Work at a Startup Algolia Search Config (Live validated keys)
WAAS_ALGOLIA_APP_ID = os.getenv("WAAS_ALGOLIA_APP_ID", "45BWZJ1SGC")
WAAS_ALGOLIA_API_KEY = os.getenv(
    "WAAS_ALGOLIA_API_KEY",
    "NTA1N2Q5MWRjMWIzZWMwYzhkYWI5NTVkNGJjNWIyOTg3MWZkNDgxOTU2MTVlYmVmMmY0MmRkY2UyYTYyMjY4MWFuYWx5dGljc1RhZ3M9d2FhcyZyZXN0cmljdEluZGljZXM9JTJBX3Byb2R1Y3Rpb24mdGFnRmlsdGVycz0lNUIlNUIlMjJub25lJTIyJTVEJTVEJnZhbGlkVW50aWw9MTc4OTY0NjAyMA=="
)
WAAS_COMPANY_INDEX = "Company_production"
WAAS_JOB_INDEX = "Job_production"

# Algolia API Base URL
ALGOLIA_API_BASE = "https://45bwzj1sgc-dsn.algolia.net/1/indexes/*/queries"

# Browserbase Configuration
BROWSERBASE_API_KEY = os.getenv("BROWSERBASE_API_KEY", "")
BROWSERBASE_PROJECT_ID = os.getenv("BROWSERBASE_PROJECT_ID", "")
BROWSERBASE_LINKEDIN_CONTEXT_ID = os.getenv("BROWSERBASE_LINKEDIN_CONTEXT_ID", "")
BROWSERBASE_API_BASE = "https://api.browserbase.com/v1"

# Gemini AI Configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")
# treg — tool catalog (https://treg.to)
TREG_TOKEN = os.getenv("TREG_TOKEN", "")
TREG_BASE_URL = "https://treg.to"
TREG_PER_CALL_CAP_USD = float(os.getenv("TREG_PER_CALL_CAP_USD", "0.05"))
TREG_MAX_RUN_COST_USD = float(os.getenv("TREG_MAX_RUN_COST_USD", "1.50"))

# jev — Vercel AI Gateway evaluation model (https://vercel.com/ai-gateway)
AI_GATEWAY_API_KEY = os.getenv("AI_GATEWAY_API_KEY", "")


DEFAULT_TIMEOUT = 15
MAX_HITS_PER_PAGE = 100

# Base Directories
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)


def fetch_live_algolia_opts(url: str, session: requests.Session = None) -> dict:
    """Fetch live Algolia Application-ID and API key directly from site HTML."""
    s = session or requests.Session()
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Referer": url
    }
    try:
        resp = s.get(url, headers=headers, timeout=DEFAULT_TIMEOUT)
        m = re.search(r'window\.AlgoliaOpts\s*=\s*({[^}]+})', resp.text)
        if m:
            opts = json.loads(m.group(1))
            logger.info(f"Successfully auto-discovered live Algolia key from {url}")
            return opts
    except Exception as e:
        logger.warning(f"Failed to auto-discover Algolia key from {url}: {e}")
    return {}
