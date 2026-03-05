# FW Environmental Stabilization + FW->Sea Ready Check (2026-03-05)

## Session objective

- Stabilize freshwater environmental mapping for all FW scope batches so parameter drift does not recur.
- Document run order/checklist + mapping contracts for future sessions.
- Decide whether FW is stable enough to begin FW->Sea mapping work.

## What was done

1. **Environmental mapping hardening (code)**
   - Updated `scripts/migration/tools/pilot_migrate_component_environmental.py`:
     - Metadata-first sensor mapping via FishTalk sensor catalogs remains canonical.
     - Added oxygen guardrail: oxygen `mg/L` streams with implausible maxima (`>30`) are remapped to `Oxygen Saturation` (`%`).
     - Added oxygen saturation normalization: values in `(200, 2000]` are scaled by `/10` (deterministic normalization).
     - Added per-sensor value-hint support in mapping decision path.
   - Updated `scripts/migration/tools/pilot_migrate_input_batch.py`:
     - Added `--use-sqlite` pass-through for environmental scope runs.

2. **Documentation updates**
   - `aquamind/docs/progress/migration/DATA_MAPPING_DOCUMENT.md`
     - Added canonical sensor-metadata mapping contract and oxygen normalization guardrails.
   - `aquamind/docs/progress/migration/MIGRATION_CANONICAL.md`
     - Added ordered FW scope replay checklist.
     - Added explicit execution safety note: avoid overlapping parallel environmental scope writes.

3. **Scope-wide data correction (all FW scope batches)**
   - Scope: `scripts/migration/output/fw_scope60_feed_infra_extract_descendants_20260303_131729/scope_batch_keys_for_replay.csv`
   - Resolved scope entities:
     - `60` batches
     - `644` sensors
     - `4,199,663` environmental readings
   - Performed deterministic global remap and realignment against `ExternalIdMap` (`SensorParameter`).

## Evidence artifacts

- Run summary (authoritative):
  - `scripts/migration/output/fw_scope60_environmental_global_realign_20260305_095609/fw_scope60_environmental_realign_summary.json`

## Final verification snapshot

- `remaining_parameter_mismatches`: `0`
- `oxygen_saturation_outliers_gt200_or_lt0`: `0`
- `dissolved_oxygen_outliers_gt30_or_lt0`: `0`
- `temperature_outliers_gt40_or_lt-5`: `2`
  - Both are duplicated source records for one temperature sensor (`59C`) and should be treated as source anomaly, not mapping drift.

### Batch 1347 spotlight

- Temperature:
  - range `4.73 .. 14.49`
  - window `2025-10-01 .. 2026-01-22`
- Oxygen Saturation:
  - range `0 .. 151`
  - window `2025-10-01 .. 2025-12-16`
- Dissolved Oxygen:
  - no rows (stream is represented as oxygen saturation for this context)

## Interpretation for operations

- FW environmental mapping is now **structurally stable** (no remaining parameter mismatches for scoped rows).
- Remaining odd values are now in the category of **source semantics/quality** (sensor drift, unit labels, or correction policy), not ETL bucket misclassification.
- AVEVA should remain the ground truth for final correction policy.

## Decision for current phase

- **Outlier policy for now:** ignore residual outlier values operationally (do not infer extra hard-coded site logic).
- **Do not over-assume normalization rules** beyond the documented deterministic guardrails pending AVEVA owner confirmation.

## Next natural high-value move

1. **GUI parity canary pass (FishTalk vs AquaMind)**
   - Pick 6-10 representative FW batches across stations.
   - Compare:
     - mortality/feed timelines
     - environmental trend shape and date coverage
     - parameter labels/units shown in Insights
   - Produce a short parity matrix with PASS/DELTA notes.

2. **AVEVA/FW-owner confirmation loop**
   - Confirm canonical unit/scaling and correction-backfill policy.
   - Feed those decisions into a finalized normalization/quality-flag policy.

## FW->Sea mapping readiness

### Recommendation

- **Yes, start FW->Sea work now at discovery/prototyping level**, while FW is stable enough to proceed.
- Keep full production linkage rollout gated until AVEVA/FW policy answers are in.

### Suggested FW->Sea phase split

1. **Phase 0 (now): deterministic candidate-link evidence model**
   - Inputs: end-of-FW tank depletion windows, sea ring fill windows, transfer/sales events when present.
   - Build candidate links with confidence scores:
     - explicit sales/transfer evidence (highest confidence)
     - temporal empty->fill proximity (same day / small-day window)
     - biomass/count plausibility and geography constraints
     - many-to-many support with split-weight logic

2. **Phase 1: canary validation**
   - Run on a small curated cohort; manually verify with domain users.

3. **Phase 2: scoped rollout**
   - Expand only after confidence and exception handling are accepted.

## Known execution caveat

- Parallel environmental writes over overlapping FW scopes caused row-lock contention during this session.
- Keep environmental scope replay single-process for deterministic ownership updates.

## Suggested next-session starter prompt

1. Read:
   - `aquamind/docs/progress/migration/MIGRATION_CANONICAL.md`
   - `aquamind/docs/progress/migration/DATA_MAPPING_DOCUMENT.md`
   - this handoff file
2. Run GUI parity canary comparison and produce a compact delta table.
3. Draft FW->Sea Phase 0 evidence scoring spec (no hard assumptions, confidence-tagged links).

