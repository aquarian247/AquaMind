# HANDOFF 2026-03-02 - FW mapped-scope regression stabilization findings

## Why this handoff exists
- Continuation of FW mapped-scope stabilization with focus on:
  - one-stage batch regression signals,
  - large `MIX-*` batch volume,
  - recovering current A/B/C/D-equivalent gate status on `migr_dev`.

## Executive result
- **A/B/C/D-equivalent gate board recovered and clean** after unblocking missing component mappings.
- **MIX proliferation is expected by current backfill design** (1 mixed batch/event per qualified transfer action), not random inflation.
- **Non-MIX one-stage signal is mixed**:
  - partly expected (seed/same-stage-only flows),
  - partly a stage representation mismatch (`batch.lifecycle_stage` vs assignment-stage coverage), including `Stofnfiskur Juni 24`.
- Freeze-readiness risk is **medium** (not red), with one reporting/interpretation gap that should be addressed explicitly before final signoff.

---

## 1) Reconfirmed DB baseline state (before making any data changes)

Commands run:
- `python3 scripts/migration/tools/migration_counts_report.py --prefix ""`
- `python3 scripts/migration/tools/migration_verification_report.py`

Observed baseline snapshot (matches prior handoff):
- `batch_batch=189`
- `batch_transferaction=280`
- `batch_batchcontainerassignment=569`
- `migration_support_externalidmap=4137`
- Verification required-table empties unchanged for this profile:
  - `infrastructure_area=0`
  - `health_licecount=0`
  - `health_journalentry=0`
  - `environmental_environmentalreading=0`

Stage-coverage baseline (scope state):
- `MIX-*`: `169/169` one-stage
- non-`MIX` scoped batches: `8/20` one-stage
- combined scoped total: `177/189` one-stage

---

## 2) Recovered fresh A/B/C/D-equivalent taxonomy on current `migr_dev`

### Initial blocker
Regression check initially blocked (`focus_mapped_regression_retry_20260302_140630.txt`) by missing `ExternalIdMap` for 5 component keys:
- `FA8EA452-AFE1-490D-B236-0150415B6E6F`
- `B884F78F-1E92-49C0-AE28-39DFC2E18C01`
- `5DC4DA59-A891-4BBB-BB2E-0CC95C633F20`
- `81AC7D6F-3C81-4F36-9875-881C828F62E3`
- `251B661F-E0A6-4AD0-9B59-40A6CE1ADC86`

### Unblock action applied
Executed targeted component migrations (CSV mode, `fw_default`) for those 5 keys only:
- `focus_mapped_component_unblock_FA8EA452-AFE1-490D-B236-0150415B6E6F_20260302_140756.txt`
- `focus_mapped_component_unblock_B884F78F-1E92-49C0-AE28-39DFC2E18C01_20260302_140756.txt`
- `focus_mapped_component_unblock_5DC4DA59-A891-4BBB-BB2E-0CC95C633F20_20260302_140756.txt`
- `focus_mapped_component_unblock_81AC7D6F-3C81-4F36-9875-881C828F62E3_20260302_140756.txt`
- `focus_mapped_component_unblock_251B661F-E0A6-4AD0-9B59-40A6CE1ADC86_20260302_140756.txt`

### Fresh regression gate rerun
- `focus_mapped_regression_retry_20260302_142324.txt`
- Exit code `0`, cohort summary written to:
  - `aquamind/docs/progress/migration/analysis_reports/2026-02-06/semantic_validation_pilot_cohort_2026-03-02.md`

### Fresh A/B/C/D-equivalent counts
Using current pilot regression taxonomy dimensions from the cohort summary:
- **A (positive transition alerts): 0**
- **B (zero-count transfer actions): 0**
- **C (non-bridge zero assignments): 0**
- **D (regression gate failures/components failed): 0**

Interpretation:
- No regression-gate rise vs prior concern for this pilot set after mapping unblock.

---

## 3) MIX proliferation interpretation (expected vs regression)

Validation evidence:
- `focus_mapped_mix_validation_20260302_144111.txt`

Observed:
- `transfer_actions_total=280`
- `transfer_actions_allow_mixed_true=169`
- `mix_batches=169`
- `mix_events=169`
- `mix_event_components=473`
- `mix_batches_without_action=0`

Conclusion:
- The `169 MIX` count is **exactly explained** by backfill contract in `pilot_backfill_transfer_mix_events.py`:
  - one mixed batch named `MIX-FTA-<action_id>` per qualified action,
  - one mix event per qualified action,
  - `allow_mixed=True` set on those same actions.
- Current MIX expansion is **design-consistent behavior**, not evidence of accidental duplicate inflation.

---

## 4) Non-MIX lifecycle-stage regression analysis

Diagnostic artifact:
- `focus_mapped_nonmix_stage_diagnostics_20260302_144111.txt`

### Non-MIX one-stage count
- Scoped non-MIX (`not MIX-*`, `not FT-*`): `8/20` one-stage.

One-stage scoped batches:
- `24Q1 LHS ex-LC` (Parr-only)
- `AquaGen juni 25` (Egg&Alevin-only assignments, current stage Fry)
- `Bakkafrost S-21 okt 25` (Fry-only)
- `Benchmark Gen. Septembur 2024` (Egg&Alevin-only assignments, current stage Fry)
- `SF nov 2025` (Fry-only)
- `Stofnfiskur Aug 23` (Egg&Alevin-only assignments, current stage Fry)
- `Stofnfiskur Juni 24` (Egg&Alevin-only assignments, current stage Parr)
- `Stofnfiskur S21 okt 25` (Fry-only)

