# HANDOFF 2026-02-25 - FW B wave10 (next5) execution and full-board recompute

## Scope
- Continue FW B-class reduction after wave9 using next ranked cohort.
- Preserve existing wins (class-A at `0`, class-C not expanded).
- Capture fresh FishTalk culprit set, with explicit non-mover flags.

## Inputs
- Pre-wave board: `scripts/migration/output/fw_policy_scope_tiebreak_postwave_wave9_next5_20260225_082405.json`
- Target cohort (wave10): `93, 140, 112, 149, 150`
  - `93` NH FEB 25
  - `140` Bakkafrost feb 2024
  - `112` SF APR 25
  - `149` Bakkafrost S-21 aug23
  - `150` Bakkafrost S-21 jan 25

## Wave10 targeted replay results
- Focused cohort mismatches: `39 -> 18` (delta `-21`)
- Focused cohort taxonomy: `A 0->0`, `B 39->18`, `C 0->0`, `D 0->0`
- All 5 replays completed successfully.

| Batch ID | Batch | Pre mism | Post mism | Delta | Outcome |
| ---: | --- | ---: | ---: | ---: | --- |
| 93 | NH FEB 25 | 10 | 10 | 0 | non-mover |
| 140 | Bakkafrost feb 2024 | 8 | 8 | 0 | non-mover |
| 112 | SF APR 25 | 7 | 0 | -7 | cleared |
| 149 | Bakkafrost S-21 aug23 | 7 | 0 | -7 | cleared |
| 150 | Bakkafrost S-21 jan 25 | 7 | 0 | -7 | cleared |

## Full FW board recompute after wave10
- New full-board mismatch count: `184` (from prior `205`, delta `-21`)
- Taxonomy totals:
  - `A=0` (preserved)
  - `B=180` (reduced from `201`)
  - `C=4` (unchanged, not expanded)
  - `D=0`

## Top FishTalk culprits (post-wave10, top 10)
| Rank | Batch ID | Batch | Mismatches | B | C | Top rationale |
| ---: | ---: | --- | ---: | ---: | ---: | --- |
| 1 | 93 | NH FEB 25 | 10 | 10 | 0 | fanout_expected_zero_bucket_size_10 |
| 2 | 140 | Bakkafrost feb 2024 | 8 | 8 | 0 | fanout_expected_zero_bucket_size_8 |
| 3 | 152 | Bakkafrost S-21 sep24 | 7 | 7 | 0 | component_initial_window_expected_zero |
| 4 | 153 | StofnFiskur S-21 apr 25 | 7 | 7 | 0 | component_initial_window_expected_zero |
| 5 | 154 | StofnFiskur S-21 juli25 | 7 | 7 | 0 | component_initial_window_expected_zero |
| 6 | 155 | Stofnfiskur S-21 feb24 | 7 | 7 | 0 | component_initial_window_expected_zero |
| 7 | 156 | Stofnfiskur S-21 juni24 | 7 | 7 | 0 | component_initial_window_expected_zero |
| 8 | 157 | Stofnfiskur S-21 nov23 | 7 | 7 | 0 | component_initial_window_expected_zero |
| 9 | 139 | Bakkafrost Okt 2023 | 6 | 6 | 0 | component_initial_window_expected_zero |
| 10 | 98 | SF NOV 24 | 5 | 5 | 0 | component_initial_window_expected_zero |

## Artifacts generated
- Targeted replay:
  - `scripts/migration/output/fw_b_class_targeted_replay_wave10_next5_20260225_090100.json`
  - `scripts/migration/output/fw_b_class_targeted_replay_wave10_next5_20260225_090100.md`
- Full board:
  - `scripts/migration/output/fw_policy_scope_tiebreak_postwave_wave10_next5_20260225_090255.json`
  - `scripts/migration/output/fw_policy_scope_tiebreak_postwave_wave10_next5_20260225_090255.md`
  - `scripts/migration/output/fw_policy_scope_tiebreak_postwave_wave10_next5_20260225_090255.csv`
- FishTalk culprits:
  - `scripts/migration/output/fw_fishtalk_culprits_wave10_top20_20260225_090310.csv`
  - `scripts/migration/output/fw_fishtalk_culprits_wave10_top20_20260225_090310.md`

## Files changed this wave
- `aquamind/docs/progress/migration/handoffs/HANDOFF_2026-02-25_FW_B_WAVE10_NEXT5_EXECUTION_AND_FULLBOARD.md`

## Go / No-go
- Decision: **FW not yet ready** for marine continuation.
- Rationale: class-A remains clean and class-C is stable, but class-B residuals still at `180`.

## Recommended next step
- Run next targeted wave on the highest remaining cluster:
  - `93, 140, 152, 153, 154`
- For `93` and `140`, prioritize row-level FishTalk swimlane evidence and isolate why deterministic guards are not reducing those fanout signatures.
