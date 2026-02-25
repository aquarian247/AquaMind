# Marine Pilot FW->Sea Run Summary (2026-02-18)

## Scope

Run a small marine pilot wave using the new FW->Sea linkage ladder:

- canonical first (`Ext_Transfers` + `SubTransfers` lineage),
- provisional temporal+geography fallback (`X` FW terminal depletion to `Y` sea fill/start in `[X, X+2 days]`) when canonical S*->A* is absent.

## Selected provisional pair

- FW component: `Stofnfiskur feb 2023|1|2023`
- Sea component: `Vár 2023|1|2023`
- Candidate rows in matrix for this pair: `7`
- Pair-level classification split: `2 true_candidate`, `5 sparse_evidence`
- Delta window observed: `0.033 .. 1.225` days

## Pilot migration execution

- Tool: `scripts/migration/tools/pilot_migrate_input_batch.py`
- Batch key: `Vár 2023|1|2023`
- Included FW batch: `Stofnfiskur feb 2023|1|2023`
- Profile: `fw_default`
- Extract horizon guard: `2026-01-22` (PASS)
- Station mismatch override: enabled (`--allow-station-mismatch`) due expected FW+Sea mixed-site cohort
- Result: **PASS** (`11/11` migration scripts completed)
- Migrated component key: `9B864694-C848-4627-BD4C-97516E71A4F7`
- Report dir: `scripts/migration/output/input_batch_migration/Vár_2023_1_2023`

## Semantic gate result

- Report: `marine_pilot_Var_2023_1_2023_semantic_validation_2026-02-18.md`
- Regression gates: **PASS**
- Overall semantic status: **PASS**
- Marine linkage evidence: `true`
- Transition caveat: `1` transition remained entry-window fallback (`entry_window_reason=incomplete_linkage`)

## Artifact index

- Pair selection + run summary JSON:
  - `aquamind/docs/progress/migration/analysis_reports/2026-02-18/marine_pilot_fwsea_run_summary_2026-02-18.json`
- Semantic report + summary:
  - `aquamind/docs/progress/migration/analysis_reports/2026-02-18/marine_pilot_Var_2023_1_2023_semantic_validation_2026-02-18.md`
  - `aquamind/docs/progress/migration/analysis_reports/2026-02-18/marine_pilot_Var_2023_1_2023_semantic_validation_2026-02-18.summary.json`
- Candidate matrix:
  - `aquamind/docs/progress/migration/analysis_reports/2026-02-18/fwsea_marine_ingress_candidate_matrix_2026-02-18.csv`
  - `aquamind/docs/progress/migration/analysis_reports/2026-02-18/fwsea_marine_ingress_candidate_matrix_2026-02-18.md`
  - `aquamind/docs/progress/migration/analysis_reports/2026-02-18/fwsea_marine_ingress_candidate_matrix_2026-02-18.summary.json`

