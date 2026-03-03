# HANDOFF 2026-03-02 - FW scope descendant replay stabilized, next: micro-discrepancy audit

## Why this handoff exists
- We recovered mapped FW scope lifecycle fidelity by replaying all scoped batches with transfer-rich descendant expansion.
- We now need a focused micro-discrepancy pass on:
  - small egg-input count mismatches (observed spot checks in `S21 Viðareiði`),
  - suspicious container assignments visible in AquaMind but not obvious in FishTalk UI.

---

## Executive result
- Scope replay is now stable and repeatable with:
  - `--expand-subtransfer-descendants`
  - `--transfer-edge-scope internal-only`
- Full mapped scope completed in 4 chunks (`20/20` success, no chunk failures).
- Pilot semantic regression cohort remains `PASS` after replay.
- Stage coverage for completed FW scoped batches is now mostly realistic:
  - completed batches: `8`
  - completed with `>=4` stages: `7`
  - completed with `<4` stages: `1` (`24Q1 LHS ex-LC`, Parr-only)

---

## What was changed

### Code / behavior hardening
- `scripts/migration/tools/pilot_migrate_input_batch.py`
  - scope-mode child invocations now forward:
    - `--expand-subtransfer-descendants`
    - `--transfer-edge-scope`
    - `--dry-run`
  - This removed a silent scope-mode drift where descendant expansion was requested but not actually applied to child runs.

### Documentation updates
- `aquamind/docs/progress/migration/DATA_MAPPING_DOCUMENT.md` (v5.6, 2026-03-02)
- `aquamind/docs/progress/migration/MIGRATION_CANONICAL.md`
- `aquamind/docs/progress/migration/MIGRATION_BEST_PRACTICES.md`
- `scripts/migration/tools/README.md`
- `aquamind/docs/progress/migration/README.md`

Key policy now documented:
- Transfer-rich scope/chunk replays must run with descendant expansion + internal-only edge scope.
- Lifecycle progression default basis (`stage_entry`) is entry semantics, not peak concurrent stock semantics.

---

## Replay execution details

### Scope files
- `scripts/migration/output/input_stitching/scope_fw78_fwonly_u30_mapped_faroe_fw22_fw13_chunk1.csv`
- `scripts/migration/output/input_stitching/scope_fw78_fwonly_u30_mapped_faroe_fw22_fw13_chunk2.csv`
- `scripts/migration/output/input_stitching/scope_fw78_fwonly_u30_mapped_faroe_fw22_fw13_chunk3.csv`
- `scripts/migration/output/input_stitching/scope_fw78_fwonly_u30_mapped_faroe_fw22_fw13_chunk4.csv`
- `scripts/migration/output/input_stitching/scope_fw78_fwonly_u30_mapped_faroe_fw22_fw13_batch_keys.csv`

### Chunk logs
- `scripts/migration/output/replay_scope_chunk1_descendants_20260302_165422.txt`
- `scripts/migration/output/replay_scope_chunk2_descendants_20260302_171412.txt`
- `scripts/migration/output/replay_scope_chunk3_descendants_20260302_173320.txt`
- `scripts/migration/output/replay_scope_chunk4_descendants_20260302_175456.txt`

### Post-run checks
- Regression gate check:
  - `scripts/migration/output/replay_scope_postrun_regression_check_20260302_181310.txt`
  - cohort summary: `aquamind/docs/progress/migration/analysis_reports/2026-02-06/semantic_validation_pilot_cohort_2026-03-02.md`
  - result: `PASS`
- Counts:
  - `scripts/migration/output/replay_scope_all_chunks_counts_20260302_182109.txt`
- Verification:
  - `scripts/migration/output/replay_scope_all_chunks_verification_20260302_182125.txt`

---

## Current scoped-stage distribution snapshot

From scoped stage-coverage query after replay:
- `TOTAL=20`, `COMPLETED=8`, `ACTIVE=12`
- `COMPLETED_GE4=7`, `COMPLETED_LT4=1`
- `ACTIVE_LE2=4`, `ACTIVE_GE4=5`

`COMPLETED` with `<4` stages:
- `24Q1 LHS ex-LC` (Parr-only)

---

## Residual concerns to investigate next

1) **Micro egg-input count discrepancies**
- User observed slight count mismatches at egg-input timing in `S21`.
- Need deterministic reconciliation between:
  - FishTalk operation/action transfer counts,
  - status snapshots at exact timestamps,
  - migration tie-break and conservation distribution behavior.

2) **AquaMind-only container assignments**
- Some assignment rows appear in AquaMind but are not obvious in FishTalk UI.
- Candidate causes to classify:
  - bridge/placeholder rows,
  - same-stage supersession artifacts,
  - synthetic destination rows,
  - strict operation-edge reconstruction where FishTalk UI collapses detail.

---

## Next-agent prompt (recommended)

You are taking over AquaMind FW migration stabilization for a micro-discrepancy audit.

Context:
- Full mapped FW scope replay (20 batches) was rerun successfully with:
  - `--expand-subtransfer-descendants`
  - `--transfer-edge-scope internal-only`
- Regression cohort check is PASS.
- Major lifecycle collapse regression is resolved.
- Remaining issues are subtle:
  1) slight egg-input count mismatches (spot-checked in S21),
  2) container assignments visible in AquaMind but not obvious in FishTalk UI.

Primary objective:
- Determine whether these residual differences are:
  - expected representation differences, or
  - true migration defects requiring code changes.

Required approach:
1. Reconfirm current DB state (read-only):
   - `migration_counts_report.py`
   - `migration_verification_report.py`
2. Focus station: `S21 Viðareiði`.
3. Build a deterministic per-batch reconciliation workbook/table for 2-4 suspect batches:
   - at egg-input transition points, compare:
     - FishTalk source counts (`SubTransfers`, relevant status snapshots),
     - AquaMind `TransferAction.transferred_count`,
     - destination assignment counts and dates.
4. For each suspicious AquaMind assignment row not obvious in FishTalk UI, classify into one of:
   - bridge/placeholder,
   - synthetic destination,
   - same-stage supersession residue,
   - valid operation-edge materialization.
5. Quantify discrepancy classes:
   - counts affected,
   - batches affected,
   - whether downstream lifecycle totals are impacted.
6. If fixes are needed:
   - implement the smallest safe change,
   - rerun only minimal affected scope (batch-level or tiny chunk),
   - re-run semantic regression check.

Deliverables:
- A discrepancy taxonomy with counts and examples.
- For each class: expected behavior vs regression.
- If code changed: exact patch list + before/after evidence.
- Updated handoff in this folder with artifact paths and recommendation on freeze-readiness risk.

Constraints:
- Keep replay mode aligned with stabilized contract:
  - descendant expansion ON
  - transfer edge scope internal-only
- Avoid monolithic reruns; use targeted reruns.

---

## Notes
- Lifecycle progression chart interpretation:
  - default API basis is `stage_entry` (first positive row per container/stage),
  - not peak-concurrent stock; use assignment timeline analytics for stock maxima.
