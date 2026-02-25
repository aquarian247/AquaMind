# HANDOFF 2026-02-18: Marine Ingress Linkage Pilot (FW->Sea)

> Update (2026-02-19): Linked batch regression fixes, component stale-state
> pruning behavior, and realistic asset reference-pack compatibility are
> captured in
> `HANDOFF_2026-02-19_LINKED_MARINE_REGRESSION_FIX_AND_REALISTIC_ASSET_COMPAT.md`.

## Scope

Continue migration from FW closure into marine-entry by implementing and executing FW->Sea linkage with the required evidence ladder:

1. canonical first (`Ext_Transfers` + `SubTransfers` lineage),
2. temporal+geography provisional fallback only when canonical S*->A* is absent,
3. explicit exclusion of `L*->S*`, FW->FW, and Marine->Marine from FW->Sea ingress inference.

## Constraints retained

- Backup horizon/cutoff: `2026-01-22`
- Migration profile baseline: `fw_default`
- Runtime remains FishTalk-agnostic
- Source-specific behavior stays in migration tooling/validation/reporting

## Legacy transfer-workflow migration guardrails

Transport workflows are optional for migrated legacy data. Migration behavior is now aligned to:

1. Do not synthesize `BatchTransferWorkflow` / `TransferAction` records just to force FW->Sea linkage.
2. A migrated batch may legitimately have zero transfer workflows.
3. Keep `planning.transfer_workflow` as `NULL` unless an explicit source-backed mapping exists.
4. Do not create `StageTransitionEnvironmental` rows without a real `batch_transfer_workflow` id.
5. Prefer canonical lifecycle history via `BatchContainerAssignment` and stage timelines; missing transfer events are expected.
6. For infrastructure containers, keep exactly one location context (`hall` OR `area` OR `carrier`), with `carrier` optional.

## What was implemented

Added tooling script:

- `scripts/migration/tools/fwsea_marine_ingress_matrix.py`

The tool computes and persists:

- FW terminal depletion timestamp `X` per FW endpoint using auditable signals:
  - `segment_end_time`,
  - `transfer_out_last_time`,
  - `culling_last_time`,
  - `mortality_last_time`,
  - `status_zero_after_nonzero_time`.
- Sea fill/start timestamp `Y` per sea endpoint using auditable signals:
  - `segment_start_time`,
  - `status_first_nonzero_time`,
  - `fw_transfer_in_first_time`.
- Candidate matrix rows with explicit evidence provenance and classifications.

## Linkage results (this run)

### Canonical scan

- Canonical FW-sourced rows from `Ext_Transfers`: `212,399`
- Canonical S*->A* rows: `0`
- Canonical classification split:
  - `reverse_flow_fw_only`: `211,978` (FW->FW)
  - `unclassified_nonzero_candidate`: `421`
- Interpretation: no canonical S*->A* ingress edges were present in the current extract for actionable marine entry.

### Provisional fallback (`[X, X+2]`, same geography, S*->A*)

- Provisional rows: `3,958`
- Boundary `S*->A*`: `true` for all provisional rows
- Provisional classification split:
  - `true_candidate`: `2,138`
  - `sparse_evidence`: `1,820`

### Linkage-aware marine preflight gate (age + linkage tiers)

Implemented sea-cohort partitioning under the FW `<30 months` gate (`window start 2023-07-22`):

- Sea cohorts with sea-stage signal: `39`
- Sea cohorts under age gate: `34`
- Tier split:
  - `linked_fw_in_scope`: `4`
  - `linked_fw_out_of_scope`: `0`
  - `unlinked_sea`: `30`

Interpretation:

- We should not migrate all sea `<30 months` cohorts blindly.
- Only the `linked_fw_in_scope` tier is immediately wave-eligible by default.
- `unlinked_sea` remains a controlled hold queue for confirmation/corroboration.

## Marine pilot execution

Selected highest-confidence available pair with both FW and Sea component keys present in current `input_batches.csv`:

- FW component: `Stofnfiskur feb 2023|1|2023`
- Sea component: `Vár 2023|1|2023`
- Pair evidence rows in matrix: `7` (`2 true_candidate`, `5 sparse_evidence`)

Pilot run:

- Command family: `scripts/migration/tools/pilot_migrate_input_batch.py`
- Batch key: `Vár 2023|1|2023`
- Included FW batch: `Stofnfiskur feb 2023|1|2023`
- Flags: `--full-lifecycle --full-lifecycle-rebuild --allow-station-mismatch --skip-environmental --skip-feed-inventory`
- Result: **PASS** (`11/11` migration scripts completed)
- Migrated component key: `9B864694-C848-4627-BD4C-97516E71A4F7`

Semantic validation:

