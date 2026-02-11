# Migration Handoff (2026-02-10 Runtime Separation + Validator State)

## Scope of this handoff
- Continue from `HANDOFF_2026-02-06_FOLLOWUP.md` and its 2026-02-09 addendum.
- Capture the current migration validation state after bridge-aware stage sanity updates.
- Record the explicit architectural boundary decision: migration/FishTalk logic must not be embedded in AquaMind runtime application code.

## Executive decisions (2026-02-10)

1. **Runtime API must remain FishTalk-agnostic.**
   - AquaMind application endpoints must not parse FishTalk-only identifiers (`PopulationID` in notes) or depend on FishTalk extract CSVs.
   - Migration-specific classification and bridge logic belongs in migration tooling and reports.

2. **Primary migration acceptance = scripts/reports, not GUI.**
   - GUI review remains important for user confidence but is secondary.
   - Canonical acceptance should come from semantic validation + counts checks + regression gates.

3. **Use clean DB resets for trial reruns.**
   - Always wipe `aquamind_db_migr_dev` before comparative trial runs to avoid stale artifacts.

## Current code state (authoritative)

### A) Migration validation/tooling state
Files:
- `scripts/migration/tools/migration_semantic_validation_report.py`
- `scripts/migration/tools/migration_pilot_regression_check.py`

Current behavior in validator:
- Temporary bridge population classification from FishTalk extracts is implemented in tooling.
- Stage sanity supports bridge-aware transition basis and entry-window fallback.
- Regression gates are implemented (positive delta alerts, zero-count transfer actions, non-bridge zero assignments threshold).

### B) Transfer replay noise control state
Files:
- `scripts/migration/tools/pilot_migrate_component_transfers.py`
- `scripts/migration/tools/pilot_migrate_input_batch.py`

Current behavior:
- Transfer replay supports `--skip-synthetic-stage-transitions`.
- Input-batch runner defaults to skipping synthetic stage transitions (legacy behavior is opt-in via `--include-synthetic-stage-transitions`).

### C) Runtime API separation state
File:
- `apps/batch/api/viewsets/assignments.py`

Current behavior:
- Batch-filtered assignment endpoint remains runtime/source agnostic:
  - `GET /api/v1/batch/container-assignments/?batch=<id>` returns lifecycle-ordered assignment history.
- No FishTalk note parsing and no migration CSV dependency in this viewset.

Validation:
- `python manage.py test apps.batch.tests.api.test_assignment_viewset --keepdb`
- Result: **12 tests, PASS**.

## Reports regenerated/validated

### SF NOV 23
Report:
- `aquamind/docs/progress/migration/analysis_reports/2026-02-06/semantic_validation_sf_nov_23_2026-02-06.md`

Key outcomes:
- Fishgroup classification:
  - temporary bridge fishgroups: `32`
  - real stage-entry fishgroups: `64`
  - temporary bridge populations: `32`
- Transition result:
  - `Parr -> Post-Smolt` = `271,029 -> 271,029`, delta `0`, basis `Fishgroup bridge-aware`.
- Regression gates: PASS.

### Stofnfiskur S-21 nov23 (batch id 358)
Report:
- `aquamind/docs/progress/migration/analysis_reports/2026-02-06/semantic_validation_stofnfiskur_s21_nov23_2026-02-06.md`

Key outcomes:
- Fishgroup classification:
  - temporary bridge fishgroups: `165`
  - real stage-entry fishgroups: `24`
  - temporary bridge populations: `165`
- Transition results:
  - `Egg&Alevin -> Fry` delta `0` (bridge-aware)
  - `Fry -> Parr` delta `-65,711` (entry-window fallback, incomplete linkage)
  - `Parr -> Smolt` delta `0` (bridge-aware)
  - `Smolt -> Post-Smolt` delta `-171,041` (entry-window fallback, incomplete linkage)
- Regression gates: PASS.

### Pilot cohort summary
Report:
- `aquamind/docs/progress/migration/analysis_reports/2026-02-06/semantic_validation_pilot_cohort_2026-02-10.md`

