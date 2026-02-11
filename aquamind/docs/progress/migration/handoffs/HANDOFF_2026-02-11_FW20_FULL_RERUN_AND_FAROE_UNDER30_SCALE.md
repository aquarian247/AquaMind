# HANDOFF 2026-02-11 - FW20 Full Rerun + Faroe FW <30m Canary/Scale

## Scope
- Continued FishTalk -> AquaMind migration hardening from the 2026-02-11 state.
- Preserved runtime separation: no FishTalk-specific coupling added to runtime API/UI logic.
- Completed FW20 full station/pre-adult rerun with tooling-only fixes.
- Produced hard before/after evidence against pre-fix baseline.
- Advanced Faroe FW `<30 months` via canary-first, then scaled summary.

## Architecture Guardrail Status
- Confirmed unchanged in this pass:
  - Migration/FishTalk logic remains in migration tooling and report scripts only.
  - No new runtime API/UI code coupling introduced.

## Commands Executed

### A) FW20 full rerun
```bash
python /tmp/run_fw20_station_parallel_2026-02-11.py
```

Runner-enforced per-batch command body (20 batches):
```bash
PYTHONPATH=/Users/aquarian247/Projects/AquaMind SKIP_CELERY_SIGNALS=1 python /Users/aquarian247/Projects/AquaMind/scripts/migration/clear_migration_db.py
PYTHONPATH=/Users/aquarian247/Projects/AquaMind SKIP_CELERY_SIGNALS=1 python /Users/aquarian247/Projects/AquaMind/scripts/migration/tools/pilot_migrate_input_batch.py --batch-key "<BATCH_KEY>" --expected-site "<SITE>" --use-csv /Users/aquarian247/Projects/AquaMind/scripts/migration/data/extract --skip-environmental --parallel-workers 6 --parallel-blas-threads 1 --script-timeout-seconds 1200
PYTHONPATH=/Users/aquarian247/Projects/AquaMind SKIP_CELERY_SIGNALS=1 python /Users/aquarian247/Projects/AquaMind/scripts/migration/tools/migration_semantic_validation_report.py --component-key "<COMPONENT_KEY>" --report-dir "<REPORT_DIR>" --use-csv /Users/aquarian247/Projects/AquaMind/scripts/migration/data/extract --check-regression-gates --output "<REPORT_MD>" --summary-json "<REPORT_JSON>"
PYTHONPATH=/Users/aquarian247/Projects/AquaMind SKIP_CELERY_SIGNALS=1 python /Users/aquarian247/Projects/AquaMind/scripts/migration/tools/migration_counts_report.py --batch-number "<BATCH_NAME>"
```

### B) FW20 before/after delta
```bash
python /tmp/compare_fw20_before_after_2026-02-11.py
```

### C) Faroe FW `<30 months` canary (5)
```bash
python /tmp/run_faroe_fw_under30_canary5_2026-02-11.py
```

### D) Faroe FW `<30 months` scaled summary build (24 unique batches)
```bash
python /tmp/build_faroe_fw_under30_scale_report_2026-02-11.py
```

## FW20 Full Rerun Outcome (Post-Fix)
- Gate result: `20/20 PASS` (`0 FAIL`)
- Aggregate non-bridge zero assignments: `0`
- Aggregate zero-count transfer actions: `0`
- Aggregate positive transition alerts: `0`
- Average timings: migrate `108.8s`, semantic `84.2s`, counts `0.3s`

### Former failures resolved in full-cohort rerun
- `Stofnfiskur mai 2025`: now `PASS`; transition basis `2/0`, `direct_linkage=1`
- `Stofnfiskur feb 2025`: now `PASS`; transition basis `1/2`, `direct_linkage=1`, `incomplete_linkage=1`
- `BF mars 2025`: now `PASS`; stage-resolution abort removed; transition basis `2/1`, `incomplete_linkage=1`

## Hard Before/After Evidence

### Canonical pre-fix backup artifacts (restored in this environment)
- `/tmp/fw20_station_parallel_2026-02-11/pre_fix_backup/fw20_parallel_summary_before_fix.tsv`
- `/tmp/fw20_station_parallel_2026-02-11/pre_fix_backup/fw20_parallel_summary_before_fix.json`
- `/tmp/fw20_station_parallel_2026-02-11/pre_fix_backup/semantic_validation_fw20_station_parallel_2026-02-11_before_fix.md`

