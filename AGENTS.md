# AGENTS.md

This repository is the public-facing home for this Hermes install.

Assume that anything committed here may be read, copied, indexed, and archived indefinitely. In other words: if you would not happily put it on a billboard, do not put it in this repo.

## Core rule

Public-facing code, docs, examples, tests, fixtures, screenshots, logs, and generated artifacts must not contain secrets or personally identifiable information (PII).

## Never commit

- API keys, access tokens, OAuth credentials, cookies, or session material
- Passwords, private keys, certificates, signing secrets, or encryption material
- Real `.env` values, auth files, local credential caches, or database dumps
- Real names, email addresses, phone numbers, home addresses, or other direct identifiers
- User content, transcripts, logs, screenshots, or traces that expose private or sensitive data
- Production data copied into examples, fixtures, or tests

## Use instead

- Placeholder values such as `YOUR_API_KEY_HERE`
- `.env.example` files with fake or empty values
- Synthetic test data and redacted sample payloads
- `example.com` addresses, fake hostnames, and clearly fictional identifiers
- Sanitized screenshots and scrubbed command output

## Public-repo posture

When editing this repository:

- Treat all content as public by default
- Prefer redaction over inclusion when there is any doubt
- Do not paste machine-local secrets, personal paths, or credential-bearing output into docs or code comments
- Do not check in debug output without reviewing it for sensitive data
- Keep examples safe to publish and safe to copy

## If you encounter secrets or PII

1. Stop propagating the data immediately
2. Do not copy it into new files, tests, issues, or documentation
3. Remove or redact it before committing
4. Notify the maintainer through an appropriate channel if follow-up cleanup is needed

## Practical standard

This repo should be safe to open in public, safe to share, and safe to fork.

That means no secret sauce, no accidental diary entries, and no surprise identity leaks hiding in "just an example" data.

## Budget bot — agent working notes

This repo includes a YNAB MCP server (`tools/ynab_mcp/`) and a customization spec (`docs/specs/budget-bot.md`) for a Slack budget channel integration. If you are modifying code related to the budget bot, keep these constraints in mind:

### No secrets or financial data

- The YNAB access token lives in a local file outside the repo (e.g., `~/.config/hermes-ynab/ynab.env`)
- Never commit a real token, real account names, real transaction amounts, or real category names into tests, fixtures, or examples
- Use `YOUR_YNAB_PAT_HERE` in `config/ynab.env.example` and synthetic data in tests
- Slack channel IDs in docs and specs use `C_BUDGET_CHANNEL_ID` as a placeholder; real IDs go in local config only

### MCP server constraints

- The MCP server is a **small, intentional surface**: read tools + single-item write tools (create transaction, update transaction, set category budget). Do not add bulk operations, deletes, or account-management endpoints without explicit direction
- Amounts are normal currency units in the tool interface; conversion to milliunits happens inside `client.py`
- Name resolution (accounts, categories) goes: exact match → case-insensitive partial → error on ambiguity. Never guess silently
- The server targets YNAB API v1 (`api.ynab.com/v1`). A v2 migration is noted in the spec but has not been implemented

### Write policy

- The budget bot uses YOLO-lite: execute clearly worded write requests directly; ask when matching is ambiguous
- This policy lives in the channel prompt (local config), not in the MCP server code. The server itself has no confirmation logic — it just executes
- If you add new write tools, do not build server-side confirmation into them. Confirmation behavior belongs in the agent prompt, not the API wrapper

### Slack formatting

- Slack does not render markdown tables. Any tabular data must go inside triple-backtick code blocks
- Never generate `<table>` HTML or bare pipe-delimited tables outside code blocks

### Spec reference

See `docs/specs/budget-bot.md` for the full customization specification.
