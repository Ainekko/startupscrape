# StartupScrape Backend

FastAPI backend for the StartupScrape pipeline and lead intelligence engine. Uses **uv** for dependency management.

## Setup

```bash
cd backend
uv sync
```

## Run locally

```bash
uv run uvicorn app.main:app --reload --port 8000
```

Interactive API documentation available at `http://localhost:8000/docs`.

## Database & Multi-Tenancy

StartupScrape connects directly to PostgreSQL (via `SQLModel` + `asyncpg`). 

- **Table Isolation**: All database tables are prefixed with `startupscrape_` (`startupscrape_users`, `startupscrape_runs`, `startupscrape_leads`, `startupscrape_outcomes`).
- **Shared DB Instance**: It can safely share the same Neon or PostgreSQL instance as other apps without risk of schema or table collisions.
- **Graceful Fallback**: If `DATABASE_URL` is omitted, the API continues to operate seamlessly using local JSON run artifacts in `data/`.

## Architecture & Reusable Services

- `app/config.py`: Environment configuration and settings via Pydantic.
- `app/db.py`: Async database engine, session dependencies, and automatic table creation.
- `app/models.py`: SQLModel entities and Pydantic schemas.
- `app/auth.py`: JWT token creation, password hashing (bcrypt), and role-based dependencies (`get_current_user`, `require_admin`).
- `app/services/`:
  - `AuthService`: Registration, authentication, JWT tokens.
  - `PipelineService`: Orchestration, background runs, DB sync, and run retrieval.
  - `LeadService`: Dynamic filtering, search, pagination, status updates, and CSV exports.
  - `AnalyticsService`: Funnel metrics, conversion KPIs, and batch performance.
- `app/routes/`:
  - `auth`: `/api/auth/register`, `/api/auth/login`, `/api/auth/me`.
  - `pipeline`: `/api/runs`, `/api/runs/{run_id}`, `/api/run`, `/api/status`.
  - `leads`: `/api/leads`, `/api/leads/{id}`, `/api/leads/{id}/status`, `/api/leads/export/csv`.
  - `analytics`: `/api/analytics/overview`.
