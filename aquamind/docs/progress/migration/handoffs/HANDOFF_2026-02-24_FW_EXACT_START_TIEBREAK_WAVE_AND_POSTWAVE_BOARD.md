# HANDOFF 2026-02-24: FW exact-start tie-break wave + post-wave board

## Session objective
Implement and validate the deterministic exact-start duplicate-timestamp tie-break discovered in FishTalk evidence, then re-run targeted/full FW validation to quantify residual impact and readiness.

## Outcome status
- Deterministic tie-break implemented in migration snapshot selection paths (CSV + SQL).
- Targeted replay wave completed for all 32 prior class-C cohorts under tie-break policy.
- Full FW post-wave board completed with tie-break policy.
- Class `A` (`expected_nonzero`) remains `0`.
- Class `C` reduced from `220` to `4`; residual board is now overwhelmingly class `B`.

## Primary evidence artifacts
- Prior authoritative board (pre tie-break):
  - `scripts/migration/output/fw_policy_scope_postwave_20260223_161157.json`
  - `scripts/migration/output/fw_policy_scope_postwave_20260223_161157.md`
- Targeted replay wave for prior C-heavy cohorts (32 batches):
  - `scripts/migration/output/fw_class_c_tiebreak_replay_wave_20260224_130603.json`
  - `scripts/migration/output/fw_class_c_tiebreak_replay_wave_20260224_130603.md`
- Full FW post-wave board with tie-break policy:
  - `scripts/migration/output/fw_policy_scope_tiebreak_postwave_20260224_130844.json`
  - `scripts/migration/output/fw_policy_scope_tiebreak_postwave_20260224_130844.md`

## Policy scoreboard summary
### Full FW board (pre tie-break -> tie-break post-wave)
- Cohorts in scope: `78 -> 78`
- Evaluable non-zero rows: `8,255 -> 8,255`
- Total mismatches: `1,961 -> 1,741` (`-220`)
- Class `A` (`expected_nonzero`): `0 -> 0`
- Class `B` (`expected_zero` seed/init/fan-out): `1,741 -> 1,737` (`-4`)
- Class `C` (false closure / holder-companion anomaly): `220 -> 4` (`-216`)
- Class `D`: `0 -> 0`

### Targeted C-wave board (32 replayed batches, tie-break policy)
- Replay success: `32/32` batches.
- Class `A`: `0 -> 0`
- Class `C`: `4 -> 4` (remaining C rows are stable outliers, not replay-clearable under current deterministic rules).

## Residual taxonomy after tie-break
- Class `B` is dominant (`1,737`) and is mostly deterministic init-window behavior:
  - `component_initial_window_expected_zero`: `1,635`
  - `component_seed_expected_zero`: `74`
  - fan-out buckets (`fanout_expected_zero_bucket_size_{2,4,8,10}`): `28`
- Class `C` is reduced to `4`:
  - `inactive_departure_matches_latest_nonzero_status`: `4`
  - concentrated in three batches: `90` (2), `118` (1), `129` (1)

## Ranked residual cohorts (post-wave, top 10)
| Rank | Batch ID | Batch | Mismatches | A | B | C | D |
| ---: | ---: | --- | ---: | ---: | ---: | ---: | ---: |
| 1 | 102 | SF JUL 25 | 78 | 0 | 78 | 0 | 0 |
| 2 | 108 | SF SEP 25 | 76 | 0 | 76 | 0 | 0 |
| 3 | 104 | SF MAR 25 | 69 | 0 | 69 | 0 | 0 |
| 4 | 107 | SF SEP 24 | 68 | 0 | 68 | 0 | 0 |
| 5 | 100 | SF DEC 24 | 66 | 0 | 66 | 0 | 0 |
| 6 | 105 | SF MAY 24 | 65 | 0 | 65 | 0 | 0 |
| 7 | 93 | NH FEB 25 | 56 | 0 | 56 | 0 | 0 |
| 8 | 92 | NH FEB 24 | 55 | 0 | 55 | 0 | 0 |
| 9 | 97 | SF NOV 23 [17-2023] | 54 | 0 | 54 | 0 | 0 |
| 10 | 106 | SF NOV 23 | 52 | 0 | 52 | 0 | 0 |

## Code and documentation changes in this session
- `scripts/migration/tools/etl_loader.py`
  - Added deterministic same-timestamp status tie-break helpers.
  - Applied tie-break to latest snapshot, near-time snapshot, and first non-zero-after resolution.
- `scripts/migration/tools/pilot_migrate_component.py`
  - SQL snapshot queries now include deterministic same-timestamp ordering (non-zero first, then count/biomass).
- `aquamind/docs/progress/migration/DATA_MAPPING_DOCUMENT.md`
  - Added v5.3 rule-level documentation for exact-start duplicate-timestamp tie-break and snapshot parity guard.

## FW->Sea linkage note (new candidate evidence fields)
User-observed columns for transfer/sales tracing:
- `PublicPlanStatusValues`: `SalesCount`, `SalesBiomassKg`
- `PublicStatusValues`: `SalesCount`, `SalesBiomassKg`
- `Ext_StatusValues_v2`: `SalesCount`, `SalesBiomassKg`
- `Ext_DailyStatusValues_v2`: `SalesCount`, `SalesKg`

Recommendation: keep these as candidate linkage diagnostics until semantics are confirmed with row-level transfer traces; then add a durable mapping rule if they prove authoritative for FW->Sea boundary events.

## Recommendation / gate decision
- **FW readiness:** `FW not yet ready`.
- **Why:** class `A` is locked at `0`, class `C` is reduced to `4`, but class `B` remains high (`1,737`) and is dominated by deterministic init-window policy behavior.
- **Marine continuation:** do **not** start marine-continuation classification yet.

## Next-step recommendations
1. Implement deterministic init-window policy for class `B` (`component_initial_window_expected_zero`) with strict FishTalk evidence gates.
2. Validate targeted B-heavy cohorts first, then re-run full FW board.
3. Keep exact-start tie-break locked as a regression guard in both migration logic and board policy checks.
