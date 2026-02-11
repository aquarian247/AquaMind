# Stofnfiskur Juni 24 - External Mixing Threshold Canary (2026-02-11)

## Scope
Deterministically test whether the persistent `Egg&Alevin -> Fry` collapse for `Stofnfiskur Juni 24` is driven by migration assignment count policy (tooling) rather than runtime lifecycle aggregation.

Runtime remained unchanged.

## Commands Run

```bash
# 1) Rebuild canonical 145-member population_members.csv (no DB writes)
PYTHONPATH=/Users/aquarian247/Projects/AquaMind SKIP_CELERY_SIGNALS=1 \
python /Users/aquarian247/Projects/AquaMind/scripts/migration/tools/pilot_migrate_input_batch.py \
  --batch-key "Stofnfiskur Juni 24|2|2024" \
  --batch-number "Stofnfiskur Juni 24" \
  --expected-site "S03 Norðtoftir" \
  --use-csv /Users/aquarian247/Projects/AquaMind/scripts/migration/data/extract \
  --skip-environmental --dry-run

# 2) Clean DB
PYTHONPATH=/Users/aquarian247/Projects/AquaMind SKIP_CELERY_SIGNALS=1 \
python /Users/aquarian247/Projects/AquaMind/scripts/migration/clear_migration_db.py

# 3) Canary assignments with only one policy change: lower external-mixing threshold
PYTHONPATH=/Users/aquarian247/Projects/AquaMind SKIP_CELERY_SIGNALS=1 \
python /Users/aquarian247/Projects/AquaMind/scripts/migration/tools/pilot_migrate_component.py \
  --component-key EDF931F2-51CC-4A10-9002-128E7BF8067C \
  --report-dir /Users/aquarian247/Projects/AquaMind/scripts/migration/output/input_batch_migration/Stofnfiskur_Juni_24_2_2024 \
  --batch-number "Stofnfiskur Juni 24 M95" \
  --expected-site "S03 Norðtoftir" \
  --use-csv /Users/aquarian247/Projects/AquaMind/scripts/migration/data/extract \
  --external-mixing-status-multiplier 9.5

# 4) Complete event pipeline (same migration tooling; no runtime changes)
PYTHONPATH=/Users/aquarian247/Projects/AquaMind SKIP_CELERY_SIGNALS=1 \
python /Users/aquarian247/Projects/AquaMind/scripts/migration/tools/pilot_migrate_component_transfers.py \
  --component-key EDF931F2-51CC-4A10-9002-128E7BF8067C \
  --report-dir /Users/aquarian247/Projects/AquaMind/scripts/migration/output/input_batch_migration/Stofnfiskur_Juni_24_2_2024 \
  --use-csv /Users/aquarian247/Projects/AquaMind/scripts/migration/data/extract \
  --use-subtransfers --skip-synthetic-stage-transitions

PYTHONPATH=/Users/aquarian247/Projects/AquaMind SKIP_CELERY_SIGNALS=1 \
python /Users/aquarian247/Projects/AquaMind/scripts/migration/tools/pilot_migrate_component_feeding.py \
  --component-key EDF931F2-51CC-4A10-9002-128E7BF8067C \
  --report-dir /Users/aquarian247/Projects/AquaMind/scripts/migration/output/input_batch_migration/Stofnfiskur_Juni_24_2_2024 \
  --use-csv /Users/aquarian247/Projects/AquaMind/scripts/migration/data/extract

PYTHONPATH=/Users/aquarian247/Projects/AquaMind SKIP_CELERY_SIGNALS=1 \
python /Users/aquarian247/Projects/AquaMind/scripts/migration/tools/pilot_migrate_component_growth_samples.py \
  --component-key EDF931F2-51CC-4A10-9002-128E7BF8067C \
  --report-dir /Users/aquarian247/Projects/AquaMind/scripts/migration/output/input_batch_migration/Stofnfiskur_Juni_24_2_2024 \
  --use-csv /Users/aquarian247/Projects/AquaMind/scripts/migration/data/extract

PYTHONPATH=/Users/aquarian247/Projects/AquaMind SKIP_CELERY_SIGNALS=1 \
python /Users/aquarian247/Projects/AquaMind/scripts/migration/tools/pilot_migrate_component_mortality.py \
  --component-key EDF931F2-51CC-4A10-9002-128E7BF8067C \
  --report-dir /Users/aquarian247/Projects/AquaMind/scripts/migration/output/input_batch_migration/Stofnfiskur_Juni_24_2_2024 \
  --use-csv /Users/aquarian247/Projects/AquaMind/scripts/migration/data/extract

PYTHONPATH=/Users/aquarian247/Projects/AquaMind SKIP_CELERY_SIGNALS=1 \
python /Users/aquarian247/Projects/AquaMind/scripts/migration/tools/pilot_migrate_component_culling.py \
  --component-key EDF931F2-51CC-4A10-9002-128E7BF8067C \
  --report-dir /Users/aquarian247/Projects/AquaMind/scripts/migration/output/input_batch_migration/Stofnfiskur_Juni_24_2_2024 \
  --use-csv /Users/aquarian247/Projects/AquaMind/scripts/migration/data/extract

PYTHONPATH=/Users/aquarian247/Projects/AquaMind SKIP_CELERY_SIGNALS=1 \
python /Users/aquarian247/Projects/AquaMind/scripts/migration/tools/pilot_migrate_component_escapes.py \
  --component-key EDF931F2-51CC-4A10-9002-128E7BF8067C \
  --report-dir /Users/aquarian247/Projects/AquaMind/scripts/migration/output/input_batch_migration/Stofnfiskur_Juni_24_2_2024 \
  --use-csv /Users/aquarian247/Projects/AquaMind/scripts/migration/data/extract

# (treatments/lice/journal/harvest/feed-inventory also executed; no runtime changes)

# 5) Evidence reports
PYTHONPATH=/Users/aquarian247/Projects/AquaMind SKIP_CELERY_SIGNALS=1 \
python /Users/aquarian247/Projects/AquaMind/scripts/migration/tools/migration_counts_report.py \
  --batch-number "Stofnfiskur Juni 24 M95"

PYTHONPATH=/Users/aquarian247/Projects/AquaMind SKIP_CELERY_SIGNALS=1 \
python /Users/aquarian247/Projects/AquaMind/scripts/migration/tools/migration_semantic_validation_report.py \
  --component-key EDF931F2-51CC-4A10-9002-128E7BF8067C \
  --report-dir /Users/aquarian247/Projects/AquaMind/scripts/migration/output/input_batch_migration/Stofnfiskur_Juni_24_2_2024 \
  --use-csv /Users/aquarian247/Projects/AquaMind/scripts/migration/data/extract \
  --check-regression-gates \
  --output /tmp/stofn_juni24_m95_semantic_full.md \
  --summary-json /tmp/stofn_juni24_m95_semantic_full.json
```

