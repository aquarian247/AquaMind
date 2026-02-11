# Handoff - 2026-02-11 - FW20 External-Mixing Sensitivity Sweep

## Objective
Continue deterministic next step after Stofnfiskur Juni 24 threshold canary by validating whether external-mixing multiplier (`10.0` vs `9.5`) generalizes to affected FW20 cohorts.

## What Changed
### Migration tooling
- `/Users/aquarian247/Projects/AquaMind/scripts/migration/tools/pilot_migrate_input_batch.py`
  - Added pass-through flag: `--external-mixing-status-multiplier`
  - Forwards to `pilot_migrate_component.py` only.

### Documentation
- Added report:
  - `/Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/migration/analysis_reports/2026-02-11/fw20_external_mixing_sensitivity_sweep_2026-02-11.md`

## Commands Executed

### Sweep runner
```bash
python /tmp/run_fw20_external_mixing_sweep_2026-02-11.py
```

Runner behavior per `(batch, multiplier)`:
1. DB wipe:
```bash
PYTHONPATH=/Users/aquarian247/Projects/AquaMind SKIP_CELERY_SIGNALS=1 \
python /Users/aquarian247/Projects/AquaMind/scripts/migration/clear_migration_db.py
```
2. Batch migration:
```bash
PYTHONPATH=/Users/aquarian247/Projects/AquaMind SKIP_CELERY_SIGNALS=1 \
python /Users/aquarian247/Projects/AquaMind/scripts/migration/tools/pilot_migrate_input_batch.py \
  --batch-key <BATCH_KEY> --expected-site <SITE> \
  --use-csv /Users/aquarian247/Projects/AquaMind/scripts/migration/data/extract \
  --skip-environmental --parallel-workers 6 --parallel-blas-threads 1 \
  --script-timeout-seconds 1200 \
  --external-mixing-status-multiplier <10.0|9.5>
```
3. Semantic evidence:
```bash
PYTHONPATH=/Users/aquarian247/Projects/AquaMind SKIP_CELERY_SIGNALS=1 \
python /Users/aquarian247/Projects/AquaMind/scripts/migration/tools/migration_semantic_validation_report.py \
  --component-key <COMPONENT_KEY> --report-dir <REPORT_DIR> \
  --use-csv /Users/aquarian247/Projects/AquaMind/scripts/migration/data/extract \
  --check-regression-gates --output <REPORT_MD> --summary-json <REPORT_JSON>
```
4. Counts evidence:
```bash
PYTHONPATH=/Users/aquarian247/Projects/AquaMind SKIP_CELERY_SIGNALS=1 \
python /Users/aquarian247/Projects/AquaMind/scripts/migration/tools/migration_counts_report.py \
  --batch-number <BATCH_NAME>
```

## Outputs
- `/tmp/fw20_external_mixing_sweep_2026-02-11/fw20_external_mixing_sweep_summary.tsv`
- `/tmp/fw20_external_mixing_sweep_2026-02-11/fw20_external_mixing_sweep_summary.json`
- `/tmp/fw20_external_mixing_sweep_2026-02-11/fw20_external_mixing_sweep_delta.tsv`
- `/tmp/fw20_external_mixing_sweep_2026-02-11/fw20_external_mixing_sweep_delta.json`
- Per-run logs + semantic JSON/MD under:
  - `/tmp/fw20_external_mixing_sweep_2026-02-11/<batch_slug>__m10_0/`
  - `/tmp/fw20_external_mixing_sweep_2026-02-11/<batch_slug>__m9_5/`

## Result Summary
All 4 targeted cohorts were unchanged between `10.0` and `9.5`:
- identical stage-entry values
- identical gate outcomes (`PASS -> PASS`)
- identical transition basis/reason for `Egg&Alevin -> Fry`
- identical non-bridge zero assignment counts (`0 -> 0`)

Practical conclusion:
- Stofnfiskur Juni 24 threshold sensitivity is not reproduced in this tested FW20 subset.
- No evidence from this sweep supports changing global default from `10.0` to `9.5`.

## Remaining Risks / Uncertainty
1. Cohort-specific sensitivity may still exist outside this 4-batch subset.
2. High-drop transitions with `bridge_aware` or `no_entry_populations` remain source-boundary/linkage issues; threshold does not resolve them here.
3. Runtime remains unchanged and FishTalk-agnostic; all changes are in migration tooling and reports.

## Next Steps
1. Keep `10.0` as default for now.
2. Apply `9.5` only as targeted override for Stofnfiskur Juni 24-like cohorts where row-level evidence shows near-threshold (`status/conserved`) behavior.
3. Continue Faroe FW `<30 months` scale with canaries, prioritizing linkage-boundary diagnostics over threshold tuning.
