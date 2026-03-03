# HANDOFF 2026-02-26 - FW B wave21 109 bucket2-no-internal qualifier + row-recheck

## Scope
- Execute one new deterministic candidate from FT-confirmed `109` semantics:
  - valid multi-day delayed input start (`FT08/FT09`, `2023-08-04`) with no InternalDelivery linkage.
- Keep prior wave guards intact:
  - delayed-input bucket-8 base
  - delayed-input egg-token bucket-4 extension (`117`)
  - station-split InternalDelivery qualifier (`139/128`).

## Code change
- Updated:
  - `scripts/migration/tools/pilot_migrate_component.py`
- Added narrow delayed-input qualifier for no-internal-link bucket-2 starts:
  - exact-start status zero
  - first non-zero status within 24h
  - creation-window seed-stage member
  - delayed-input start cluster size `>=2` and below existing threshold
  - start-time input count `>0`, no delivery/source link
  - no InternalDelivery link at exact start
  - supplier continuity with component start
  - no near-start SubTransfer touch.

## Validation sequence
### 1) Single-batch first (`109`)
- Replay command run succeeded (exit `0`).
- Validation artifacts:
  - `scripts/migration/output/fw_b109_bucket2_no_internal_validation_migrdb_20260226_120635.json`
  - `scripts/migration/output/fw_b109_bucket2_no_internal_validation_migrdb_20260226_120635.md`
- Result:
  - `109`: `2 -> 0` (`-2`)

### 2) Targeted replay (`117, 139, 109, 128, 90`)
- Replay artifacts:
  - `scripts/migration/output/fw_b_class_targeted_replay_wave21_bucket2_no_internal_next5_20260226_115327.json`
  - `scripts/migration/output/fw_b_class_targeted_replay_wave21_bucket2_no_internal_next5_20260226_115327.md`
- Execution status:
  - all five replays exit `0`.

### 3) Fixed-source row-recheck
- Source board:
  - `scripts/migration/output/fw_policy_scope_tiebreak_postwave_wave10_next5_20260225_090255.json`
- Row-recheck artifacts:
  - `scripts/migration/output/fw_b_class_row_recheck_wave21_next5_bucket2_no_internal_override_migrdb_20260226_120635.json`
  - `scripts/migration/output/fw_b_class_row_recheck_wave21_next5_bucket2_no_internal_override_migrdb_20260226_120635.md`
  - `scripts/migration/output/fw_b_class_row_recheck_wave21_next5_bucket2_no_internal_override_migrdb_20260226_120635.csv`

## Results
- Totals:
  - `before_mismatch_rows=36`
  - `after_mismatch_rows=17`
  - `delta=-19`
- Rule-match rows:
  - total `19`
  - `delayed_input_bucket8_base=8`
  - `delayed_input_egg_bucket4_extension=4`
  - `station_split_internal_delivery_input_branch=5`
  - `delayed_input_bucket2_no_internal_link=2`
- Taxonomy:
  - `A=0, B=14, C=3, D=0`

## Targeted next5 delta
- Delta artifacts:
  - `scripts/migration/output/fw_b_class_targeted_delta_wave21_next5_20260226_120635.json`
  - `scripts/migration/output/fw_b_class_targeted_delta_wave21_next5_20260226_120635.md`
- Cohort total:
  - `12 -> 2` (`-10`)
- Per batch:
  - `117`: `4 -> 0` (`-4`)
  - `139`: `2 -> 0` (`-2`)
  - `128`: `2 -> 0` (`-2`)
  - `109`: `2 -> 0` (`-2`)
  - `90`: `2 -> 2` (`0`)

## Residual ranking (post-wave21)
- Artifacts:
  - `scripts/migration/output/fw_fishtalk_culprits_wave21_top20_20260226_120635.csv`
  - `scripts/migration/output/fw_fishtalk_culprits_wave21_top20_20260226_120635.md`
- Top residuals:
  1. `90` 24Q1 LHS ex-LC (`2`)
  2. `104` SF MAR 25 (`2`)
  3. `129` YC 23 (`2`)
  4. `118` Gjógv/Fiskaaling mars 2023 (`1`)
  5. `103` SF JUN 25 (`1`)

## Notes
- `90` remains unchanged and consistent with FT interpretation of external smolt purchase semantics.
- A parity recheck shows one existing station-split-qualified row in `118` (class `C`) is no longer mismatched under current rule stack.

## Files changed in this wave
- `scripts/migration/tools/pilot_migrate_component.py`
- `aquamind/docs/progress/migration/handoffs/HANDOFF_2026-02-26_FW_B_WAVE21_109_BUCKET2_NO_INTERNAL_AND_ROWRECHECK.md`

## Go / No-go
- Decision: **FW not yet ready** for marine continuation.
- Rationale:
  - `A=0` remains protected and `B/C` improved materially.
  - Residuals remain (`B=14`, `C=3`), with `90` still unresolved and requiring explicit policy treatment.
