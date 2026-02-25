# HANDOFF 2026-02-24: FW B-wave8 next5 execution + full board compute

## Session objective
Execute the next focused FW class-B reduction wave on the current top residual cluster, then recompute the full FW board.

## Cohorts replayed in this wave
- `NH FEB 25` (batch id `93`)
- `Bakkafrost feb 2024` (batch id `140`)
- `AG FEB 24` (batch id `99`)
- `Stofnfiskur Aug 23` (batch id `119`)
- `Stofnfiskur Des 23` (batch id `120`)

All five replayed successfully (`returncode=0`).

## Focused wave result (5 cohorts only)
Source: `scripts/migration/output/fw_b_class_targeted_replay_wave8_next5_20260224_212753.json`

- Before: `65` mismatches (`B=65`, `C=0`)
- After: `18` mismatches (`B=18`, `C=0`)
- Delta: `-47`

Per-cohort deltas:
- `93 NH FEB 25`: `15 -> 10` (`-5`)
- `140 Bakkafrost feb 2024`: `14 -> 8` (`-6`)
- `99 AG FEB 24`: `12 -> 0` (`-12`)
- `119 Stofnfiskur Aug 23`: `12 -> 0` (`-12`)
- `120 Stofnfiskur Des 23`: `12 -> 0` (`-12`)

## Full FW board after wave8
Source: `scripts/migration/output/fw_policy_scope_tiebreak_postwave_wave8_next5_20260224_212914.json`

- Totals:
  - `mismatches=260`
  - `A=0, B=256, C=4, D=0`
- Delta vs prior board (`fw_policy_scope_tiebreak_postwave_wave7_seedinit_guard_20260224_205050.json`):
  - `307 -> 260` (`-47`)
  - `B: 303 -> 256` (`-47`)
  - `A` unchanged at `0`, `C` unchanged at `4`

## Ranked residual board (post-wave8, top 10)
Source: `scripts/migration/output/fw_policy_scope_tiebreak_postwave_wave8_next5_20260224_212914.json`

1. `Stofnfiskur Des 24` (`12`)
2. `Stofnfiskur Juni 24` (`12`)
3. `Stofnfiskur sept 24` (`12`)
4. `NH FEB 25` (`10`)
5. `Stofnfiskur Mars 24` (`10`)
6. `Stofnfiskur Okt 25` (`9`)
7. `Bakkafrost feb 2024` (`8`)
8. `Bakkafrost S-21 aug23` (`7`)
9. `Bakkafrost S-21 jan 25` (`7`)
10. `Bakkafrost S-21 sep24` (`7`)

## New artifacts from this wave
- `scripts/migration/output/fw_b_class_targeted_replay_wave8_next5_20260224_212753.json`
- `scripts/migration/output/fw_b_class_targeted_replay_wave8_next5_20260224_212753.md`
- `scripts/migration/output/fw_policy_scope_tiebreak_postwave_wave8_next5_20260224_212914.json`
- `scripts/migration/output/fw_policy_scope_tiebreak_postwave_wave8_next5_20260224_212914.md`
- `scripts/migration/output/fw_policy_scope_tiebreak_postwave_wave8_next5_20260224_212914.csv`

## Code changes in this wave
- No new deterministic logic change introduced in wave8.
- This wave is replay + evaluation on top of the seed/init exact-start zero guard introduced in wave7.

## Gate decision
**FW not yet ready** for marine continuation.

Rationale:
- FW residuals reduced further, but `B=256` remains above readiness threshold.
- Guardrails remain intact (`A=0`, `C=4`).

## Next-step recommendation
Run the next focused cluster:
- `121`, `122`, `125`, `123`, `124`

Then recompute full board immediately and continue promoting only proven deterministic reductions.
