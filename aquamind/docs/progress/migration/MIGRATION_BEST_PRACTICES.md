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

## Scenario & Planning Data Policy

### Decision (2026-01-20)
**DO NOT migrate FishTalk planning/projection data.** The scenario tables (`PlanScenario`, `PlannedActivities`, `PlanPopulation`, `PlanTransfer`, etc.) contain stale or "junk" planning data that does not reflect operational reality and would pollute AquaMind's planning features.

### What TO Migrate (Master Data Only)
- **TGC Models:** FishTalk `GrowthModels` + `TGCTableEntries` → AquaMind `scenario_tgcmodel` + `scenario_tgc_model_stage`
- **FCR Models:** FishTalk `FCRTableEntries` → AquaMind `scenario_fcrmodel` + `scenario_fcrmodelstage`
- **Temperature Profiles:** FishTalk `TemperatureTables` + `TemperatureTableEntries` → AquaMind `scenario_temperatureprofile` + `scenario_temperaturereading`

### What NOT to Migrate
- `PlanScenario` - Planning scenarios (stale)
- `PlannedActivities` - Planned activities (stale)
- `PlanPopulation` - Population forecasts (not actuals)
- `PlanTransfer` - Planned transfers (not actual transfers)
- `FFFinancialScenario` - Financial scenarios (out of scope)
- `OptimeeringScenarioData` - Optimization data (out of scope)

### Post-Migration Workflow
After batch data migration is complete:
1. Migrate TGC/FCR/Temperature master data from FishTalk
2. Create baseline scenarios in AquaMind for each migrated batch
3. Pin scenarios to batches via UI or API
4. Run projections manually to generate `ActualDailyAssignmentState` and `LiveForwardProjection` data

### Rationale
- Migrated batches have **actual historical data** (feeding, mortality, treatments, transfers)
- AquaMind's assimilation engine can compute daily states from this actual data once scenarios exist
- FishTalk scenarios were for **planning future batches**, not tracking historical ones
- This approach keeps the migration focused on verifiable actuals and avoids importing stale forecasts
