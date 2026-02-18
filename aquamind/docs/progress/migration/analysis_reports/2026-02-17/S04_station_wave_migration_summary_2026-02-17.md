# S04 STATION WAVE MIGRATION SUMMARY (2026-02-17)

- Station: `S04 Húsar`
- Profile: `fw_default`
- Backup horizon: `2026-01-22`
- Cohorts attempted: `6`
- Migration successes: `6/6`
- Semantic gate passes: `6/6`

| Batch key | Migration | Semantic | Notes |
| --- | --- | --- | --- |
| `23 Testfiskur\|2\|2024` | PASS | PASS | - |
| `BF 2022\|3\|2023` | PASS | PASS | - |
| `Fiskaaling sep 2022\|2\|2023` | PASS | PASS | post-fix-retry |
| `YC 23\|1\|2024` | PASS | PASS | - |
| `YC 24 Elitibólkur 1A\|1\|2025` | PASS | PASS | - |
| `YC 24 Elitibólkur 1B\|2\|2025` | PASS | PASS | - |

## Notes

- Cohort `Fiskaaling sep 2022|2|2023` rerun after creation-action idempotency fix; retry passed migration+semantic.
