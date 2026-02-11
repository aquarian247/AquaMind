# FW 5-Batch Canary v2 Regression Report (2026-02-10)

## Scope
- Re-ran the exact 5-batch FW canary set after tooling stabilization.
- Same enforcement: DB wipe per batch, `--expected-site`, semantic gates, counts.

## Gate Summary
- Before (canary v1): PASS `3/5`, FAIL `2/5`.
- After (canary v2): PASS `5/5`, FAIL `0/5`.
- Zero-count transfer actions: `0` in all v2 runs.
- Positive transition alert failures: `0` in all v2 runs.

## Compact Findings Table
| batch | non-bridge zero assignments before/after | gate result before/after | transition basis changes (if any) |
| --- | --- | --- | --- |
| Benchmark Gen. Mars 2025 | 45 -> 0 | FAIL -> PASS | unchanged; incomplete-linkage 1 -> 1 |
| Bakkafrost mai 24 | 0 -> 0 | PASS -> PASS | unchanged; incomplete-linkage 3 -> 3 |
| StofnFiskur mars 2024 | 24 -> 0 | FAIL -> PASS | unchanged; incomplete-linkage 2 -> 2 |
| Stofnfiskur S-21 feb24 | 0 -> 0 | PASS -> PASS | unchanged; incomplete-linkage 0 -> 0 |
| Stofnfiskur Juni 24 | 0 -> 0 | PASS -> PASS | unchanged; incomplete-linkage 1 -> 1 |

## v2 Zero-Row Decomposition (new buckets)
| batch | no-count-evidence zeros | known-loss-depleted zeros |
| --- | ---: | ---: |
| Benchmark Gen. Mars 2025 | 35 | 10 |
| Bakkafrost mai 24 | 0 | 0 |
| StofnFiskur mars 2024 | 0 | 24 |
| Stofnfiskur S-21 feb24 | 0 | 0 |
| Stofnfiskur Juni 24 | 0 | 0 |

## Readiness Decision
- **Ready for controlled 20-batch rollout with current scripts**, provided the same station guards and gate checks are kept in the runbook.

## Outputs
- `/Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/migration/analysis_reports/2026-02-10/semantic_validation_benchmark_gen_mars_2025_2026-02-10_canary5_v2.md`
- `/Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/migration/analysis_reports/2026-02-10/semantic_validation_benchmark_gen_mars_2025_2026-02-10_canary5_v2.summary.json`
- `/Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/migration/analysis_reports/2026-02-10/semantic_validation_bakkafrost_mai_24_2026-02-10_canary5_v2.md`
- `/Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/migration/analysis_reports/2026-02-10/semantic_validation_bakkafrost_mai_24_2026-02-10_canary5_v2.summary.json`
- `/Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/migration/analysis_reports/2026-02-10/semantic_validation_stofnfiskur_mars_2024_2026-02-10_canary5_v2.md`
- `/Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/migration/analysis_reports/2026-02-10/semantic_validation_stofnfiskur_mars_2024_2026-02-10_canary5_v2.summary.json`
- `/Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/migration/analysis_reports/2026-02-10/semantic_validation_stofnfiskur_s21_feb24_2026-02-10_canary5_v2.md`
- `/Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/migration/analysis_reports/2026-02-10/semantic_validation_stofnfiskur_s21_feb24_2026-02-10_canary5_v2.summary.json`
- `/Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/migration/analysis_reports/2026-02-10/semantic_validation_stofnfiskur_juni24_2026-02-10_canary5_v2.md`
- `/Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/migration/analysis_reports/2026-02-10/semantic_validation_stofnfiskur_juni24_2026-02-10_canary5_v2.summary.json`