### Post-fix FW20 artifacts
- `/tmp/fw20_station_parallel_2026-02-11/fw20_parallel_summary.tsv`
- `/tmp/fw20_station_parallel_2026-02-11/fw20_parallel_summary.json`
- `/Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/migration/analysis_reports/2026-02-11/semantic_validation_fw20_station_parallel_2026-02-11_post_fix.md`

### Before/after deltas
- `/tmp/fw20_station_parallel_2026-02-11/fw20_before_after_delta.tsv`
- `/tmp/fw20_station_parallel_2026-02-11/fw20_before_after_delta.json`
- `/Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/migration/analysis_reports/2026-02-11/fw20_before_after_2026-02-11.md`
- `/Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/migration/analysis_reports/2026-02-11/fw20_compact_findings_2026-02-11.md`

Delta headline:
- PASS before/after: `17/20 -> 20/20`
- FAIL before/after: `3/20 -> 0/20`
- Improved batches: `3`
- Regressed batches: `0`

## Faroe FW <30m Continuation

### Canary (5 batches)
- Gate result: `5/5 PASS` (`0 FAIL`)
- Aggregate non-bridge zero assignments: `0`
- Aggregate zero-count transfer actions: `0`
- Aggregate positive transition alerts: `0`

Artifacts:
- `/tmp/faroe_fw_under30_canary5_2026-02-11/faroe_fw_under30_canary5_summary.tsv`
- `/tmp/faroe_fw_under30_canary5_2026-02-11/faroe_fw_under30_canary5_summary.json`
- `/Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/migration/analysis_reports/2026-02-11/semantic_validation_faroe_fw_under30_canary5_2026-02-11.md`

### Scale step (canary + FW20)
- Cohort size: `24` unique station-contained Faroe FW batches (`<30m` continuation set)
- Gate result: `24/24 PASS`
- Aggregate non-bridge zero assignments: `0`
- Aggregate zero-count transfer actions: `0`
- Aggregate positive transition alerts: `0`

Artifacts:
- `/tmp/faroe_fw_under30_scale_2026-02-11/faroe_fw_under30_scale24_summary.tsv`
- `/tmp/faroe_fw_under30_scale_2026-02-11/faroe_fw_under30_scale24_summary.json`
- `/Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/migration/analysis_reports/2026-02-11/semantic_validation_faroe_fw_under30_scale24_2026-02-11.md`

## Staged Roadmap (Scotland FW -> Sea), with Uncertainty Labels

### Stage 1: Scotland FW station canary
- Start with a guarded Scotland FW canary (5 station-contained batches with explicit `--expected-site`).
- Pass criteria: no regression gate failures, `non_bridge_zero_assignments=0`, `zero_count_transfer_actions=0`.
- **Uncertainty label:** Scotland hall inventory exists, but several hall-stage mappings remain less qualified than Faroe; expect potential stage-resolution gaps requiring explicit mapping evidence.

### Stage 2: Scotland FW scale-out
- Expand to 20+ Scotland FW batches only after stage-1 canary passes.
- Keep same wipe + station guard + semantic + counts protocol.
- **Uncertainty label:** Site/hall nomenclature in Scotland may require additional deterministic normalization for ambiguous labels (`Hatchery`, `RAS`, etc.).

### Stage 3: Sea-based batches (deferred deterministic linkage)
- Run sea cohorts as separate, unlinked components unless explicit deterministic FW->Sea linkage evidence is available.
- Continue enforcing transfer edge integrity and semantic gates within sea-only cohorts.
- **Uncertainty label:** FW->Sea linkage remains unresolved in current extracts for modern cohorts; no heuristic linkage should be promoted to canonical without deterministic evidence.

## Unresolved Risks
1. FW->Sea linkage for active/modern cohorts still lacks deterministic extract evidence in current dataset.
2. Some stage transitions still rely on `incomplete_linkage` fallback (warning-level evidence), though gate outcomes are now clean.
3. Scaled Faroe `<30m` summary is station-contained and validated, but not yet an exhaustive all-batch extract-wide sweep.

## Next Steps
1. Execute Scotland FW canary5 with station guards and identical gate policy.
2. If Scotland canary passes, run Scotland FW scale cohort and publish before/after gate table.
3. Begin sea-only cohort canary (no FW linkage inference), then scale with explicit uncertainty labeling carried forward.
