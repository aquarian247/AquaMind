# Migration Replay Stress Test (2026-02-19)

## Objective

Validate full replayability and regression safety by wiping `aquamind_db_migr_dev` and re-running migration waves end-to-end on a clean database.

## Scope executed

1. Drop/recreate migration database.
2. Re-apply full Django schema (`migrate --database=migr_dev`).
3. Seed required migration master data (`scripts/migration/setup_master_data.py`).
4. Rebuild infrastructure (`scripts/migration/legacy/migrate.py --phases infrastructure`).
5. Replay linked FW->Sea anchor wave (4 cohorts).
6. Replay controlled provisional micro-wave (3 cohorts).
7. Re-run semantic regression gates for all 7 cohorts.
8. Refresh realistic reference pack and run schedule/event-engine dry-run checks.

## Replay blockers found and resolved

### 1) Clean-DB bootstrap dependency

- Symptom: first linked run failed in `pilot_migrate_component.py` with `Missing Species master data`.
- Resolution: run `python3 scripts/migration/setup_master_data.py` after schema bootstrap on clean DB.
- Result: linked and provisional waves execute successfully after seeding.

### 2) Synthetic transfer guardrail drift

- Symptom: linked full-lifecycle runs with `--include-fw-batch` auto-enabled synthetic stage transitions, producing non-zero transfer actions against guarded policy.
- Resolution: patched `scripts/migration/tools/pilot_migrate_input_batch.py` to make synthetic stage transitions opt-in only via explicit `--include-synthetic-stage-transitions`.
- Result: linked wave restored to source-backed behavior (`transfer_actions.total_count = 0` on all linked semantic summaries).

## Infrastructure integrity gates (post-replay)

- `A*` freshwater stations in Faroe: `0`
- Faroe `S*` freshwater stations: `7`
- GUID-like freshwater station names in Faroe: `0`
- Faroe area groups present: `3`
- Structural containers assigned to fish: `0`
- Parent-linked containers present (rack/tray hierarchy): `1078`

## Linked anchor wave replay (guarded)

| Cohort | Component key | Scripts | Semantic gates | Transfer actions | Zero transfer actions |
| --- | --- | --- | --- | ---: | ---: |
| `Vetur 2024|1|2024` | `152E8378-B673-4C7F-8EF9-1933627F4143` | `11/11` PASS | PASS | 0 | 0 |
| `Vetur 2024/2025|1|2024` | `73B6F838-24D5-4F5D-A1A4-CC57DF375D05` | `11/11` PASS | PASS | 0 | 0 |
| `Heyst 2023|1|2024` | `33BD2243-57BE-437E-B026-BACBFDA640BB` | `11/11` PASS | PASS | 0 | 0 |
| `Vetur 2025|1|2025` | `04A3BDDC-344A-4CDE-A6D2-2184FA7F3870` | `11/11` PASS | PASS | 0 | 0 |

## Controlled provisional micro-wave replay

| Cohort | Component key | Scripts | Semantic gates | Transfer actions | Zero transfer actions |
| --- | --- | --- | --- | ---: | ---: |
| `Vár 2025|1|2025|A83A9BFF-005B-4ED2-856D-8C7BDF37B54F` | `67677EF3-C7D0-431C-9BFE-2533D67EF523` | `11/11` PASS | PASS | 0 | 0 |
| `Heyst 2025|1|2025|EE44DDC3-ED36-4AC7-85F0-E338C8F2EA78` | `C78845D7-8A8D-4B31-968B-8127642563D7` | `11/11` PASS | PASS | 9 | 0 |
| `Summar 2025|1|2025|6E496E90-F34B-4CD7-84DC-164EC3473A5E` | `F12F9479-E82C-499C-99E4-4BB3F5EF991F` | `11/11` PASS | PASS | 12 | 0 |

Notes:

- Non-zero transfer actions in `Heyst 2025` and `Summar 2025` are source-backed from `SubTransfers` edges (canonical), not synthetic backfill.
- `Heyst 2025` required `--allow-station-mismatch` due InputProjects vs Ext_Inputs site-set mismatch.

## Counts snapshot (post-replay)

From `scripts/migration/tools/migration_counts_report.py` across replayed 7 batches:

- `batch_batch`: `7`
- `batch_batchcontainerassignment`: `267`
- `batch_batchtransferworkflow`: `21`
- `batch_transferaction`: `21`
- `batch_mortalityevent`: `17006`
- `inventory_feedingevent`: `8032`
- `health_treatment`: `1392`
- `health_licecount`: `3301`

## Realistic test-data path health

### Reference pack refresh

- Command: `scripts/data_generation/export_realistic_asset_pack.py --output-dir scripts/data_generation/reference_pack/latest`
- Output snapshot: `scripts/data_generation/reference_pack/snapshots/2026-02-19_1430Z`
- Export counts: `stations=31`, `halls=122`, `areas=197`, `containers=10105`, `batch_refs=7`

### Schedule dry-run

- Default saturated reference-pack dry-run failed with:
  - `No available reference-pack containers for stage Post-Smolt in Scotland for batch 1`
- Constrained smoke dry-run passed with:
  - `--batches 1 --stagger 30 --dry-run`
  - Result: schedule valid, zero conflicts.

### Event-engine dry-run

- Command: `scripts/data_generation/04_batch_orchestrator.py --batches 1 --saturation 0.1 --stagger 30` (dry-run mode).
- Result: PASS; deterministic event-engine command plan emitted, no writes performed.

## Artifacts

- Linked semantic summaries: `scripts/migration/output/input_batch_migration/*/semantic_validation_*.stress_replay.json`
- Provisional semantic summaries: `scripts/migration/output/input_batch_migration/*/semantic_validation_*.stress_replay.json`
- This report: `aquamind/docs/progress/migration/analysis_reports/2026-02-19/migration_replay_stress_test_2026-02-19.md`

## Conclusion

Replayability is materially improved:

- clean DB bootstrap succeeds with known seed step,
- infrastructure classification and hierarchy guardrails hold,
- linked and provisional waves replay cleanly with semantic regression gates passing,
- synthetic transfer-action guardrail is restored by default,
- realistic-path tooling is functional with constrained reference-pack schedule smoke tests.

Remaining housekeeping opportunity:

- improve default reference-pack schedule auto-sizing for Scotland Post-Smolt capacity to avoid immediate dry-run failure in high-saturation mode.