### Why these are one-stage
Two clear buckets:
1) **Expected single-stage cohorts / no cross-stage transfer evidence**
   - no transfer workflows or same-stage-only (`Fry->Fry`, `Egg->Egg`) transfer actions.
2) **Current-stage vs assignment-stage mismatch**
   - 4 scoped batches where `batch.lifecycle_stage` is more advanced than assignment coverage:
     - `AquaGen juni 25`
     - `Benchmark Gen. Septembur 2024`
     - `Stofnfiskur Aug 23`
     - `Stofnfiskur Juni 24`

### Deep-dive: `Stofnfiskur Juni 24` inconsistency
Artifacts:
- `focus_mapped_juni24_component_dryrun_20260302_143634.txt`
- `focus_mapped_juni24_deepdive_20260302_144111.txt`

Facts:
- Batch state: `COMPLETED`, current stage `Parr`, dates `2024-06-05 -> 2024-08-14`.
- Transfer workflow coverage for this batch:
  - only one workflow, stage `Egg&Alevin -> Egg&Alevin`, `12` actions.
- Assignment coverage:
  - `24` assignments total, all `Egg&Alevin`, all inactive.
  - timeline split:
    - `12` rows `2024-06-05 -> 2024-08-14`
    - `12` synthetic destination rows `2024-08-14 -> 2024-08-14`
- Dry-run component diagnostics show:
  - hall fallback hint resolves `S03 NORDTOFTIR / KLEKING -> Parr`,
  - all active-container candidates filtered by later outside-component holders (`12`).

Root-cause interpretation:
- Batch-level stage (`Parr`) and assignment-stage coverage (`Egg&Alevin`) are produced by different materialization paths:
  - batch stage from component-level lifecycle selection/fallback,
  - assignment coverage dominated by transfer-stage assignment materialization/backfill (and synthetic destination assignments), which remained Egg&Alevin.
- This is primarily a **stage-history representation mismatch**, not a random data-corruption signal.

---

## 5) Changes made in this session

Data changes:
- Added missing component mappings via targeted `pilot_migrate_component.py` runs for the 5 blocked keys.

No code changes applied:
- No migration-tool logic modified in this run.
- No full replay performed.

Current DB note:
- After targeted unblock migrations, DB now includes `5` additional `FT-*` batches (total batch count `194`).
- Scoped analysis in this handoff keeps FW mapped replay lens on `MIX-* + non-FT non-MIX` (`169 + 20`).

---

## 6) Ranked fix plan (smallest-safe first)

1) **P1 - Reporting fix (lowest risk, recommended first)**
   - Update `migration_verification_report.py` stage section to show both:
     - assignment-stage coverage,
     - whether current batch stage is contained in assignment coverage.
   - This removes false "regression" alarms for known representation mismatches.

2) **P2 - Targeted transfer-stage sync guard (medium risk, canary first)**
   - In `pilot_migrate_component_transfers.py`, gate/flag source-stage backfill for departed source assignments when it collapses higher component lifecycle evidence.
   - Re-run only affected keys (start with `Stofnfiskur Juni 24`) and compare semantic gates.

3) **P3 - MIX policy tuning (optional, product decision)**
   - Keep current 1:1 action-based `MIX-FTA-*` lineage for audit fidelity, unless freeze policy wants condensed MIX entities.
   - If condensed view is needed, prefer reporting-layer aggregation first (not data-layer mutation).

---

## 7) Freeze-readiness risk recommendation

Recommendation:
- **Conditional GO (amber)** for FW freeze parity on current evidence:
  - pilot regression gate board recovered and clean (`A/B/C/D-equivalent all zero`),
  - MIX growth explained by deterministic backfill contract, not uncontrolled inflation,
  - remaining risk is interpretation/visibility around lifecycle stage representation mismatch in non-MIX one-stage outliers.

Must-call-out residual risk:
- stage-coverage output currently conflates assignment-history stage materialization with current batch stage semantics.
- This should be explicitly documented in freeze note (and ideally patched via P1).

---

## 8) Artifacts produced in this session

- `scripts/migration/output/focus_mapped_regression_retry_20260302_140630.txt`
- `scripts/migration/output/focus_mapped_component_unblock_FA8EA452-AFE1-490D-B236-0150415B6E6F_20260302_140756.txt`
- `scripts/migration/output/focus_mapped_component_unblock_B884F78F-1E92-49C0-AE28-39DFC2E18C01_20260302_140756.txt`
- `scripts/migration/output/focus_mapped_component_unblock_5DC4DA59-A891-4BBB-BB2E-0CC95C633F20_20260302_140756.txt`
- `scripts/migration/output/focus_mapped_component_unblock_81AC7D6F-3C81-4F36-9875-881C828F62E3_20260302_140756.txt`
- `scripts/migration/output/focus_mapped_component_unblock_251B661F-E0A6-4AD0-9B59-40A6CE1ADC86_20260302_140756.txt`
- `scripts/migration/output/focus_mapped_regression_retry_20260302_142324.txt`
- `scripts/migration/output/focus_mapped_juni24_component_dryrun_20260302_143634.txt`
- `scripts/migration/output/focus_mapped_nonmix_stage_diagnostics_20260302_144111.txt`
- `scripts/migration/output/focus_mapped_mix_validation_20260302_144111.txt`
- `scripts/migration/output/focus_mapped_juni24_deepdive_20260302_144111.txt`
- `aquamind/docs/progress/migration/analysis_reports/2026-02-06/semantic_validation_pilot_cohort_2026-03-02.md`

