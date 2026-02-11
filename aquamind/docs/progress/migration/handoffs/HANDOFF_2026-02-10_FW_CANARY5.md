# Migration Handoff (2026-02-10 FW 5-Batch Canary)

## Scope
- Objective: evaluate readiness to scale from single-batch stabilization to a broader rollout.
- Canary set: 5 FW station-contained batches, each replayed in isolation.
- Enforcement used for every run:
  - DB wipe before run,
  - `--expected-site` station guard,
  - semantic regression gates,
  - counts report.

## Batches executed
1. `Benchmark Gen. Mars 2025|1|2025` (`S24 Strond`)
2. `Bakkafrost mai 24|2|2024` (`S16 Glyvradalur`)
3. `StofnFiskur mars 2024|1|2024` (`S08 Gjógv`)
4. `Stofnfiskur S-21 feb24|1|2024` (`S21 Viðareiði`)
5. `Stofnfiskur Juni 24|2|2024` (`S03 Norðtoftir`)

## Exact command body used per batch
```bash
PYTHONPATH=/Users/aquarian247/Projects/AquaMind SKIP_CELERY_SIGNALS=1 python /Users/aquarian247/Projects/AquaMind/scripts/migration/clear_migration_db.py
PYTHONPATH=/Users/aquarian247/Projects/AquaMind SKIP_CELERY_SIGNALS=1 python /Users/aquarian247/Projects/AquaMind/scripts/migration/tools/pilot_migrate_input_batch.py --batch-key "<batch_key>" --expected-site "<site>" --use-csv /Users/aquarian247/Projects/AquaMind/scripts/migration/data/extract --skip-environmental
PYTHONPATH=/Users/aquarian247/Projects/AquaMind SKIP_CELERY_SIGNALS=1 python /Users/aquarian247/Projects/AquaMind/scripts/migration/tools/migration_semantic_validation_report.py --component-key "<component_key>" --report-dir "<report_dir>" --use-csv /Users/aquarian247/Projects/AquaMind/scripts/migration/data/extract --check-regression-gates --output "<report.md>" --summary-json "<report.summary.json>"
PYTHONPATH=/Users/aquarian247/Projects/AquaMind SKIP_CELERY_SIGNALS=1 python /Users/aquarian247/Projects/AquaMind/scripts/migration/tools/migration_counts_report.py --batch-number "<batch_name>"
```

## Results table

| batch | station | gate | non-bridge zero assignments | transition basis (bridge/entry) | incomplete-linkage | migrate_rc | semantic_rc | counts_rc |
| --- | --- | --- | ---: | --- | ---: | ---: | ---: | ---: |
| Benchmark Gen. Mars 2025 | S24 Strond | FAIL | 45 | 1/3 | 1 | 0 | 1 | 0 |
| Bakkafrost mai 24 | S16 Glyvradalur | PASS | 0 | 1/3 | 3 | 0 | 0 | 0 |
| StofnFiskur mars 2024 | S08 Gjógv | FAIL | 24 | 1/2 | 2 | 0 | 1 | 0 |
| Stofnfiskur S-21 feb24 | S21 Viðareiði | PASS | 0 | 4/0 | 0 | 0 | 0 | 0 |
| Stofnfiskur Juni 24 | S03 Norðtoftir | PASS | 0 | 3/1 | 1 | 0 | 0 | 0 |

## Gate outcome summary
- PASS: `3/5`
- FAIL: `2/5`
- Zero-count transfer actions: `0` in all 5 batches.
- Positive transition alert gate: `0` in all 5 batches.

## Failure decomposition (evidence)
1. `Benchmark Gen. Mars 2025`:
- failure gate: `non_bridge_zero_assignments_within_threshold`
- value: `45` (threshold `2`)
- zero-row buckets:
  - total `165`
  - bridge `62`
  - same-stage superseded `1`
  - short-lived orphan `57`
  - residual non-bridge `45`

2. `StofnFiskur mars 2024`:
- failure gate: `non_bridge_zero_assignments_within_threshold`
- value: `24` (threshold `2`)
- zero-row buckets:
  - total `130`
  - bridge `86`
  - same-stage superseded `20`
  - short-lived orphan `0`
  - residual non-bridge `24`

## Decision
- **Not ready for 20-batch rollout yet.**
- Reason: canary still shows significant residual non-bridge zero-assignment failures in 2/5 FW station batches under current tooling.

## Outputs
- Consolidated report:
  - `/Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/migration/analysis_reports/2026-02-10/semantic_validation_fw_canary5_2026-02-10.md`
  - `/Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/migration/analysis_reports/2026-02-10/semantic_validation_fw_canary5_2026-02-10.summary.json`
- Per-batch semantic reports:
  - `semantic_validation_benchmark_gen_mars_2025_2026-02-10_canary5.*`
  - `semantic_validation_bakkafrost_mai_24_2026-02-10_canary5.*`
  - `semantic_validation_stofnfiskur_mars_2024_2026-02-10_canary5.*`
  - `semantic_validation_stofnfiskur_s21_feb24_2026-02-10_canary5.*`
  - `semantic_validation_stofnfiskur_juni24_2026-02-10_canary5.*`

## Recommended next step (before 20-batch)
1. Run a focused zero-assignment classification pass on S24 + S08 failure patterns and rerun this same 5-batch canary unchanged.
2. Proceed to 20 batches only if this canary reaches `5/5` gate PASS with no new gate regressions.
