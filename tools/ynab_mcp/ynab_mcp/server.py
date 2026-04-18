from __future__ import annotations

from contextlib import closing
from typing import Callable

from mcp.server.fastmcp import FastMCP

from .client import YnabClient
from .config import Settings


def create_mcp(
    *,
    settings: Settings | None = None,
    client_factory: Callable[[Settings], object] | None = None,
) -> FastMCP:
    resolved_settings = settings or Settings.from_env()
    factory = client_factory or (lambda s: YnabClient(s))
    mcp = FastMCP("ynab", instructions="Read and write YNAB tools for Hermes budgeting workflows. Prefer explicit confirmation before write actions.")

    def run_with_client(callback):
        client = factory(resolved_settings)
        close = getattr(client, "close", None)
        if callable(close):
            with closing(client):
                return callback(client)
        return callback(client)

    def resolved_plan_id(plan_id: str | None) -> str:
        return plan_id or resolved_settings.plan_id

    @mcp.tool(description="List YNAB plans visible to the configured token.")
    def list_plans() -> dict:
        plans = run_with_client(lambda client: client.list_plans())
        return {"plans": plans, "plan_count": len(plans)}

    @mcp.tool(description="Get a compact summary for a YNAB plan.")
    def get_plan_summary(plan_id: str | None = None) -> dict:
        active_plan_id = resolved_plan_id(plan_id)
        summary = run_with_client(lambda client: client.get_plan_summary(plan_id=active_plan_id))
        return {"plan_id": active_plan_id, **summary}

    @mcp.tool(description="List YNAB accounts for a plan.")
    def list_accounts(plan_id: str | None = None, include_closed: bool = False) -> dict:
        active_plan_id = resolved_plan_id(plan_id)
        accounts = run_with_client(
            lambda client: client.list_accounts(plan_id=active_plan_id, include_closed=include_closed)
        )
        return {"plan_id": active_plan_id, "accounts": accounts, "account_count": len(accounts)}

    @mcp.tool(description="List YNAB category groups and categories for a plan.")
    def list_categories(plan_id: str | None = None) -> dict:
        active_plan_id = resolved_plan_id(plan_id)
        groups = run_with_client(lambda client: client.list_categories(plan_id=active_plan_id))
        return {"plan_id": active_plan_id, "category_groups": groups, "group_count": len(groups)}

    @mcp.tool(description="Get a month overview for a YNAB plan. Month may be 'current', YYYY-MM, or YYYY-MM-DD.")
    def get_month_overview(plan_id: str | None = None, month: str = "current") -> dict:
        active_plan_id = resolved_plan_id(plan_id)
        overview = run_with_client(lambda client: client.get_month_overview(plan_id=active_plan_id, month=month))
        return {"plan_id": active_plan_id, "month": month, **overview}

    @mcp.tool(description="Get a category balance by category id or name for a plan month.")
    def get_category_balance(category: str, plan_id: str | None = None, month: str = "current") -> dict:
        active_plan_id = resolved_plan_id(plan_id)
        category_data = run_with_client(
            lambda client: client.get_category_balance(category=category, plan_id=active_plan_id, month=month)
        )
        return {"plan_id": active_plan_id, "month": month, **category_data}

    @mcp.tool(description="List recent YNAB transactions for a plan, optionally filtered by account and since_date.")
    def list_transactions(
        plan_id: str | None = None,
        since_date: str | None = None,
        account_id: str | None = None,
        limit: int = 10,
    ) -> dict:
        active_plan_id = resolved_plan_id(plan_id)
        transactions = run_with_client(
            lambda client: client.list_transactions(
                plan_id=active_plan_id,
                since_date=since_date,
                account_id=account_id,
                limit=limit,
            )
        )
        return {
            "plan_id": active_plan_id,
            "since_date": since_date,
            "account_id": account_id,
            "limit": limit,
            "transactions": transactions,
            "transaction_count": len(transactions),
        }

    @mcp.tool(description="List scheduled YNAB transactions for a plan.")
    def list_scheduled_transactions(plan_id: str | None = None) -> dict:
        active_plan_id = resolved_plan_id(plan_id)
        scheduled = run_with_client(lambda client: client.list_scheduled_transactions(plan_id=active_plan_id))
        return {"plan_id": active_plan_id, "scheduled_transactions": scheduled, "transaction_count": len(scheduled)}

    @mcp.tool(description="Create a single YNAB transaction. Amount is in normal currency units; direction controls inflow vs outflow.")
    def create_transaction(
        account: str,
        amount: float,
        date: str,
        payee_name: str | None = None,
        category: str | None = None,
        memo: str | None = None,
        cleared: str = "uncleared",
        approved: bool = True,
        direction: str = "outflow",
        plan_id: str | None = None,
    ) -> dict:
        active_plan_id = resolved_plan_id(plan_id)
        transaction = run_with_client(
            lambda client: client.create_transaction(
                plan_id=active_plan_id,
                account=account,
                amount=amount,
                date=date,
                payee_name=payee_name,
                category=category,
                memo=memo,
                cleared=cleared,
                approved=approved,
                direction=direction,
            )
        )
        return {"plan_id": active_plan_id, "transaction": transaction}

    @mcp.tool(description="Update a single YNAB transaction by id. Only provided fields are changed.")
    def update_transaction(
        transaction_id: str,
        amount: float | None = None,
        date: str | None = None,
        payee_name: str | None = None,
        category: str | None = None,
        memo: str | None = None,
        cleared: str | None = None,
        approved: bool | None = None,
        direction: str | None = None,
        plan_id: str | None = None,
    ) -> dict:
        active_plan_id = resolved_plan_id(plan_id)
        transaction = run_with_client(
            lambda client: client.update_transaction(
                plan_id=active_plan_id,
                transaction_id=transaction_id,
                amount=amount,
                date=date,
                payee_name=payee_name,
                category=category,
                memo=memo,
                cleared=cleared,
                approved=approved,
                direction=direction,
            )
        )
        return {"plan_id": active_plan_id, "transaction": transaction}

    @mcp.tool(description="Set the assigned/budgeted amount for a category in a plan month. Amount is in normal currency units.")
    def set_month_category_budgeted(
        category: str,
        budgeted_amount: float,
        month: str = "current",
        plan_id: str | None = None,
    ) -> dict:
        active_plan_id = resolved_plan_id(plan_id)
        category_data = run_with_client(
            lambda client: client.set_month_category_budgeted(
                plan_id=active_plan_id,
                category=category,
                budgeted_amount=budgeted_amount,
                month=month,
            )
        )
        return {"plan_id": active_plan_id, "month": month, "category": category_data}

    return mcp


def main() -> None:
    create_mcp().run(transport="stdio")


if __name__ == "__main__":
    main()
