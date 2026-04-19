# Budget Bot — Customization Specification

A specification for building and customizing a Hermes budget bot: a Slack channel where your agent becomes your primary interface to YNAB, reading live budget data and performing explicit writes on your behalf.

Hand this document to a coding agent and tell it what to customize. Every section is explicitly labeled as **required** or **optional**.

---

## What this builds

A dedicated Slack channel where Hermes:

- Answers budget questions using **live YNAB data** via an MCP server
- **Logs transactions**, updates them, and adjusts category budgets on explicit request
- Operates as a **budget coach** — forward-thinking, willing to call out bad calls
- Maintains **channel-scoped memory** so budget context doesn't leak into other channels

The user should never need to open YNAB directly for routine tasks.

---

## Architecture

```
Slack #budget channel
  └─ Hermes gateway (channel prompt + session config)
       └─ YNAB MCP server (stdio, via uv)
            └─ YNAB API (api.ynab.com/v1, v2 migration noted below)
```

Three integration layers:

1. **MCP server** (`tools/ynab_mcp/`) — Python package that wraps the YNAB API as MCP tools
2. **Hermes config** (`~/.hermes/config.yaml`) — channel prompt, session behavior, MCP registration
3. **Honcho scoping** (`~/.hermes/honcho.json`) — keeps memory channel-isolated

All local state (tokens, config) lives **outside** this repo. The repo holds the MCP server code, runbooks, and this spec. No secrets committed.

---

## 1. MCP Server (required)

The MCP server is a Python package at `tools/ynab_mcp/` built on `mcp` (FastMCP) and `httpx`.

### 1.1 Project structure

```
tools/ynab_mcp/
├── pyproject.toml          # uv project, deps: httpx, mcp
├── README.md
├── ynab_mcp/
│   ├── __init__.py
│   ├── server.py           # FastMCP tool definitions
│   ├── client.py           # YNAB API client (httpx sync)
│   ├── config.py           # Settings from env file / environment
│   └── errors.py           # Typed error hierarchy
└── tests/
    ├── __init__.py
    ├── test_server.py
    ├── test_client.py
    └── test_config.py
```

### 1.2 Tools exposed

| Tool | Direction | Description |
|------|-----------|-------------|
| `list_plans` | read | List YNAB plans visible to the token |
| `get_plan_summary` | read | Compact plan metadata |
| `list_accounts` | read | Accounts in a plan |
| `list_categories` | read | Category groups and categories |
| `get_month_overview` | read | Monthly budget overview |
| `get_category_balance` | read | Single category balance by id or name |
| `list_transactions` | read | Recent transactions, filterable by account and date |
| `list_scheduled_transactions` | read | Upcoming scheduled transactions |
| `create_transaction` | write | Single transaction create |
| `update_transaction` | write | Single transaction update by id |
| `set_month_category_budgeted` | write | Set a category's assigned amount for a month |

### 1.3 Key client behaviors to preserve

- **Name resolution**: Account and category parameters accept either a YNAB id or a human-readable name. Exact match first, then case-insensitive partial match. If multiple matches exist, raise an error rather than guessing.
- **Amount handling**: Amounts are in normal currency units (e.g. `42.50`). The client converts to YNAB milliunits internally (±42500) based on the `direction` parameter (`"outflow"` = negative, `"inflow"` = positive).
- **Plan resolution**: If `YNAB_PLAN_ID=default` and exactly one plan is visible, auto-resolve. If multiple plans are visible, require an explicit plan id.
- **Month normalization**: Accepts `"current"`, `"YYYY-MM"`, or `"YYYY-MM-DD"`. `"current"` resolves to the first day of the current month.
- **Error hierarchy**: `YnabError` → `YnabConfigError` (missing settings), `YnabApiError` (API failures), `YnabAuthError` (401), `YnabRateLimitError` (429).

### 1.4 Configuration

The server reads from an env file pointed to by `YNAB_ENV_FILE`:

```bash
# ~/.config/hermes-ynab/ynab.env
YNAB_ACCESS_TOKEN=YOUR_YNAB_PAT_HERE
YNAB_PLAN_ID=default          # or a specific plan id
YNAB_BASE_URL=https://api.ynab.com/v1
YNAB_TIMEOUT=30
```

Permissions: `chmod 600` on the env file.

### 1.5 YNAB API versioning note (optional — for future migration)

The current server targets **YNAB API v1** (`api.ynab.com/v1`). YNAB has introduced **v2** endpoints. Key differences to plan for:

- v2 uses `plans` instead of `budgets` in some endpoint paths
- Some response shapes differ (e.g., nested vs. flat category structures)
- The v1 API remains functional; no forced migration timeline has been announced

When migrating to v2:
1. Update `YNAB_BASE_URL` to `https://api.ynab.com/v2`
2. Update `client.py` path strings and response parsing
3. Run existing tests against v2 (add `v2` test fixtures)
4. Update `config/ynab.env.example` with the new default URL
5. Keep v1 as a fallback option via the `YNAB_BASE_URL` override

---

## 2. Hermes Configuration (required)

This is local machine state in `~/.hermes/config.yaml`. Not committed to the repo.

