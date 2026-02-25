# HANDOFF 2026-02-25 - FW B wave13 delayed-input rule for 140 + next5 execution

## Scope
- Implement a deterministic, evidence-backed exception for the `140` false-positive pattern:
  - exact-start zero
  - supplier-input-backed row (no source link)
  - same-supplier continuity with component-start anchors
  - first non-zero status shortly after start
  - no near-start SubTransfers touch
  - large same-start cluster (`>=8`) to avoid broad relaxation
- Validate `140` first.
- Then run next targeted replay cohort: `156, 157, 139, 98, 106`.
- Preserve guardrails (`A=0`, no class-C expansion).

## Code changes
- `scripts/migration/tools/etl_loader.py`
  - Added `get_input_rows_by_population(...)` to expose `Ext_Inputs_v2` rows by population.
- `scripts/migration/tools/pilot_migrate_component.py`
  - Added `DataSource.get_input_rows(...)` (CSV + SQL fallback variants).
  - Added delayed-input same-supplier cluster detection and near-start SubTransfers timing map.
  - Added a guarded non-zero authoritative path for delayed-status input starts:
    - keep non-zero count for qualifying clusters instead of allowing downstream flattening.

## Focused batch-140 validation
- Batch: `140` (`Bakkafrost feb 2024`)
- Result with delayed-input rule:
  - before: `8` mismatches
  - after: `0` mismatches
  - delta: `-8`

## Wave13 targeted replay result (next5)
- Cohort: `156, 157, 139, 98, 106`
- Pre-wave13 (from prior recheck board): `30` mismatches
- Post-wave13: `2` mismatches
- Delta: `-28`

| Batch ID | Batch | Before | After | Delta |
| ---: | --- | ---: | ---: | ---: |
| 156 | Stofnfiskur S-21 juni24 | 7 | 0 | -7 |
| 157 | Stofnfiskur S-21 nov23 | 7 | 0 | -7 |
| 139 | Bakkafrost Okt 2023 | 6 | 2 | -4 |
| 98 | SF NOV 24 | 5 | 0 | -5 |
| 106 | SF NOV 23 | 5 | 0 | -5 |

## Post-wave13 board (row-recheck with delayed-input override)
- Reference pre-wave13 board (after applying the 140 override): `138`
- Post-wave13 board: `110`
- Delta vs pre-wave13 board: `-28`
- Delta vs source mismatch set (`184`): `-74`

Taxonomy (remaining):
- `A=0`
- `B=106`
- `C=4`
- `D=0`

## Ranked residual board (top culprits)
1. `109` 24Q1 LHS (`5`)
2. `110` AG JAN 24 (`5`)
3. `113` SF AUG 24 [4-2024] (`5`)
4. `114` SF MAY 24 [3-2024] (`5`)
5. `116` AquaGen Mars 25 (`5`)
6. `143` Stofnfiskur Aug 2024 (`5`)
7. `144` Stofnfiskur August 25 (`5`)
8. `145` Stofnfiskur Nov 2024 (`5`)
9. `146` Stofnfiskur feb 2025 (`5`)
10. `147` Stofnfiskur mai 2024 (`5`)

## Artifacts generated
- `140` focused validation:
  - `scripts/migration/output/fw_b140_delayed_input_rule_validation_migrdb_20260225_133045.json`
  - `scripts/migration/output/fw_b140_delayed_input_rule_validation_migrdb_20260225_133045.md`
- Pre-next5 board (with delayed-input override):
  - `scripts/migration/output/fw_b_class_row_recheck_wave13_delayed_input_override_migrdb_20260225_133213.json`
  - `scripts/migration/output/fw_b_class_row_recheck_wave13_delayed_input_override_migrdb_20260225_133213.md`
- Targeted replay execution (next5):
  - `scripts/migration/output/fw_b_class_targeted_replay_wave13_next5_20260225_133256.json`
  - `scripts/migration/output/fw_b_class_targeted_replay_wave13_next5_20260225_133256.md`
- Post-next5 board (with delayed-input override):
  - `scripts/migration/output/fw_b_class_row_recheck_wave13_next5_delayed_input_override_migrdb_20260225_135012.json`
  - `scripts/migration/output/fw_b_class_row_recheck_wave13_next5_delayed_input_override_migrdb_20260225_135012.md`

## Files changed this wave
- `scripts/migration/tools/etl_loader.py`
- `scripts/migration/tools/pilot_migrate_component.py`
- `aquamind/docs/progress/migration/handoffs/HANDOFF_2026-02-25_FW_B_WAVE13_140_DELAYED_INPUT_RULE_AND_NEXT5.md`

## Go / No-go
- Decision: **FW not yet ready** for marine continuation.
- Rationale: significant reduction achieved (`138 -> 110` on the rechecked board), but residual class-B remains material (`B=106`) and must be reduced further before FW can be considered ready.

## Recommended next step
- Run the next residual cohort centered on the `5-count` tie group:
  - `109, 110, 113, 114, 116`
- Keep the delayed-input `fanout_expected_zero_bucket_size_8` exception locked as-is (narrow scope) and require FT evidence before any broader fanout relaxation.
