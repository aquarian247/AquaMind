# HANDOFF 2026-02-24: FWSEA directional parity validation + top-4 B-wave2 replay

## Session objective
Execute the user-requested directional FW->Sea validation ("fish out of station container vs fish into destination ring") and proceed with the next focused B-wave on top FW residual cohorts.

## Outcome status
- Directional FW->Sea count parity check implemented and run.
- Top-4 FW class-B residual cohorts replayed with refined exact-start logic and reassessed.
- Full FW board re-evaluated after the focused wave.
- Gate decision remains: **FW not yet ready** for marine continuation.

## What changed (code/docs)
- Added: `scripts/migration/tools/fwsea_sales_directional_parity_extract.py`
  - Deterministic operation-pair parity extraction:
    - sales out count = sales side (`OperationType=7`, `ActionType=7`, `ParameterID=10`, absolute delta)
    - ring/input in count = paired input side (`OperationType=5`, `ActionType=4`, `ParameterID=10`, absolute delta)
    - parity banding: exact / within tolerance / outside tolerance / missing-side.
- Updated: `scripts/migration/tools/README.md`
  - Added active-tool entry for `fwsea_sales_directional_parity_extract.py`.
- Added: `aquamind/docs/progress/migration/handoffs/HANDOFF_2026-02-24_FWSEA_DIRECTIONAL_PARITY_AND_TOP4_B_WAVE2.md`

## Track B update: directional FW->Sea parity evidence

### Repro command
```bash
python scripts/migration/tools/fwsea_sales_directional_parity_extract.py \
  --sql-profile fishtalk_readonly \
  --since "2023-01-01" \
  --only-fw-sources
```

### Key directional results
Source: `scripts/migration/output/fwsea_sales_directional_parity_20260224_154953.json`

- Operation pairs: `1006`
- Comparable pairs (both sides present): `984`
- Exact parity: `978`
- Within tolerance (`abs<=500` or `<=2%`): `6`
- Outside tolerance: `0`
- Missing input side count: `22`
- Directional match rate on comparable pairs: `1.0000`

Interpretation:
- Where both paired operations have count deltas, the directional count signal is effectively exact/near-exact.
- The meaningful residual for linkage confidence is not numeric drift; it is missing counterpart input counts (`22` pairs), which should be treated as deterministic exceptions (incomplete pairing side).

## Track A update: focused B-wave2 on top residual cohorts

### Replayed cohorts
- `SF DEC 24` (`SF DEC 24|8|2024`)
- `SF NOV 23 [17-2023]` (`SF NOV 23|17|2023`, used batch-number override and station-mismatch override)
- `SF AUG 24 [4-2024]` (`SF AUG 24|4|2024`, used batch-number override and station-mismatch override)
- `SF JUN 25` (`SF JUN 25|2|2025`)

### Focused wave result (top-4 only)
Source: `scripts/migration/output/fw_b_class_targeted_replay_wave2_top4_20260224_161502.json`

- Before: `221` mismatches (`B=221`, `C=0`)
- After: `6` mismatches (`B=6`, `C=0`)
- Delta: `-215`

Per-batch:
- `SF DEC 24`: `66 -> 0` (`-66`)
- `SF NOV 23 [17-2023]`: `54 -> 0` (`-54`)
- `SF AUG 24 [4-2024]`: `51 -> 5` (`-46`)
- `SF JUN 25`: `50 -> 1` (`-49`)

## Full FW board after wave2
Source: `scripts/migration/output/fw_policy_scope_tiebreak_postwave_wave2_top4_20260224_161631.json`

- Totals:
  - `mismatches=1007`
  - `A=0, B=1003, C=4, D=0`
- Delta vs prior post-wave refined board (`1222` mismatches):
  - `-215` total mismatches
  - `-215` class-B mismatches
  - class-A/class-C unchanged (`A=0`, `C=4`)

Residual rationale counts:
- `component_initial_window_expected_zero=915`
- `component_seed_expected_zero=60`
- `fanout_expected_zero_bucket_size_10=10`
- `fanout_expected_zero_bucket_size_8=8`
- `fanout_expected_zero_bucket_size_2=6`
- `fanout_expected_zero_bucket_size_4=4`
- `inactive_departure_matches_latest_nonzero_status=4`

## Ranked residual board (post wave2, top 10)
Source: `scripts/migration/output/fw_policy_scope_tiebreak_postwave_wave2_top4_20260224_161631.json`

1. `SF AUG 24` (`50`)
2. `SF APR 25` (`49`)
3. `SF MAY 24 [3-2024]` (`49`)
4. `NH MAY 24` (`48`)
5. `SF NOV 24` (`45`)
6. `Benchmark Gen Septembur 2025` (`39`)
7. `Benchmark Gen. Desembur 2024` (`39`)
8. `Benchmark Gen. Juni 2024` (`39`)
9. `Benchmark Gen. Juni 2025` (`39`)
10. `Benchmark Gen. Mars 2024` (`39`)

## New artifacts from this session

### Directional FW->Sea parity
- `scripts/migration/output/fwsea_sales_directional_parity_20260224_154953.csv`
- `scripts/migration/output/fwsea_sales_directional_parity_20260224_154953.json`
- `scripts/migration/output/fwsea_sales_directional_parity_20260224_154953.md`

### Focused top-4 B-wave2
- `scripts/migration/output/fw_b_class_targeted_replay_wave2_top4_20260224_161502.json`
- `scripts/migration/output/fw_b_class_targeted_replay_wave2_top4_20260224_161502.md`

### Full FW board after wave2
- `scripts/migration/output/fw_policy_scope_tiebreak_postwave_wave2_top4_20260224_161631.json`
- `scripts/migration/output/fw_policy_scope_tiebreak_postwave_wave2_top4_20260224_161631.md`
- `scripts/migration/output/fw_policy_scope_tiebreak_postwave_wave2_top4_mismatches_20260224_161631.csv`

### Additional semantic evidence generated during replay
- `scripts/migration/output/sf_dec_24_semantic_after_wave2_20260224_161130.json`
- `scripts/migration/output/sf_dec_24_semantic_after_wave2_20260224_161130.md`

## Go / No-Go
**FW not yet ready** for marine continuation.

Rationale:
- This wave materially improved FW residuals (`1222 -> 1007`) while preserving class-A/class-C guardrails.
- Residual class-B remains too high (`1003`), still dominated by deterministic init-window expected-zero behavior.
- FW->Sea directional count parity is now strongly evidenced for paired operations; remaining linkage risk is mostly from missing paired input-count rows (`22`) rather than count drift.

## Next-step recommendation
1. Continue focused B-wave on next ranked cohorts (`SF AUG 24`, `SF APR 25`, `SF MAY 24 [3-2024]`, `NH MAY 24`, `SF NOV 24`) using the same exact-start-zero authority pattern.
2. For FW->Sea acceptance logic, add directional parity as a deterministic gate:
   - pass when `CountParityBand in {exact, within_tolerance}`
   - treat `missing_input_in` as explicit exception class requiring separate evidence review.
3. Keep marine continuation blocked until FW class-B residuals are reduced to readiness threshold with `A=0` and no class-C expansion.
