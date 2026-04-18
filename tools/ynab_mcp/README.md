# YNAB MCP for Hermes

Small MCP server for using the official YNAB API from Hermes.

What it exposes:
- list plans
- plan summary
- list accounts
- list categories
- get month overview
- get category balance by id or name
- list recent transactions
- list scheduled transactions
- create a single transaction
- update a single transaction
- set a category's assigned/budgeted amount for a month

## Local setup

1. Create a local env file outside the repo, for example:
   - `~/.config/hermes-ynab/ynab.env`
2. Put your real token there:

```bash
YNAB_ACCESS_TOKEN=YOUR_REAL_TOKEN_HERE
YNAB_PLAN_ID=default
```

3. Register the server in `~/.hermes/config.yaml` using `uv run --project ...`
4. Restart Hermes / Hermes gateway.

If the token can see more than one YNAB plan, set `YNAB_PLAN_ID` to the specific plan id instead of leaving it as `default`.

## Run tests

```bash
uv run --project tools/ynab_mcp pytest tools/ynab_mcp/tests -q
```

## Run the server directly

```bash
uv run --project tools/ynab_mcp python -m ynab_mcp.server
```

## Security notes

- Keep the real token out of this repo.
- Prefer `chmod 600` on the local env file.
- Read operations are safe by default; write operations should only happen on explicit user request.
- Current write surface is intentionally small: single-transaction create/update and category-month budgeting.
- Recommended Slack policy is YOLO-lite: execute clearly worded requests directly, but stop and ask when account, category, transaction, or intent matching is ambiguous.
