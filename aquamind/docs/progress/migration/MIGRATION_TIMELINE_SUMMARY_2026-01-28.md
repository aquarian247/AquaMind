# FishTalk -> AquaMind Migration Timeline Summary (through 2026-01-26)

Purpose: Consolidate what has been tried, what worked, what failed, and where the migration stands now. This is based on all docs under aquamind/docs/progress/migration as of 2026-01-28.

---

## Current state (most recent evidence: 2026-01-26)

- Direction is firm: input-based batch identity from Ext_Inputs_v2, CSV-based ETL, SubTransfers for within-environment movements, and recompute daily states in AquaMind (do not migrate snapshot tables).
- The latest full-lifecycle attempt targeted the sea batch "Var 2024|1|2024" (source key uses an accented a). Full-lifecycle stitching now exists but has open data-quality and performance issues.
- Mortality migration is still slow and can time out in wrapper runs; manual reruns succeed.
- Reruns may accumulate assignments and inflate totals unless the DB is cleared or old assignments are cleaned.
- Creation workflow logic has been improved (input counts and earliest stage), but egg counts still look inflated in the full-lifecycle run.
- Environmental migration is now feasible at scale using SQLite indexing, but is still heavy.

---

## Timeline (high-level)

### 2025-11 (framework groundwork)
- Migration framework validated with mock data and full test suite pass. This is now deprecated as a current source of truth but is the origin of the chronological replay approach. See MIGRATION_FRAMEWORK_IMPLEMENTATION_SUMMARY.md.
- Hall-stage identifier fix proposed to stop fragile name matching and add lifecycle_stage FK to Hall (hall_stage_identifier_fix.md).

### 2026-01-17 (first 15-component pilot)
- Ran migration for 15 components end-to-end: core batch, transfers, feeding, mortality, treatments, lice, health journal.
- Environmental tables were empty and flagged as a failure to investigate.
- Several script fixes landed (transfer action numbering, timezone awareness). See MIGRATION_HANDOVER_2026-01-17.md.

### 2026-01-19 (15-component pilot expanded and verified)
- Environmental migration implemented (Ext_SensorReadings_v2 + Ext_DailySensorReadings_v2).
- Feed inventory migration added (FeedReceptions, FeedReceptionBatches, FeedStore/Assignments).
- RBAC restoration script added for system_admin.
- Major UI issues surfaced: batches marked Completed incorrectly; transfer workflows show wrong type; lifecycle transitions unclear. See MIGRATION_HANDOVER_2026-01-19.md.

### 2026-01-21 (performance and workflow corrections; batch identity crisis)
- Environmental migration accelerated with SQLite indexing and parallel workers.
- Active assignments logic corrected; lifecycle workflows consolidated to one per stage transition (no per-population explosion).
- Feeding percentage numeric overflow fixed by capping at 99.99.
- Critical finding: project tuple grouping is not a biological batch key; it over-aggregates cohorts. The migration is mechanically working but identity logic is wrong. See SESSION_SUMMARY_2026_01_21.md and MIGRATION_HANDOVER_2026-01-21.md.

### 2026-01-22 (breakthrough: true batch identity)
- Ext_Inputs_v2 discovered as the biological batch key. InputName + InputNumber + YearClass is now the canonical batch identity.
- Input-based stitching and migration wrapper created.
- InputName changes at FW->Sea, so sea-phase batches have their own identity.
- Partial sea batch migration (Summar 2024) had feeding mismatch; Var 2024 migration became the next target.
- Growth samples migration added in Session 3 (Ext_WeightSamples_v2 + PublicWeightSamples), and assignment active-window defaults adjusted.
- Canonical docs updated to reflect the new approach. See MIGRATION_HANDOVER_2026-01-22.md, MIGRATION_HANDOVER_2026-01-22-v2.md, MIGRATION_HANDOVER_2026-01-22-v3.md, MIGRATION_CANONICAL.md.

