# Marine Guarded Linked-FW-In-Scope Completion (2026-02-18)

## Scope

Executed all four `linked_fw_in_scope` cohorts from:

- `aquamind/docs/progress/migration/analysis_reports/2026-02-18/fwsea_marine_ingress_candidate_matrix_2026-02-18.marine_linkage_age_tiers.csv`

Guardrails enforced for all runs:

- no synthetic transfer-workflow generation
- `planning.transfer_workflow` remains source-backed only
- no `StageTransitionEnvironmental` without real transfer workflow id
- lifecycle history carried via assignments/state timelines

> Update: this guarded-wave snapshot was later superseded by linked integrity remediation for batches `553-556`.
> Latest status is in `aquamind/docs/progress/migration/analysis_reports/2026-02-18/marine_linked_batch_integrity_regression_fix_r2_553_556_2026-02-19.md`.
> (The earlier intermediary report remains at `aquamind/docs/progress/migration/analysis_reports/2026-02-18/marine_linked_batch_integrity_remediation_553_556_2026-02-18.md`.)

## Wave execution status

| Sea batch key | Included FW seed batch keys | Component key | Migration scripts | Semantic gates |
| --- | --- | --- | --- | --- |
| `Vetur 2024|1|2024` | `Benchmark Gen. Septembur 2024|3|2024` | `152E8378-B673-4C7F-8EF9-1933627F4143` | PASS (`11/11`) | PASS (post-wave refreshed) |
| `Vetur 2024/2025|1|2024` | `StofnFiskur okt. 2024|3|2024`; `Bakkafrost S-21 sep24|3|2024`; `Stofnfiskur Nov 2024|5|2024` | `73B6F838-24D5-4F5D-A1A4-CC57DF375D05` | PASS (`11/11`) | PASS |
| `Heyst 2023|1|2024` | `Bakkafrost Okt 2023|4|2023` | `33BD2243-57BE-437E-B026-BACBFDA640BB` | PASS (`11/11`) | PASS |
| `Vetur 2025|1|2025` | `Stofnfiskur Des 24|4|2024`; `Benchmark Gen. Desembur 2024|4|2024` | `04A3BDDC-344A-4CDE-A6D2-2184FA7F3870` | PASS (`11/11`) | PASS |

## Regression gate ledger

All four semantic summaries report:

- `regression_gates.passed = true`
- `transfer_actions.total_count = 0`
- `transfer_actions.zero_count = 0`
- `regression_gates.non_bridge_zero_assignments = 0`
- `regression_gates.transition_alert_count = 0`

## Current per-batch migrated counts (snapshot)

From:

- `python3 scripts/migration/tools/migration_counts_report.py --batch-number "Vetur 2024" --batch-number "Vetur 2024/2025" --batch-number "Heyst 2023" --batch-number "Vetur 2025"`

| Batch | Assignments | Creation actions | Workflows | Actions | Feeding | Mortality | Treatments | Lice |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `Heyst 2023` | 6 | 4 | 0 | 0 | 1157 | 3207 | 199 | 523 |
| `Vetur 2024` | 586 | 567 | 0 | 0 | 2027 | 8066 | 148 | 549 |
| `Vetur 2024/2025` | 50 | 4 | 0 | 0 | 2167 | 3829 | 404 | 838 |
| `Vetur 2025` | 27 | 7 | 0 | 0 | 1812 | 3114 | 331 | 710 |

## Note on overlap and refresh

`Vetur 2024/2025` re-attributed a subset of shared stitched lifecycle rows previously observed in `Vetur 2024`.  
`Vetur 2024` semantic validation was re-run after subsequent waves to confirm final-state gate integrity:

- `scripts/migration/output/input_batch_migration/Vetur_2024_1_2024/semantic_validation_Vetur_2024_1_2024.post_wave_refresh.md`
- `scripts/migration/output/input_batch_migration/Vetur_2024_1_2024/semantic_validation_Vetur_2024_1_2024.post_wave_refresh.json`

## Remaining queue

- `linked_fw_in_scope`: complete (`4/4`)
- `unlinked_sea`: `30` cohorts remain held for operator confirmation/corroboration before migration promotion.
