import asyncio
import json

from ynab_mcp.config import Settings
from ynab_mcp.server import create_mcp


class FakeClient:
    def list_plans(self):
        return [{"id": "plan-1", "name": "Household"}]

    def get_month_overview(self, *, plan_id: str, month: str):
        return {"plan_id": plan_id, "month": month, "summary": {"ready_to_assign": 12345}}

    def create_transaction(self, **kwargs):
        return {"id": "tx-1", **kwargs}

    def update_transaction(self, **kwargs):
        return {"id": kwargs["transaction_id"], **kwargs}

    def set_month_category_budgeted(self, **kwargs):
        return {"id": "cat-1", **kwargs}


def test_mcp_server_exposes_expected_tools():
    settings = Settings(
        access_token="test-token",
        plan_id="default",
        base_url="https://api.ynab.example/v1",
        timeout=30,
    )
    mcp = create_mcp(settings=settings, client_factory=lambda _settings: FakeClient())

    tools = asyncio.run(mcp.list_tools())
    names = {tool.name for tool in tools}

    assert "list_plans" in names
    assert "get_month_overview" in names
    assert "create_transaction" in names
    assert "update_transaction" in names
    assert "set_month_category_budgeted" in names


def test_get_month_overview_tool_uses_default_plan_id():
    settings = Settings(
        access_token="test-token",
        plan_id="default",
        base_url="https://api.ynab.example/v1",
        timeout=30,
    )
    mcp = create_mcp(settings=settings, client_factory=lambda _settings: FakeClient())

    result = asyncio.run(mcp.call_tool("get_month_overview", {"month": "2026-04"}))
    payload = json.loads(result[0].text)

    assert payload["plan_id"] == "default"
    assert payload["month"] == "2026-04"
    assert payload["summary"]["ready_to_assign"] == 12345


def test_create_transaction_tool_uses_default_plan_id():
    settings = Settings(
        access_token="test-token",
        plan_id="default",
        base_url="https://api.ynab.example/v1",
        timeout=30,
    )
    mcp = create_mcp(settings=settings, client_factory=lambda _settings: FakeClient())

    result = asyncio.run(
        mcp.call_tool(
            "create_transaction",
            {
                "account": "Checking",
                "amount": 12.34,
                "date": "2026-04-18",
                "payee_name": "Cafe",
                "category": "Dining Out",
            },
        )
    )
    payload = json.loads(result[0].text)

    assert payload["plan_id"] == "default"
    assert payload["transaction"]["amount"] == 12.34
    assert payload["transaction"]["account"] == "Checking"


def test_set_month_category_budgeted_tool_uses_default_plan_id():
    settings = Settings(
        access_token="test-token",
        plan_id="default",
        base_url="https://api.ynab.example/v1",
        timeout=30,
    )
    mcp = create_mcp(settings=settings, client_factory=lambda _settings: FakeClient())

    result = asyncio.run(
        mcp.call_tool(
            "set_month_category_budgeted",
            {"category": "Groceries", "month": "2026-04", "budgeted_amount": 50},
        )
    )
    payload = json.loads(result[0].text)

    assert payload["plan_id"] == "default"
    assert payload["category"]["budgeted_amount"] == 50
