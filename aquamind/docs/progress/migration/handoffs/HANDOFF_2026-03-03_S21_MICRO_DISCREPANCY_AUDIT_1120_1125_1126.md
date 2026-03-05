# HANDOFF 2026-03-03 - S21 micro-discrepancy audit (batch IDs 1120/1125/1126)

## Scope and objective
- Focus station: `S21 Viðareiði`.
- Target batches (migr_dev IDs): `1120` (`Bakkafrost S-21 jan 25`), `1125` (`StofnFiskur S-21 apr 25`), `1126` (`StofnFiskur S-21 juli25`).
- Objective: classify residual micro discrepancies and decide expected behavior vs true defect, using deterministic FishTalk vs AquaMind evidence up to cutoff `2026-01-22 23:59:59`.

## Read-only state reconfirmation
- Executed:
  - `python3 scripts/migration/tools/migration_counts_report.py`
  - `python3 scripts/migration/tools/migration_verification_report.py`
- Captured artifacts:
  - `scripts/migration/output/s21_micro_discrepancy_audit_20260303_100817/migration_counts_report_20260303_100817.txt`
  - `scripts/migration/output/s21_micro_discrepancy_audit_20260303_100817/migration_verification_report_20260303_100817.txt`
- Snapshot remains aligned with stabilized replay state (`batch=194`, `assignments=4484`, `workflows=88`, `actions=1082`).

## Audit artifact bundle
- Root: `scripts/migration/output/s21_micro_discrepancy_audit_20260303_100817`
- Key files:
  - `egg_input_reconciliation.csv`
  - `egg_to_fry_action_reconciliation.csv`
  - `raw_subtransfers_for_operations.csv`
  - `assignment_classification_5m_fry.csv`
  - `suspect_assignments_5m_fry.csv`
  - `container_parity_check.csv`
  - `summary.json`
  - `summary.md`

## Deterministic findings

### 1) Micro egg-input deltas (1120/1125 mismatch, 1126 spot-on)

From `egg_input_reconciliation.csv`:
- Non-zero rows vs `Ext_Inputs_v2.InputCount`: `9` rows across `2` batches (`1120`, `1125`).
- Max absolute delta: `148`.
- Aggregate delta: `-505`.
- Batch `1126`: zero deltas for all seven egg-origin rows.

Representative rows:

| Batch | Container | InputCount | First non-zero status | AquaMind assignment | Delta vs Input |
|---|---:|---:|---:|---:|---:|
| 1120 | R2 | 222503 | 222355 | 222355 | -148 |
| 1120 | R1 | 213884 | 213761 | 213761 | -123 |
| 1125 | R1 | 196705 | 196615 | 196615 | -90 |
| 1125 | R4 | 224715 | 224660 | 224660 | -55 |
| 1126 | R2 | 212630 | 212630 | 212630 | 0 |

Interpretation:
- For these egg populations, status at exact `population_start_time` is `0`.
- CSV-mode assignment logic then uses first non-zero status after start; in 1120/1125 that first non-zero snapshot is slightly below `InputCount`, in 1126 it is equal.
- `delta_vs_first_nonzero_status = 0` for every row.

Decision: **expected representation behavior**, not a migration defect.

---

### 2) Egg->Fry transfer reconciliation (FishTalk SubTransfers + exact-time source counts + AquaMind actions)

From `egg_to_fry_action_reconciliation.csv`:
- For all examined actions, `delta_action_vs_expected = 0`.
- `TransferAction.transferred_count` matches deterministic allocation from source counts and operation-edge shares.

From `raw_subtransfers_for_operations.csv`:
- Operations include direct `1.0` rows and chained SubTransfer sequences.
- For chained branches (notably R7 fan-out), direct root `SourcePopBefore -> DestPopAfter` rows are not the whole story; expanded lineage produces effective shares (captured in `TransferAction.notes`), which reconcile exactly to persisted counts.

Decision: **expected and correct** operation-edge materialization.

---

### 3) AquaMind-only assignment rows in 5M hall

From `assignment_classification_5m_fry.csv` / `suspect_assignments_5m_fry.csv`:

| Class | Rows | Batches | Decision | Notes |
|---|---:|---:|---|---|
| `synthetic_destination_row` | 18 | 3 | Expected representation artifact (non-defect) | Created to materialize transfer edges before destination population assignment map is available |
| `same_stage_supersession_artifact` | 54 | 3 | Expected representation artifact (non-defect) | Short-lived same-day zero rows (superseded holders) retained for lineage history |
| `bridge_placeholder` | 0 | 0 | N/A | None in this slice |
| `legitimate_operation_edge_materialization` | 20 | 3 | Expected | Canonical non-zero destination rows |

Container parity check (`container_parity_check.csv`):
- For all 18 `(batch, 5M container)` pairs, `sum(transferred_count) == max assignment population_count` (delta `0` everywhere).
- Downstream impact flag: `False`.

Decision: visible duplicates are **representation artifacts**, not conservation failures.

## Expected-vs-defect decisions (final)
- Micro egg-input deltas in 1120/1125: **Expected** (first non-zero status fallback semantics).
- Synthetic destination rows: **Expected artifact** in current replay order (UI-noisy, data-conservative).
- Same-stage supersession zero rows: **Expected artifact** (history-preserving supersession handling).
- Legitimate operation-edge rows: **Expected canonical behavior**.

## Code fix assessment
- **No code patch applied** in this handoff.
- Reason: no evidence of data-conservation or downstream lifecycle-impact defect in this slice.

Optional post-freeze polish (not required for correctness):
- Add a targeted migration reconciliation step that folds synthetic destination assignments into later mapped population assignments when `(component_key, dest_population_id)` resolves, to reduce history noise.

## Freeze-readiness recommendation
- **Freeze-ready (GO) for data correctness** for this discrepancy family.
- Residual risk: low, UI/history readability only (synthetic + supersession artifacts remain visible in assignment history).
- No minimal rerun required because no patch was introduced.

