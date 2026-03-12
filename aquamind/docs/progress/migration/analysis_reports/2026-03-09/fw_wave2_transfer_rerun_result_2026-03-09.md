# FW Wave 2 Transfer Rerun Result

Date: 2026-03-09

## Scope

- Trigger condition met:
  - FW canaries `1344`, `1348`, `1349`, and `1352` all pass after replay cleanup and bridge-aware lineage validation fixes.
- Execution mode:
  - transfer-only reruns via `pilot_migrate_component_transfers.py`
  - `--workflow-grouping stage-bucket`
  - `--transfer-edge-scope source-in-scope`
  - `--skip-synthetic-stage-transitions`
- Scope file:
  - `scripts/migration/output/fw_wave2_transfer_scope_2026-03-09.csv`

## Manual-Reconstruction Exceptions Not Rerun

- `24Q1 LHS ex-LC|13|2023`
- `Stofnfiskur feb 2025|1|2025`
- `Benchmark Gen. Mars 2025|1|2025`
- `Gjógv/Fiskaaling mars 2023|5|2023`

## Result

- Attempted mapped FW reruns: `15`
- Failures: `0`

## Successful Wave 2 Reruns

- `Stofnfiskur Aug 2024|4|2024`
- `Bakkafrost S-21 jan 25|1|2025`
- `Bakkafrost Okt 2023|4|2023`
- `Stofnfiskur Nov 2024|5|2024`
- `Benchmark Gen. Septembur 2024|3|2024`
- `Bakkafrost Juli 2023|3|2023`
- `Stofnfiskur Juni 24|2|2024`
- `Stofnfiskur Aug 23|4|2023`
- `Stofnfiskur mai 2024|3|2024`
- `StofnFiskur S-21 apr 25|2|2025`
- `Stofnfiskur mai 2025|3|2025`
- `AquaGen juni 25|2|2025`
- `StofnFiskur S-21 juli25|3|2025`
- `Stofnfiskur August 25|4|2025`
- `Bakkafrost S-21 okt 25|5|2025`

## Notes

- All reruns completed with prune-and-rebuild transfer sync semantics, so stale FishTalk transfer workflows/actions from earlier internal-only replays were removed before rebuilding current source-in-scope edges.
- Broad FW->Sea continuation remains paused in this session.