### 2026-01-26 (full-lifecycle stitching attempt + crawl-phase focus)
- Full-lifecycle stitching script introduced to connect FW origins to sea batch (Var 2024).
- Creation workflow now uses Ext_Inputs_v2.InputCount and broader creation window.
- Environmental and mortality reruns completed for the full-lifecycle batch, but totals appear inflated due to rerun accumulation.
- Mortality script remains slow and times out in the wrapper; manual rerun succeeds.
- Status report pivots to raw events as the authoritative source; snapshot tables are to be skipped. See MIGRATION_HANDOVER_2026-01-26.md and status_reports/2026-01-26.md.

---

## What has been tried (and outcomes)

### Batch identity strategies
- UUID component stitching: worked mechanically but is arbitrary; not biological.
- Project tuple (ProjectNumber, InputYear, RunningNumber): works for many but proven wrong for many cohorts; mixes year-classes.
- SubTransfers chain linking with project tuples: over-linked, producing 70M+ fish super-batches.
- Population name year-class parsing: partial success only; used as fallback analysis.
- Ext_Inputs_v2 input-based stitching: confirmed as biological origin; now canonical.

### Transfer and lifecycle workflows
- Per-population lifecycle workflows: caused workflow explosion (hundreds per batch).
- Consolidated lifecycle workflows: now one workflow per batch stage transition (works).
- SubTransfers: used for within-environment transfers (works).
- PublicTransfers: broken since Jan 2023; must not be used.

### Performance and scalability
- Per-query SQL extraction: 20+ hours for full dataset; too slow.
- Bulk extract to CSV + --use-csv migration: 7-10x faster; now standard.
- Environmental migration: CSV too large per worker; SQLite index added to support parallelism.
- Mortality migration: still slow due to full CSV scans; needs indexing or pre-filter.

### Data coverage and correctness
- Feeding: corrected schema (Feeding is ActionID-based); percent overflow bug fixed.
- Health journal: corrected to UserSample + Action path.
- Environmental: correct source tables with is_manual distinction (Daily vs Time-series).
- Feed inventory: added and fixed idempotency; coverage sparse in source.
- Growth samples: added from Ext_WeightSamples_v2 with PublicWeightSamples fallback.

---

## What works (validated)

- Ext_Inputs_v2 as the primary batch key (InputName + InputNumber + YearClass).
- CSV ETL flow with ExternalIdMap idempotency and history-safe writes.
- SubTransfers for transfer workflows within FW or sea environments.
- Environmental ingestion using is_manual True/False to preserve data provenance.
- Lifecycle workflow consolidation and active assignment window logic.
- Growth sample import to support KPI display (avg weight).

---

## What does not work / known failure modes

- Project tuple as primary batch identity; mixes cohorts.
- PublicTransfers as FW->Sea linkage (broken since Jan 2023).
- Hybrid SubTransfers + project tuple linking; creates massive over-linking.
- Per-population lifecycle workflows (explosion).
- Feeding mismatch (earlier Summar 2024 run) when container vs population matching was wrong.
- Mortality migration performance (wrapper timeouts).
- Rerun accumulation (assignments and totals inflate across repeated runs).

---

## Where we are now (actionable state)

- Canonical approach is input-based stitching; project-based stitching is deprecated.
- Full-lifecycle attempt exists but needs cleanup and validation (egg counts, stage totals, rerun accumulation).
- Mortality migration needs optimization (indexing or pre-filter) to avoid timeouts.
- Environmental migration is technically solved but heavy; use SQLite index.
- The schema and mapping blueprint are stable enough to proceed, but validation gates must be enforced.

---

## Mapping highlights (FishTalk -> AquaMind)

These are the most critical table/column corrections and mappings that drove success:

- Batch identity: Ext_Inputs_v2 (InputName + InputNumber + YearClass) -> batch_batch
- Feeding: dbo.Feeding is ActionID-based; join via Action.PopulationID and Operations.StartTime -> inventory_feedingevent
- Health journal: UserSample + Action -> health_journalentry (one per ActionID)
- Environmental readings:
  - Ext_SensorReadings_v2 -> environmental_reading (is_manual = false)
  - Ext_DailySensorReadings_v2 -> environmental_reading (is_manual = true)
