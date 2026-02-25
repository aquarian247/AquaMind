# HANDOFF 2026-02-25 - FW B wave9 (next5) execution and full-board recompute

## Scope
- Continue FW B-class reduction after wave8 using the next ranked residual cluster.
- Preserve existing wins: class-A must remain `0` and class-C must not expand.
- Produce fresh FishTalk culprit pack for swimlane inspection.

## Inputs
- Pre-wave board: `scripts/migration/output/fw_policy_scope_tiebreak_postwave_wave8_next5_20260224_212914.json`
- Target cohort (wave9): `121, 122, 125, 123, 124`
  - `121` Stofnfiskur Des 24
  - `122` Stofnfiskur Juni 24
  - `125` Stofnfiskur sept 24
  - `123` Stofnfiskur Mars 24
  - `124` Stofnfiskur Okt 25

## Wave9 targeted replay results
- Focused cohort mismatches: `55 -> 0` (delta `-55`)
- Focused cohort taxonomy: `A 0->0`, `B 55->0`, `C 0->0`, `D 0->0`
- All 5 replays completed successfully.

| Batch ID | Batch | Pre mism | Post mism | Delta |
| ---: | --- | ---: | ---: | ---: |
| 121 | Stofnfiskur Des 24 | 12 | 0 | -12 |
| 122 | Stofnfiskur Juni 24 | 12 | 0 | -12 |
| 125 | Stofnfiskur sept 24 | 12 | 0 | -12 |
| 123 | Stofnfiskur Mars 24 | 10 | 0 | -10 |
| 124 | Stofnfiskur Okt 25 | 9 | 0 | -9 |

## Full FW board recompute after wave9
- New full-board mismatch count: `205` (from prior `260`, delta `-55`)
- Taxonomy totals:
  - `A=0` (preserved)
  - `B=201` (reduced from `256`)
  - `C=4` (unchanged, not expanded)
  - `D=0`

## Top FishTalk culprits (post-wave9, top 10)
| Rank | Batch ID | Batch | Mismatches | B | C | Top rationale |
| ---: | ---: | --- | ---: | ---: | ---: | --- |
| 1 | 93 | NH FEB 25 | 10 | 10 | 0 | fanout_expected_zero_bucket_size_10 |
| 2 | 140 | Bakkafrost feb 2024 | 8 | 8 | 0 | fanout_expected_zero_bucket_size_8 |
| 3 | 112 | SF APR 25 | 7 | 7 | 0 | component_initial_window_expected_zero |
| 4 | 149 | Bakkafrost S-21 aug23 | 7 | 7 | 0 | component_initial_window_expected_zero |
| 5 | 150 | Bakkafrost S-21 jan 25 | 7 | 7 | 0 | component_initial_window_expected_zero |
| 6 | 152 | Bakkafrost S-21 sep24 | 7 | 7 | 0 | component_initial_window_expected_zero |
| 7 | 153 | StofnFiskur S-21 apr 25 | 7 | 7 | 0 | component_initial_window_expected_zero |
| 8 | 154 | StofnFiskur S-21 juli25 | 7 | 7 | 0 | component_initial_window_expected_zero |
| 9 | 155 | Stofnfiskur S-21 feb24 | 7 | 7 | 0 | component_initial_window_expected_zero |
| 10 | 156 | Stofnfiskur S-21 juni24 | 7 | 7 | 0 | component_initial_window_expected_zero |

## Artifacts generated
- Targeted replay:
  - `scripts/migration/output/fw_b_class_targeted_replay_wave9_next5_20260225_082242.json`
  - `scripts/migration/output/fw_b_class_targeted_replay_wave9_next5_20260225_082242.md`
- Full board:
  - `scripts/migration/output/fw_policy_scope_tiebreak_postwave_wave9_next5_20260225_082405.json`
  - `scripts/migration/output/fw_policy_scope_tiebreak_postwave_wave9_next5_20260225_082405.md`
  - `scripts/migration/output/fw_policy_scope_tiebreak_postwave_wave9_next5_20260225_082405.csv`
- FishTalk culprits:
  - `scripts/migration/output/fw_fishtalk_culprits_wave9_top20_20260225_082430.csv`
  - `scripts/migration/output/fw_fishtalk_culprits_wave9_top20_20260225_082430.md`

## Files changed this wave
- `aquamind/docs/progress/migration/handoffs/HANDOFF_2026-02-25_FW_B_WAVE9_NEXT5_EXECUTION_AND_FULLBOARD.md`

## Go / No-go
- Decision: **FW not yet ready** for marine continuation.
- Rationale: class-A remains clean and class-C did not expand, but class-B residuals remain at `201` and still require additional deterministic reduction.

## Recommended next step
- Execute next targeted wave on: `93, 140, 112, 149, 150`, then recompute full board.
- Keep FishTalk swimlane inspection prioritized for the top two fanout signatures (`93`, `140`) and any batch that shows `0` delta after replay.