### 2.1 MCP server registration

```yaml
mcp_servers:
  ynab:
    command: uv
    args:
      - run
      - --project
      - /ABSOLUTE/PATH/TO/hermes-agent/tools/ynab_mcp
      - python
      - -m
      - ynab_mcp.server
    env:
      YNAB_ENV_FILE: /home/YOUR_USER/.config/hermes-ynab/ynab.env
    timeout: 60
    connect_timeout: 30
```

Replace `/ABSOLUTE/PATH/TO/hermes-agent` and `/home/YOUR_USER` with real paths.

### 2.2 Slack channel config

```yaml
slack:
  channel_prompts:
    C_BUDGET_CHANNEL_ID: |
      You are a personal budget coach in this Slack channel.
      Use the YNAB MCP tools for live budget data:
      plans, accounts, categories, month overview,
      scheduled transactions, recent spending, and explicit writes.
      When a user explicitly asks to make a change, use the
      YNAB write tools to create or update transactions
      or change a category's assigned amount.
      Think forward: surface downstream consequences of today's choices.
      Be openly critical of bad calls. Protect the user from themselves.
      Prefer concise numeric summaries, explicit assumptions,
      and actionable next steps. Jokes welcome.
      Use YOLO-lite behavior: execute clearly worded writes directly;
      only stop to ask when matching is ambiguous.
  shared_session_channels:
    - C_BUDGET_CHANNEL_ID
  free_response_channels:
    - C_BUDGET_CHANNEL_ID
```

Replace `C_BUDGET_CHANNEL_ID` with your real Slack channel ID.

### 2.3 What these settings do

- **`channel_prompts`** — gives the channel its own system instructions
- **`shared_session_channels`** — top-level messages share one conversation (not per-user)
- **`free_response_channels`** — the bot responds without needing `@mention`

### 2.4 Optional channel overrides

You can add per-channel model or provider overrides:

```yaml
slack:
  channel_model_overrides:
    C_BUDGET_CHANNEL_ID:
      model: your-model-name
      provider: your-provider
```

---

## 3. Memory Scoping (required)

Budget conversations contain sensitive financial data. Use Honcho channel scoping to prevent cross-channel memory leakage.

Local `~/.hermes/honcho.json`:

```json
{
  "enabled": true,
  "workspace": "hermes-local",
  "gatewayPeerScope": "channel",
  "gatewayAssistantScope": "channel",
  "gatewayScopeIncludeWorkspace": true
}
```

This means:
- Conversations in the budget channel stay in the budget channel's memory scope
- Other Slack channels cannot recall budget-specific context
- The workspace prefix prevents collisions if you run multiple Hermes instances

---

## 4. Write Policy — YOLO-lite (required)

The budget bot uses a **YOLO-lite** write policy:

- **Execute directly** when the request is clearly worded and all required fields (account, category, amount, date) are known or unambiguously inferrable
- **Stop and ask** when:
  - Account or category name matches multiple targets
  - The intended transaction is ambiguous (e.g., "update that coffee purchase" when there are three)
  - The write could be destructive or has unclear intent

This is not "ask for permission on every write." It's "act like a competent human who asks before doing something they're not sure about."

### Customizing the write policy

If you want stricter confirmation (prompt before every write), change the channel prompt:

```
Before any write to YNAB, show the user a short preview and wait for confirmation.
```

If you want even more aggressive auto-execution, be explicit about which categories are safe:

```
Auto-log transactions under $50 in Groceries, Gas, and Dining Out without preview.
For amounts over $50 or any other category, confirm first.
```

---

## 5. Prompt Customization (optional — the main knob)

The channel prompt is the single most powerful customization point. Everything the bot prioritizes, avoids, emphasizes, or skips is controlled here.

### 5.1 Prompt anatomy

A good budget bot prompt has five parts:

1. **Role** — who the bot is in this channel
2. **Tools** — what it has access to and when to use them
3. **Behavior** — how it makes decisions (YOLO-lite, coach vs. clerk tone)
4. **Formatting** — Slack-specific output rules
5. **Privacy** — what stays in the channel

### 5.2 Example: Coach-style prompt

```yaml
C_BUDGET_CHANNEL_ID: |
  You are a personal budget coach in this Slack channel.
  Your job is to help make smart money decisions today
  that the user's future self will thank them for.
  Think in weeks and months, not just today's balance.
  Call out bad calls, question impulses, and flag when
  a choice creates a downstream problem. Pull no punches.
  Use YNAB MCP tools for live data.
  When the user explicitly asks for a change, use write tools.
  YOLO-lite: execute clearly worded requests directly;
  ask only when matching is ambiguous.
  Prefer concise numeric summaries. Jokes welcome.
  Format tables inside triple-backtick code blocks.
  Do NOT use bare Slack markdown tables — they break.
  Keep financial specifics within this channel.
```

### 5.3 Example: Clerk-style prompt

```yaml
C_BUDGET_CHANNEL_ID: |
  You are a YNAB assistant in this channel.
  Answer budget questions accurately using YNAB MCP tools.
  Log transactions and adjust categories on explicit request.
  Always confirm writes before executing.
  Prefer short, neutral summaries. No opinions on spending.
  Format tables inside triple-backtick code blocks.
  Do NOT use bare Slack markdown tables — they break.
```

