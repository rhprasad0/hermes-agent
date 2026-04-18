import json

import httpx
import pytest

from ynab_mcp.client import YnabClient
from ynab_mcp.config import Settings
from ynab_mcp.errors import YnabAuthError, YnabRateLimitError


def make_settings(plan_id: str = "default") -> Settings:
    return Settings(
        access_token="test-token",
        plan_id=plan_id,
        base_url="https://api.ynab.example/v1",
        timeout=12,
    )


def test_list_plans_sends_bearer_auth_and_returns_plans():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["Authorization"] == "Bearer test-token"
        assert request.url.path == "/v1/plans"
        return httpx.Response(200, json={"data": {"plans": [{"id": "plan-1", "name": "Household"}]}})

    client = YnabClient(make_settings(), transport=httpx.MockTransport(handler))

    plans = client.list_plans()

    assert plans == [{"id": "plan-1", "name": "Household"}]


def test_get_month_overview_normalizes_year_month_path():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/plans/plan-1/months/2026-04-01"
        return httpx.Response(200, json={"data": {"month": {"month": "2026-04-01", "note": "ok"}}})

    client = YnabClient(make_settings(plan_id="plan-1"), transport=httpx.MockTransport(handler))

    month = client.get_month_overview(month="2026-04")

    assert month["month"] == "2026-04-01"


def test_default_plan_id_resolves_single_visible_plan_before_month_lookup():
    seen_paths: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen_paths.append(request.url.path)
        if request.url.path == "/v1/plans":
            return httpx.Response(200, json={"data": {"plans": [{"id": "plan-1", "name": "Household"}]}})
        if request.url.path == "/v1/plans/plan-1/months/2026-04-01":
            return httpx.Response(200, json={"data": {"month": {"month": "2026-04-01", "note": "ok"}}})
        return httpx.Response(404, json={"error": {"detail": "missing"}})

    client = YnabClient(make_settings(), transport=httpx.MockTransport(handler))

    month = client.get_month_overview(month="2026-04")

    assert month["month"] == "2026-04-01"
    assert seen_paths == ["/v1/plans", "/v1/plans/plan-1/months/2026-04-01"]


def test_create_transaction_resolves_account_and_category_names_and_posts_payload():
    seen_paths: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen_paths.append(request.url.path)
        if request.url.path == "/v1/plans/plan-1/accounts":
            return httpx.Response(200, json={"data": {"accounts": [{"id": "acct-1", "name": "Checking", "closed": False}]}})
        if request.url.path == "/v1/plans/plan-1/categories":
            return httpx.Response(
                200,
                json={"data": {"category_groups": [{"name": "Core", "categories": [{"id": "cat-1", "name": "Groceries"}]}]}},
            )
        if request.url.path == "/v1/plans/plan-1/transactions":
            assert request.method == "POST"
            assert json.loads(request.content.decode()) == {
                "transaction": {
                    "account_id": "acct-1",
                    "date": "2026-04-18",
                    "amount": -23450,
                    "payee_name": "Cafe",
                    "category_id": "cat-1",
                    "memo": "Lunch",
                    "cleared": "cleared",
                    "approved": True,
                }
            }
            return httpx.Response(201, json={"data": {"transaction": {"id": "tx-1", "amount": -23450}}})
        return httpx.Response(404, json={"error": {"detail": "missing"}})

    client = YnabClient(make_settings(plan_id="plan-1"), transport=httpx.MockTransport(handler))

    transaction = client.create_transaction(
        account="Checking",
        amount=23.45,
        date="2026-04-18",
        payee_name="Cafe",
        category="Groceries",
        memo="Lunch",
        cleared="cleared",
        approved=True,
    )

    assert transaction == {"id": "tx-1", "amount": -23450}
    assert seen_paths == [
        "/v1/plans/plan-1/accounts",
        "/v1/plans/plan-1/categories",
        "/v1/plans/plan-1/transactions",
    ]


