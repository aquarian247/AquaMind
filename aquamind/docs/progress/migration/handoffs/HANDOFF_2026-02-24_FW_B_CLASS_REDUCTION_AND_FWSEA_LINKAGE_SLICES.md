# HANDOFF 2026-02-24: FW B-class reduction + FWSEA linkage slices with transport quality

## Session objective
Execute the two required tracks with evidence-first decisions:
1) reduce dominant FW class-B residuals with minimal deterministic fixes and hard FishTalk evidence, and
2) continue FW->Sea deterministic linkage validation with confidence slices and transport-field quality checks.

## Outcome status
- Track A (FW stabilization): completed with a single focused logic refinement preserving prior wins.
- Track B (FW->Sea linkage validation): completed with scoring extractor extension and fresh run artifacts.
- Gate decision: **FW not yet ready** for marine continuation.

## Hard-constraint checks
- Class-A preserved at `0` (no regression).
- Exact-start tie-break behavior preserved (`Class C` remains `4`, no expansion).
- No schema changes made.
- Run outcomes recorded in output artifacts + this handoff.
- Marine continuation remains blocked pending FW readiness.

## Code/doc files changed in this session
- `scripts/migration/tools/pilot_migrate_component.py`
  - Added exact-time status retrieval path (`get_status_snapshot_exact_time`) and used it for completed-population start-time authority.
  - Enforced authoritative exact-start zero handling for seed/initial-window members and prevented later known-removal re-inflation in that case.
- `scripts/migration/tools/fwsea_sales_linkage_scoring_extract.py`
  - Extended output summary with deterministic evidence slices (`C/R/T/S`) and transport-field quality metrics.
  - Added transport UUID-likeness checks for trip/carrier/transporter fields.
- `aquamind/docs/progress/migration/handoffs/HANDOFF_2026-02-24_FW_B_CLASS_REDUCTION_AND_FWSEA_LINKAGE_SLICES.md` (new)

## Track A: FW class-B reduction (baseline -> targeted -> full board)

### Baseline reproduction (pre-fix)
Artifact: `/Users/aquarian247/Projects/AquaMind/scripts/migration/output/fw_policy_scope_tiebreak_reproduce_20260224_145312.json`

- Totals:
  - `mismatches=1741`
  - `A=0, B=1737, C=4, D=0`
- Dominant rationale:
  - `component_initial_window_expected_zero=1635`
  - `component_seed_expected_zero=74`

### Targeted replay wave (refined rule)
Artifact: `/Users/aquarian247/Projects/AquaMind/scripts/migration/output/fw_b_class_targeted_replay_wave_refined_20260224_153306.json`

- Scope: 9 representative seed/init/fanout-heavy batches.
- Aggregate delta:
  - before `466` mismatches -> after `55` mismatches
  - `delta=-411` (all in class-B, expected-zero side).

### Full FW board replay (post-wave)
Artifact: `/Users/aquarian247/Projects/AquaMind/scripts/migration/output/fw_policy_scope_tiebreak_postwave_refined_20260224_153444.json`

- Totals:
  - `mismatches=1222` (`-519` vs baseline)
  - `A=0, B=1218, C=4, D=0`
- Residual rationale counts:
  - `component_initial_window_expected_zero=1126`
  - `component_seed_expected_zero=64`
  - `fanout_expected_zero_bucket_size_10=10`
  - `fanout_expected_zero_bucket_size_8=8`
  - `fanout_expected_zero_bucket_size_2=6`
  - `fanout_expected_zero_bucket_size_4=4`
  - `inactive_departure_matches_latest_nonzero_status=4`

## Ranked residual board (post-wave, top 10 by mismatch count)
Source: `/Users/aquarian247/Projects/AquaMind/scripts/migration/output/fw_policy_scope_tiebreak_postwave_refined_20260224_153444.json`

1. `SF DEC 24` (`batch_id=100`): `66`
2. `SF NOV 23 [17-2023]` (`batch_id=97`): `54`
3. `SF AUG 24 [4-2024]` (`batch_id=113`): `51`
4. `SF AUG 24` (`batch_id=96`): `50`
5. `SF JUN 25` (`batch_id=103`): `50`
6. `SF APR 25` (`batch_id=112`): `49`
7. `SF MAY 24 [3-2024]` (`batch_id=114`): `49`
8. `NH MAY 24` (`batch_id=94`): `48`
9. `SF NOV 24` (`batch_id=98`): `45`
10. `Benchmark Gen Septembur 2025` (`batch_id=159`): `39`

## Track B: FW->Sea deterministic linkage validation (confidence slices + transport quality)

### Extractor extension
- Added confidence-slice aggregation over deterministic evidence tuple:
  - `C` = customer present
  - `R` = ring present
  - `T` = trip present
  - `S` = status sales count present (>0 at exact operation time)
- Added transport-field quality checks:
  - `TransportXml` presence
  - parsed transport tags (`TripID`, `CompartmentID`, `CompartmentNr`, `CarrierID`, `TransporterID`)
  - UUID-like validation for `TripID` / `CarrierID` / `TransporterID`.

