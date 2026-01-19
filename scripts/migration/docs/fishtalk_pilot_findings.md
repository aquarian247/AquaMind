# FishTalk → AquaMind Migration Pilot Findings

Date: 2026-01-16

This document captures **pilot migration learnings** and **data-model particularities** discovered while migrating a small number of FishTalk “components” (stitched populations) into AquaMind.

The goal is to maximise success probability for the next phase (5–10 batches) by documenting:

- Which FishTalk tables/columns actually contain the data we need (vs assumptions)
- What needs “stitching” (PopulationID discontinuities)
- Unit conversions / field semantics
- Practical safety/operational guardrails
- Known limitations and next steps

---

## 1) Safety & Operational Guardrails

### 1.1 Migration target DB safety

All migration scripts **must write ONLY** to the dedicated migration database (`aquamind_db_migr_dev`).

Implemented in:

- `scripts/migration/safety.py`
  - `configure_migration_environment()` forces `DB_*` env vars to the migration target defined in `scripts/migration/migration_config.json`.
  - `assert_default_db_is_migration_db()` fails fast if `connections['default']` is not the migration DB.

This is intentionally “belt and braces”: even if a script is run from a different shell/session, it still refuses to write to the wrong database.

### 1.2 Idempotency / rerunability

Every pilot tool uses `apps.migration_support.models.ExternalIdMap` to ensure reruns are safe:

- `PopulationComponent` → `Batch`
- `Populations` → `BatchContainerAssignment`
- `Feeding`/`HWFeeding` → `FeedingEvent`
- `UserSampleAction` → `JournalEntry`

This allows:

- repeatable “dry-run → fix → rerun” cycles
- crash recovery without manual cleanup
- future “incremental” migration runs

---

## 2) The Core FishTalk Problem: PopulationID Discontinuity

FishTalk `PopulationID` is **not stable across freshwater → sea transfers**.

Stable lineage is reconstructed using:

- `PopulationLink` with `LinkType 1/2` (source→TransportPop, TransportPop→destination)
- `Operations` timestamps

This produces a *transfer graph* that we treat as the source-of-truth for “batch continuity”.

Tool used:

- `scripts/migration/tools/population_stitching_report.py`
  - Union-Find to compute connected components
  - deterministic `component_key` for stable referencing across reruns

---

## 3) Pilot Scope & Results (What Was Actually Migrated)

### 3.1 Pilot batch A (multi-pop, transfers)

- `component_key`: `3A394B11-9DC6-4E86-BF0E-D11A12F0EB92`
- 7 FishTalk populations (includes sea-transfer stitching)
- 4 unique FishTalk `ContainerID`s → 4 AquaMind `infrastructure_container` rows
- **Feeding:** no rows found for those populations via FishTalk `dbo.Feeding` join path
- **User samples:** no `dbo.UserSample` actions

Interpretation: this batch is useful for validating stitching + assignments, but not for feeding/health event pipelines.

### 3.2 Pilot batch B (single-pop, real feeding + sampling)

- `component_key`: `0AC618D9-43F1-4A52-B5D2-8AA2D52E42A2`
- Population name: `KLM_LHS 23 Q1`
- 1 FishTalk population → 1 assignment
- **FeedingEvents created:** 269
- **JournalEntries created:** 41 (one per sampling ActionID)

This batch validated the end-to-end event extraction patterns for:

- FishTalk Feeding schema (ActionID-based)
- FeedAmount unit conversions
- Biomass lookups from `PublicStatusValues`
- Health journal extraction from UserSample tables

---

## 4) FishTalk Feeding: Actual Schema & Required Join Path

### 4.1 The real Feeding table schema

FishTalk `dbo.Feeding` columns (key subset):

- `ActionID` (NOT FeedingID)
- `FeedAmount`
- `FeedTypeID`
- `FeedBatchID`
- `OperationStartTime`

There is **no** `PopulationID`, `ContainerID`, or `FeedingTime` column in this schema.

### 4.2 Correct join path for population + time

To attach a feeding row to a population and timestamp:

- `Feeding.ActionID` → `Action.ActionID`
  - `Action.PopulationID`
  - `Action.OperationID` → `Operations.StartTime`
- Timestamp used: `COALESCE(Operations.StartTime, Feeding.OperationStartTime)`

### 4.3 Feed type/batch naming

Useful lookups:

- `FeedBatch.FeedBatchID -> BatchNumber, FeedTypeID`
- `FeedTypes.FeedTypeID -> Name`

We currently create AquaMind `Feed` records as placeholders (brand = “FishTalk Import”), using a readable name derived from `FeedTypes.Name` + optional batch number.

### 4.4 Units: FeedAmount is grams

Empirically validated:

- `FeedAmount` values like `95000`, `130000`, etc.
- Corresponding population biomass in `PublicStatusValues.CurrentBiomassKg` is on the order of **10,000+ kg**.
- Treating FeedAmount as **grams** yields realistic daily feeding amounts (e.g., `95000g = 95kg`).

Therefore:

- `amount_kg = FeedAmount / 1000`

### 4.5 Biomass lookup gotcha (critical)

AquaMind `FeedingEvent.save()` auto-calculates `feeding_percentage = amount_kg / batch_biomass_kg * 100`.

