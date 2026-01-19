# FishTalk → AquaMind Migration Best Practices

## Purpose
This document defines **non‑negotiable migration standards** to preserve data integrity, audit trail continuity, and repeatable validation. It contains **no run status**.

## Non‑Negotiables (Data Integrity)
- **All writes must use Django model methods** that populate audit history (e.g., `save_with_history()`, `get_or_create_with_history()`), never raw SQL inserts/updates into target tables.
- Always set `_history_user` and a **change reason** for migrated records so `django-simple-history` captures correct audit trails.
- Avoid bulk writes that bypass history unless a dedicated history-safe pathway exists.

## Idempotency & Traceability
- Every migrated row must be tracked in `migration_support.ExternalIdMap` to prevent duplicates on replay.
- Migration scripts must **check ExternalIdMap first** and upsert via history-safe methods.

## Safety Guardrails
- `scripts/migration/safety.py` must enforce `aquamind_db_migr_dev` before any write.
- Use `SKIP_CELERY_SIGNALS=1` for all migration scripts to prevent background tasks from mutating data.
- Use `scripts/migration/clear_migration_db.py` for clean replays (keeps schema + auth tables).

## Validation Standards
- Run `scripts/migration/tools/migration_counts_report.py` after each run and confirm expected non‑zero core tables.
- Validate GUI in the migration preview stack before expanding scope.
- Reconcile source vs target counts for any table with discrepancies.

## Repeatability & Logging
- Keep migrations deterministic: explicit ordering, consistent time‑zone conversions, and stable identifiers.
- Log errors with source identifiers, target model, and action taken (skip/retry/fail).
