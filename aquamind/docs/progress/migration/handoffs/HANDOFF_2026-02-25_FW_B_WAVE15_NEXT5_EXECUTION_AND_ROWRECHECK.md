# HANDOFF 2026-02-25 - FW B wave15 next5 execution and row-recheck board

## Scope
- Continue FW B-class reduction after wave14.
- Execute targeted replay cohort:
  - `143` Stofnfiskur Aug 2024
  - `144` Stofnfiskur August 25
  - `145` Stofnfiskur Nov 2024
  - `146` Stofnfiskur feb 2025
  - `147` Stofnfiskur mai 2024
- Preserve guardrails (`A=0`, no class-C expansion).

## Inputs
- Source mismatch-set board:
  - `scripts/migration/output/fw_policy_scope_tiebreak_postwave_wave10_next5_20260225_090255.json`
- Pre-wave15 row-recheck reference:
  - `scripts/migration/output/fw_b_class_row_recheck_wave14_next5_delayed_input_override_migrdb_20260225_140642.json`
- Existing delayed-input override remains active for the confirmed `140` pattern.

## Wave15 targeted replay result (next5)
- Net cohort delta (pre-wave15 board -> post-wave15 board): `25 -> 0` (`-25`)

| Batch ID | Batch | Before | After | Delta |
| ---: | --- | ---: | ---: | ---: |
| 143 | Stofnfiskur Aug 2024 | 5 | 0 | -5 |
| 144 | Stofnfiskur August 25 | 5 | 0 | -5 |
| 145 | Stofnfiskur Nov 2024 | 5 | 0 | -5 |
| 146 | Stofnfiskur feb 2025 | 5 | 0 | -5 |
| 147 | Stofnfiskur mai 2024 | 5 | 0 | -5 |

Execution status:
- All five targeted replays exited `0`.

## Post-wave15 board (row-recheck with delayed-input override)
- Pre-wave15 board remaining mismatch rows: `87`
- Post-wave15 board remaining mismatch rows: `62`
- Delta vs pre-wave15 board: `-25`
- Delta vs source mismatch set (`184`): `-122`

Taxonomy (remaining):
- `A=0`
- `B=58`
- `C=4`
- `D=0`

Top remaining rationale counts:
- `component_initial_window_expected_zero=32`
- `component_seed_expected_zero=16`
- `fanout_expected_zero_bucket_size_2=6`
- `fanout_expected_zero_bucket_size_4=4`
- `inactive_departure_matches_latest_nonzero_status=4`

## Updated top FishTalk culprits (post-wave15)
1. `148` Stofnfiskur mai 2025 (`5`)
2. `151` Bakkafrost S-21 okt 25 (`5`)
3. `101` SF FEB 24 (`4`)
4. `105` SF MAY 24 (`4`)
5. `115` SF SEP 23 [4-2023] (`4`)
6. `117` AquaGen juni 25 (`4`)
7. `138` Bakkafrost Juli 2023 (`4`)

## Artifacts generated
- Targeted replay execution:
  - `scripts/migration/output/fw_b_class_targeted_replay_wave15_next5_20260225_141035.json`
  - `scripts/migration/output/fw_b_class_targeted_replay_wave15_next5_20260225_141035.md`
- Targeted cohort delta:
  - `scripts/migration/output/fw_b_class_targeted_delta_wave15_next5_20260225_142414.json`
  - `scripts/migration/output/fw_b_class_targeted_delta_wave15_next5_20260225_142414.md`
- Post-wave15 row-recheck board:
  - `scripts/migration/output/fw_b_class_row_recheck_wave15_next5_delayed_input_override_migrdb_20260225_142339.json`
  - `scripts/migration/output/fw_b_class_row_recheck_wave15_next5_delayed_input_override_migrdb_20260225_142339.md`
- FishTalk culprit pack:
  - `scripts/migration/output/fw_fishtalk_culprits_wave15_top20_20260225_142414.csv`
  - `scripts/migration/output/fw_fishtalk_culprits_wave15_top20_20260225_142414.md`

## Files changed this wave
- `aquamind/docs/progress/migration/handoffs/HANDOFF_2026-02-25_FW_B_WAVE15_NEXT5_EXECUTION_AND_ROWRECHECK.md`

## Go / No-go
- Decision: **FW not yet ready** for marine continuation.
- Rationale: reduction is strong (`87 -> 62`) with guardrails intact (`A=0`, `C=4`), but residual class-B (`58`) is still material.

## Recommended next step
- Execute next top residual cohort:
  - `148, 151, 101, 105, 115`
- Keep delayed-input override scope unchanged and continue evidence-first FT validation before any additional expected-zero classifier expansion.
