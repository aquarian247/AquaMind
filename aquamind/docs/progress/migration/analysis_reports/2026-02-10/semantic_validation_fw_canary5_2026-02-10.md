# FW 5-Batch Canary Regression Report (2026-02-10)

## Scope
- Fresh isolated replay per batch (`clear_migration_db.py` before each run).
- Guarded migration with `--expected-site` for station containment.
- Semantic gates + counts run for each batch.

## Commands (per batch)
```bash
PYTHONPATH=/Users/aquarian247/Projects/AquaMind SKIP_CELERY_SIGNALS=1 python /Users/aquarian247/Projects/AquaMind/scripts/migration/clear_migration_db.py
PYTHONPATH=/Users/aquarian247/Projects/AquaMind SKIP_CELERY_SIGNALS=1 python /Users/aquarian247/Projects/AquaMind/scripts/migration/tools/pilot_migrate_input_batch.py --batch-key "<batch_key>" --expected-site "<site>" --use-csv /Users/aquarian247/Projects/AquaMind/scripts/migration/data/extract --skip-environmental
PYTHONPATH=/Users/aquarian247/Projects/AquaMind SKIP_CELERY_SIGNALS=1 python /Users/aquarian247/Projects/AquaMind/scripts/migration/tools/migration_semantic_validation_report.py --component-key "<component_key>" --report-dir "<report_dir>" --use-csv /Users/aquarian247/Projects/AquaMind/scripts/migration/data/extract --check-regression-gates --output "<report.md>" --summary-json "<report.summary.json>"
PYTHONPATH=/Users/aquarian247/Projects/AquaMind SKIP_CELERY_SIGNALS=1 python /Users/aquarian247/Projects/AquaMind/scripts/migration/tools/migration_counts_report.py --batch-number "<batch_name>"
```

## Outcome Summary
- Batches run: `5`
- Gate PASS: `3`
- Gate FAIL: `2`
- Transfer-action zero-count gate: `0` for all 5 batches.
- Positive transition alert gate: `0` for all 5 batches (some incomplete-linkage exclusions present).

| Batch | Station | Gate | Non-bridge zero assignments | Transition basis (bridge/entry) | Incomplete-linkage transitions | semantic_rc |
| --- | --- | --- | ---: | --- | ---: | ---: |
| Benchmark Gen. Mars 2025 | S24 Strond | FALSE | 45 | 1/3 | 1 | 1 |
| Bakkafrost mai 24 | S16 Glyvradalur | TRUE | 0 | 1/3 | 3 | 0 |
| StofnFiskur mars 2024 | S08 Gjógv | FALSE | 24 | 1/2 | 2 | 1 |
| Stofnfiskur S-21 feb24 | S21 Viðareiði | TRUE | 0 | 4/0 | 0 | 0 |
| Stofnfiskur Juni 24 | S03 Norðtoftir | TRUE | 0 | 3/1 | 1 | 0 |

## Failure Decomposition
- `Benchmark Gen. Mars 2025` (S24): gate FAIL due `non_bridge_zero_assignments=45` (threshold `2`).
  - Zero-row buckets: total `165`, bridge `62`, superseded `1`, orphan-short `57`, residual non-bridge `45`.
- `StofnFiskur mars 2024` (S08): gate FAIL due `non_bridge_zero_assignments=24` (threshold `2`).
  - Zero-row buckets: total `130`, bridge `86`, superseded `20`, orphan-short `0`, residual non-bridge `24`.

## Readiness Decision
- **Not ready for 20-batch rollout yet.**
- Evidence: 2/5 batches fail the non-bridge zero-assignment regression gate under current tooling.
- Stable in this canary: station guards, transfer-action counts, and positive-delta transition gate behavior.

## Produced per-batch semantic outputs
- `/Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/migration/analysis_reports/2026-02-10/semantic_validation_benchmark_gen_mars_2025_2026-02-10_canary5.md`
- `/Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/migration/analysis_reports/2026-02-10/semantic_validation_benchmark_gen_mars_2025_2026-02-10_canary5.summary.json`
- `/Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/migration/analysis_reports/2026-02-10/semantic_validation_bakkafrost_mai_24_2026-02-10_canary5.md`
- `/Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/migration/analysis_reports/2026-02-10/semantic_validation_bakkafrost_mai_24_2026-02-10_canary5.summary.json`
- `/Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/migration/analysis_reports/2026-02-10/semantic_validation_stofnfiskur_mars_2024_2026-02-10_canary5.md`
- `/Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/migration/analysis_reports/2026-02-10/semantic_validation_stofnfiskur_mars_2024_2026-02-10_canary5.summary.json`
- `/Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/migration/analysis_reports/2026-02-10/semantic_validation_stofnfiskur_s21_feb24_2026-02-10_canary5.md`
- `/Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/migration/analysis_reports/2026-02-10/semantic_validation_stofnfiskur_s21_feb24_2026-02-10_canary5.summary.json`
- `/Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/migration/analysis_reports/2026-02-10/semantic_validation_stofnfiskur_juni24_2026-02-10_canary5.md`
- `/Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/migration/analysis_reports/2026-02-10/semantic_validation_stofnfiskur_juni24_2026-02-10_canary5.summary.json`
