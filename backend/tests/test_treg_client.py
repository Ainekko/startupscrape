import asyncio
import json

import httpx

from app.trigger_engine.treg_client import TregClient


def _client(handler) -> TregClient:
    return TregClient(token="tok", base_url="https://treg.test", transport=httpx.MockTransport(handler))


def test_post_call_sends_auth_cap_and_body_and_reads_header_cost():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["method"] = request.method
        seen["path"] = request.url.path
        seen["token"] = request.headers.get("x-treg-token")
        seen["cap"] = request.headers.get("x-treg-route-max-cost")
        seen["body"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={"output": {"posts": []}, "_treg": {"served_by": "fetchinio"}},
            headers={"X-Treg-Cost-Micro": "1500", "X-Treg-Call-Id": "call_1", "X-Treg-Served-By": "fetchinio"},
        )

    client = _client(handler)
    res = asyncio.run(client.call("treg.linkedin.user.posts", json={"linkedin_url": "u"}, max_cost=0.006))

    assert seen == {
        "method": "POST",
        "path": "/call/treg.linkedin.user.posts",
        "token": "tok",
        "cap": "0.0060",
        "body": {"linkedin_url": "u"},
    }
    assert res["success"] is True
    assert res["cost_usd"] == 0.0015
    assert res["call_id"] == "call_1"
    assert res["served_by"] == "fetchinio"
    assert client.total_cost_usd == 0.0015
    assert client.calls_made == 1


def test_get_call_uses_query_params_without_body_and_drops_none():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["method"] = request.method
        seen["params"] = dict(request.url.params)
        seen["content"] = request.content
        seen["content_type"] = request.headers.get("content-type")
        return httpx.Response(200, json={"elements": []}, headers={"X-Treg-Cost-Micro": "4000"})

    client = _client(handler)
    res = asyncio.run(client.call(
        "harvestapi.linkedin.company.posts",
        method="GET",
        params={"companyUniversalName": "acme", "page": 1, "paginationToken": None},
    ))

    assert seen["method"] == "GET"
    assert seen["params"] == {"companyUniversalName": "acme", "page": "1"}
    assert seen["content"] == b""
    assert seen["content_type"] is None
    assert res["success"] is True and res["cost_usd"] == 0.004


def test_body_cost_fallback_when_header_missing():
    client = _client(lambda r: httpx.Response(200, json={"costUsd": 0.0005, "output": {}}))
    res = asyncio.run(client.call("anyapi.linkedin.search.jobs", json={"query": "x"}))
    assert res["cost_usd"] == 0.0005


def test_routed_charged_micro_fallback():
    client = _client(lambda r: httpx.Response(200, json={"output": {}, "_treg": {"charged_micro": 2500}}))
    res = asyncio.run(client.call("treg.linkedin.post.comments", json={"post_urn": "x"}))
    assert res["cost_usd"] == 0.0025


def test_error_status_is_not_billed():
    client = _client(lambda r: httpx.Response(402, json={"detail": "balance"}, headers={"X-Treg-Call-Id": "c9"}))
    res = asyncio.run(client.call("treg.linkedin.user.posts", json={}))
    assert res["success"] is False
    assert res["status_code"] == 402
    assert res["cost_usd"] == 0.0
    assert res["call_id"] == "c9"
    assert client.total_cost_usd == 0.0


def test_pending_202_is_flagged_and_not_success():
    client = _client(lambda r: httpx.Response(202, json={"_treg": {"outcome": "pending"}}))
    res = asyncio.run(client.call("treg.linkedin.user.posts", json={}))
    assert res["success"] is False
    assert res["pending"] is True


def test_network_exception_is_caught():
    def handler(request):
        raise httpx.ConnectError("boom", request=request)

    client = _client(handler)
    res = asyncio.run(client.call("treg.google.serp.organic", json={"q": "x"}))
    assert res["success"] is False
    assert "boom" in res["error"]


def test_call_endpoint_backward_compatible_post():
    seen = {}

    def handler(request):
        seen["method"] = request.method
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json={"output": {"organic_results": []}}, headers={"X-Treg-Cost-Micro": "150"})

    client = _client(handler)
    res = asyncio.run(client.call_endpoint("treg.google.serp.organic", payload={"q": "acme"}, max_cost=0.005))
    assert seen == {"method": "POST", "body": {"q": "acme"}}
    assert res["success"] is True and res["cost_usd"] == 0.00015

