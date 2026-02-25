# Linked Marine Integrity Regression Fix R2 (553-556) - 2026-02-19

## Why this second remediation pass was needed

After the first linked remediation, GUI checks still showed cross-stage/count anomalies for `553-556` (adult counts larger than source entry stages, empty active assignments for some batches, and chronology/location confusion). The second pass targeted stale assignment carryover on reruns.

## What changed in migration tooling

- Added stale component-state pruning in `scripts/migration/tools/pilot_migrate_component.py`:
  - remove stale `BatchContainerAssignment` rows for component members no longer in the current stitched member set,
  - remove protected dependents tied to those stale assignments (transfer/creation/event records),
  - clean orphan legacy migration workflows and obsolete assignment external-id mappings.
- Retained component-scoped assignment mapping (`component_key:population_id`) to avoid cross-batch collisions on shared population ids.
- Retained linked-only synthetic stage-transition workflow policy for linked FW->Sea runs.

## Rebuild scope

Rebuilt the four linked sea batches with explicit FW seeds and full-lifecycle rebuild:

- `Vetur 2024` (`553`) <- `Benchmark Gen. Septembur 2024|3|2024`
- `Vetur 2024/2025` (`554`) <- `StofnFiskur okt. 2024|3|2024`, `Bakkafrost S-21 sep24|3|2024`, `Stofnfiskur Nov 2024|5|2024`
- `Heyst 2023` (`555`) <- `Bakkafrost Okt 2023|4|2023`
- `Vetur 2025` (`556`) <- `Stofnfiskur Des 24|4|2024`, `Benchmark Gen. Desembur 2024|4|2024`

## Post-fix integrity snapshot

All values below are live database counts after the R2 rebuild.

| Batch | Batch ID stable | Assignments (total/active) | Inactive missing departure | Stage rows | Stage population totals | Transfer workflows/actions | Location buckets |
| --- | --- | --- | ---: | --- | --- | --- | --- |
| `Vetur 2024` | `553 (unchanged)` | `58 / 6` | `0` | `Fry:39, Adult:19` | `Fry:3,500,000; Adult:1,227,321` | `1 / 19` | `S24 Strond:39; A73 Hvannas.Nordur:19` |
| `Vetur 2024/2025` | `554 (unchanged)` | `57 / 5` | `0` | `Egg&Alevin:7, Fry:5, Parr:1, Adult:44` | `Egg&Alevin:1,500,408; Fry:1,800,784; Parr:400,520; Adult:2,449,905` | `3 / 50` | `S21 Vidareidi:7; S16 Glyvradalur:5; S08 Gjogv:1; A57 Fuglafjordur:44` |
| `Heyst 2023` | `555 (unchanged)` | `12 / 0` | `0` | `Fry:6, Adult:6` | `Fry:1,627,054; Adult:527,628` | `1 / 6` | `S16 Glyvradalur:6; A81 Kolbeinargjogv:6` |
| `Vetur 2025` | `556 (unchanged)` | `78 / 7` | `0` | `Egg&Alevin:51, Adult:27` | `Egg&Alevin:5,266,339; Adult:1,499,015` | `1 / 27` | `S24 Strond:39; S03 Nordtoftir:12; A72 Haraldsund:27` |

Notes:

- This run uses `source_supported_only` stage behavior; not every batch is expected to include every pre-adult token if source support is absent.
- No inactive assignments are left with missing departure dates in these four batches.

## Semantic gate status (R2 artifacts)

All four linked batches pass regression gates (`passed=true`) with:

- `transition_alert_count = 0`
- `non_bridge_zero_assignments = 0`
- `transfer_actions.zero_count = 0`

Generated artifacts:

- `scripts/migration/output/input_batch_migration/Vetur_2024_1_2024/semantic_validation_Vetur_2024_1_2024.linked_integrity_fix_r2.md`
- `scripts/migration/output/input_batch_migration/Vetur_2024_1_2024/semantic_validation_Vetur_2024_1_2024.linked_integrity_fix_r2.json`
- `scripts/migration/output/input_batch_migration/Vetur_2024_2025_1_2024/semantic_validation_Vetur_2024_2025_1_2024.linked_integrity_fix_r2.md`
- `scripts/migration/output/input_batch_migration/Vetur_2024_2025_1_2024/semantic_validation_Vetur_2024_2025_1_2024.linked_integrity_fix_r2.json`
- `scripts/migration/output/input_batch_migration/Heyst_2023_1_2024/semantic_validation_Heyst_2023_1_2024.linked_integrity_fix_r2.md`
- `scripts/migration/output/input_batch_migration/Heyst_2023_1_2024/semantic_validation_Heyst_2023_1_2024.linked_integrity_fix_r2.json`
- `scripts/migration/output/input_batch_migration/Vetur_2025_1_2025/semantic_validation_Vetur_2025_1_2025.linked_integrity_fix_r2.md`
- `scripts/migration/output/input_batch_migration/Vetur_2025_1_2025/semantic_validation_Vetur_2025_1_2025.linked_integrity_fix_r2.json`

## Supersession

This report supersedes:

- `aquamind/docs/progress/migration/analysis_reports/2026-02-18/marine_linked_batch_integrity_remediation_553_556_2026-02-18.md`
