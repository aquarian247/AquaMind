# Faroe FW 7-Station Coverage Scoreboard (2026-02-17)

- Backup cutoff: `2026-01-22`
- Window start (`<30 months`): `2023-07-22`
- Scope filter: ProdStage in `FreshWater|Hatchery|Smolt`, `InputCount > 0`

| Station | In scope | Migrated+semantic PASS | Missing |
| --- | ---: | ---: | ---: |
| `S03` | 10 | 10 | 0 |
| `S04` | 6 | 6 | 0 |
| `S08` | 6 | 6 | 0 |
| `S10` | 1 | 0 | 1 |
| `S16` | 11 | 11 | 0 |
| `S21` | 10 | 10 | 0 |
| `S24` | 9 | 9 | 0 |

Raw totals: `52/53` migrated+semantic PASS.
Operational totals (excluding approved admin placeholders): `52/52` migrated+semantic PASS (`status=PASS`).

## Admin-data exclusions

- `S10`: `Support Finance|999|2023` -> `admin_placeholder` (excluded_from_operational_fw_closure_denominator; basis: FT Production Analyser review + operator confirmation; date: 2026-02-18)

## Missing batches by station (raw view)

- `S03`: none
- `S04`: none
- `S08`: none
- `S10` (1): `Support Finance|999|2023`
- `S16`: none
- `S21`: none
- `S24`: none

## Notes

- Migration success criterion: migration+semantic pass observed in analysis report JSON artifacts.
- S16/S03/S08/S04 completed; S21 fully closed via remaining-cohort retry.
- S10 batch `Support Finance|999|2023` classified as admin placeholder and excluded from operational FW closure denominator on 2026-02-18.

## Artifacts

- JSON: `/Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/migration/analysis_reports/2026-02-17/Faroe_fw_7station_coverage_scoreboard_2026-02-17.json`
