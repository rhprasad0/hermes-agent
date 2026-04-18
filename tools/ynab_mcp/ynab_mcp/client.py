from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from typing import Any

import httpx

from .config import Settings, normalize_month
from .errors import YnabApiError, YnabAuthError, YnabRateLimitError


class YnabClient:
    def __init__(self, settings: Settings, *, transport: httpx.BaseTransport | None = None):
        self.settings = settings
        self._resolved_default_plan_id: str | None = None
        self._client = httpx.Client(
            base_url=f"{settings.base_url}/",
            headers={"Authorization": f"Bearer {settings.access_token}"},
            timeout=settings.timeout,
            transport=transport,
        )

    def close(self) -> None:
        self._client.close()

    def list_plans(self) -> list[dict[str, Any]]:
        data = self._request_data("GET", "plans")
        return data.get("plans", [])

    def get_plan_summary(self, *, plan_id: str | None = None) -> dict[str, Any]:
        active_plan_id = self._resolve_plan_id(plan_id)
        plan = self._request_data("GET", f"plans/{active_plan_id}").get("plan", {})
        return {
            key: plan.get(key)
            for key in ["id", "name", "last_modified_on", "first_month", "last_month", "date_format", "currency_format"]
            if key in plan
        } | {
            "account_count": len(plan.get("accounts", [])),
            "category_group_count": len(plan.get("category_groups", [])),
            "payee_count": len(plan.get("payees", [])),
        }

    def list_accounts(self, *, plan_id: str | None = None, include_closed: bool = False) -> list[dict[str, Any]]:
        active_plan_id = self._resolve_plan_id(plan_id)
        accounts = self._request_data("GET", f"plans/{active_plan_id}/accounts").get("accounts", [])
        if not include_closed:
            accounts = [account for account in accounts if not account.get("closed")]
        return accounts

    def list_categories(self, *, plan_id: str | None = None) -> list[dict[str, Any]]:
        active_plan_id = self._resolve_plan_id(plan_id)
        return self._request_data("GET", f"plans/{active_plan_id}/categories").get("category_groups", [])

    def get_month_overview(self, *, plan_id: str | None = None, month: str = "current") -> dict[str, Any]:
        active_plan_id = self._resolve_plan_id(plan_id)
        normalized_month = normalize_month(month)
        return self._request_data("GET", f"plans/{active_plan_id}/months/{normalized_month}").get("month", {})

    def get_category_balance(self, *, category: str, plan_id: str | None = None, month: str = "current") -> dict[str, Any]:
        active_plan_id = self._resolve_plan_id(plan_id)
        category_id = self._resolve_category_id(active_plan_id, category)
        normalized_month = normalize_month(month)
        return self._request_data(
            "GET",
            f"plans/{active_plan_id}/months/{normalized_month}/categories/{category_id}",
        ).get("category", {})

    def list_transactions(
        self,
        *,
        plan_id: str | None = None,
        since_date: str | None = None,
        account_id: str | None = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        active_plan_id = self._resolve_plan_id(plan_id)
        path = f"plans/{active_plan_id}/transactions"
        if account_id:
            path = f"plans/{active_plan_id}/accounts/{account_id}/transactions"
        params = {"since_date": since_date} if since_date else None
        data = self._request_data("GET", path, params=params)
        transactions = data.get("transactions", [])
        return transactions[:limit]

    def list_scheduled_transactions(self, *, plan_id: str | None = None) -> list[dict[str, Any]]:
        active_plan_id = self._resolve_plan_id(plan_id)
        data = self._request_data("GET", f"plans/{active_plan_id}/scheduled_transactions")
        return data.get("scheduled_transactions", [])

    def create_transaction(
        self,
        *,
        account: str,
        amount: int | float | str,
        date: str,
        payee_name: str | None = None,
        category: str | None = None,
        memo: str | None = None,
        cleared: str = "uncleared",
        approved: bool = True,
        direction: str = "outflow",
        plan_id: str | None = None,
    ) -> dict[str, Any]:
        active_plan_id = self._resolve_plan_id(plan_id)
        payload: dict[str, Any] = {
            "account_id": self._resolve_account_id(active_plan_id, account),
            "date": date,
            "amount": self._amount_to_milliunits(amount, direction=direction),
            "cleared": cleared,
            "approved": approved,
        }
        if payee_name:
            payload["payee_name"] = payee_name
        if category:
            payload["category_id"] = self._resolve_category_id(active_plan_id, category)
        if memo:
            payload["memo"] = memo

        data = self._request_data(
            "POST",
            f"plans/{active_plan_id}/transactions",
            json_body={"transaction": payload},
        )
        return data.get("transaction") or (data.get("transactions") or [{}])[0]

    def update_transaction(
        self,
        *,
        transaction_id: str,
        amount: int | float | str | None = None,
        date: str | None = None,
        payee_name: str | None = None,
        category: str | None = None,
        memo: str | None = None,
        cleared: str | None = None,
        approved: bool | None = None,
        direction: str | None = None,
        plan_id: str | None = None,
    ) -> dict[str, Any]:
        active_plan_id = self._resolve_plan_id(plan_id)
        existing = self.get_transaction(transaction_id=transaction_id, plan_id=active_plan_id)
        resolved_direction = direction or ("inflow" if int(existing.get("amount", 0)) >= 0 else "outflow")
        payload: dict[str, Any] = {
            "id": existing["id"],
            "account_id": existing["account_id"],
            "date": date or existing["date"],
            "amount": self._amount_to_milliunits(amount, direction=resolved_direction)
            if amount is not None
            else existing["amount"],
            "payee_name": payee_name if payee_name is not None else existing.get("payee_name"),
            "category_id": self._resolve_category_id(active_plan_id, category)
            if category is not None
            else existing.get("category_id"),
            "memo": memo if memo is not None else existing.get("memo"),
            "cleared": cleared if cleared is not None else existing.get("cleared"),
            "approved": approved if approved is not None else existing.get("approved"),
        }

        data = self._request_data(
            "PUT",
            f"plans/{active_plan_id}/transactions/{transaction_id}",
            json_body={"transaction": payload},
        )
        return data.get("transaction", {})

    def set_month_category_budgeted(
        self,
        *,
        category: str,
        budgeted_amount: int | float | str,
        month: str = "current",
        plan_id: str | None = None,
    ) -> dict[str, Any]:
        active_plan_id = self._resolve_plan_id(plan_id)
        category_id = self._resolve_category_id(active_plan_id, category)
        normalized_month = normalize_month(month)
        data = self._request_data(
            "PATCH",
            f"plans/{active_plan_id}/months/{normalized_month}/categories/{category_id}",
            json_body={"category": {"budgeted": self._amount_to_milliunits(budgeted_amount, direction="inflow")}},
        )
        return data.get("category", {})

    def get_transaction(self, *, transaction_id: str, plan_id: str | None = None) -> dict[str, Any]:
        active_plan_id = self._resolve_plan_id(plan_id)
        return self._request_data("GET", f"plans/{active_plan_id}/transactions/{transaction_id}").get("transaction", {})

    def _resolve_plan_id(self, plan_id: str | None) -> str:
        active_plan_id = plan_id or self.settings.plan_id
        if active_plan_id != "default":
            return active_plan_id
        if self._resolved_default_plan_id:
            return self._resolved_default_plan_id

        plans = self.list_plans()
        if len(plans) == 1:
            self._resolved_default_plan_id = plans[0]["id"]
            return self._resolved_default_plan_id
        if not plans:
            raise YnabApiError("No YNAB plans are visible to the configured token.")
        raise YnabApiError(
            "YNAB_PLAN_ID is set to 'default' but multiple plans are visible. Set YNAB_PLAN_ID to a specific plan id."
        )

    def _resolve_account_id(self, plan_id: str, account: str) -> str:
        identifier = account.strip()
        accounts = self.list_accounts(plan_id=plan_id, include_closed=True)
        for item in accounts:
            if item.get("id") == identifier:
                return identifier
        return self._resolve_by_name(identifier, accounts, "account")

    def _resolve_category_id(self, plan_id: str, category: str) -> str:
        identifier = category.strip()
        categories = [item for group in self.list_categories(plan_id=plan_id) for item in group.get("categories", [])]
        for item in categories:
            if item.get("id") == identifier:
                return identifier
        return self._resolve_by_name(identifier, categories, "category")

    @staticmethod
    def _resolve_by_name(identifier: str, items: list[dict[str, Any]], item_type: str) -> str:
        exact_matches: list[str] = []
        partial_matches: list[str] = []
        lowered = identifier.casefold()
        for item in items:
            name = str(item.get("name", ""))
            if name.casefold() == lowered:
                exact_matches.append(item["id"])
            elif lowered in name.casefold():
                partial_matches.append(item["id"])

        if len(exact_matches) == 1:
            return exact_matches[0]
        if len(exact_matches) > 1:
            raise YnabApiError(f"multiple {item_type}s matched '{identifier}'")
        if len(partial_matches) == 1:
            return partial_matches[0]
        if len(partial_matches) > 1:
            raise YnabApiError(f"multiple {item_type}s partially matched '{identifier}'")
        raise YnabApiError(f"{item_type} not found: {identifier}")

    @staticmethod
    def _amount_to_milliunits(amount: int | float | str, *, direction: str) -> int:
        value = Decimal(str(amount)).copy_abs()
        milliunits = int((value * Decimal("1000")).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
        if direction == "outflow":
            return -milliunits
        if direction == "inflow":
            return milliunits
        raise YnabApiError("direction must be 'outflow' or 'inflow'")

    def _request_data(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        try:
            response = self._client.request(method, path, params=params, json=json_body)
        except httpx.RequestError as exc:
            raise YnabApiError(f"YNAB request failed: {exc}") from exc

        if response.status_code == 401:
            raise YnabAuthError("YNAB authentication failed. Check YNAB_ACCESS_TOKEN.")
        if response.status_code == 429:
            raise YnabRateLimitError("YNAB rate limit exceeded (200 requests/hour rolling window).")
        if response.is_error:
            raise YnabApiError(self._extract_error_detail(response))

        payload = response.json()
        return payload.get("data", {})

    @staticmethod
    def _extract_error_detail(response: httpx.Response) -> str:
        try:
            payload = response.json()
        except ValueError:
            return f"YNAB API error {response.status_code}"
        error = payload.get("error") or {}
        detail = error.get("detail") or error.get("name") or response.text
        return f"YNAB API error {response.status_code}: {detail}"