Key outcomes:
- Components checked: `5`
- Total transitions: `11`
- Bridge-aware transitions: `4` (`36.4%`)
- Entry-window transitions: `7` (`63.6%`)
- Positive transition alerts (without mixed-batch rows): `0`
- Zero-count transfer actions: `0`
- Overall cohort gate: FAIL due to high non-bridge zero assignments in:
  - `Benchmark Gen. Juni 2024`
  - `Summar 2024`
  - `Vár 2024`

## Station guardrail and replay integrity status

- Station preflight + guard (`--expected-site`) is present in:
  - `scripts/migration/tools/pilot_migrate_input_batch.py`
  - `scripts/migration/tools/pilot_migrate_component.py`
- Assignment population replay synchronization is present for removals:
  - `resolved_count = baseline_population_count - (mortality + culling + escapes totals)`
  - Implemented in mortality/culling/escapes scripts with baseline stored during component migration.

## Reproduction commands (clean trial run)

### 1) Wipe migration DB
```bash
PYTHONPATH=/Users/aquarian247/Projects/AquaMind \
SKIP_CELERY_SIGNALS=1 \
python scripts/migration/clear_migration_db.py
```

### 2) Run one input batch with station guard
```bash
PYTHONPATH=/Users/aquarian247/Projects/AquaMind \
SKIP_CELERY_SIGNALS=1 \
python scripts/migration/tools/pilot_migrate_input_batch.py \
  --batch-key "SF NOV 23|5|2023" \
  --expected-site "FW22 Applecross" \
  --use-csv scripts/migration/data/extract
```

### 3) Regenerate semantic validation (single batch)
```bash
python scripts/migration/tools/migration_semantic_validation_report.py \
  --component-key FA8EA452-AFE1-490D-B236-0150415B6E6F \
  --report-dir scripts/migration/output/input_batch_migration/SF_NOV_23_5_2023 \
  --use-csv scripts/migration/data/extract \
  --stage-entry-window-days 2 \
  --check-regression-gates \
  --max-non-bridge-zero-assignments 2 \
  --output aquamind/docs/progress/migration/analysis_reports/2026-02-06/semantic_validation_sf_nov_23_2026-02-06.md
```

### 4) Regenerate pilot cohort summary
```bash
python scripts/migration/tools/migration_pilot_regression_check.py \
  --analysis-dir aquamind/docs/progress/migration/analysis_reports/2026-02-06 \
  --report-dir-root scripts/migration/output/input_batch_migration \
  --use-csv scripts/migration/data/extract \
  --stage-entry-window-days 2 \
  --max-non-bridge-zero-assignments 2
```

## Open risks / unresolved work

1. **High non-bridge zero assignments** remain for Benchmark/Summar/Vár and still fail cohort gates.
2. **Incomplete linkage** remains in some S21 transitions, forcing entry-window fallback on those transitions.
3. **GUI lifecycle cards can still mislead if interpreted as migration truth source.**
   - Treat script outputs as canonical migration acceptance signal.

## Recommended next work package (for next agent)

1. Enforce a strict clean-run protocol in every comparative trial (wipe + replay + semantic + counts).
2. For each failing component (Benchmark/Summar/Vár), isolate non-bridge zero assignment rows:
   - identify source population IDs,
   - prove whether each row is truly operationally material or should be bridge-classified,
   - update migration replay classification only in migration tooling.
3. Increase bridge-aware transition coverage where linkage is complete and valid, while preserving fallback behavior for incomplete linkage.
4. Produce a migration acceptance bundle per component:
   - counts report,
   - semantic report,
   - regression gate outcome,
   - short evidence note for any remaining fallback/exception.

## Guardrails for next agent

- Do not add FishTalk-specific logic to AquaMind runtime application endpoints.
- Keep FW and Sea separation policy unchanged unless new canonical linkage evidence is provided.
- Keep weight policy unchanged: `Ext_WeightSamples_v2` only; `AvgWeight` interpreted as grams.
- Keep docs factual; no inferred claims without extract/report evidence.

