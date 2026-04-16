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

That means no secret sauce, no accidental diary entries, and no surprise identity leaks hiding in “just an example” data.
