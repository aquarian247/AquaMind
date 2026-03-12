# Stofnfiskur Mars 2023 Targeted Apply Result

Date: `2026-03-06`

## Outcome

- Result: `applied`
- Migration DB batch id: `1361`
- Batch number: `Stofnfiskur Mars 2023`
- Component key: `MANUAL_FWSEA_STOFNFISKUR_MARS_2023_1_2023`

## Applied Shape

- Custom component report created from:
  - full FW members for `Stofnfiskur Mars 2023|1|2023`
  - exact destination populations from the operation ledger
  - short-lived sale-side source populations recovered from raw FishTalk extracts
- Component migration applied with `--scoped-assignment-maps-only`
- Exact transfer replay applied from persisted `InternalDelivery`-anchored event rows

## Result Counts

- Assignments: `122`
- Component-scoped assignment maps: `122`
- Legacy global `Populations` assignment maps to new batch: `0`
- Creation workflows: `1`
- Creation actions: `39`
- Transfer workflows: `40`
- Transfer actions: `43`
- Total transferred fish: `2,000,921`

## Transfer Surface Checks

- `A06 Argir / 06`: `205,660` fish across `7` actions
- `A18 Hov / 08`: `196,219` fish across `3` actions
- `A25 Gøtuvík / S09`: `125,956` fish across `3` actions
- `A25 Gøtuvík / S11`: `69,376` fish across `3` actions
- `A47 Gøtuvík / N05`: `194,549` fish across `5` actions

## Important Caveat

This run is intentionally isolated with component-scoped assignment maps. Existing legacy global `Populations` maps in `aquamind_db_migr_dev` still point the same sea populations at earlier marine-side batches such as `Bakkafrost feb 2024 - Vár 2024` and `Bakkafrost Okt 2023 - Summar 2024`. The targeted `Stofnfiskur Mars 2023` batch therefore coexists with those earlier migrated batches in the dev DB instead of replacing them.

## Artifacts

- Custom case pack:
  - `scripts/migration/output/manual_fwsea_cases/stofnfiskur_mars_2023/population_members.csv`
  - `scripts/migration/output/manual_fwsea_cases/stofnfiskur_mars_2023/exact_transfer_events.csv`
  - `scripts/migration/output/manual_fwsea_cases/stofnfiskur_mars_2023/exact_transfer_events.json`
  - `scripts/migration/output/manual_fwsea_cases/stofnfiskur_mars_2023/summary.json`
- Source evidence:
  - `aquamind/docs/progress/migration/analysis_reports/2026-03-06/stofnfiskur_mars_2023_manual_ft_swimlane_evidence_2026-03-06.json`
  - `aquamind/docs/progress/migration/analysis_reports/2026-03-06/stofnfiskur_mars_2023_operation_ledger_2026-03-06.csv`
  - `aquamind/docs/progress/migration/analysis_reports/2026-03-06/stofnfiskur_mars_2023_targeted_migration_spec_2026-03-06.json`
