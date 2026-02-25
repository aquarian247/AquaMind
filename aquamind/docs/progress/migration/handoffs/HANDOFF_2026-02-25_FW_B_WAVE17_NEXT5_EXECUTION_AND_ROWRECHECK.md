# HANDOFF 2026-02-25 - FW B wave17 next5 execution and row-recheck board

## Scope
- Continue FW B-class reduction after wave16.
- Execute targeted replay cohort:
  - `117` AquaGen juni 25
  - `138` Bakkafrost Juli 2023
  - `107` SF SEP 24
  - `111` NH DEC 23
  - `128` Fiskaaling sep 2022
- Preserve guardrails (`A=0`, no class-C expansion).

## Inputs
- Source mismatch-set board:
  - `scripts/migration/output/fw_policy_scope_tiebreak_postwave_wave10_next5_20260225_090255.json`
- Pre-wave17 row-recheck reference:
  - `scripts/migration/output/fw_b_class_row_recheck_wave16_next5_delayed_input_override_migrdb_20260225_143933.json`
- Existing delayed-input override remains active for the confirmed `140` pattern.

## Wave17 targeted replay result (next5)
- Net cohort delta (pre-wave17 board -> post-wave17 board): `17 -> 6` (`-11`)

| Batch ID | Batch | Before | After | Delta |
| ---: | --- | ---: | ---: | ---: |
| 117 | AquaGen juni 25 | 4 | 4 | 0 |
| 138 | Bakkafrost Juli 2023 | 4 | 0 | -4 |
| 107 | SF SEP 24 | 3 | 0 | -3 |
| 111 | NH DEC 23 | 3 | 0 | -3 |
| 128 | Fiskaaling sep 2022 | 3 | 2 | -1 |

Execution status:
- All five targeted replays exited `0`.

## Post-wave17 board (row-recheck with delayed-input override)
- Pre-wave17 board remaining mismatch rows: `40`
- Post-wave17 board remaining mismatch rows: `29`
- Delta vs pre-wave17 board: `-11`
- Delta vs source mismatch set (`184`): `-155`

Taxonomy (remaining):
- `A=0`
- `B=25`
- `C=4`
- `D=0`

Top remaining rationale counts:
- `component_seed_expected_zero=12`
- `fanout_expected_zero_bucket_size_2=6`
- `fanout_expected_zero_bucket_size_4=4`
- `inactive_departure_matches_latest_nonzero_status=4`
- `component_initial_window_expected_zero=3`

## Updated top FishTalk culprits (post-wave17)
1. `117` AquaGen juni 25 (`4`)
2. `90` 24Q1 LHS ex-LC (`3`)
3. `139` Bakkafrost Okt 2023 (`2`)
4. `109` 24Q1 LHS (`2`)
5. `128` Fiskaaling sep 2022 (`2`)
6. `104` SF MAR 25 (`2`)
7. `118` Gjógv/Fiskaaling mars 2023 (`2`)
8. `129` YC 23 (`2`)

## Artifacts generated
- Targeted replay execution:
  - `scripts/migration/output/fw_b_class_targeted_replay_wave17_next5_20260225_145014.json`
  - `scripts/migration/output/fw_b_class_targeted_replay_wave17_next5_20260225_145014.md`
- Targeted cohort delta:
  - `scripts/migration/output/fw_b_class_targeted_delta_wave17_next5_20260225_150048.json`
  - `scripts/migration/output/fw_b_class_targeted_delta_wave17_next5_20260225_150048.md`
- Post-wave17 row-recheck board:
  - `scripts/migration/output/fw_b_class_row_recheck_wave17_next5_delayed_input_override_migrdb_20260225_150012.json`
  - `scripts/migration/output/fw_b_class_row_recheck_wave17_next5_delayed_input_override_migrdb_20260225_150012.md`
- FishTalk culprit pack:
  - `scripts/migration/output/fw_fishtalk_culprits_wave17_top20_20260225_150048.csv`
  - `scripts/migration/output/fw_fishtalk_culprits_wave17_top20_20260225_150048.md`

## Files changed this wave
- `aquamind/docs/progress/migration/handoffs/HANDOFF_2026-02-25_FW_B_WAVE17_NEXT5_EXECUTION_AND_ROWRECHECK.md`

## Go / No-go
- Decision: **FW not yet ready** for marine continuation.
- Rationale: residual B is substantially reduced to `25` with guardrails intact (`A=0`, `C=4`), but still above a conservative readiness threshold.

## Recommended next step
- Execute next residual cohort:
  - `117, 90, 139, 109, 128`
- Keep the delayed-input override scope unchanged; prioritize focused FT deep-dive on the persistent `117` non-mover signature before broadening any expected-zero classifier logic.
