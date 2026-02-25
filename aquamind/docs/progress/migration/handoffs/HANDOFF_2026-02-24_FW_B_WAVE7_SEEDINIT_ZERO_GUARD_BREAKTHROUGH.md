# HANDOFF 2026-02-24: FW B-wave7 seed/init zero guard breakthrough

## Session objective
Continue FW class-B reduction while waiting for manual FishTalk swimlane review by:
- building stronger non-mover evidence for previously stuck families,
- testing a minimal deterministic rule guard,
- and replaying the highest-impact cluster.

## What was executed
1. Built non-mover swimlane evidence pack for `164` + `91` to validate row-level signatures.
2. Ran wave6 likely-movers replay (`94, 96, 92, 93, 140`) to confirm no-change baseline.
3. Applied minimal deterministic guard in `pilot_migrate_component.py`:
   - re-enforce seed/initial-window exact-start zero authority immediately before assignment persistence (prevents later same-stage/bridge heuristics from re-inflating counts).
4. Ran wave7 focused replay on top cluster (`164, 91, 94, 96, 92`).
5. Recomputed full FW board and regenerated FishTalk culprit shortlist.

## Non-mover evidence (pre-fix)
Source: `scripts/migration/output/fw_nonmovers_swimlane_evidence_wave5_20260224_201750.csv`

Key signature:
- `63` total mismatch rows (`39` for `164`, `24` for `91`)
- all rows had `expected_count=0`
- all rows had `exact_start_counts_seen=0`
- all rows were inactive historical holders (`is_active=0`)
- primary rationale: `component_initial_window_expected_zero` (plus 2 seed rows)

This supported a scoped guard against downstream re-inflation after exact-start zero was already proven.

## Wave6 control run (likely movers, pre-fix)
Source: `scripts/migration/output/fw_b_class_targeted_replay_wave6_likely_movers_20260224_203206.json`

- Scope: `94, 96, 92, 93, 140`
- Before: `84` mismatches (`B=84`)
- After: `84` mismatches (`B=84`)
- Delta: `0`

Purpose: confirm these families were still non-moving before applying new logic.

## Code change introduced
File changed:
- `scripts/migration/tools/pilot_migrate_component.py`

Change summary:
- Added a single guard right before assignment materialization:
  - if `exact_start_seed_init_zero_authoritative` is true, force `count=0` and `biomass=0`.
- This preserves prior exact-start policy and prevents same-stage/bridge/mixing blocks from re-inflating closed historical rows later in the flow.

## Wave7 focused replay result (post-fix)
Source: `scripts/migration/output/fw_b_class_targeted_replay_wave7_seedinit_guard_20260224_204952.json`

- Scope: `164, 91, 94, 96, 92`
- Before: `118` mismatches (`B=118`, `C=0`)
- After: `0` mismatches (`B=0`, `C=0`)
- Delta: `-118`

Per-cohort deltas:
- `164 Benchmark Gen. Mars 2025`: `39 -> 0` (`-39`)
- `91 SF SEP 23`: `24 -> 0` (`-24`)
- `94 NH MAY 24`: `20 -> 0` (`-20`)
- `96 SF AUG 24`: `18 -> 0` (`-18`)
- `92 NH FEB 24`: `17 -> 0` (`-17`)

## Full FW board after wave7
Source: `scripts/migration/output/fw_policy_scope_tiebreak_postwave_wave7_seedinit_guard_20260224_205050.json`

- Totals:
  - `mismatches=307`
  - `A=0, B=303, C=4, D=0`
- Delta vs pre-wave7 board (`fw_policy_scope_tiebreak_postwave_wave6_likely_movers_20260224_203419.json`):
  - `425 -> 307` (`-118`)
  - `B: 421 -> 303` (`-118`)
  - `A` unchanged at `0`, `C` unchanged at `4`

## Cumulative progression snapshot
- Baseline reproduce: `1741`
- Post wave5 top5: `425`
- Post wave7 seed/init guard: `307`
- Net vs baseline: `1741 -> 307` (`-1434`)

