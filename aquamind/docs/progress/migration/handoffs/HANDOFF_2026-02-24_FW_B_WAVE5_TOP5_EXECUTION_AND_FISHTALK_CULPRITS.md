# HANDOFF 2026-02-24: FW B-wave5 top5 execution + FishTalk culprits

## Session objective
Execute the next focused FW class-B wave on the top post-wave4 residual family and produce a FishTalk-friendly culprit list for swimlane inspection.

## Cohorts replayed in this wave
- `Benchmark Gen. Mars 2025` (batch id `164`)
- `AG JAN 24` (batch id `110`)
- `NH DEC 23` (batch id `111`)
- `SF SEP 23` (batch id `91`)
- `SF SEP 23 [4-2023]` (batch id `115`)

All five replayed successfully (`returncode=0`).

## Focused wave result (5 cohorts only)
Source: `scripts/migration/output/fw_b_class_targeted_replay_wave5_top5_20260224_183041.json`

- Before: `134` mismatches (`B=134`, `C=0`)
- After: `75` mismatches (`B=75`, `C=0`)
- Delta: `-59`

Per-cohort deltas:
- `164 Benchmark Gen. Mars 2025`: `39 -> 39` (`0`)
- `110 AG JAN 24`: `24 -> 5` (`-19`)
- `111 NH DEC 23`: `24 -> 3` (`-21`)
- `91 SF SEP 23`: `24 -> 24` (`0`)
- `115 SF SEP 23 [4-2023]`: `23 -> 4` (`-19`)

## Full FW board after wave5
Source: `scripts/migration/output/fw_policy_scope_tiebreak_postwave_wave5_top5_20260224_183220.json`

- Totals:
  - `mismatches=425`
  - `A=0, B=421, C=4, D=0`
- Delta vs prior board (`fw_policy_scope_tiebreak_postwave_wave4_cluster10_20260224_180635.json`):
  - `484 -> 425` (`-59`)
  - `B: 480 -> 421` (`-59`)
  - `A` unchanged at `0`, `C` unchanged at `4`

## Cumulative progression snapshot
- Baseline reproduce: `1741` mismatches
- Post refined wave: `1222`
- Post wave2 top-4: `1007`
- Post wave3 next-5: `821`
- Post wave4 cluster10: `484`
- Post wave5 top5: `425`
- Net vs baseline: `1741 -> 425` (`-1316`)

## Ranked residual board (post wave5, top 10)
Source: `scripts/migration/output/fw_policy_scope_tiebreak_postwave_wave5_top5_20260224_183220.json`

1. `Benchmark Gen. Mars 2025` (`39`)
2. `SF SEP 23` (`24`)
3. `NH MAY 24` (`20`)
4. `SF AUG 24` (`18`)
5. `NH FEB 24` (`17`)
6. `NH FEB 25` (`15`)
7. `Bakkafrost feb 2024` (`14`)
8. `AG FEB 24` (`12`)
9. `Stofnfiskur Aug 23` (`12`)
10. `Stofnfiskur Des 23` (`12`)

## Taxonomy rationale distribution (post wave5)
- `component_initial_window_expected_zero=348`
- `component_seed_expected_zero=45`
- `fanout_expected_zero_bucket_size_10=10`
- `fanout_expected_zero_bucket_size_8=8`
- `fanout_expected_zero_bucket_size_2=6`
- `fanout_expected_zero_bucket_size_4=4`
- `inactive_departure_matches_latest_nonzero_status=4`

## FishTalk swimlane inspection pack
Generated dedicated culprit shortlist for direct FishTalk lookup:

- `scripts/migration/output/fw_fishtalk_culprits_wave5_top20_20260224_183240.csv`
- `scripts/migration/output/fw_fishtalk_culprits_wave5_top20_20260224_183240.md`

Included per culprit:
- batch id / batch number,
- `PopulationComponent` key (`component_key`) for deterministic anchor,
- primary mismatch rationale,
- sample `population_id`, container, station, and start-time values.

## New artifacts from this wave
- `scripts/migration/output/fw_b_class_targeted_replay_wave5_top5_20260224_183041.json`
- `scripts/migration/output/fw_b_class_targeted_replay_wave5_top5_20260224_183041.md`
- `scripts/migration/output/fw_policy_scope_tiebreak_postwave_wave5_top5_20260224_183220.json`
- `scripts/migration/output/fw_policy_scope_tiebreak_postwave_wave5_top5_20260224_183220.md`
- `scripts/migration/output/fw_policy_scope_tiebreak_postwave_wave5_top5_20260224_183220.csv`
- `scripts/migration/output/fw_fishtalk_culprits_wave5_top20_20260224_183240.csv`
- `scripts/migration/output/fw_fishtalk_culprits_wave5_top20_20260224_183240.md`

## Code changes in this wave
- No deterministic migration logic code changes were introduced.
- This wave was execution + evaluation + evidence packaging on top of existing exact-start authoritative rules.

## Gate decision
**FW not yet ready** for marine continuation.

Rationale:
- Additional reduction is strong but remaining `B=421` is still above readiness threshold.
- Guardrails remain intact (`A=0`, `C=4`).

## Next-step recommendation
1. Perform FT swimlane review on the two non-moving families from this wave:
   - `Benchmark Gen. Mars 2025` (`39`)
   - `SF SEP 23` (`24`)
2. Use the FishTalk culprit artifact sample `population_id` and container sequences to test whether these are true deterministic expected-zero carriers or require a scoped rule variant.
3. Run next focused replay on the updated top cluster (`164`, `91`, `94`, `96`, `92`) after swimlane evidence review.
