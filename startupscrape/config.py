import os
from dotenv import load_dotenv

load_dotenv()

# Y Combinator Algolia Search Config
YC_ALGOLIA_APP_ID = os.getenv("YC_ALGOLIA_APP_ID", "45BWZJ1SGC")
YC_ALGOLIA_API_KEY = os.getenv(
    "YC_ALGOLIA_API_KEY",
    "NzllNTY5MzJiZGM2OTY2ZTQwMDEzOTNhYWZiZGRjODlhYzVkNjBmOGRjNzJiMWM4ZTU0ZDlhYTZjOTJiMjlhMWFuYWx5dGljc1RhZ3M9eWNkYyZyZXN0cmljdEluZGljZXM9WUNDb21wYW55X3Byb2R1Y3Rpb24lMkNZQ0NvbXBhbnlfQnlfTGF1bmNoX0RhdGVfcHJvZHVjdGlvbiZ0YWdGaWx0ZXJzPSU1QiUyMnljZGNfcHVibGljJTIyJTVE"
)
YC_PRIMARY_INDEX = "YCCompany_production"
YC_LAUNCH_DATE_INDEX = "YCCompany_By_Launch_Date_production"

# Work at a Startup Algolia Search Config
WAAS_ALGOLIA_APP_ID = os.getenv("WAAS_ALGOLIA_APP_ID", "45BWZJ1SGC")
WAAS_ALGOLIA_API_KEY = os.getenv(
    "WAAS_ALGOLIA_API_KEY",
    "ODI0N2JiZGQyNjMxMTljNGQwZjM5NDFkNzY4NmFkNTM1MTI4ZDdlNzRlNWE3ZTZhODY3NTAxYWM1ZmUxY2JmZGFuYWx5dGljc1RhZ3M9d2FhcyZyZXN0cmljdEluZGljZXM9JTJBX3Byb2R1Y3Rpb24mdGFnRmlsdGVycz0lNUIlNUIlMjJub25lJTIyJTVEJTVEJnZhbGlkVW50aWw9MTc4OTIwNTYxOA=="
)
WAAS_COMPANY_INDEX = "Company_production"
WAAS_JOB_INDEX = "Job_production"

# Algolia API Base URL
ALGOLIA_API_BASE = "https://45bwzj1sgc-dsn.algolia.net/1/indexes/*/queries"

# Browserbase Configuration
BROWSERBASE_API_KEY = os.getenv("BROWSERBASE_API_KEY", "")
BROWSERBASE_PROJECT_ID = os.getenv("BROWSERBASE_PROJECT_ID", "")
BROWSERBASE_API_BASE = "https://api.browserbase.com/v1"

# Gemini AI Configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

DEFAULT_TIMEOUT = 15
MAX_HITS_PER_PAGE = 100

# Base Directories
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)
