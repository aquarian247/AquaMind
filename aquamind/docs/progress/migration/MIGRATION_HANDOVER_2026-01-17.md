"""Deprecated. See MIGRATION_CANONICAL.md for current migration documentation."""

> **Deprecated:** This file is retained for history. See `MIGRATION_CANONICAL.md` for the single source of truth.

# Migration Handover (2026-01-17)

## Purpose
This handover captures the current FishTalk → AquaMind migration run status, scope, results, and open verification tasks. The next agent should **continue verification before expanding scope**.

## Where to Start (Documents to Read)
1. `aquamind/docs/progress/migration/MIGRATION_FRAMEWORK_IMPLEMENTATION_SUMMARY.md`
   - Overall migration framework context, safety controls, and previous validation history.
2. `scripts/migration/tools/population_stitching_report.py`
   - How components are stitched and reported; run outputs live in `scripts/migration/output/population_stitching/`.
3. `scripts/migration/tools/pilot_migrate_component.py`
   - Infrastructure + Batch creation; includes SiteGroup → Geography bucket mapping logic.
4. `scripts/migration/tools/pilot_migrate_component_transfers.py`
   - Transfer workflows + lifecycle stage transitions.
5. `scripts/migration/tools/pilot_migrate_component_feeding.py`
6. `scripts/migration/tools/pilot_migrate_component_mortality.py`
7. `scripts/migration/tools/pilot_migrate_component_treatments.py`
8. `scripts/migration/tools/pilot_migrate_component_lice.py`
9. `scripts/migration/tools/pilot_migrate_component_health_journal.py`
10. `scripts/migration/safety.py`
    - Enforces migration DB safety (migr_dev only).

## Environment / Setup Notes
- Project root: `/Users/aquarian247/Projects/AquaMind`
- All scripts target `aquamind_db_migr_dev` (safety checks in place).
- FishTalk SQL Server container expected as `sqlserver` (Docker).
- `SKIP_CELERY_SIGNALS=1` used to avoid background tasks during migration.
- Frontend migration preview uses `docker-compose.migr-preview.yml` (not modified in this run).

## Current Scope (This Run)
**15 batch components** (9 active + 6 completed). Component keys:

Active:
- `6DD18F69-7E87-49E0-AEC3-A1A08BF21543`
- `04BA2F0E-AF69-4FF0-88C2-0D9B6FE6FA81`
- `D31330BF-8C1E-4629-B4D6-92757B8F8026`
- `ADB084F5-FB3A-480C-8C01-47219C99D73C`
- `1DB47077-F68E-40AA-A775-659A4D3DC5C6`
- `6E3B731F-DBFF-4B43-9063-D9AED34EE9CA`
- `0EEF86D7-056F-4DCC-B3A5-4591E5F493AC`
- `3A06FDA0-853F-44E3-9794-F683EC13CFF3`
- `25A7302B-52A2-40F4-8338-1B4CE9A8DB78`

Completed:
- `027AB5BB-FDFA-4613-84F5-07DEAFC2BF76`
- `63467AE1-FC41-49B1-AB5D-5D7DF983C580`
- `82214D2A-D43F-4514-B18C-5C9FF264E749`
- `14F4DDB7-5592-4531-AE40-A2FC743DBAF9`
- `038A576C-3959-4D06-8C6A-44C45DE5E7C7`
- `055BD5E5-FC43-42E8-B2D2-738B34DAEDEE`

Infrastructure-only sites (do not migrate batches yet):
- `L01 Við Áir`, `L02 Skopun`, `H125 Glyvrar`

## Commands Used (Run History)
The following scripts were run for all 15 components:
- `pilot_migrate_component.py --component-key <key>` (batch + infra)
- `pilot_migrate_component_transfers.py --component-key <key>`
- `pilot_migrate_component_feeding.py --component-key <key>`
- `pilot_migrate_component_mortality.py --component-key <key>`
- `pilot_migrate_component_treatments.py --component-key <key>`
- `pilot_migrate_component_lice.py --component-key <key>`
- `pilot_migrate_component_health_journal.py --component-key <key>`

