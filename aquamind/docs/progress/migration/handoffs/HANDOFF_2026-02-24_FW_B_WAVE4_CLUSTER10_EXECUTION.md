# HANDOFF 2026-02-24: FW B-wave4 cluster10 execution

## Session objective
Execute the next recommended FW class-B reduction wave on the 10-batch cluster (`Benchmark Gen*`, `Stofnfiskur Septembur 2023`, `SF FEB 24`, `SF AUG 23`) while preserving exact-start deterministic behavior and A/C guardrails.

## Cohorts replayed in this wave
- `Benchmark Gen Septembur 2025` (batch id `159`)
- `Benchmark Gen. Desembur 2024` (batch id `160`)
- `Benchmark Gen. Juni 2024` (batch id `161`)
- `Benchmark Gen. Juni 2025` (batch id `162`)
- `Benchmark Gen. Mars 2024` (batch id `163`)
- `Benchmark Gen. Mars 2025` (batch id `164`)
- `Benchmark Gen. Septembur 2024` (batch id `165`)
- `Stofnfiskur Septembur 2023` (batch id `166`)
- `SF FEB 24` (batch id `101`)
- `SF AUG 23` (batch id `95`)

All 10 replayed successfully (`returncode=0`).

## Focused wave result (10 cohorts only)
Source: `scripts/migration/output/fw_b_class_targeted_replay_wave4_cluster10_20260224_180423.json`

- Before: `380` mismatches (`B=380`, `C=0`)
- After: `43` mismatches (`B=43`, `C=0`)
- Delta: `-337`

Per-cohort highlights:
- `159/160/161/162/163/165/166`: each reduced `39 -> 0`
- `101 (SF FEB 24)`: reduced `36 -> 4`
- `95 (SF AUG 23)`: reduced `32 -> 0`
- `164 (Benchmark Gen. Mars 2025)`: unchanged `39 -> 39` (all residuals still `component_initial_window_expected_zero`/`component_seed_expected_zero`)

## Full FW board after wave4
Source: `scripts/migration/output/fw_policy_scope_tiebreak_postwave_wave4_cluster10_20260224_180635.json`

- Totals:
  - `mismatches=484`
  - `A=0, B=480, C=4, D=0`
- Delta vs prior board (`fw_policy_scope_tiebreak_postwave_wave3_next5_20260224_172913.json`):
  - `821 -> 484` (`-337`)
  - `B: 817 -> 480` (`-337`)
  - `A` unchanged at `0`, `C` unchanged at `4`

## Cumulative progression snapshot
- Baseline reproduce: `1741` mismatches
- Post refined wave: `1222`
- Post wave2 top-4: `1007`
- Post wave3 next-5: `821`
- Post wave4 cluster10: `484`
- Net vs baseline: `1741 -> 484` (`-1257`)

## Ranked residual board (post wave4, top 10)
Source: `scripts/migration/output/fw_policy_scope_tiebreak_postwave_wave4_cluster10_20260224_180635.json`

1. `Benchmark Gen. Mars 2025` (`39`)
2. `AG JAN 24` (`24`)
3. `NH DEC 23` (`24`)
4. `SF SEP 23` (`24`)
5. `SF SEP 23 [4-2023]` (`23`)
6. `NH MAY 24` (`20`)
7. `SF AUG 24` (`18`)
8. `NH FEB 24` (`17`)
9. `NH FEB 25` (`15`)
10. `Bakkafrost feb 2024` (`14`)

## Taxonomy rationale distribution (post wave4)
- `component_initial_window_expected_zero=404`
- `component_seed_expected_zero=48`
- `fanout_expected_zero_bucket_size_10=10`
- `fanout_expected_zero_bucket_size_8=8`
- `fanout_expected_zero_bucket_size_2=6`
- `fanout_expected_zero_bucket_size_4=4`
- `inactive_departure_matches_latest_nonzero_status=4`

## New artifacts from this wave
- `scripts/migration/output/fw_b_class_targeted_replay_wave4_cluster10_20260224_180423.json`
- `scripts/migration/output/fw_b_class_targeted_replay_wave4_cluster10_20260224_180423.md`
- `scripts/migration/output/fw_policy_scope_tiebreak_postwave_wave4_cluster10_20260224_180635.json`
- `scripts/migration/output/fw_policy_scope_tiebreak_postwave_wave4_cluster10_20260224_180635.md`
- `scripts/migration/output/fw_policy_scope_tiebreak_postwave_wave4_cluster10_20260224_180635.csv`

## Code changes in this wave
- No deterministic logic code changes were introduced.
- This wave was execution + evaluation on top of previously introduced exact-start authoritative logic.

## Gate decision
**FW not yet ready** for marine continuation.

Rationale:
- Strong additional reduction in class-B residuals, but remaining `B=480` is still above readiness threshold.
- Guardrails remain intact (`A=0`, `C=4`), so no regression was introduced while reducing B.

## Next-step recommendation
1. Execute the next focused wave on the current top family:
   - `Benchmark Gen. Mars 2025` (single remaining `39` cluster),
   - then the `24/24/24/23` group (`AG JAN 24`, `NH DEC 23`, `SF SEP 23`, `SF SEP 23 [4-2023]`).
2. For `Benchmark Gen. Mars 2025`, run row-level FT evidence extraction first (same exact-start zero proof used previously) because this cohort did not move in wave4 despite sibling cohorts collapsing to zero.
3. Continue full-board replay after each focused wave; keep marine continuation blocked until FW reaches agreed readiness threshold with `A=0` and no C-class expansion.
