# FW20 FWSEA Endpoint Gate Matrix

## Scope

- Cohort source: `semantic_validation_*_fw20_parallel_post_fix.summary.json` under `/Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/migration/analysis_reports/2026-02-11` (20 semantic summaries).
- Gate config:
  - `expected-direction=sales_to_input`
  - `max-source-candidates=3`
  - `max-target-candidates=1`
  - `min-deterministic-coverage=0.9`
  - `max-ambiguous-rows=0`
  - `max-targets-per-source=1`
  - `min-candidate-rows=4` (`require-evidence=True`)
  - `require-marine-target=True` (`min-marine-target-ratio=1.0`)

## Topline

- Gate PASS: `3/20`
- Gate FAIL: `17/20`
- Non-zero candidate cohorts: `7`
- High-signal persistent FAIL cohorts: `3`
- Non-zero candidate classification counts:
  - `reverse_flow_fw_only`: 3
  - `true_fw_to_sea_candidate`: 3
  - `true_fw_to_sea_sparse_evidence`: 1

## Gate-Failure Totals

- `evidence`: 17
- `coverage`: 16
- `marine_target`: 16
- `uniqueness`: 3

| batch | gate | failed gates | candidate rows | deterministic rows | ambiguous rows | coverage | marine ratio | max targets/source | incomplete-linkage fallback | dominant direction | dominant pair | primary reason | classification |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | --- | --- |
| AquaGen Mars 25 | FAIL | evidence, coverage, marine_target | 0 | 0 | 0 | 0.000 | 0.000 | 0 | 0 | none | none | none | no_candidate_rows |
| BF mars 2025 | FAIL | evidence, uniqueness, coverage, marine_target | 1 | 0 | 1 | 0.000 | 0.000 | 0 | 1 | input_to_sales | fw->fw | direction_mismatch | reverse_flow_fw_only |
| BF oktober 2025 | FAIL | evidence, uniqueness, coverage, marine_target | 1 | 0 | 1 | 0.000 | 0.000 | 0 | 0 | input_to_sales | fw->fw | direction_mismatch | reverse_flow_fw_only |
| Bakkafrost S-21 jan 25 | FAIL | evidence, uniqueness, coverage, marine_target | 1 | 0 | 1 | 0.000 | 0.000 | 0 | 0 | input_to_sales | fw->fw | direction_mismatch | reverse_flow_fw_only |
| Bakkafrost S-21 okt 25 | FAIL | evidence, coverage, marine_target | 0 | 0 | 0 | 0.000 | 0.000 | 0 | 0 | none | none | none | no_candidate_rows |
| Bakkafrost feb 2025 | FAIL | evidence, coverage, marine_target | 0 | 0 | 0 | 0.000 | 0.000 | 0 | 0 | none | none | none | no_candidate_rows |
| Benchmark Gen Septembur 2025 | FAIL | evidence, coverage, marine_target | 0 | 0 | 0 | 0.000 | 0.000 | 0 | 0 | none | none | none | no_candidate_rows |
| Benchmark Gen. Desembur 2024 | FAIL | evidence, coverage, marine_target | 0 | 0 | 0 | 0.000 | 0.000 | 0 | 1 | none | none | none | no_candidate_rows |
| Benchmark Gen. Mars 2025 | FAIL | evidence, coverage, marine_target | 0 | 0 | 0 | 0.000 | 0.000 | 0 | 1 | none | none | none | no_candidate_rows |
| Benchmark Gen. Septembur 2024 | PASS | - | 15 | 15 | 0 | 1.000 | 1.000 | 1 | 0 | sales_to_input | fw->marine | deterministic | true_fw_to_sea_candidate |
| StofnFiskur S-21 apr 25 | FAIL | evidence, coverage, marine_target | 0 | 0 | 0 | 0.000 | 0.000 | 0 | 1 | none | none | none | no_candidate_rows |
| StofnFiskur S-21 juli25 | FAIL | evidence, coverage, marine_target | 0 | 0 | 0 | 0.000 | 0.000 | 0 | 0 | none | none | none | no_candidate_rows |
| StofnFiskur okt. 2024 | FAIL | evidence | 2 | 2 | 0 | 1.000 | 1.000 | 1 | 2 | sales_to_input | fw->marine | deterministic | true_fw_to_sea_sparse_evidence |
| Stofnfiskur Aug 2024 | PASS | - | 10 | 10 | 0 | 1.000 | 1.000 | 1 | 0 | sales_to_input | fw->marine | deterministic | true_fw_to_sea_candidate |
| Stofnfiskur Des 24 | FAIL | evidence, coverage, marine_target | 0 | 0 | 0 | 0.000 | 0.000 | 0 | 0 | none | none | none | no_candidate_rows |
| Stofnfiskur Nov 2024 | FAIL | evidence, coverage, marine_target | 0 | 0 | 0 | 0.000 | 0.000 | 0 | 3 | none | none | none | no_candidate_rows |
| Stofnfiskur Okt 25 | FAIL | evidence, coverage, marine_target | 0 | 0 | 0 | 0.000 | 0.000 | 0 | 0 | none | none | none | no_candidate_rows |
| Stofnfiskur feb 2025 | FAIL | evidence, coverage, marine_target | 0 | 0 | 0 | 0.000 | 0.000 | 0 | 1 | none | none | none | no_candidate_rows |
| Stofnfiskur mai 2025 | FAIL | evidence, coverage, marine_target | 0 | 0 | 0 | 0.000 | 0.000 | 0 | 0 | none | none | none | no_candidate_rows |
| Stofnfiskur sept 24 | PASS | - | 4 | 4 | 0 | 1.000 | 1.000 | 1 | 0 | sales_to_input | fw->marine | deterministic | true_fw_to_sea_candidate |

## Artifacts

- Matrix JSON: `/Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/migration/analysis_reports/2026-02-12/fw20_endpoint_gate_matrix_diag_source3_min4_with_blocker_family_2026-02-12/fw20_endpoint_gate_matrix.summary.json`
- Matrix TSV: `/Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/migration/analysis_reports/2026-02-12/fw20_endpoint_gate_matrix_diag_source3_min4_with_blocker_family_2026-02-12/fw20_endpoint_gate_matrix.tsv`
- Per-cohort gate files: `/Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/migration/analysis_reports/2026-02-12/fw20_endpoint_gate_matrix_diag_source3_min4_with_blocker_family_2026-02-12`
