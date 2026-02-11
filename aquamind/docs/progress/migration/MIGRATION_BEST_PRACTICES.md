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
- Use station guards for batch/component runs when verifying a known station:
  - `pilot_migrate_input_batch.py --expected-site "<site name>"`
  - `pilot_migrate_component.py --expected-site "<site name>"`
- Do not bypass station preflight errors unless intentionally testing mismatch behavior.

## Validation Standards
- Run `scripts/migration/tools/migration_counts_report.py` after each run and confirm expected non‑zero core tables.
- Run `scripts/migration/tools/migration_semantic_validation_report.py` for batch‑level reconciliation (counts + biomass).
  - Use `--stage-entry-window-days 2` for transition sanity checks.
- Validate GUI in the migration preview stack before expanding scope.
- Reconcile source vs target counts for any table with discrepancies.
  - Expect **mortality biomass** mismatch: FishTalk extracts provide `0` in many cases; AquaMind computes per‑event biomass from same‑day status snapshots.
- Treat stage population increases as alert conditions unless mixed-batch composition exists.

## CSV vs Raw Database (Early Development)
- **CSV mode is recommended** for speed, repeatability, and controlled snapshots.
- **Use raw SQL** when validating schema changes, missing tables/columns, or unexpected gaps.
- Re‑extract CSVs after any schema or logic change to keep snapshots aligned.

## Performance Tuning (Apple Silicon / High-Core Hosts)
- Keep `pilot_migrate_component.py` and `pilot_migrate_component_transfers.py` **serial** (they establish core batch state and transfer graph).
- Use optional parallel post-transfer replay in `pilot_migrate_input_batch.py` for independent event scripts:
  - `--parallel-workers <N>` enables parallel phase (`N=1` keeps full sequential behavior).
  - `--parallel-blas-threads 1` prevents thread oversubscription when running many CSV-heavy subprocesses.
  - `--script-timeout-seconds <S>` raises per-script timeout for large batches.
- Recommended starting point on M4 Max:
  - `--parallel-workers 6 --parallel-blas-threads 1 --script-timeout-seconds 1200`
- Keep **DB wipe + station guard + semantic gates** unchanged while tuning performance.

## Source Quirks to Treat as Policy
- **Weight samples**: `Ext_WeightSamples_v2` and `PublicWeightSamples` are duplicates in this backup. Use **Ext only** and treat `AvgWeight` as **grams**.
- **Infra naming**: Do not prepend `FT` or append `FW`/`Sea` on names. Normalize by stripping those tokens at load time.
- **Hall stage over ProductionStage**: where FishTalk source stage is noisy, use qualified hall-stage mapping as the authoritative stage source.

## Mortality Replay Policy
- Replay mortality/culling/escapes into `batch.MortalityEvent` (with `ExternalIdMap` linkage per source row).
- Keep assignment population counts deterministic by resolving:
  - `resolved_count = baseline_population_count - (mortality + culling + escapes totals for that population)`
- Persist baseline on population assignment mappings so replays remain idempotent.

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
