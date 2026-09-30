"""
tests/test_backend_api_and_db.py — Comprehensive Test Suite
============================================================
Tests:
1. PostgreSQL Database Connection & Tables (`startupscrape_*`)
2. Persisting the last JSON run (`data/run_20260922_143528.json`) into the DB
3. Frontend API Schema Validation (RunSummary, Run, Lead, RunStatus)
4. Leads Querying, Filtering, Status Updates & CSV Export
5. Analytics Overview KPI endpoint
6. Auth Workflow (Registration, Login, Protected Me endpoint)

Can be executed with:
    cd backend && uv run pytest ../tests/test_backend_api_and_db.py -v
or:
    cd backend && uv run python ../tests/test_backend_api_and_db.py
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient

# Setup sys.path
TESTS_DIR = Path(__file__).resolve().parent
ROOT_DIR = TESTS_DIR.parent
BACKEND_DIR = ROOT_DIR / "backend"

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.config import get_settings
from app.db import check_db_connection, get_engine, get_session_context, init_db
from app.main import app
from app.models import Lead, PipelineRun, User
from app.services.pipeline_service import PipelineService
from sqlmodel import select


# ── Fixtures & Setup ───────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# ── Test Cases ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_01_database_connection_and_table_creation():
    """Verify PostgreSQL connectivity and verify isolated startupscrape_ tables exist."""
    settings = get_settings()
    assert settings.database_url, "DATABASE_URL must be defined in .env"

    is_connected = await check_db_connection()
    assert is_connected is True, "Failed to connect to PostgreSQL database"

    initialized = await init_db()
    assert initialized is True, "Failed to initialize database tables"

    # Verify tables exist by querying each model
    async with get_session_context() as session:
        assert session is not None, "Session context failed to initialize"

        # Check users table
        users_result = await session.exec(select(User).limit(1))
        assert users_result is not None

        # Check runs table
        runs_result = await session.exec(select(PipelineRun).limit(1))
        assert runs_result is not None

        # Check leads table
        leads_result = await session.exec(select(Lead).limit(1))
        assert leads_result is not None


@pytest.mark.asyncio
async def test_02_persist_last_json_run_into_database():
    """Load and persist the last JSON run into PostgreSQL."""
    data_dir = ROOT_DIR / "data"
    candidates = sorted(data_dir.glob("run_*.json"))
    assert len(candidates) > 0, "No run_*.json files found in data/"

    # Target the latest complete run
    last_run_file = candidates[-1]

    async with get_session_context() as session:
        persisted_data = await PipelineService.persist_json_run_file(last_run_file, session=session)
        assert persisted_data is not None
        run_id = persisted_data.get("run_id")
        assert run_id, "Run data missing run_id"

        # Verify PipelineRun record in DB
        db_run = (await session.exec(select(PipelineRun).where(PipelineRun.id == run_id))).first()
        assert db_run is not None, f"Run {run_id} not found in database"
        assert db_run.status == "complete"
        assert db_run.lead_count > 0

        # Verify Leads in DB
        db_leads = (await session.exec(select(Lead).where(Lead.run_id == run_id))).all()
        assert len(db_leads) == db_run.lead_count
        assert len(db_leads) > 0

        # Verify lead contents
        sample_lead = db_leads[0]
        assert sample_lead.company_name
        assert sample_lead.final_score >= 0.0


@pytest.mark.asyncio
async def test_03_frontend_runs_endpoints_and_schema():
    """
    Test GET /api/runs and GET /api/runs/{run_id}.
    Validate exact contract expected by frontend Svelte client (RunSummary and Run).
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. GET /api/runs (List of RunSummary)
        res = await client.get("/api/runs")
        assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
        runs_list = res.json()
        assert isinstance(runs_list, list)
        assert len(runs_list) > 0

        # Verify RunSummary schema expected by frontend
        first_run = runs_list[0]
        expected_run_summary_keys = {"run_id", "started_at", "finished_at", "status", "funnel", "spend", "lead_count"}
        for k in expected_run_summary_keys:
            assert k in first_run, f"Missing key '{k}' in RunSummary response: {first_run.keys()}"

        run_id = first_run["run_id"]

        # 2. GET /api/runs/{run_id} (Full Run with Lead[])
        run_res = await client.get(f"/api/runs/{run_id}")
        assert run_res.status_code == 200
        run_data = run_res.json()

        for k in expected_run_summary_keys:
            assert k in run_data, f"Missing key '{k}' in Run response"

        assert "leads" in run_data
        leads = run_data["leads"]
        assert isinstance(leads, list)
        assert len(leads) > 0

        # Verify Lead schema expected by frontend (Lead interface in pipeline.ts & LeadRow.svelte)
        sample = leads[0]
        assert "id" in sample
        assert "company_name" in sample
        assert "is_competitor" in sample and isinstance(sample["is_competitor"], bool)
        assert "is_vertical_product" in sample and isinstance(sample["is_vertical_product"], bool)
        assert "signals" in sample and isinstance(sample["signals"], list)
        assert "tier1_score" in sample and isinstance(sample["tier1_score"], (int, float))
        assert "final_score" in sample and isinstance(sample["final_score"], (int, float))
        assert "founders" in sample and isinstance(sample["founders"], list)
        assert "email_result" in sample


