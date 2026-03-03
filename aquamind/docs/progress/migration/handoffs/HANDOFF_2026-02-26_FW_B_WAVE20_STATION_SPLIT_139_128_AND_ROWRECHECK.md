# HANDOFF 2026-02-26 - FW B wave20 station-split qualifier (139/128) + row-recheck

## Scope
- Continue FW stabilization after wave19 with a narrow deterministic extension for validated FW->FW station-split input branches.
- Keep constraints intact:
  - preserve `A=0`
  - no class-`C` expansion
  - no schema changes
  - evidence-first and minimal code churn.

## Deterministic change implemented
- File changed:
  - `scripts/migration/tools/pilot_migrate_component.py`
- Added a narrow exact-start delayed non-zero authority path for qualified station-split InternalDelivery starts:
  - exact-start status is zero
  - first non-zero status appears within 24h
  - destination input row exists at exact start with `InputCount > 0`
  - no delivery/source link on input row
  - no near-start SubTransfer touch
  - paired InternalDelivery sales/input operations at row start
  - source populations are outside the component and source site differs from destination site.
- Existing guards retained:
  - exact-start tie-break and zero guards
  - delayed-input base bucket-8
  - egg-token bucket-4 extension for batch 117.

## Validation and replay
- Single-batch validation run (`139`) executed successfully (exit `0`).
- Targeted replay run (`117, 139, 109, 128, 90`) executed successfully (all exit `0`).
- Replay artifact:
  - `scripts/migration/output/fw_b_class_targeted_replay_wave20_station_split_next5_20260226_111221.json`
  - `scripts/migration/output/fw_b_class_targeted_replay_wave20_station_split_next5_20260226_111221.md`

## Post-wave20 row-recheck (same fixed source board)
- Source board retained:
  - `scripts/migration/output/fw_policy_scope_tiebreak_postwave_wave10_next5_20260225_090255.json`
- Row-recheck artifacts:
  - `scripts/migration/output/fw_b_class_row_recheck_wave20_next5_station_split_input_override_migrdb_20260226_112057.json`
  - `scripts/migration/output/fw_b_class_row_recheck_wave20_next5_station_split_input_override_migrdb_20260226_112057.md`
  - `scripts/migration/output/fw_b_class_row_recheck_wave20_next5_station_split_input_override_migrdb_20260226_112057.csv`
- Totals:
  - `before_mismatch_rows=36`
  - `after_mismatch_rows=20`
  - `delta=-16`
  - `rule_match_rows=16`
  - rule breakdown:
    - `delayed_input_bucket8_base=8`
    - `delayed_input_egg_bucket4_extension=4`
    - `station_split_internal_delivery_input_branch=4`
- Taxonomy:
  - `A=0, B=16, C=4, D=0`

## Targeted next5 delta (wave20)
- Delta artifacts:
  - `scripts/migration/output/fw_b_class_targeted_delta_wave20_next5_20260226_112057.json`
  - `scripts/migration/output/fw_b_class_targeted_delta_wave20_next5_20260226_112057.md`
- Cohort total:
  - `12 -> 4` (`-8`)
- Per batch:
  - `117`: `4 -> 0` (`-4`)
  - `139`: `2 -> 0` (`-2`)
  - `128`: `2 -> 0` (`-2`)
  - `109`: `2 -> 2` (`0`)
  - `90`: `2 -> 2` (`0`)

## Additional artifacts
- 139 single-batch validation snapshot:
  - `scripts/migration/output/fw_b139_station_split_input_validation_migrdb_20260226_112057.json`
  - `scripts/migration/output/fw_b139_station_split_input_validation_migrdb_20260226_112057.md`
- Updated residual ranking:
  - `scripts/migration/output/fw_fishtalk_culprits_wave20_top20_20260226_112057.csv`
  - `scripts/migration/output/fw_fishtalk_culprits_wave20_top20_20260226_112057.md`

## Ranked residual board (post-wave20, top)
1. `109` 24Q1 LHS (`2`)
2. `90` 24Q1 LHS ex-LC (`2`, class `C`)
3. `104` SF MAR 25 (`2`)
4. `118` Gjógv/Fiskaaling mars 2023 (`2`)
5. `129` YC 23 (`2`)

## Go / No-go
- Decision: **FW not yet ready** for marine continuation.
- Rationale:
  - `A=0` preserved and `B` reduced (`20 -> 16`) with no `C` expansion.
  - residual `B/C` remains (`B=16`, `C=4`) and unresolved high-signal non-movers remain (`109`, `90`).

## Recommended next step
- Keep wave20 station-split qualifier locked.
- Run focused FT inspection on `109` and `90` only, then propose exactly one next deterministic candidate based on confirmed lane semantics:
  - `109`: confirm whether fanout-2 rows are true delayed-input starts or expected-zero placeholders.
  - `90`: resolve holder-of-record semantics for class-`C` inactive-departure companions.
