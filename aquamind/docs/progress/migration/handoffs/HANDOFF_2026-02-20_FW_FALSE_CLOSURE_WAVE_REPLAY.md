# HANDOFF 2026-02-20: FW False-Closure Wave Replay + Hard-Data Calibration

## Session objective

Run the controlled freshwater replay wave for cutoff-date false closures, verify whether the hard-data calibration is sustainable across batches, and document the mapping behavior in the main migration blueprint.

## Outcome status

- Controlled FW wave replay: complete.
- Major reduction in cutoff false closures: `42 -> 5` rows (net `-37`, ~`88%` reduced).
- Fully cleared batches in this wave: `9/11`.
- Residual rows remain in:
  - `Bakkafrost S-21 jan 25` (`4` rows)
  - `NH FEB 25` (`1` row)
- Mapping blueprint updated to include the hard-data closure calibration behavior.

## Breakthrough statement

The migration now aligns much better to FishTalk hard evidence at the cutoff horizon by combining:

- latest-status-aware active-holder tie-break,
- latest measured count authority for open populations,
- recency-aware stage-mismatch handling.

This combination resolves the large majority of previously observed false departures in a controlled cross-batch replay.

## Primary evidence artifacts

- Wave scoreboard (batch-by-batch before/after):
  - `scripts/migration/output/fw_cutoff_false_departure_wave_scoreboard_20260220_164050.md`
  - `scripts/migration/output/fw_cutoff_false_departure_wave_scoreboard_20260220_164050.json`
- Residual row probe with cause taxonomy:
  - `scripts/migration/output/fw_cutoff_false_departure_residual_probe_v2_20260220_171346.md`
  - `scripts/migration/output/fw_cutoff_false_departure_residual_probe_v2_20260220_171346.json`
- Restore replay (stable patch set) for touched residual batches:
  - `scripts/migration/output/fw_cutoff_targeted_residual_replay_restore_20260220_173420.md`
  - `scripts/migration/output/fw_cutoff_targeted_residual_replay_restore_20260220_173420.json`

## Residual taxonomy (current 5 rows)

From the residual probe (`v2`) and restore replay:

- `source_latest_holder_inactive_zero_count_companion`: `2` rows (`B06`, `B12` in `Bakkafrost S-21 jan 25`)
- `source_latest_holder_inactive_nonzero_companion`: `1` row (`CR06` in `NH FEB 25`)
- `historical_non_holder_zero_row`: `1` row (`B02` in `Bakkafrost S-21 jan 25`)
- `historical_non_holder_nonzero_row`: `1` row (`B02` in `Bakkafrost S-21 jan 25`)

Interpretation:

- Most residuals are now narrow companion-row edge cases rather than broad batch-level false closures.
- The two `B02` rows appear to be non-holder historical companions.
- Three rows still look like latest-holder companion anomalies at the cutoff timestamp and require a narrower follow-up rule (or detector refinement) before claiming full closure.

## Documentation updates completed

- Updated: `aquamind/docs/progress/migration/DATA_MAPPING_DOCUMENT.md`
  - Version bumped to `5.1` (`2026-02-20`)
  - Added key revision note for FW hard-data closure calibration
  - Updated section `3.2` to reflect:
    - open-population latest-count authority,
    - active-holder tie-break order,
    - recency-aware stage-mismatch guard.

## Notes on experimental follow-up

- A narrow residual-tuning experiment was tested and replayed, but it produced no net reduction in residual count and was rolled back.
- Final state documented here is from the stable patch set plus restore replay (`...restore_20260220_173420`).

## Recommended next step

Implement a dedicated residual pass for the remaining 5 rows with explicit rule labels per row (holder-companion vs historical companion), then decide whether to:

- refine migration activation/departure logic for same-timestamp companion populations, or
- refine the detector to avoid classifying expected historical companions as false closures.
