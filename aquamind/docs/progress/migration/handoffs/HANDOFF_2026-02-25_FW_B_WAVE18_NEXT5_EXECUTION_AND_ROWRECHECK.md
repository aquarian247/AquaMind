# HANDOFF 2026-02-25 - FW B wave18 next5 execution and row-recheck board

## Scope
- Continue FW B-class reduction after wave17.
- Execute targeted replay cohort:
  - `117` AquaGen juni 25
  - `90` 24Q1 LHS ex-LC
  - `139` Bakkafrost Okt 2023
  - `109` 24Q1 LHS
  - `128` Fiskaaling sep 2022
- Preserve guardrails (`A=0`, no class-C expansion).

## Inputs
- Source mismatch-set board:
  - `scripts/migration/output/fw_policy_scope_tiebreak_postwave_wave10_next5_20260225_090255.json`
- Pre-wave18 row-recheck reference:
  - `scripts/migration/output/fw_b_class_row_recheck_wave17_next5_delayed_input_override_migrdb_20260225_150012.json`
- Existing delayed-input override remains active for the confirmed `140` pattern.

## Wave18 targeted replay result (next5)
- Net cohort delta (pre-wave18 board -> post-wave18 board): `13 -> 12` (`-1`)

| Batch ID | Batch | Before | After | Delta |
| ---: | --- | ---: | ---: | ---: |
| 117 | AquaGen juni 25 | 4 | 4 | 0 |
| 90 | 24Q1 LHS ex-LC | 3 | 2 | -1 |
| 139 | Bakkafrost Okt 2023 | 2 | 2 | 0 |
| 109 | 24Q1 LHS | 2 | 2 | 0 |
| 128 | Fiskaaling sep 2022 | 2 | 2 | 0 |

Execution status:
- All five targeted replays exited `0`.

## Post-wave18 board (row-recheck with delayed-input override)
- Pre-wave18 board remaining mismatch rows: `29`
- Post-wave18 board remaining mismatch rows: `28`
- Delta vs pre-wave18 board: `-1`
- Delta vs source mismatch set (`184`): `-156`

Taxonomy (remaining):
- `A=0`
- `B=24`
- `C=4`
- `D=0`

Top remaining rationale counts:
- `component_seed_expected_zero=11`
- `fanout_expected_zero_bucket_size_2=6`
- `fanout_expected_zero_bucket_size_4=4`
- `inactive_departure_matches_latest_nonzero_status=4`
- `component_initial_window_expected_zero=3`

## Updated top FishTalk culprits (post-wave18)
1. `117` AquaGen juni 25 (`4`)
2. `139` Bakkafrost Okt 2023 (`2`)
3. `109` 24Q1 LHS (`2`)
4. `128` Fiskaaling sep 2022 (`2`)
5. `90` 24Q1 LHS ex-LC (`2`)

## Artifacts generated
- Targeted replay execution:
  - `scripts/migration/output/fw_b_class_targeted_replay_wave18_next5_20260225_150514.json`
  - `scripts/migration/output/fw_b_class_targeted_replay_wave18_next5_20260225_150514.md`
- Targeted cohort delta:
  - `scripts/migration/output/fw_b_class_targeted_delta_wave18_next5_20260225_151546.json`
  - `scripts/migration/output/fw_b_class_targeted_delta_wave18_next5_20260225_151546.md`
- Post-wave18 row-recheck board:
  - `scripts/migration/output/fw_b_class_row_recheck_wave18_next5_delayed_input_override_migrdb_20260225_151512.json`
  - `scripts/migration/output/fw_b_class_row_recheck_wave18_next5_delayed_input_override_migrdb_20260225_151512.md`
- FishTalk culprit pack:
  - `scripts/migration/output/fw_fishtalk_culprits_wave18_top20_20260225_151546.csv`
  - `scripts/migration/output/fw_fishtalk_culprits_wave18_top20_20260225_151546.md`

## Files changed this wave
- `aquamind/docs/progress/migration/handoffs/HANDOFF_2026-02-25_FW_B_WAVE18_NEXT5_EXECUTION_AND_ROWRECHECK.md`

## Go / No-go
- Decision: **FW not yet ready** for marine continuation.
- Rationale: residual B is down to `24` with guardrails intact (`A=0`, `C=4`), but this wave showed diminishing replay returns (`-1`), indicating more evidence-led refinement is needed.

## Recommended next step
- Prioritize focused FishTalk evidence extraction for persistent non-movers:
  - `117` (primary), then `139`, `109`, `128`, `90`
- Then apply one minimal deterministic rule candidate for the dominant validated non-mover pattern before running another replay cohort.
