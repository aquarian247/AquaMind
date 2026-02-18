# HANDOFF 2026-02-17: S03 Partial Checkpoint Before Shutdown

## Why this checkpoint exists

The `S03` station-wave run was intentionally interrupted due laptop shutdown/offline requirement.

To avoid a hard power-off during active migration work, the in-flight orchestrator was terminated in a controlled way.

## Execution context

- Station: `S03` (`S03 Nordtoftir`)
- Profile: `fw_default`
- Backup horizon: `2026-01-22`
- Mode: strict pass first (`--expected-site`), recovery pass only if strict mismatch blockers appear

## Confirmed completed cohorts (migration + semantic artifacts present)

1. `AquaGen Mars 25|1|2025`
2. `AquaGen juni 25|2|2025`
3. `Gjogv/Fiskaaling mars 2023|5|2023`
4. `Stofnfiskur Aug 23|4|2023`
5. `Stofnfiskur Des 23|6|2023`
6. `Stofnfiskur Des 24|4|2024`
7. `Stofnfiskur Juni 24|2|2024`

Current confirmed strict progress: `7/10`.

## Remaining S03 cohorts to run after restart

1. `Stofnfiskur Mars 24|1|2024` (was in-flight when interruption happened; rerun from start)
2. `Stofnfiskur Okt 25|3|2025`
3. `Stofnfiskur sept 24|3|2024`

## Notes

- `S03_station_wave_migration_summary_2026-02-17.json` was not emitted yet.
- `S03_station_wave_two_pass_execution_result_2026-02-17.json` was not emitted yet.
- No `S03_allow_station_mismatch_*` artifacts were observed at interruption time.

## Resume instruction

Resume by executing the S03 two-pass runner again, targeting at least the 3 remaining cohorts above.
After completion, regenerate:

- `S03_station_wave_migration_summary_2026-02-17.{md,json}`
- `S03_station_wave_two_pass_execution_result_2026-02-17.json`
- updated Faroe 7-station coverage scoreboard