FishTalk `PublicStatusValues` sometimes has a **first status snapshot with `CurrentBiomassKg=0`** at the population “start moment” (StatusType=0). Example:

- start row at `2023-02-05 10:22:20`: biomass=0
- first feeding at `2023-02-05 14:00:00`: would pick the 0-biomass snapshot if we only look backwards

If we insert a FeedingEvent with near-zero biomass, `feeding_percentage` explodes and overflows the DB field.

Fix implemented:

- query **both** status snapshot “before” and “after” feeding time
- pick the first non-zero biomass (prefer before, else after)
- if still unknown, **skip the feeding event** rather than creating invalid data

Script:

- `scripts/migration/tools/pilot_migrate_component_feeding.py`

### 4.6 HWFeeding is empty (in this FishTalk DB)

`dbo.HWFeeding` exists but contains **0 rows** here.

Our migration tool supports it (joins `HWFeeding.FTActionID -> Action.ActionID`) but in this dataset it has no effect.

---

## 5) FishTalk Health Journals: Mapping to AquaMind `health_journalentry`

### 5.1 AquaMind JournalEntry model (target)

`apps.health.models.JournalEntry` key fields:

- `batch` (required)
- `container` (optional)
- `user` (required)
- `entry_date` (datetime)
- `category` (choices)
- `severity` (choices)
- `description`, `resolution_status`, `resolution_notes`

### 5.2 FishTalk sampling tables (source)

The expected “SampleID/Notes/SampleDate” schema did **not** exist. Actual observed schema:

- `dbo.UserSample`
  - per-fish rows
  - key columns: `MeasID`, `Returned`, `LivingWeight`, `ActionID`
- `dbo.UserSampleTypes`
  - maps `ActionID -> SampleType (int)`
- `dbo.UserSampleType`
  - maps `UserSampleTypeID -> DefaultText` (human name)
- `dbo.UserSampleParameterValue`
  - per-fish attribute values
  - key columns: `MeasID`, `AttributeID`, typed value columns (`IntValue`, `FloatValue`, etc), `ActionID`
- `dbo.FishGroupAttributes`
  - maps `AttributeID -> Name` (e.g., “Active AGS score [0-5]”)

### 5.3 Correct join path

`UserSample.ActionID` is the sampling-session key.

To place the sampling session on a timeline and assign it to a population:

- `UserSample.ActionID -> Action.ActionID`
  - `Action.PopulationID`
  - `Action.OperationID -> Operations.StartTime`

### 5.4 Granularity decision: **one JournalEntry per ActionID**

UserSample has many rows per ActionID (one per fish), e.g. `420 UserSample rows` but only `41 distinct ActionID`s.

For the pilot, we migrate **one** AquaMind JournalEntry per sampling ActionID with a summary:

- sample types (can be multiple per ActionID)
- n fish sampled
- weight stats when present (LivingWeight appears to be in grams)
- aggregated attribute scores (avg/min/max) when present

Tool:

- `scripts/migration/tools/pilot_migrate_component_health_journal.py`

---

## 6) Practical Runbook for Next Phase (5–10 batches)

### 6.1 Pre-reqs

1. Ensure Docker Desktop is running.
2. Ensure FishTalk SQLServer container is running (`sqlserver` on port `1433`).
3. Ensure migration DB exists and migrations are applied:
   - `aquamind_db_migr_dev`
4. Ensure master data is seeded:
   - `python3 scripts/migration/setup_master_data.py`

### 6.2 Generate stitching report (if needed)

Run:

- `python3 scripts/migration/tools/population_stitching_report.py --since YYYY-MM-DD`

Outputs live in:

- `scripts/migration/output/population_stitching/`
  - `components.csv`
  - `population_members.csv`

### 6.3 For each selected component_key

1. Migrate batch + assignments + just-in-time infra:
   - `python3 scripts/migration/tools/pilot_migrate_component.py --component-key <uuid>`
2. Migrate feeding events (if any):
   - `python3 scripts/migration/tools/pilot_migrate_component_feeding.py --component-key <uuid>`
3. Migrate health journal entries (if any):
   - `python3 scripts/migration/tools/pilot_migrate_component_health_journal.py --component-key <uuid>`

### 6.4 Validation (must-run)

From repo root:

- `python3 audit_basenames.py`
- `python3 manage.py test --settings=aquamind.settings_ci`

---

## 7) Known Gaps / Next Steps

This pilot validated *pattern + join paths* but does not yet cover:

- Mortality migration into `health_mortalityrecord` (and implications of its `save()` side effects)
- Treatment migration into `health_treatment`
- Full health sampling model migration (`HealthSamplingEvent`, `IndividualFishObservation`, `FishParameterScore`) beyond narrative journals
- Feed economics / feed stock reconciliation (`FeedPurchase`, `FeedContainerStock`, etc)
- Full infrastructure import (all containers, halls, areas) — current approach is **just-in-time** creation per migrated component

Recommended next improvements before scaling:

1. Add a “component preflight” report:
   - counts per component: feeding rows, user sample actions, mortality rows, etc.
2. Add chunking / pagination strategies for large components to avoid long SQL queries.
3. Decide policy for missing/zero biomass at feeding time (current: look-ahead snapshot; else skip).
4. Decide whether health sampling should be migrated into structured health models or remain as narrative journals.