## Hard Evidence

### A) Row-level root-cause signal (deterministic)
For all 12 Fry entry populations (hall `5 M Høll`):
- `conserved_count ~= 14,765` each
- status-at-start `~= 142,381` each
- ratio `status/conserved ~= 9.64`
- all flagged `external_mix=True`

Current default policy threshold in `pilot_migrate_component.py` is `10.0`; these rows stay on conservative counts under default and collapse Fry stage-entry.

### B) Stage-entry comparison

| run | Egg&Alevin | Fry | Parr | Smolt | Post-Smolt |
| --- | ---: | ---: | ---: | ---: | ---: |
| Post-fix default run (batch 449, documented baseline) | 1,760,038 | 196,889 | 299,007 | 104,377 | 42,547 |
| Canary `M95` (`--external-mixing-status-multiplier 9.5`, batch 452) | 1,760,038 | 1,708,576 | 299,007 | 104,377 | 42,547 |

Only Fry changed materially.

### C) Semantic gate state (M95)
- Source: `/tmp/stofn_juni24_m95_semantic_full.json`
- `regression_gates.passed = true`
- `zero_count_transfer_actions = 0`
- `non_bridge_zero_assignments = 0`
- `transition_alert_count = 0`

## Interpretation
1. The user-facing Egg->Fry collapse is reproducibly policy-driven in migration assignment materialization.
2. This canary does **not** resolve all lineage uncertainty:
   - bridge-aware transition accounting still reports large unresolved drops (`entry_window_reason=incomplete_linkage` at Fry->Parr), indicating remaining component-boundary uncertainty.
3. Uncertainty label:
   - It is still uncertain whether `9.5` is globally correct for all FW cohorts; this run verifies it changes this cohort deterministically and keeps gates green.

## Recommended Deterministic Next Step
1. Use the new pass-through option in `pilot_migrate_input_batch.py` for `--external-mixing-status-multiplier` (migration tooling only; implemented in this run).
2. Run a bounded FW20 sensitivity sweep on problematic batches only (`10.0` vs `9.5`) with DB wipe between runs and semantic/counts deltas captured.
3. Promote a default only if cohort-level evidence stays stable (no gate regressions, no transfer zero-count regressions, and no new positive transition deltas).

## Follow-up Status (same day)
- Completed bounded FW20 sensitivity sweep:
  - `/Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/migration/analysis_reports/2026-02-11/fw20_external_mixing_sensitivity_sweep_2026-02-11.md`
- Outcome: no tested FW20 cohort changed under `10.0 -> 9.5`; keep global default at `10.0` pending further cohort-specific evidence.
