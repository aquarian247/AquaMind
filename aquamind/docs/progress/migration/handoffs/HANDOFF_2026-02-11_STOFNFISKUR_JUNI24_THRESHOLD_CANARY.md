# Handoff - 2026-02-11 - Stofnfiskur Juni 24 Threshold Canary

## Objective
Run the next deterministic migration-only step for the lifecycle discrepancy: isolate whether assignment materialization policy (not runtime chart logic) is driving the `Egg&Alevin -> Fry` collapse.

## What was done
1. Regenerated canonical 145-member `population_members.csv` for `Stofnfiskur Juni 24|2|2024`.
2. Wiped DB.
3. Migrated component with only one policy change at runtime invocation:
   - `pilot_migrate_component.py --external-mixing-status-multiplier 9.5`
4. Ran full migration event pipeline (transfers, feeding, growth, mortality, culling, escapes, treatments, lice, journal, harvest, feed inventory).
5. Generated counts + semantic reports.
6. Added migration tooling pass-through:
   - `pilot_migrate_input_batch.py --external-mixing-status-multiplier`
   - forwards to `pilot_migrate_component.py`
7. Smoke-validated pass-through by executing `run_migration_script(..., external_mixing_status_multiplier=9.5, dry_run=True)` successfully.

## Exact key commands
- Assignment canary:
```bash
PYTHONPATH=/Users/aquarian247/Projects/AquaMind SKIP_CELERY_SIGNALS=1 \
python /Users/aquarian247/Projects/AquaMind/scripts/migration/tools/pilot_migrate_component.py \
  --component-key EDF931F2-51CC-4A10-9002-128E7BF8067C \
  --report-dir /Users/aquarian247/Projects/AquaMind/scripts/migration/output/input_batch_migration/Stofnfiskur_Juni_24_2_2024 \
  --batch-number "Stofnfiskur Juni 24 M95" \
  --expected-site "S03 Norðtoftir" \
  --use-csv /Users/aquarian247/Projects/AquaMind/scripts/migration/data/extract \
  --external-mixing-status-multiplier 9.5
```

- Semantic evidence output:
```bash
PYTHONPATH=/Users/aquarian247/Projects/AquaMind SKIP_CELERY_SIGNALS=1 \
python /Users/aquarian247/Projects/AquaMind/scripts/migration/tools/migration_semantic_validation_report.py \
  --component-key EDF931F2-51CC-4A10-9002-128E7BF8067C \
  --report-dir /Users/aquarian247/Projects/AquaMind/scripts/migration/output/input_batch_migration/Stofnfiskur_Juni_24_2_2024 \
  --use-csv /Users/aquarian247/Projects/AquaMind/scripts/migration/data/extract \
  --check-regression-gates \
  --output /tmp/stofn_juni24_m95_semantic_full.md \
  --summary-json /tmp/stofn_juni24_m95_semantic_full.json
```

## Outputs and evidence
- Batch in DB: `452` (`Stofnfiskur Juni 24 M95`)
- Counts (`migration_counts_report.py`):
  - assignments `145`
  - transfer workflows/actions `57/57`
  - feeding `3927`
  - mortality `3734`
- Stage-entry-like sums (container+stage earliest-positive):
  - Egg&Alevin `1,760,038`
  - Fry `1,708,576`
  - Parr `299,007`
  - Smolt `104,377`
  - Post-Smolt `42,547`

Comparison vs post-fix default documented baseline (batch 449):
- Egg&Alevin `1,760,038 -> 1,760,038`
- Fry `196,889 -> 1,708,576`
- Parr `299,007 -> 299,007`
- Smolt `104,377 -> 104,377`
- Post-Smolt `42,547 -> 42,547`

Semantic gate status (`/tmp/stofn_juni24_m95_semantic_full.json`):
- regression gates: `PASS`
- zero-count transfer actions: `0`
- non-bridge zero assignments: `0`

## Deterministic root-cause signal
For all 12 Fry entry populations:
- conserved start count `~14,765`
- status-at-start `~142,381`
- ratio `~9.64`
- all have external-mixing evidence

With default multiplier `10.0`, these rows stay on conserved counts; with `9.5`, they promote to status and restore Fry entry near expected cohort scale.

## Unresolved risks / uncertainty
1. This canary verifies a deterministic lever for this cohort only; global default change still needs cohort-level validation.
2. Bridge-aware transition accounting still shows large unresolved drops/incomplete linkage at `Fry -> Parr` (source-boundary uncertainty persists).
3. No runtime/API logic was changed; discrepancy handling remains migration-tooling-only.

## Next steps
1. Run bounded FW20 sensitivity rerun (`10.0` vs `9.5`) on affected cohorts with DB wipe per run.
2. Promote a default only if no new semantic regressions are introduced.

## Follow-up completed
- FW20 bounded sensitivity rerun executed and documented:
  - `/Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/migration/handoffs/HANDOFF_2026-02-11_FW20_EXTERNAL_MIXING_SENSITIVITY.md`
  - `/Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/migration/analysis_reports/2026-02-11/fw20_external_mixing_sensitivity_sweep_2026-02-11.md`
- Result: no cohort-level change in tested FW20 subset under `10.0 -> 9.5`; keep default `10.0` and use targeted override only when deterministic row-level evidence supports it.