### 5.4 Prompt decisions to make

| Decision | Coach default | Clerk alternative |
|----------|--------------|-------------------|
| Tone | Opinionated, jokes, direct | Neutral, factual |
| Unsolicited advice | Yes — flag risks | No — only answer questions |
| Write confirmation | YOLO-lite | Always confirm |
| Forward thinking | Surface downstream impact | Report current state only |
| Privacy | Keep in channel | Same |

---

## 6. Slack Formatting Rules (required)

Slack does not render markdown tables. The bot must use:

- **Bullet lists** for simple key-value or enumeration content
- **Triple-backtick code blocks** for any table with rows and columns:

```
| Category  | Budgeted | Spent | Left |
|-----------|----------|--------|------|
| Groceries | $300     | $210   | $90  |
| Dining    | $100     | $95    | $5   |
```

- **Bold** (`*text*`) for emphasis
- Never use `<table>` HTML or bare `|col|col|` outside code blocks

---

## 7. Testing & Verification (required)

### 7.1 MCP server unit tests

```bash
uv run --project tools/ynab_mcp pytest tools/ynab_mcp/tests -q
```

### 7.2 Smoke tests for the integration

1. **CLI**: Ask Hermes for a month overview → should return live YNAB data
2. **CLI**: Ask for a specific category balance → should resolve by name
3. **CLI**: Ask to create a tiny test transaction → should succeed, then clean up
4. **CLI**: Ask to set a small assigned amount → should stick
5. **Slack budget channel**: Ask for recent spending or scheduled transactions
6. **Slack other channel**: Confirm the budget prompt does not leak

### 7.3 Run the MCP server directly (for debugging)

```bash
uv run --project tools/ynab_mcp python -m ynab_mcp.server
```

### 7.4 Restart after config changes

```bash
hermes gateway restart
```

---

## 8. Extending the MCP Server (optional)

### 8.1 Adding a new tool

Add a method to `YnabClient` in `client.py`, then expose it as a decorated function in `server.py`:

```python
# client.py
def get_payees(self, *, plan_id: str | None = None) -> list[dict[str, Any]]:
    active_plan_id = self._resolve_plan_id(plan_id)
    return self._request_data("GET", f"plans/{active_plan_id}/payees").get("payees", [])

# server.py
@mcp.tool(description="List YNAB payees for a plan.")
def list_payees(plan_id: str | None = None) -> dict:
    active_plan_id = resolved_plan_id(plan_id)
    payees = run_with_client(lambda client: client.get_payees(plan_id=active_plan_id))
    return {"plan_id": active_plan_id, "payees": payees, "payee_count": len(payees)}
```

### 8.2 Write safety when extending

Every new **write** tool should:
1. Accept only single-item operations (no bulk)
2. Require explicit direction (`outflow`/`inflow`) for amounts
3. Resolve names the same way existing tools do (exact → case-insensitive partial → error on ambiguity)
4. Update `errors.py` if new error types are needed

### 8.3 YNAB API v2 migration path

When building new tools, prefer v2 endpoint patterns where available. Keep existing v1 tools working until a full migration is tested. Pattern:

```python
# future: v2 endpoint
def list_payees(self, *, plan_id: str | None = None) -> list[dict[str, Any]]:
    active_plan_id = self._resolve_plan_id(plan_id)
    # v2 path
    return self._request_data("GET", f"plans/{active_plan_id}/payees").get("payees", [])
```

---

## 9. Security & Privacy (required)

- **No secrets in this repo.** Tokens go in local files outside the repo (e.g., `~/.config/hermes-ynab/ynab.env`).
- **`chmod 600`** on any file containing a YNAB token.
- **Channel IDs** in docs use `C_BUDGET_CHANNEL_ID` as a placeholder. Replace with your real ID in local config only.
- **Financial specifics** stay in the budget channel. The prompt should instruct the bot not to surface balances, account numbers, or transaction details in other channels.
- **Write surface is intentionally small.** Only: single-transaction create/update and single-category budget set. No deletes, no bulk ops, no account management.
- **Rate limit awareness.** YNAB enforces 200 requests/hour. The MCP server surfaces `YnabRateLimitError` when hit.

---

## 10. File Map

Files in this repo related to the budget bot:

| Path | What it is |
|------|-----------|
| `tools/ynab_mcp/` | MCP server package (code) |
| `tools/ynab_mcp/README.md` | MCP server setup and usage |
| `config/ynab.env.example` | Placeholder env file (no real tokens) |
| `docs/runbooks/ynab-budget-channel.md` | Operational runbook for the integration |
| `docs/specs/budget-bot.md` | This file — customization spec |

Files on the local machine only (not committed):

| Path | What it is |
|------|-----------|
| `~/.config/hermes-ynab/ynab.env` | Real YNAB token and plan id |
| `~/.hermes/config.yaml` | Hermes gateway config (MCP + Slack) |
| `~/.hermes/honcho.json` | Honcho memory scoping config |