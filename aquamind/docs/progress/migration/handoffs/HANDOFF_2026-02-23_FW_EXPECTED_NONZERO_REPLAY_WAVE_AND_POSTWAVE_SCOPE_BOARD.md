# HANDOFF 2026-02-23: FW Expected-Nonzero Replay Wave + Post-Wave Scope Board

## Session objective

Clear all freshwater class `A` (`expected_nonzero`) regressions discovered in full-scope validation, then produce an updated full FW residual board with explicit A/B/C/D taxonomy.

## Outcome status

- Targeted replay wave complete: `32/32` batches replayed with `fw_default`.
- Class `A` (`expected_nonzero`) mismatches cleared in all replay targets.
- Full-scope FW post-wave validation complete and confirms class `A = 0` across all evaluated FW cohorts.
- Residual mismatches are now entirely class `B`/`C` (expected-zero initialization/fan-out and closure behavior).

## Primary evidence artifacts

- Full FW pre-wave baseline (authoritative before-state):
  - `scripts/migration/output/fw_policy_scope_baseline_20260223_152506.md`
  - `scripts/migration/output/fw_policy_scope_baseline_20260223_152506.json`
- Targeted replay wave (`32` batches that had class `A > 0`):
  - `scripts/migration/output/fw_expected_nonzero_replay_wave_20260223_161036.md`
  - `scripts/migration/output/fw_expected_nonzero_replay_wave_20260223_161036.json`
- Full FW post-wave board (authoritative after-state):
  - `scripts/migration/output/fw_policy_scope_postwave_20260223_161157.md`
  - `scripts/migration/output/fw_policy_scope_postwave_20260223_161157.json`

## Policy scoreboard summary

### Full-scope FW board (before -> after)

- Cohorts in scope: `78 -> 78`
- Evaluable non-zero rows: `8,255 -> 8,255`
- Total mismatches: `2,345 -> 1,961` (`-384`)
- Class `A` (`expected_nonzero`): `384 -> 0` (`-384`)
- Class `B` (`expected_zero` seed/init/fan-out): `1,741 -> 1,741` (`0`)
- Class `C` (false closure / holder-companion anomaly): `220 -> 220` (`0`)
- Class `D` (other): `0 -> 0`

### Replay-target-only board (`32` batches)

- Total mismatches: `1,580 -> 1,200` (`-380`)
- Class `A`: `384 -> 0` (`-384`)
- Class `B`: `1,141 -> 1,141` (`0`)
- Class `C`: `55 -> 59` (`+4`)

## Residual taxonomy (post-wave)

- Class `A` is fully cleared in the current FW scope.
- Residual class `B` is dominated by deterministic initialization windows:
  - `component_initial_window_expected_zero`: `1,635`
  - `component_seed_expected_zero`: `74`
  - fan-out signatures (`fanout_expected_zero_bucket_size_*`): `32` total
- Residual class `C` is almost entirely:
  - `inactive_departure_matches_latest_nonzero_status`: `218`
  - `inactive_holder_with_active_companion_nonzero_latest_status`: `2`

## Ranked residual cohorts (post-wave top 10)

| Rank | Batch ID | Batch | Mismatches | A | B | C | D |
| ---: | ---: | --- | ---: | ---: | ---: | ---: | ---: |
| 1 | 166 | Stofnfiskur Septembur 2023 | 85 | 0 | 39 | 46 | 0 |
| 2 | 102 | SF JUL 25 | 78 | 0 | 78 | 0 | 0 |
| 3 | 167 | Stofnfiskur desembur 2023 | 77 | 0 | 39 | 38 | 0 |
| 4 | 108 | SF SEP 25 | 76 | 0 | 76 | 0 | 0 |
| 5 | 107 | SF SEP 24 | 71 | 0 | 68 | 3 | 0 |
| 6 | 105 | SF MAY 24 | 69 | 0 | 65 | 4 | 0 |
| 7 | 104 | SF MAR 25 | 69 | 0 | 69 | 0 | 0 |
| 8 | 100 | SF DEC 24 | 68 | 0 | 66 | 2 | 0 |
| 9 | 161 | Benchmark Gen. Juni 2024 | 62 | 0 | 39 | 23 | 0 |
| 10 | 163 | Benchmark Gen. Mars 2024 | 59 | 0 | 39 | 20 | 0 |

## Owner logic / rule candidates for next wave

- **Class B owner candidate (init/fan-out policy):**
  - narrow deterministic handling for exact-start zero snapshots in component-root initialization and fan-out windows, without weakening current non-zero authority rules.
- **Class C owner candidate (closure policy):**
  - deterministic false-closure guard when an inactive row aligns to latest non-zero status timing (especially departure-date matches), with companion-holder protection where applicable.

## Recommendation / gate decision

- **FW readiness:** `FW not yet ready`.
- **Why:** class `A` is successfully cleared (`0`), but residual class `B/C` volume remains high (`1,961` total mismatches) and needs dedicated deterministic policy cleanup.
- **Marine continuation:** do **not** start marine-continuation classification yet (including the "split the 42 into at-sea active, sea-completed/harvested, and true anomalies" pass) until the next FW residual reduction/taxonomy wave is completed and re-validated.