def test_update_transaction_fetches_existing_transaction_and_puts_merged_payload():
    seen_paths: list[str] = []

    existing_transaction = {
        "id": "tx-1",
        "account_id": "acct-1",
        "date": "2026-04-18",
        "amount": -1250,
        "payee_name": "Old Payee",
        "category_id": "cat-old",
        "memo": "old memo",
        "cleared": "uncleared",
        "approved": False,
    }

    def handler(request: httpx.Request) -> httpx.Response:
        seen_paths.append(f"{request.method} {request.url.path}")
        if request.url.path == "/v1/plans/plan-1/transactions/tx-1" and request.method == "GET":
            return httpx.Response(200, json={"data": {"transaction": existing_transaction}})
        if request.url.path == "/v1/plans/plan-1/categories" and request.method == "GET":
            return httpx.Response(
                200,
                json={"data": {"category_groups": [{"name": "Core", "categories": [{"id": "cat-1", "name": "Dining Out"}]}]}},
            )
        if request.url.path == "/v1/plans/plan-1/transactions/tx-1" and request.method == "PUT":
            assert json.loads(request.content.decode()) == {
                "transaction": {
                    "id": "tx-1",
                    "account_id": "acct-1",
                    "date": "2026-04-18",
                    "amount": -2500,
                    "payee_name": "New Payee",
                    "category_id": "cat-1",
                    "memo": "updated memo",
                    "cleared": "cleared",
                    "approved": True,
                }
            }
            return httpx.Response(200, json={"data": {"transaction": {"id": "tx-1", "amount": -2500, "memo": "updated memo"}}})
        return httpx.Response(404, json={"error": {"detail": "missing"}})

    client = YnabClient(make_settings(plan_id="plan-1"), transport=httpx.MockTransport(handler))

    transaction = client.update_transaction(
        transaction_id="tx-1",
        amount=2.50,
        payee_name="New Payee",
        category="Dining Out",
        memo="updated memo",
        cleared="cleared",
        approved=True,
    )

    assert transaction["amount"] == -2500
    assert seen_paths == [
        "GET /v1/plans/plan-1/transactions/tx-1",
        "GET /v1/plans/plan-1/categories",
        "PUT /v1/plans/plan-1/transactions/tx-1",
    ]


def test_set_month_category_budgeted_patches_budgeted_milliunits():
    seen_paths: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen_paths.append(f"{request.method} {request.url.path}")
        if request.url.path == "/v1/plans/plan-1/categories":
            return httpx.Response(
                200,
                json={"data": {"category_groups": [{"name": "Core", "categories": [{"id": "cat-1", "name": "Groceries"}]}]}},
            )
        if request.url.path == "/v1/plans/plan-1/months/2026-04-01/categories/cat-1":
            assert request.method == "PATCH"
            assert json.loads(request.content.decode()) == {"category": {"budgeted": 50000}}
            return httpx.Response(200, json={"data": {"category": {"id": "cat-1", "budgeted": 50000}}})
        return httpx.Response(404, json={"error": {"detail": "missing"}})

    client = YnabClient(make_settings(plan_id="plan-1"), transport=httpx.MockTransport(handler))

    category = client.set_month_category_budgeted(category="Groceries", month="2026-04", budgeted_amount=50)

    assert category == {"id": "cat-1", "budgeted": 50000}
    assert seen_paths == [
        "GET /v1/plans/plan-1/categories",
        "PATCH /v1/plans/plan-1/months/2026-04-01/categories/cat-1",
    ]


@pytest.mark.parametrize(
    ("status_code", "expected_error"),
    [
        (401, YnabAuthError),
        (429, YnabRateLimitError),
    ],
)
def test_request_maps_auth_and_rate_limit_errors(status_code, expected_error):
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code, json={"error": {"detail": "nope"}})

    client = YnabClient(make_settings(), transport=httpx.MockTransport(handler))

    with pytest.raises(expected_error):
        client.list_plans()
