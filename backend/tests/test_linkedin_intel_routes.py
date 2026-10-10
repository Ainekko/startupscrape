"""HTTP contract tests for /api/triggers/linkedin/intel* (no DB, FakeTreg)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.db import get_session
from app.main import app
from app.trigger_engine import routes as trigger_routes
from app.trigger_engine.linkedin_intel import LinkedInIntelService
from tests.linkedin_fixtures import NOW, FakeTreg

BASE = "/api/triggers/linkedin/intel"


class PinnedIntelService(LinkedInIntelService):
    async def gather(self, account, options=None, extra_founder_urls=None, now=None):
        return await super().gather(account, options=options, extra_founder_urls=extra_founder_urls, now=NOW)


async def _no_session():
    yield None


@pytest.fixture
def client(monkeypatch):
    fake = FakeTreg()
    monkeypatch.setattr(trigger_routes, "_linkedin_intel", PinnedIntelService(treg_client=fake))
    app.dependency_overrides[get_session] = _no_session
    try:
        yield TestClient(app), fake  # no context manager → lifespan (DB init) is not run
    finally:
        app.dependency_overrides.pop(get_session, None)


def test_intel_by_company_name(client):
    http, fake = client
    res = http.post(BASE, json={
        "company_name": "Acme AI",
        "company_linkedin_url": "https://www.linkedin.com/company/acme-ai",
        "founder_linkedin_urls": ["https://www.linkedin.com/in/jane-doe"],
    })
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["company_name"] == "Acme AI"
    assert body["company_linkedin_url"].rstrip("/").endswith("/company/acme-ai")
    assert body["signals"]
    assert body["company_posts"]
    assert body["post_comments"]
    assert body["calls_made"] == len(fake.calls)
    assert 1 <= body["urgency_score"] <= 10


def test_intel_requires_company(client):
    http, fake = client
    res = http.post(BASE, json={})
    assert res.status_code == 400
    assert fake.calls == []


def test_intel_lead_id_without_db_is_503(client):
    http, _ = client
    assert http.post(BASE, json={"lead_id": "lead_x"}).status_code == 503


def test_intel_lead_id_with_company_name_works_without_db(client):
    http, _ = client
    res = http.post(BASE, json={
        "lead_id": "lead_x",
        "company_name": "Acme AI",
        "company_linkedin_url": "https://www.linkedin.com/company/acme-ai",
    })
    assert res.status_code == 200, res.text
    assert res.json()["lead_id"] == "lead_x"


def test_get_snapshot_without_db_is_503(client):
    http, _ = client
    assert http.get(f"{BASE}/lead_x").status_code == 503


def test_batch_without_db_is_503(client):
    http, _ = client
    assert http.post(f"{BASE}/batch", json={}).status_code == 503

