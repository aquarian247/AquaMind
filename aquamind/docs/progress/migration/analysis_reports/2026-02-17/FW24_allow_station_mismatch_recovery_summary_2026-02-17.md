# FW24 ALLOW STATION MISMATCH RECOVERY SUMMARY (2026-02-17)

- Station: `FW24 KinlochMoidart`
- Profile: `fw_default`
- Backup horizon: `2026-01-22`
- Skip environmental: `true`
- Cohorts attempted: `6`
- Migration successes: `6/6`
- Semantic gate passes: `6/6`

| Batch key | Migration | Semantic | Scripts | InputProjects sites | Member sites | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| `24Q1 LHS\|1\|2024` | PASS | PASS | 12/12 | ['FW24 KinlochMoidart'] | ['FW22 Applecross', 'FW24 KinlochMoidart'] | allow-mismatch |
| `SF SEP 23\|4\|2023` | PASS | PASS | 12/12 | ['FW24 KinlochMoidart'] | ['FW22 Applecross', 'FW24 KinlochMoidart'] | allow-mismatch |
| `NH DEC 23\|5\|2023` | PASS | PASS | 12/12 | ['FW24 KinlochMoidart'] | ['FW22 Applecross', 'FW24 KinlochMoidart'] | allow-mismatch |
| `AG JAN 24\|2\|2024` | PASS | PASS | 12/12 | ['FW24 KinlochMoidart'] | ['FW22 Applecross', 'FW24 KinlochMoidart'] | allow-mismatch |
| `SF MAY 24\|3\|2024` | PASS | PASS | 12/12 | ['FW24 KinlochMoidart'] | ['FW22 Applecross', 'FW24 KinlochMoidart'] | allow-mismatch, batch-number=SF MAY 24 3 |
| `SF AUG 24\|4\|2024` | PASS | PASS | 12/12 | ['FW24 KinlochMoidart'] | ['FW22 Applecross', 'FW24 KinlochMoidart'] | allow-mismatch, batch-number=SF AUG 24 4 |

## Notes

- SF MAY 24|3|2024 rerun used --batch-number 'SF MAY 24 3' due batch-number collision.
- SF AUG 24|4|2024 rerun used --batch-number 'SF AUG 24 4' due batch-number collision.
- SF SEP 23|4|2023 semantic gate now passes after validator update: bridge-aware consolidation positive-delta rows are downgraded to incomplete-linkage fallback.

## Artifacts

- JSON summary: `/Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/migration/analysis_reports/2026-02-17/FW24_allow_station_mismatch_recovery_summary_2026-02-17.json`
- Semantic outputs directory: `/Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/migration/analysis_reports/2026-02-17`