### Notable Script Adjustments During This Run
- `pilot_migrate_component_transfers.py`:
  - Fixed rerun collisions on `TransferAction(action_number)` by starting at max existing action number and ensuring uniqueness.
  - Updated `ensure_aware()` to use `datetime.timezone.utc` (removes Django deprecation warnings).
- `pilot_migrate_component_mortality.py`:
  - Updated `ensure_aware()` to use `datetime.timezone.utc`.

## Outcomes (High-Level)
### Successes
- All 15 batches created and assigned (`batch_batch` = 15).
- Transfer workflows created where applicable (42 workflows / 80 actions).
- Feeding, mortality, treatments, lice, and health journal runs completed.
- Journal entries verified against FishTalk source (see below).

### Failures / Gaps (Need Follow-up)
**Environmental tables are empty** (expected to be populated if source data exists):
- `environmental_environmentalreading`: 0
- `environmental_environmentalparameter`: 0
- `environmental_weatherdata`: 0
- `environmental_photoperioddata`: 0
- `environmental_stagetransitionenvironmental`: 0

This is considered a **failure** for the current run and must be investigated.

## Current Migration DB Table Counts
Core tables (after run):
- `batch_batch`: 15
- `batch_batchcontainerassignment`: 93
- `batch_batchtransferworkflow`: 42
- `batch_transferaction`: 80
- `batch_mortalityevent`: 3348
- `inventory_feedingevent`: 2429
- `health_treatment`: 364
- `health_licecount`: 1150
- `health_journalentry`: 200
- `migration_support_externalidmap`: 11015
- `infrastructure_container`: 41
- `infrastructure_area`: 15
- `infrastructure_hall`: 15
- `infrastructure_freshwaterstation`: 15

Additional checks (all zero / likely missing in current scope):
- `inventory_feedpurchase`: 0
- `inventory_feedcontainerstock`: 0
- `inventory_containerfeedingsummary`: 0
- `inventory_batchfeedingsummary`: 0
- `health_mortalityreason`: 0
- `health_healthlabsample`: 0
- `health_sampletype`: 0
- `batch_batchcomposition`: 0

Non-zero support/master data:
- `inventory_feed`: 36
- `health_vaccinationtype`: 2

## Health Journal Count Verification
The **200 journal entries** are not a bug. Verification:
- All 200 entries belong to batch `FT-04BA2F0E-MW_AG-24-Q1`.
- FishTalk validation: 200 distinct `UserSample.ActionID` in FishTalk for component `04BA2F0E` within its population time window. This matches the 200 journal entries.

## Validation / Tests
- `python manage.py test --settings=aquamind.settings_ci --noinput` → **0 tests**, OK.
- `flake8` run on modified migration scripts → **OK**.

## Required Next Steps (Before Expanding Scope)
1. **Investigate missing environmental data**:
   - Determine if FishTalk has environmental readings for any of the 15 components.
   - If yes, locate relevant FishTalk tables and implement migration.
   - If no, document absence (could be legitimate).
2. **Verify additional tables** (beyond core):
   - Confirm whether `inventory_feedpurchase`, `feedcontainerstock`, `batchfeedingsummary`, etc. are expected to be empty.
   - If expected to be populated, add migration steps.
3. **Confirm mortality/treatment/lice counts for each batch** to detect anomalies.
4. **Only then** decide whether to expand to new components (including FW→sea components `0342D6AF` and `513172E5`).

## Known Context Notes
- There are only **two FW→sea components** in 2023–2024.
- Many components are single-stage; transfers mostly intra-site.
- `health_journalentry` uses **UserSample** tables; one entry per ActionID.

## Suggested Queries / Scripts
Use Django ORM or raw SQL for counts; for FishTalk use `BaseExtractor` with `ExtractionContext(profile='fishtalk_readonly')`.

Examples:
- Validate environmental source data exists in FishTalk (if any):
  - Search for candidate tables like `SensorReadings`, `Ext_SensorReadings_v2`, `Ext_DailySensorReadings_v2`.
  - Confirm whether any readings are within component windows.

## Contact / Operational Notes
- Docker must be running for FishTalk SQL access via `sqlcmd`.
- Migration scripts must **only** target `aquamind_db_migr_dev` (safety checks enforced).
