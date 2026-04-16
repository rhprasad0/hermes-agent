# Hermes Backend

Backend foundation for Hermes.

Right now this repo is the infrastructure layer: local Postgres, pgvector, process management, and nightly backups.

Hermes itself is not wired into it yet.

## What exists

- PostgreSQL 16
- pgvector
- Honcho for local process orchestration
- Nightly S3 backups
- Restore-tested recovery flow

## Current status

Backend is up.
Connection layer to Hermes is next.

## Notes

This repo is still early and documentation-heavy. The current work was focused on getting the backend online first, with backup and recovery validated before application integration.