- Report: `marine_pilot_Var_2023_1_2023_semantic_validation_2026-02-18.md`
- Regression gates: **PASS**
- Overall semantic status: **PASS**
- Residual caveat: `Egg&Alevin -> Adult` remained `entry_window_reason=incomplete_linkage` (warning, not gate failure).

## Deterministic vs provisional linkage status

- Deterministically linked this run:
  - canonical FW->Sea S*->A* pairs: **none observed**
- Provisionally linked this run:
  - temporal+geography S*->A* candidate set (`3,958` rows), explicitly marked tooling evidence only.

## Operator confirmation queue (next focus)

Priority sparse/ambiguous component pairs needing confirmation before promotion:

1. `Stofnfiskur Sep 2021|3|2021 -> Vetur 2021/2022|1|2021`
2. `Stofnfiskur Aug 22|3|2022 -> Heyst 2022|1|2022`
3. `Stofnfiskur Juni 2023|2|2023 -> Heyst 2023|1|2023`
4. `Bakkafrost S-21 sep24|3|2024 -> Vetur 2024/2025|1|2024`
5. `Stofnfiskur Novembur 2022|4|2022 -> Heyst 2022|1|2022`

## Linked FW-in-scope wave completion (overnight continuation)

All `linked_fw_in_scope` cohorts from the age-aware tier gate were executed with guarded defaults:

- `--full-lifecycle --full-lifecycle-rebuild`
- explicit `--include-fw-batch` linkage seeds from the tier matrix
- `--allow-station-mismatch --skip-environmental --skip-feed-inventory`
- transfer guardrails active (no synthetic transfer workflows/actions)

| Sea batch key | Included FW batch keys | Migrated component key | Migration status | Semantic regression gates |
| --- | --- | --- | --- | --- |
| `Vetur 2024|1|2024` | `Benchmark Gen. Septembur 2024|3|2024` | `152E8378-B673-4C7F-8EF9-1933627F4143` | PASS (`11/11`) | PASS |
| `Vetur 2024/2025|1|2024` | `StofnFiskur okt. 2024|3|2024`; `Bakkafrost S-21 sep24|3|2024`; `Stofnfiskur Nov 2024|5|2024` | `73B6F838-24D5-4F5D-A1A4-CC57DF375D05` | PASS (`11/11`) | PASS |
| `Heyst 2023|1|2024` | `Bakkafrost Okt 2023|4|2023` | `33BD2243-57BE-437E-B026-BACBFDA640BB` | PASS (`11/11`) | PASS |
| `Vetur 2025|1|2025` | `Stofnfiskur Des 24|4|2024`; `Benchmark Gen. Desembur 2024|4|2024` | `04A3BDDC-344A-4CDE-A6D2-2184FA7F3870` | PASS (`11/11`) | PASS |

Guardrail check across all four waves:

- `TransferAction` total for migrated wave components: `0`
- `TransferAction` with `transferred_count <= 0`: `0`
- regression gate `non_bridge_zero_assignments_within_threshold`: PASS for all four

### Note on overlapping stitched populations

After running `Vetur 2024/2025`, some metric allocations in `Vetur 2024` changed (expected when stitched populations overlap and source-backed rows are re-attributed).  
To ensure end-state integrity, `Vetur 2024` semantic validation was re-run post-wave, and regression gates remained **PASS**.

## Remaining queue and next action

`linked_fw_in_scope` queue is now complete for this extract snapshot.

Remaining marine cohorts are in `unlinked_sea` (`30`) and remain intentionally blocked for operator confirmation/corroboration before migration promotion.

## Controlled provisional policy and first micro-wave

User-approved policy shift: `controlled_provisional`.

### Empirical FW-empty -> sea-fill timing learned so far

From provisional actionable matrix rows (`n=3,958`):

- `true_candidate` rule in tooling: `delta_days <= 1.0` with `fw_signal_count >= 2` and `sea_signal_count >= 2`.
- `sparse_evidence` rule in tooling: `delta_days <= 2.0` with at least one signal on each side.
- Observed distribution:
  - `true_candidate` (`n=2,138`): min `0.000`, p50 `0.522`, p90 `0.996`, max `1.000`
  - `sparse_evidence` (`n=1,820`): min `1.001`, p50 `1.678`, p90 `1.996`, max `2.000`
- Practical interpretation:
  - `<=1.0 day`: strongest FW->Sea temporal plausibility
  - `1.0-1.6 days`: plausible but weaker
  - `1.6-2.0 days`: sparse fallback only
  - `>2.0 days`: not used (no +3-day extension used in this run)

### Controlled provisional micro-wave executed

To limit blast radius and avoid same-batch key collisions, one unlinked cohort per distinct base batch was migrated:

| Cohort key | Component key | Migration | Regression gates | Transfer actions |
| --- | --- | --- | --- | ---: |
| `Vár 2025|1|2025|A83A9BFF-005B-4ED2-856D-8C7BDF37B54F` | `67677EF3-C7D0-431C-9BFE-2533D67EF523` | PASS (`11/11`) | PASS | 0 |
| `Heyst 2025|1|2025|EE44DDC3-ED36-4AC7-85F0-E338C8F2EA78` | `C78845D7-8A8D-4B31-968B-8127642563D7` | PASS (`11/11`) | PASS | 9 (source-backed SubTransfers) |
| `Summar 2025|1|2025|6E496E90-F34B-4CD7-84DC-164EC3473A5E` | `F12F9479-E82C-499C-99E4-4BB3F5EF991F` | PASS (`11/11`) | PASS | 12 (source-backed SubTransfers) |

Notes:

- Transfer actions above are canonical source-backed (not synthetic stage-transition backfill).
- Regression gate `no_zero_count_transfer_actions` remained PASS in all three.
- GUI/API health remained `200` after wave execution.

Operational remaining queue after this controlled micro-wave:

- `unlinked_sea`: `27` cohorts still pending.

## Linked marine integrity remediation update (553-556)

Follow-up remediation was executed for linked batches `553-556` to stabilize cross-batch assignment mapping and restore linked transfer history semantics under the approved linked-only synthetic stage-transition policy.

Current post-remediation state:

- Batch IDs remain stable: `553`, `554`, `555`, `556` unchanged.
- Linked transfer history is now present for all four linked batches.
- Semantic regression gates are `PASS` for all four linked batches (`linked_integrity_fix` summaries).
- Stage coverage now reflects source-supported linked membership after deterministic explicit FW stitching:
  - `Vetur 2024` (`553`): `Fry`, `Adult`
  - `Vetur 2024/2025` (`554`): `Egg&Alevin`, `Fry`, `Parr`, `Adult`
  - `Heyst 2023` (`555`): `Egg&Alevin`, `Fry`, `Adult`
  - `Vetur 2025` (`556`): `Egg&Alevin`, `Adult`

Additionally, infrastructure container migration now sources FishTalk overridden volume (`ContainerPhysics` ParameterID `6`) into `infrastructure.container.volume_m3` when present (for example `S24 / G Høll / G1 = 1200 m3`).

## Artifact index

- Candidate matrix artifacts:
  - `aquamind/docs/progress/migration/analysis_reports/2026-02-18/fwsea_marine_ingress_candidate_matrix_2026-02-18.csv`
  - `aquamind/docs/progress/migration/analysis_reports/2026-02-18/fwsea_marine_ingress_candidate_matrix_2026-02-18.md`
  - `aquamind/docs/progress/migration/analysis_reports/2026-02-18/fwsea_marine_ingress_candidate_matrix_2026-02-18.summary.json`
- Marine linkage age-tier gate artifacts:
  - `aquamind/docs/progress/migration/analysis_reports/2026-02-18/fwsea_marine_ingress_candidate_matrix_2026-02-18.marine_linkage_age_tiers.csv`
  - `aquamind/docs/progress/migration/analysis_reports/2026-02-18/fwsea_marine_ingress_candidate_matrix_2026-02-18.marine_linkage_age_tiers.md`
  - `aquamind/docs/progress/migration/analysis_reports/2026-02-18/fwsea_marine_ingress_candidate_matrix_2026-02-18.marine_linkage_age_tiers.summary.json`
- Pilot execution summary:
  - `aquamind/docs/progress/migration/analysis_reports/2026-02-18/marine_pilot_fwsea_run_summary_2026-02-18.md`
  - `aquamind/docs/progress/migration/analysis_reports/2026-02-18/marine_pilot_fwsea_run_summary_2026-02-18.json`
- Guarded wave completion summary:
  - `aquamind/docs/progress/migration/analysis_reports/2026-02-18/marine_guarded_linked_fw_in_scope_completion_2026-02-18.md`
- Controlled provisional micro-wave summary:
  - `aquamind/docs/progress/migration/analysis_reports/2026-02-18/marine_controlled_provisional_micro_wave_2026-02-18.md`
- Linked integrity remediation ledger:
  - `aquamind/docs/progress/migration/analysis_reports/2026-02-18/marine_linked_batch_integrity_remediation_553_556_2026-02-18.md`
- Pilot semantic validation:
  - `aquamind/docs/progress/migration/analysis_reports/2026-02-18/marine_pilot_Var_2023_1_2023_semantic_validation_2026-02-18.md`
  - `aquamind/docs/progress/migration/analysis_reports/2026-02-18/marine_pilot_Var_2023_1_2023_semantic_validation_2026-02-18.summary.json`
