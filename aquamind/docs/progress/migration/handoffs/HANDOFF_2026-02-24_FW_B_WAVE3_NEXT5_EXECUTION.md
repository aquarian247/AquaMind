# HANDOFF 2026-02-24: FW B-wave3 next-5 execution

## Session objective
Execute the next recommended FW class-B reduction wave on the five highest-ranked residual cohorts after wave2, keeping deterministic exact-start handling and preserving A/C guardrails.

## Cohorts replayed in this wave
- `SF AUG 24` (`SF AUG 24|3|2024`)
- `SF APR 25` (`SF APR 25|1|2025`)
- `SF MAY 24 [3-2024]` (`SF MAY 24|3|2024`)
- `NH MAY 24` (`NH MAY 24|2|2024`)
- `SF NOV 24` (`SF NOV 24|4|2024`)

All five replayed successfully.

## Focused wave result (5 cohorts only)
Source: `scripts/migration/output/fw_b_class_targeted_replay_wave3_next5_20260224_172816.json`

- Before: `241` mismatches (`B=241`, `C=0`)
- After: `55` mismatches (`B=55`, `C=0`)
- Delta: `-186`

## Full FW board after wave3
Source: `scripts/migration/output/fw_policy_scope_tiebreak_postwave_wave3_next5_20260224_172913.json`

- Totals:
  - `mismatches=821`
  - `A=0, B=817, C=4, D=0`
- Delta vs prior board (`fw_policy_scope_tiebreak_postwave_wave2_top4_20260224_161631.json`):
  - `1007 -> 821` (`-186`)
  - `B: 1003 -> 817` (`-186`)
  - `A` unchanged at `0`, `C` unchanged at `4`

## Cumulative progression snapshot
- Baseline reproduce: `1741` mismatches
- Post refined wave: `1222`
- Post wave2 top-4: `1007`
- Post wave3 next-5: `821`
- Net vs baseline: `1741 -> 821` (`-920`)

## Ranked residual board (post wave3, top 10)
Source: `scripts/migration/output/fw_policy_scope_tiebreak_postwave_wave3_next5_20260224_172913.json`

1. `Benchmark Gen Septembur 2025` (`39`)
2. `Benchmark Gen. Desembur 2024` (`39`)
3. `Benchmark Gen. Juni 2024` (`39`)
4. `Benchmark Gen. Juni 2025` (`39`)
5. `Benchmark Gen. Mars 2024` (`39`)
6. `Benchmark Gen. Mars 2025` (`39`)
7. `Benchmark Gen. Septembur 2024` (`39`)
8. `Stofnfiskur Septembur 2023` (`39`)
9. `SF FEB 24` (`36`)
10. `SF AUG 23` (`32`)

## Taxonomy rationale distribution (post wave3)
- `component_initial_window_expected_zero=732`
- `component_seed_expected_zero=57`
- `fanout_expected_zero_bucket_size_10=10`
- `fanout_expected_zero_bucket_size_8=8`
- `fanout_expected_zero_bucket_size_2=6`
- `fanout_expected_zero_bucket_size_4=4`
- `inactive_departure_matches_latest_nonzero_status=4`

## New artifacts from this wave
- `scripts/migration/output/fw_b_class_targeted_replay_wave3_next5_20260224_172816.json`
- `scripts/migration/output/fw_b_class_targeted_replay_wave3_next5_20260224_172816.md`
- `scripts/migration/output/fw_policy_scope_tiebreak_postwave_wave3_next5_20260224_172913.json`
- `scripts/migration/output/fw_policy_scope_tiebreak_postwave_wave3_next5_20260224_172913.md`
- `scripts/migration/output/fw_policy_scope_tiebreak_postwave_wave3_next5_mismatches_20260224_172913.csv`

## Code changes in this wave
- No additional deterministic logic code changes were needed.
- This wave was execution + evaluation on top of the previously introduced exact-start authoritative logic.

## Gate decision
**FW not yet ready** for marine continuation.

Rationale:
- Material improvement continues, but class-B residual volume remains substantial (`817`).
- Guardrails remain intact (`A=0`, `C=4`).

## Next-step recommendation
1. Run the next focused wave on the top clustered residual families now leading the board:
   - `Benchmark Gen*` cohort group and `Stofnfiskur Septembur 2023` (all `39` each),
   - then `SF FEB 24` and `SF AUG 23`.
2. Maintain the same deterministic evidence protocol:
   - row-level exact-start zero proof,
   - minimal logic surface changes,
   - full-board replay after each focused wave.
3. Keep marine continuation blocked until FW reaches agreed readiness threshold with no A/C regression.
