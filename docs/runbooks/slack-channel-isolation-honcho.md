# Slack channel isolation with Honcho runbook

This runbook describes how to give a Slack channel its own:
- channel-specific prompt
- shared or isolated session behavior
- Honcho memory scope
- optional free-response behavior without `@mention`

This setup is designed for the local Hermes install used on this machine.

## Where things live

Tracked repo files:
- `docs/runbooks/slack-channel-isolation-honcho.md`
- `README.md`
- Hermes source changes under the tracked repo checkout when applicable

Local machine state, not tracked in git:
- `~/.hermes/config.yaml`
- `~/.hermes/honcho.json`
- `~/.hermes/.env`
- live gateway service state

Important:
- `/home/ryan/` itself is not a git repo
- only specific repos under it, such as `/home/ryan/hermes-agent`, are version-controlled

## Design goal

Use one Honcho workspace, but isolate memory by gateway metadata instead of creating one Honcho workspace per Slack channel.

That gives you:
- one Honcho deployment to operate
- channel-local long-term memory
- no memory bleed across Slack channels/workspaces
- room for per-channel prompts and response policies

## Required pieces

1. Hermes gateway must already be connected to Slack
2. Hermes must already be using Honcho as the active memory provider
3. The Slack channel must exist and Hermes must be present in it
4. The gateway code must include channel/workspace-aware Honcho scoping support

## Local config files

### 1. Honcho scoping in `~/.hermes/honcho.json`

Example:

```json
{
  "enabled": true,
  "baseUrl": "http://127.0.0.1:8000",
  "workspace": "hermes-local",
  "aiPeer": "hermes",
  "writeFrequency": "turn",
  "recallMode": "hybrid",
  "observationMode": "directional",
  "gatewayPeerScope": "channel",
  "gatewayAssistantScope": "channel",
  "gatewayScopeIncludeWorkspace": true
}
```

What this does:
- `gatewayPeerScope: "channel"` makes the human-side Honcho identity channel-scoped
- `gatewayAssistantScope: "channel"` makes the assistant-side Honcho identity channel-scoped
- `gatewayScopeIncludeWorkspace: true` prevents collisions across Slack workspaces

## 2. Slack channel behavior in `~/.hermes/config.yaml`

Example for one shared-room channel:

```yaml
slack:
  channel_prompts:
    C_TARGET_CHANNEL_ID: |
      You are Hermes in this Slack channel.
      Follow the room-specific instructions for this channel.
  shared_session_channels:
    - C_TARGET_CHANNEL_ID
  free_response_channels:
    - C_TARGET_CHANNEL_ID

group_sessions_per_user: true
thread_sessions_per_user: false
```

Meaning:
- `channel_prompts` gives the room its own prompt
- `shared_session_channels` makes top-level session state shared only in the listed Slack channels
- `free_response_channels` allows Hermes to respond in those channels without `@mention`
- `group_sessions_per_user: true` preserves per-user isolation elsewhere
- `thread_sessions_per_user: false` keeps Slack threads shared by default

## Shared-room vs per-user behavior

### Shared-room channel

Use when you want the whole channel to behave like one collaborative room.

Recommended:

```yaml
slack:
  shared_session_channels:
    - C_TARGET_CHANNEL_ID
```

and keep:

```yaml
group_sessions_per_user: true
thread_sessions_per_user: false
```

This makes only the listed channel shared at the top level, while other channels keep default per-user behavior.

### Per-user-in-channel behavior

Use when you want each person in a channel to keep their own separate conversation state.

Recommended:
- do not list the channel under `shared_session_channels`
- keep `group_sessions_per_user: true`

If you also want long-term memory per user rather than per room, use a different Honcho gateway peer scope such as a channel+user strategy if supported by the installed gateway code.

## Example: budget channel

A budget-planning room might use:

```yaml
slack:
  channel_prompts:
    C_BUDGET_CHANNEL_ID: |
      You are Hermes in the #budget Slack channel.
      Treat this room as a shared budgeting workspace.
      Focus on budgets, cash flow, commuting costs, tolls,
      savings plans, and concrete financial planning.
      Prefer explicit assumptions, simple arithmetic,
      crisp summaries, and actionable next steps.
  shared_session_channels:
    - C_BUDGET_CHANNEL_ID
  free_response_channels:
    - C_BUDGET_CHANNEL_ID
```

## Rollout procedure

1. Create or identify the Slack channel
2. Get the Slack channel ID
3. Add or update the `channel_prompts` entry in `~/.hermes/config.yaml`
4. Decide whether the room should be shared or per-user
5. If shared, add the channel ID to `slack.shared_session_channels`
6. If you want mention-free operation, add the channel ID to `slack.free_response_channels`
7. Ensure `~/.hermes/honcho.json` uses channel-scoped gateway memory settings
8. Restart the gateway service
9. Verify behavior in Slack

## Restart

After changing local config or gateway code, restart Hermes gateway.

Example:

```bash
sudo "$(command -v hermes)" gateway restart
```

If the system service needs to be reset first:

```bash
sudo systemctl reset-failed hermes-gateway.service
sudo systemctl restart hermes-gateway.service
```

Check status:

```bash
"$(command -v hermes)" gateway status
```

## Verification checklist

### Prompt behavior
- Send a message in the target channel
- Confirm replies reflect the room-specific prompt

### Free-response behavior
- Send a normal message in the target channel without `@mention`
- Confirm Hermes responds
- Send a normal message in another Slack channel
- Confirm Hermes still follows that channel's normal gating rules

### Session behavior
For a shared-room channel:
- user A asks a question in-channel
- user B follows up in the same channel
- confirm Hermes retains shared room context

For other channels:
- confirm they still keep their expected per-user behavior

### Honcho isolation
- interact in channel A
- interact in channel B on a different topic
- confirm memory and recall do not bleed across channels
- if multi-workspace Slack is in use, confirm the same channel ID in another workspace does not collide

## Troubleshooting

### Hermes does not respond without mention
Check:
- `slack.free_response_channels` contains the correct channel ID
- the gateway was restarted after editing config
- Slack gateway connection is healthy

### Channel prompt does not apply
Check:
- `slack.channel_prompts` uses the exact Slack channel ID
- YAML indentation is valid
- the gateway was restarted

### Memory bleeds across channels
Check:
- `~/.hermes/honcho.json` includes:
  - `gatewayPeerScope: "channel"`
  - `gatewayAssistantScope: "channel"`
  - `gatewayScopeIncludeWorkspace: true`
- the installed gateway code includes channel/workspace-aware Honcho scoping

### The whole Slack install becomes shared-room by accident
Cause:
- setting `group_sessions_per_user: false` globally

Preferred fix:
- restore `group_sessions_per_user: true`
- use `slack.shared_session_channels` for only the channels that should be shared

## Notes

- Keep examples in tracked docs sanitized and safe to publish
- Do not commit real secrets, tokens, or private local config values
- Prefer placeholder channel IDs like `C_TARGET_CHANNEL_ID` in repo docs