- Guarded linked FW-in-scope wave semantic validations:
  - `scripts/migration/output/input_batch_migration/Vetur_2024_1_2024/semantic_validation_Vetur_2024_1_2024.md`
  - `scripts/migration/output/input_batch_migration/Vetur_2024_1_2024/semantic_validation_Vetur_2024_1_2024.json`
  - `scripts/migration/output/input_batch_migration/Vetur_2024_1_2024/semantic_validation_Vetur_2024_1_2024.post_wave_refresh.md`
  - `scripts/migration/output/input_batch_migration/Vetur_2024_1_2024/semantic_validation_Vetur_2024_1_2024.post_wave_refresh.json`
  - `scripts/migration/output/input_batch_migration/Vetur_2024_2025_1_2024/semantic_validation_Vetur_2024_2025_1_2024.md`
  - `scripts/migration/output/input_batch_migration/Vetur_2024_2025_1_2024/semantic_validation_Vetur_2024_2025_1_2024.json`
  - `scripts/migration/output/input_batch_migration/Heyst_2023_1_2024/semantic_validation_Heyst_2023_1_2024.md`
  - `scripts/migration/output/input_batch_migration/Heyst_2023_1_2024/semantic_validation_Heyst_2023_1_2024.json`
  - `scripts/migration/output/input_batch_migration/Vetur_2025_1_2025/semantic_validation_Vetur_2025_1_2025.md`
  - `scripts/migration/output/input_batch_migration/Vetur_2025_1_2025/semantic_validation_Vetur_2025_1_2025.json`
  - `scripts/migration/output/input_batch_migration/Vetur_2024_1_2024/semantic_validation_Vetur_2024_1_2024.linked_integrity_fix.md`
  - `scripts/migration/output/input_batch_migration/Vetur_2024_1_2024/semantic_validation_Vetur_2024_1_2024.linked_integrity_fix.json`
  - `scripts/migration/output/input_batch_migration/Vetur_2024_2025_1_2024/semantic_validation_Vetur_2024_2025_1_2024.linked_integrity_fix.md`
  - `scripts/migration/output/input_batch_migration/Vetur_2024_2025_1_2024/semantic_validation_Vetur_2024_2025_1_2024.linked_integrity_fix.json`
  - `scripts/migration/output/input_batch_migration/Heyst_2023_1_2024/semantic_validation_Heyst_2023_1_2024.linked_integrity_fix.md`
  - `scripts/migration/output/input_batch_migration/Heyst_2023_1_2024/semantic_validation_Heyst_2023_1_2024.linked_integrity_fix.json`
  - `scripts/migration/output/input_batch_migration/Vetur_2025_1_2025/semantic_validation_Vetur_2025_1_2025.linked_integrity_fix.md`
  - `scripts/migration/output/input_batch_migration/Vetur_2025_1_2025/semantic_validation_Vetur_2025_1_2025.linked_integrity_fix.json`
  - `scripts/migration/output/input_batch_migration/Vár_2025_1_2025_A83A9BFF-005B-4ED2-856D-8C7BDF37B54F/semantic_validation_Vár_2025_1_2025_A83A9BFF-005B-4ED2-856D-8C7BDF37B54F.md`
  - `scripts/migration/output/input_batch_migration/Vár_2025_1_2025_A83A9BFF-005B-4ED2-856D-8C7BDF37B54F/semantic_validation_Vár_2025_1_2025_A83A9BFF-005B-4ED2-856D-8C7BDF37B54F.json`
  - `scripts/migration/output/input_batch_migration/Heyst_2025_1_2025_EE44DDC3-ED36-4AC7-85F0-E338C8F2EA78/semantic_validation_Heyst_2025_1_2025_EE44DDC3-ED36-4AC7-85F0-E338C8F2EA78.md`
  - `scripts/migration/output/input_batch_migration/Heyst_2025_1_2025_EE44DDC3-ED36-4AC7-85F0-E338C8F2EA78/semantic_validation_Heyst_2025_1_2025_EE44DDC3-ED36-4AC7-85F0-E338C8F2EA78.json`
  - `scripts/migration/output/input_batch_migration/Summar_2025_1_2025_6E496E90-F34B-4CD7-84DC-164EC3473A5E/semantic_validation_Summar_2025_1_2025_6E496E90-F34B-4CD7-84DC-164EC3473A5E.md`
  - `scripts/migration/output/input_batch_migration/Summar_2025_1_2025_6E496E90-F34B-4CD7-84DC-164EC3473A5E/semantic_validation_Summar_2025_1_2025_6E496E90-F34B-4CD7-84DC-164EC3473A5E.json`