@pytest.mark.asyncio
async def test_04_frontend_status_endpoint():
    """Test GET /api/status against frontend RunStatus schema."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/status")
        assert res.status_code == 200
        data = res.json()
        assert "status" in data
        assert data["status"] in ("idle", "running", "done", "complete", "error")


@pytest.mark.asyncio
async def test_05_leads_search_filter_and_status_update():
    """Test /api/leads search, filtering, status updates, and CSV export."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Query leads
        res = await client.get("/api/leads?limit=10")
        assert res.status_code == 200
        body = res.json()
        assert "total" in body
        assert "items" in body
        assert len(body["items"]) > 0

        lead = body["items"][0]
        lead_id = lead["id"]

        # 2. Filter by search query
        company_name = lead["company_name"]
        search_res = await client.get(f"/api/leads?query={company_name[:4]}")
        assert search_res.status_code == 200
        search_body = search_res.json()
        assert any(l["id"] == lead_id for l in search_body["items"])

        # 3. Update status (e.g. contacted)
        patch_res = await client.patch(
            f"/api/leads/{lead_id}/status",
            json={"outreach_status": "contacted", "notes": "Email sent via outreach campaign"},
        )
        assert patch_res.status_code == 200
        updated = patch_res.json()
        assert updated["outreach_status"] == "contacted"
        assert updated["notes"] == "Email sent via outreach campaign"

        # 4. Export CSV
        csv_res = await client.get("/api/leads/export/csv")
        assert csv_res.status_code == 200
        assert "text/csv" in csv_res.headers.get("content-type", "")
        csv_text = csv_res.text
        assert "Company Name" in csv_text
        assert "Final Score" in csv_text
        assert company_name in csv_text


@pytest.mark.asyncio
async def test_06_analytics_overview():
    """Test GET /api/analytics/overview."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/analytics/overview")
        assert res.status_code == 200
        stats = res.json()
        assert stats["total_leads"] > 0
        assert stats["total_runs"] > 0
        assert stats["avg_score"] >= 0.0
        assert "status_breakdown" in stats


@pytest.mark.asyncio
async def test_07_auth_workflow():
    """Test user registration, login, and JWT protected profile endpoint."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        import uuid
        unique_email = f"test_{uuid.uuid4().hex[:8]}@startupscrape.internal"
        password = "SecurePassword123!"

        # Register
        reg_res = await client.post(
            "/api/auth/register",
            json={"email": unique_email, "password": password, "full_name": "Test User"},
        )
        assert reg_res.status_code == 201
        reg_data = reg_res.json()
        assert reg_data["email"] == unique_email

        # Login
        login_res = await client.post(
            "/api/auth/login",
            json={"email": unique_email, "password": password},
        )
        assert login_res.status_code == 200
        token_data = login_res.json()
        assert "access_token" in token_data
        token = token_data["access_token"]

        # Authenticated /me
        me_res = await client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert me_res.status_code == 200
        me_data = me_res.json()
        assert me_data["email"] == unique_email


# ── Standalone CLI Runner ─────────────────────────────────────────────────────

async def run_all_tests():
    """Direct runner when executed as a script."""
    print("=" * 60)
    print("STARTUPSC RAPE BACKEND & DATABASE TEST RUNNER")
    print("=" * 60)

    tests = [
        ("Database Connection & Tables", test_01_database_connection_and_table_creation),
        ("Persist Last JSON Run to DB", test_02_persist_last_json_run_into_database),
        ("Frontend Runs Endpoint & Schema", test_03_frontend_runs_endpoints_and_schema),
        ("Frontend Status Endpoint", test_04_frontend_status_endpoint),
        ("Leads Filter, Status & CSV Export", test_05_leads_search_filter_and_status_update),
        ("Analytics Overview", test_06_analytics_overview),
        ("Auth Registration & JWT Me", test_07_auth_workflow),
    ]

    passed = 0
    failed = 0

    for name, test_func in tests:
        print(f"\n[RUNNING] {name}...")
        try:
            await test_func()
            print(f"[PASS] {name}")
            passed += 1
        except Exception as exc:
            print(f"[FAIL] {name}: {exc}")
            import traceback
            traceback.print_exc()
            failed += 1

    print("\n" + "=" * 60)
    print(f"RESULTS: {passed} PASSED, {failed} FAILED")
    print("=" * 60)
    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(run_all_tests())
