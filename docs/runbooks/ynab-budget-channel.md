# YNAB Budget Channel Runbook

This runbook documents the local YNAB integration for the Slack budget channel.

## Goal

Give Hermes safe YNAB access in the budget Slack channel without committing any secrets to this public repo.
Hermes should become the primary budgeting interface so the user does not have to open YNAB directly for normal read/write workflows.

## Components

- Local secret file: `~/.config/hermes-ynab/ynab.env`
- MCP server code: `tools/ynab_mcp/`
- Local Hermes config: `~/.hermes/config.yaml`
- Local Honcho config: `~/.hermes/honcho.json`

## Local secret file

Example local file:

```bash
YNAB_ACCESS_TOKEN=YOUR_REAL_TOKEN_HERE
YNAB_PLAN_ID=default
```

If the token can see more than one YNAB plan, replace `default` with the specific plan id you want Hermes to use.

Recommended permissions:

```bash
chmod 600 ~/.config/hermes-ynab/ynab.env
```

## MCP server registration

Example local config snippet for `~/.hermes/config.yaml`:

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
      YNAB_ENV_FILE: /home/USER/.config/hermes-ynab/ynab.env
    timeout: 60
    connect_timeout: 30
```

## Slack budget channel wiring

Example local Slack config:

```yaml
slack:
  channel_prompts:
    C_BUDGET_CHANNEL_ID: |
      You are Hermes in the #budget Slack channel.
      Treat this room as a shared budgeting workspace.
      Use the YNAB MCP tools for live plan, account, category,
      month overview, scheduled transaction, and transaction questions.
      When a user explicitly asks to make a change, you may use the YNAB write tools
      to create/update transactions or change a category's assigned amount.
      Prefer concise numeric summaries, explicit assumptions,
      and actionable next steps.
      Use YOLO-lite behavior: for clearly worded write requests, execute directly;
      only stop to ask when account, category, transaction, or intent matching is ambiguous.
  shared_session_channels:
    - C_BUDGET_CHANNEL_ID
  free_response_channels:
    - C_BUDGET_CHANNEL_ID
```

## Honcho memory scoping

Recommended local `~/.hermes/honcho.json` settings:

```json
{
  "enabled": true,
  "workspace": "hermes-local",
  "gatewayPeerScope": "channel",
  "gatewayAssistantScope": "channel",
  "gatewayScopeIncludeWorkspace": true
}
```

## Smoke test ideas

1. CLI: ask Hermes for a month overview from YNAB.
2. CLI: ask Hermes for a specific category balance.
3. CLI: ask Hermes to create a tiny sandbox transaction, then update it.
4. CLI: ask Hermes to set a small assigned amount for a safe category and verify it.
5. Slack budget channel: ask for recent spending or scheduled transactions.
6. Confirm another Slack channel does not get the budget-specific prompt.

## Commands

Run tests:

```bash
uv run --project tools/ynab_mcp pytest tools/ynab_mcp/tests -q
```

Run the server directly:

```bash
uv run --project tools/ynab_mcp python -m ynab_mcp.server
```

Restart gateway after config changes:

```bash
sudo "$(command -v hermes)" gateway restart
```