- Assignments: PublicStatusValues snapshots used to populate biomass/counts (prefer non-zero after start)
- Transfers: SubTransfers -> batch_transferaction within environment; OperationProductionStageChange for lifecycle transitions
- Feed purchases: FeedReceptions + FeedReceptionBatches -> inventory_feedpurchase
- Growth samples: Ext_WeightSamples_v2 (fallback PublicWeightSamples) -> growthsample

See DATA_MAPPING_DOCUMENT.md for full field-level rules.

---

## File timestamps (local filesystem mtime)

- aquamind/docs/progress/migration/MIGRATION_CANONICAL.md                                  - 2026-01-26 16:39:59
- aquamind/docs/progress/migration/MIGRATION_LESSONS_LEARNED.md                           - 2026-01-28 10:06:56
- aquamind/docs/progress/migration/FISHTALK_SCHEMA_ANALYSIS.md                            - 2026-01-28 10:06:56
- aquamind/docs/progress/migration/MIGRATION_BEST_PRACTICES.md                            - 2026-01-28 10:06:56
- aquamind/docs/progress/migration/DATA_MAPPING_DOCUMENT.md                               - 2026-01-27 09:16:55
- aquamind/docs/progress/migration/INFRA_ETL_PLAN.md                                      - 2026-01-27 09:23:39
- aquamind/docs/progress/migration/archive/MIGRATION_FRAMEWORK_IMPLEMENTATION_SUMMARY.md - 2026-01-17 20:21:56
- aquamind/docs/progress/migration/archive/MIGRATION_PLAN.md                              - 2026-01-17 20:22:04
- aquamind/docs/progress/migration/archive/MIGRATION_HANDOVER_2026-01-17.md               - 2026-01-19 10:13:44
- aquamind/docs/progress/migration/archive/MIGRATION_HANDOVER_2026-01-19.md               - 2026-01-19 11:05:54
- aquamind/docs/progress/migration/archive/SESSION_SUMMARY_2026_01_21.md                  - 2026-01-21 13:11:32
- aquamind/docs/progress/migration/archive/NEXT_SESSION_PROMPT.md                         - 2026-01-22 13:14:19
- aquamind/docs/progress/migration/archive/MIGRATION_HANDOVER_2026-01-22-v2.md            - 2026-01-22 15:59:53
- aquamind/docs/progress/migration/archive/MIGRATION_HANDOVER_2026-01-22-v3.md            - 2026-01-23 10:37:56
- aquamind/docs/progress/migration/archive/MIGRATION_HANDOVER_2026-01-21.md               - 2026-01-28 10:06:56
- aquamind/docs/progress/migration/archive/MIGRATION_HANDOVER_2026-01-22.md               - 2026-01-28 10:06:56
- aquamind/docs/progress/migration/archive/MIGRATION_HANDOVER_2026-01-26.md               - 2026-01-28 10:06:56
- aquamind/docs/progress/migration/archive/hall_stage_identifier_fix.md                   - 2025-11-22 12:51:24
- aquamind/docs/progress/migration/archive/status_reports/minimal_migration_checklist.md  - 2026-01-26 14:50:35
- aquamind/docs/progress/migration/archive/status_reports/2026-01-26.md                   - 2026-01-26 18:46:47
- aquamind/docs/progress/migration/archive/fishtalk_tables/table_columns.csv              - 2026-01-26 10:45:24
- aquamind/docs/progress/migration/archive/fishtalk_tables/tables_rowcount.csv            - 2026-01-26 10:46:55

---

## Notes on document freshness

- MIGRATION_CANONICAL.md says "last updated 2026-01-22" but the file mtime is 2026-01-26.
- MIGRATION_LESSONS_LEARNED.md is dated 2026-01-21 but file mtime is 2026-01-28.
- The most recent operational details appear in archive/MIGRATION_HANDOVER_2026-01-26.md and archive/status_reports/2026-01-26.md.