### Repro command
```bash
python scripts/migration/tools/fwsea_sales_linkage_scoring_extract.py \
  --sql-profile fishtalk_readonly \
  --since "2023-01-01" \
  --only-fw-sources
```

### Run summary (extended)
Source: `/Users/aquarian247/Projects/AquaMind/scripts/migration/output/fwsea_sales_linkage_scoring_20260224_153550.json`

- Core totals:
  - `row_count=1470`
  - `distinct_sales_operations=1006`
  - `rows_with_customer=1470`
  - `rows_with_ring=945`
  - `rows_with_trip=1006`
  - `rows_with_status_sales_count=1470`
- Score bands:
  - `strong=1095`, `medium=140`, `weak=235`, `sparse=0`
- Confidence slices (`C/R/T/S`):
  - `C1_R1_T1_S1=839`
  - `C1_R0_T0_S1=358`
  - `C1_R0_T1_S1=167`
  - `C1_R1_T0_S1=106`
- Transport quality:
  - `rows_with_transport_xml=1006`
  - `rows_with_any_transport_field=1006`
  - `rows_with_trip_id=1006` and `rows_with_trip_uuid_like=1006`
  - `rows_with_compartment_id=0`
  - `rows_with_compartment_nr=0`
  - `rows_with_carrier_id=0` and `rows_with_carrier_uuid_like=0`
  - `rows_with_transporter_id=0` and `rows_with_transporter_uuid_like=0`

### Proven vs unproven FW->Sea deterministic signals (current backup)
- Proven:
  - customer evidence (`220`) is consistently populated.
  - status sales count at exact action time is consistently populated and non-zero.
  - trip evidence is populated and UUID-like where present (`1006` rows).
- Partially proven:
  - ring evidence present in a majority subset (`945/1470`), but not universal.
- Not proven in this dataset:
  - `CarrierID`, `TransporterID`, `CompartmentID`, `CompartmentNr` (all absent in this run).

## Exact artifact paths (new in this session)

### FW class-B evidence + replays
- `/Users/aquarian247/Projects/AquaMind/scripts/migration/output/fw_policy_scope_tiebreak_reproduce_20260224_145312.json`
- `/Users/aquarian247/Projects/AquaMind/scripts/migration/output/fw_policy_scope_tiebreak_reproduce_20260224_145312.md`
- `/Users/aquarian247/Projects/AquaMind/scripts/migration/output/fw_policy_scope_tiebreak_reproduce_mismatches_20260224_145312.csv`
- `/Users/aquarian247/Projects/AquaMind/scripts/migration/output/fw_b_class_focus_cohort_set_20260224_145641.csv`
- `/Users/aquarian247/Projects/AquaMind/scripts/migration/output/fw_b_class_pattern_evidence_20260224_145641.csv`
- `/Users/aquarian247/Projects/AquaMind/scripts/migration/output/fw_b_class_pattern_evidence_20260224_145641.md`
- `/Users/aquarian247/Projects/AquaMind/scripts/migration/output/fw_b_class_targeted_replay_wave_refined_20260224_153306.json`
- `/Users/aquarian247/Projects/AquaMind/scripts/migration/output/fw_b_class_targeted_replay_wave_refined_20260224_153306.md`
- `/Users/aquarian247/Projects/AquaMind/scripts/migration/output/fw_policy_scope_tiebreak_postwave_refined_20260224_153444.json`
- `/Users/aquarian247/Projects/AquaMind/scripts/migration/output/fw_policy_scope_tiebreak_postwave_refined_20260224_153444.md`
- `/Users/aquarian247/Projects/AquaMind/scripts/migration/output/fw_policy_scope_tiebreak_postwave_refined_mismatches_20260224_153444.csv`

### FW->Sea scoring (extended slices + transport quality)
- `/Users/aquarian247/Projects/AquaMind/scripts/migration/output/fwsea_sales_linkage_scoring_20260224_153550.csv`
- `/Users/aquarian247/Projects/AquaMind/scripts/migration/output/fwsea_sales_linkage_scoring_20260224_153550.json`
- `/Users/aquarian247/Projects/AquaMind/scripts/migration/output/fwsea_sales_linkage_scoring_20260224_153550.md`

## Go / No-Go decision
**FW not yet ready** for marine continuation.

Rationale:
- Although this wave removed `519` FW mismatches while preserving `A=0` and stable tie-break behavior, class-B residual volume remains high (`B=1218`), dominated by `component_initial_window_expected_zero`.
- FW->Sea evidence is materially improved and deterministic, but transport semantics are still limited to trip-level IDs in this backup; carrier/transporter/compartment-level fields are not yet available to support stricter linkage confidence.

## Next-step recommendation (priority order)
1. Run another focused B-wave on top post-wave residual leaders (`SF DEC 24`, `SF NOV 23`, `SF AUG 24`, `SF JUN 25`) using the same exact-start-zero authority pattern and row-level FT proof before each rule.
2. For FW->Sea acceptance, promote only the proven deterministic tuple in this backup:
   - source stage class FW + customer + exact-time status sales count + optional ring/trip enrichment.
3. Keep marine continuation blocked until FW class-B residuals reach an agreed readiness threshold and class-C does not expand.