## Ranked residual board (post-wave7, top 10)
Source: `scripts/migration/output/fw_policy_scope_tiebreak_postwave_wave7_seedinit_guard_20260224_205050.json`

1. `NH FEB 25` (`15`)
2. `Bakkafrost feb 2024` (`14`)
3. `AG FEB 24` (`12`)
4. `Stofnfiskur Aug 23` (`12`)
5. `Stofnfiskur Des 23` (`12`)
6. `Stofnfiskur Des 24` (`12`)
7. `Stofnfiskur Juni 24` (`12`)
8. `Stofnfiskur sept 24` (`12`)
9. `Stofnfiskur Mars 24` (`10`)
10. `Stofnfiskur Okt 25` (`9`)

## Taxonomy rationale distribution (post-wave7)
- `component_initial_window_expected_zero=233`
- `component_seed_expected_zero=42`
- `fanout_expected_zero_bucket_size_10=10`
- `fanout_expected_zero_bucket_size_8=8`
- `fanout_expected_zero_bucket_size_2=6`
- `fanout_expected_zero_bucket_size_4=4`
- `inactive_departure_matches_latest_nonzero_status=4`

## Updated FishTalk culprit pack
- `scripts/migration/output/fw_fishtalk_culprits_wave7_top20_20260224_205107.csv`
- `scripts/migration/output/fw_fishtalk_culprits_wave7_top20_20260224_205107.md`

Top 5 now:
1. `93 NH FEB 25` (`15`)
2. `140 Bakkafrost feb 2024` (`14`)
3. `99 AG FEB 24` (`12`)
4. `119 Stofnfiskur Aug 23` (`12`)
5. `120 Stofnfiskur Des 23` (`12`)

## New artifacts from this session
- `scripts/migration/output/fw_nonmovers_swimlane_evidence_wave5_20260224_201750.csv`
- `scripts/migration/output/fw_nonmovers_swimlane_evidence_wave5_20260224_201750.md`
- `scripts/migration/output/fw_b_class_targeted_replay_wave6_likely_movers_20260224_203206.json`
- `scripts/migration/output/fw_b_class_targeted_replay_wave6_likely_movers_20260224_203206.md`
- `scripts/migration/output/fw_policy_scope_tiebreak_postwave_wave6_likely_movers_20260224_203419.json`
- `scripts/migration/output/fw_policy_scope_tiebreak_postwave_wave6_likely_movers_20260224_203419.md`
- `scripts/migration/output/fw_policy_scope_tiebreak_postwave_wave6_likely_movers_20260224_203419.csv`
- `scripts/migration/output/fw_fishtalk_culprits_wave6_top20_20260224_203439.csv`
- `scripts/migration/output/fw_fishtalk_culprits_wave6_top20_20260224_203439.md`
- `scripts/migration/output/fw_b_class_targeted_replay_wave7_seedinit_guard_20260224_204952.json`
- `scripts/migration/output/fw_b_class_targeted_replay_wave7_seedinit_guard_20260224_204952.md`
- `scripts/migration/output/fw_policy_scope_tiebreak_postwave_wave7_seedinit_guard_20260224_205050.json`
- `scripts/migration/output/fw_policy_scope_tiebreak_postwave_wave7_seedinit_guard_20260224_205050.md`
- `scripts/migration/output/fw_policy_scope_tiebreak_postwave_wave7_seedinit_guard_20260224_205050.csv`
- `scripts/migration/output/fw_fishtalk_culprits_wave7_top20_20260224_205107.csv`
- `scripts/migration/output/fw_fishtalk_culprits_wave7_top20_20260224_205107.md`

## Gate decision
**FW not yet ready** for marine continuation.

Rationale:
- Breakthrough reduction achieved, but `B=303` remains non-trivial.
- Safety guardrails are preserved (`A=0`, `C=4` unchanged).

## Next-step recommendation
1. Run next focused replay on the new top cluster:
   - `93`, `140`, `99`, `119`, `120`
2. Recompute full board immediately after that wave.
3. Keep FishTalk swimlane checks focused on any family that still shows `0` delta after one replay with this guard.
