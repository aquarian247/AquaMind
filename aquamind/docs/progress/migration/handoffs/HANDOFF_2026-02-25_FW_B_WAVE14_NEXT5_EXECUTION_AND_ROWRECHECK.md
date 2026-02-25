# HANDOFF 2026-02-25 - FW B wave14 next5 execution and row-recheck board

## Scope
- Continue FW B-class reduction after wave13.
- Execute targeted replay cohort:
  - `109` 24Q1 LHS
  - `110` AG JAN 24
  - `113` SF AUG 24 [4-2024]
  - `114` SF MAY 24 [3-2024]
  - `116` AquaGen Mars 25
- Preserve guardrails (`A=0`, no class-C expansion).

## Inputs
- Source mismatch-set board:
  - `scripts/migration/output/fw_policy_scope_tiebreak_postwave_wave10_next5_20260225_090255.json`
- Pre-wave14 row-recheck reference:
  - `scripts/migration/output/fw_b_class_row_recheck_wave13_next5_delayed_input_override_migrdb_20260225_135012.json`
- Existing delayed-input override stays active for the confirmed `140` pattern.

## Wave14 targeted replay result (next5)
- Net cohort delta (pre-wave14 board -> post-wave14 board): `25 -> 2` (`-23`)

| Batch ID | Batch | Before | After | Delta |
| ---: | --- | ---: | ---: | ---: |
| 109 | 24Q1 LHS | 5 | 2 | -3 |
| 110 | AG JAN 24 | 5 | 0 | -5 |
| 113 | SF AUG 24 [4-2024] | 5 | 0 | -5 |
| 114 | SF MAY 24 [3-2024] | 5 | 0 | -5 |
| 116 | AquaGen Mars 25 | 5 | 0 | -5 |

Execution status:
- All five targeted replays exited `0`.

## Post-wave14 board (row-recheck with delayed-input override)
- Pre-wave14 board remaining mismatch rows: `110`
- Post-wave14 board remaining mismatch rows: `87`
- Delta vs pre-wave14 board: `-23`
- Delta vs source mismatch set (`184`): `-97`

Taxonomy (remaining):
- `A=0`
- `B=83`
- `C=4`
- `D=0`

Top remaining rationale counts:
- `component_initial_window_expected_zero=52`
- `component_seed_expected_zero=21`
- `fanout_expected_zero_bucket_size_2=6`
- `fanout_expected_zero_bucket_size_4=4`
- `inactive_departure_matches_latest_nonzero_status=4`

## Updated top FishTalk culprits (post-wave14)
1. `143` Stofnfiskur Aug 2024 (`5`)
2. `144` Stofnfiskur August 25 (`5`)
3. `145` Stofnfiskur Nov 2024 (`5`)
4. `146` Stofnfiskur feb 2025 (`5`)
5. `147` Stofnfiskur mai 2024 (`5`)
6. `148` Stofnfiskur mai 2025 (`5`)
7. `151` Bakkafrost S-21 okt 25 (`5`)

## Artifacts generated
- Targeted replay execution:
  - `scripts/migration/output/fw_b_class_targeted_replay_wave14_next5_20260225_135441.json`
  - `scripts/migration/output/fw_b_class_targeted_replay_wave14_next5_20260225_135441.md`
- Targeted cohort delta:
  - `scripts/migration/output/fw_b_class_targeted_delta_wave14_next5_20260225_140738.json`
  - `scripts/migration/output/fw_b_class_targeted_delta_wave14_next5_20260225_140738.md`
- Post-wave14 row-recheck board:
  - `scripts/migration/output/fw_b_class_row_recheck_wave14_next5_delayed_input_override_migrdb_20260225_140642.json`
  - `scripts/migration/output/fw_b_class_row_recheck_wave14_next5_delayed_input_override_migrdb_20260225_140642.md`
- FishTalk culprit pack:
  - `scripts/migration/output/fw_fishtalk_culprits_wave14_top20_20260225_140738.csv`
  - `scripts/migration/output/fw_fishtalk_culprits_wave14_top20_20260225_140738.md`

## Files changed this wave
- `aquamind/docs/progress/migration/handoffs/HANDOFF_2026-02-25_FW_B_WAVE14_NEXT5_EXECUTION_AND_ROWRECHECK.md`

## Go / No-go
- Decision: **FW not yet ready** for marine continuation.
- Rationale: substantial progress continues (`110 -> 87`), class-A remains `0`, and class-C remains stable at `4`, but residual class-B (`83`) is still material.

## Recommended next step
- Execute the next top residual cohort:
  - `143, 144, 145, 146, 147`
- Keep delayed-input override scope unchanged and demand FT evidence before any additional expected-zero classifier changes.
