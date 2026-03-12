# Stofnfiskur Mars 2023 Apply-Ready Event Rows

Created: `2026-03-06`

This row set is the apply-ready execution surface for `Stofnfiskur Mars 2023`.

## Execution Policy

- `Create Batch`: forbidden
- synthetic sea-only creation workflow: forbidden
- marine ingress must be created by `Transfer to Sea` workflows/actions only
- workflow grouping must be `operation`
- synthetic stage transitions: disabled
- dynamic runtime workflows: disabled
- action grain: one action per sale/input event row in this file

## Summary

- rows: `43`
- total fish: `2,000,921`
- `direct_var_2024`: `32` rows, `1,611,040` fish, apply component `Vár 2024|1|2024`
- `direct_summar_2024`: `3` rows, `145,111` fish, apply component `Summar 2024|1|2024`
- `mixed_successor_summar_2024`: `8` rows, `244,770` fish, apply component `Summar 2024|1|2024`

## Notes

- `A06 Argir / 06` uses canonical container `06`; `Ring 6` is only the FishTalk delivery text.
- `D26A` and `D26B` are both kept because destination-side swimlane input actions plus mortality reconciliation support both `35,926` ingress rows as real.
- Mixed `A25 Gøtuvík` rows keep only `Summar 2024|1|2024` as the canonical apply component; `Stofnfiskur Juni 2023|2|2023` remains lineage evidence only.
- `M05` remains operationally valid but still carries the naming anomaly `N05 S24 SF JUL 24 (MAR/JUN 24)` in the population-member artifact.

## Files

- JSON: `aquamind/docs/progress/migration/analysis_reports/2026-03-06/stofnfiskur_mars_2023_apply_ready_event_rows_2026-03-06.json`
- CSV: `aquamind/docs/progress/migration/analysis_reports/2026-03-06/stofnfiskur_mars_2023_apply_ready_event_rows_2026-03-06.csv`
