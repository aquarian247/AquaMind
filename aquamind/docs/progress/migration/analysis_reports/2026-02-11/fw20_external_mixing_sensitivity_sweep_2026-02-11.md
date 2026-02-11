# FW20 External-Mixing Multiplier Sensitivity Sweep (2026-02-11)

## Scope
Bounded sensitivity rerun for FW20 cohorts with severe `Egg&Alevin -> Fry` drop signatures under post-fix tooling.

Tested multipliers (migration tooling only):
- `10.0` (current default)
- `9.5` (Stofnfiskur Juni 24 canary-sensitive setting)

Targeted cohorts:
- `Stofnfiskur sept 24|3|2024` (`S03 Norðtoftir`)
- `Stofnfiskur Des 24|4|2024` (`S03 Norðtoftir`)
- `Benchmark Gen. Septembur 2024|3|2024` (`S24 Strond`)
- `Benchmark Gen. Desembur 2024|4|2024` (`S24 Strond`)

## Execution Profile
- DB wipe before every run.
- `pilot_migrate_input_batch.py --expected-site <station>` with:
  - `--use-csv /Users/aquarian247/Projects/AquaMind/scripts/migration/data/extract`
  - `--skip-environmental`
  - `--parallel-workers 6 --parallel-blas-threads 1`
  - `--script-timeout-seconds 1200`
  - `--external-mixing-status-multiplier {10.0|9.5}`
- Semantic evidence via `migration_semantic_validation_report.py`.
- Counts evidence via `migration_counts_report.py`.

Automation runner:
- `/tmp/run_fw20_external_mixing_sweep_2026-02-11.py`

Artifacts:
- `/tmp/fw20_external_mixing_sweep_2026-02-11/fw20_external_mixing_sweep_summary.tsv`
- `/tmp/fw20_external_mixing_sweep_2026-02-11/fw20_external_mixing_sweep_summary.json`
- `/tmp/fw20_external_mixing_sweep_2026-02-11/fw20_external_mixing_sweep_delta.tsv`
- `/tmp/fw20_external_mixing_sweep_2026-02-11/fw20_external_mixing_sweep_delta.json`

## Compact Findings Table

| batch | non-bridge zero assignments (`10.0 -> 9.5`) | gate result (`10.0 -> 9.5`) | transition basis/reason changes | Fry entry (`10.0 -> 9.5`) |
| --- | --- | --- | --- | --- |
| Stofnfiskur sept 24 | `0 -> 0` | `PASS -> PASS` | none (`fishgroup_bridge_aware / bridge_aware`) | `1,733,832 -> 1,733,832` |
| Stofnfiskur Des 24 | `0 -> 0` | `PASS -> PASS` | none (`fishgroup_bridge_aware / bridge_aware`) | `329,652 -> 329,652` |
| Benchmark Gen. Septembur 2024 | `0 -> 0` | `PASS -> PASS` | none (`fishgroup_bridge_aware / bridge_aware`) | `3,397,931 -> 3,397,931` |
| Benchmark Gen. Desembur 2024 | `0 -> 0` | `PASS -> PASS` | none (`fishgroup_bridge_aware / bridge_aware`) | `3,196,671 -> 3,196,671` |

## Deterministic Outcome
- No targeted FW20 cohort changed under `10.0 -> 9.5`.
- No gate regressions or improvements were observed in this subset.
- Interpretation: the Stofnfiskur Juni 24 threshold sensitivity is cohort-specific and does not generalize to this tested FW20 subset.

## Uncertainty Label
- This sweep covered only the 4 high-drop FW20 cohorts selected by post-fix signature; additional cohorts could still have isolated threshold sensitivity.
- Existing transition uncertainty (`incomplete_linkage`, `no_entry_populations`) remains source-boundary driven and is not resolved by this threshold in tested cohorts.
