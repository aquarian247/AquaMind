# FW21 Allow-Station-Mismatch Recovery Summary (2026-02-17)

- Station guard anchor: `FW21 Couldoran`
- Profile: `fw_default`
- Backup horizon: `2026-01-22`
- Skip environmental: `true`
- Allow station mismatch: `true`
- Cohorts attempted: `4`
- Migration successes: `4/4`
- Semantic gate passes: `4/4`

| Batch key | Migration | Semantic gates | Scripts | InputProjects sites | Member sites |
| --- | --- | --- | --- | --- | --- |
| `SF AUG 23\|15\|2023` | PASS | PASS | 12/12 | ['FW21 Couldoran'] | ['FW21 Couldoran', 'FW22 Applecross'] |
| `SF NOV 23\|17\|2023` | PASS | PASS | 12/12 | ['FW21 Couldoran'] | ['FW21 Couldoran', 'FW22 Applecross'] |
| `NH FEB 24\|1\|2024` | PASS | PASS | 12/12 | ['FW21 Couldoran'] | ['BRS3 Geocrab', 'FW21 Couldoran'] |
| `SF AUG 24\|3\|2024` | PASS | PASS | 12/12 | ['FW21 Couldoran'] | ['FW13 Geocrab', 'FW21 Couldoran'] |

## Notes

- SF NOV 23|17|2023 required targeted rerun with --batch-number 'SF NOV 23 17' to avoid batch_number collision with existing 'SF NOV 23' record from another component.

## Artifacts

- JSON summary: `aquamind/docs/progress/migration/analysis_reports/2026-02-17/FW21_allow_station_mismatch_recovery_summary_2026-02-17.json`
- Per-cohort semantic outputs: `aquamind/docs/progress/migration/analysis_reports/2026-02-17`

