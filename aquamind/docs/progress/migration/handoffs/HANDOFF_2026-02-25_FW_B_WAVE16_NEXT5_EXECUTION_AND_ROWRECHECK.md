# HANDOFF 2026-02-25 - FW B wave16 next5 execution and row-recheck board

## Scope
- Continue FW B-class reduction after wave15.
- Execute targeted replay cohort:
  - `148` Stofnfiskur mai 2025
  - `151` Bakkafrost S-21 okt 25
  - `101` SF FEB 24
  - `105` SF MAY 24
  - `115` SF SEP 23 [4-2023]
- Preserve guardrails (`A=0`, no class-C expansion).

## Inputs
- Source mismatch-set board:
  - `scripts/migration/output/fw_policy_scope_tiebreak_postwave_wave10_next5_20260225_090255.json`
- Pre-wave16 row-recheck reference:
  - `scripts/migration/output/fw_b_class_row_recheck_wave15_next5_delayed_input_override_migrdb_20260225_142339.json`
- Existing delayed-input override remains active for the confirmed `140` pattern.

## Wave16 targeted replay result (next5)
- Net cohort delta (pre-wave16 board -> post-wave16 board): `22 -> 0` (`-22`)

| Batch ID | Batch | Before | After | Delta |
| ---: | --- | ---: | ---: | ---: |
| 148 | Stofnfiskur mai 2025 | 5 | 0 | -5 |
| 151 | Bakkafrost S-21 okt 25 | 5 | 0 | -5 |
| 101 | SF FEB 24 | 4 | 0 | -4 |
| 105 | SF MAY 24 | 4 | 0 | -4 |
| 115 | SF SEP 23 [4-2023] | 4 | 0 | -4 |

Execution status:
- All five targeted replays exited `0`.

## Post-wave16 board (row-recheck with delayed-input override)
- Pre-wave16 board remaining mismatch rows: `62`
- Post-wave16 board remaining mismatch rows: `40`
- Delta vs pre-wave16 board: `-22`
- Delta vs source mismatch set (`184`): `-144`

Taxonomy (remaining):
- `A=0`
- `B=36`
- `C=4`
- `D=0`

Top remaining rationale counts:
- `component_seed_expected_zero=14`
- `component_initial_window_expected_zero=12`
- `fanout_expected_zero_bucket_size_2=6`
- `fanout_expected_zero_bucket_size_4=4`
- `inactive_departure_matches_latest_nonzero_status=4`

## Updated top FishTalk culprits (post-wave16)
1. `117` AquaGen juni 25 (`4`)
2. `138` Bakkafrost Juli 2023 (`4`)
3. `107` SF SEP 24 (`3`)
4. `111` NH DEC 23 (`3`)
5. `128` Fiskaaling sep 2022 (`3`)
6. `90` 24Q1 LHS ex-LC (`3`)

## Artifacts generated
- Targeted replay execution:
  - `scripts/migration/output/fw_b_class_targeted_replay_wave16_next5_20260225_142830.json`
  - `scripts/migration/output/fw_b_class_targeted_replay_wave16_next5_20260225_142830.md`
- Targeted cohort delta:
  - `scripts/migration/output/fw_b_class_targeted_delta_wave16_next5_20260225_144006.json`
  - `scripts/migration/output/fw_b_class_targeted_delta_wave16_next5_20260225_144006.md`
- Post-wave16 row-recheck board:
  - `scripts/migration/output/fw_b_class_row_recheck_wave16_next5_delayed_input_override_migrdb_20260225_143933.json`
  - `scripts/migration/output/fw_b_class_row_recheck_wave16_next5_delayed_input_override_migrdb_20260225_143933.md`
- FishTalk culprit pack:
  - `scripts/migration/output/fw_fishtalk_culprits_wave16_top20_20260225_144006.csv`
  - `scripts/migration/output/fw_fishtalk_culprits_wave16_top20_20260225_144006.md`

## Files changed this wave
- `aquamind/docs/progress/migration/handoffs/HANDOFF_2026-02-25_FW_B_WAVE16_NEXT5_EXECUTION_AND_ROWRECHECK.md`

## Go / No-go
- Decision: **FW not yet ready** for marine continuation.
- Rationale: reduction remains strong (`62 -> 40`) with guardrails intact (`A=0`, `C=4`), but residual class-B (`36`) still needs further reduction.

## Recommended next step
- Execute next top residual cohort:
  - `117, 138, 107, 111, 128`
- Keep delayed-input override scope unchanged and continue strict FT evidence before expanding any expected-zero classifier logic.
