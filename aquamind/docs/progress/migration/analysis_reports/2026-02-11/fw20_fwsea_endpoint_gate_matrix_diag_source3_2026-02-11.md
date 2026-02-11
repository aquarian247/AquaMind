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
  - `min-candidate-rows=10` (`require-evidence=True`)
  - `require-marine-target=True` (`min-marine-target-ratio=1.0`)

## Topline

- Gate PASS: `2/20`
- Gate FAIL: `18/20`

## Gate-Failure Totals

- `evidence`: 18
- `coverage`: 16
- `marine_target`: 16
- `uniqueness`: 3

| batch | gate | failed gates | candidate rows | deterministic rows | ambiguous rows | coverage | marine ratio | max targets/source | incomplete-linkage fallback |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| AquaGen Mars 25 | FAIL | evidence, coverage, marine_target | 0 | 0 | 0 | 0.000 | 0.000 | 0 | 0 |
| BF mars 2025 | FAIL | evidence, uniqueness, coverage, marine_target | 1 | 0 | 1 | 0.000 | 0.000 | 0 | 1 |
| BF oktober 2025 | FAIL | evidence, uniqueness, coverage, marine_target | 1 | 0 | 1 | 0.000 | 0.000 | 0 | 0 |
| Bakkafrost S-21 jan 25 | FAIL | evidence, uniqueness, coverage, marine_target | 1 | 0 | 1 | 0.000 | 0.000 | 0 | 0 |
| Bakkafrost S-21 okt 25 | FAIL | evidence, coverage, marine_target | 0 | 0 | 0 | 0.000 | 0.000 | 0 | 0 |
| Bakkafrost feb 2025 | FAIL | evidence, coverage, marine_target | 0 | 0 | 0 | 0.000 | 0.000 | 0 | 0 |
| Benchmark Gen Septembur 2025 | FAIL | evidence, coverage, marine_target | 0 | 0 | 0 | 0.000 | 0.000 | 0 | 0 |
| Benchmark Gen. Desembur 2024 | FAIL | evidence, coverage, marine_target | 0 | 0 | 0 | 0.000 | 0.000 | 0 | 1 |
| Benchmark Gen. Mars 2025 | FAIL | evidence, coverage, marine_target | 0 | 0 | 0 | 0.000 | 0.000 | 0 | 1 |
| Benchmark Gen. Septembur 2024 | PASS | - | 15 | 15 | 0 | 1.000 | 1.000 | 1 | 0 |
| StofnFiskur S-21 apr 25 | FAIL | evidence, coverage, marine_target | 0 | 0 | 0 | 0.000 | 0.000 | 0 | 1 |
| StofnFiskur S-21 juli25 | FAIL | evidence, coverage, marine_target | 0 | 0 | 0 | 0.000 | 0.000 | 0 | 0 |
| StofnFiskur okt. 2024 | FAIL | evidence | 2 | 2 | 0 | 1.000 | 1.000 | 1 | 2 |
| Stofnfiskur Aug 2024 | PASS | - | 10 | 10 | 0 | 1.000 | 1.000 | 1 | 0 |
| Stofnfiskur Des 24 | FAIL | evidence, coverage, marine_target | 0 | 0 | 0 | 0.000 | 0.000 | 0 | 0 |
| Stofnfiskur Nov 2024 | FAIL | evidence, coverage, marine_target | 0 | 0 | 0 | 0.000 | 0.000 | 0 | 3 |
| Stofnfiskur Okt 25 | FAIL | evidence, coverage, marine_target | 0 | 0 | 0 | 0.000 | 0.000 | 0 | 0 |
| Stofnfiskur feb 2025 | FAIL | evidence, coverage, marine_target | 0 | 0 | 0 | 0.000 | 0.000 | 0 | 1 |
| Stofnfiskur mai 2025 | FAIL | evidence, coverage, marine_target | 0 | 0 | 0 | 0.000 | 0.000 | 0 | 0 |
| Stofnfiskur sept 24 | FAIL | evidence | 4 | 4 | 0 | 1.000 | 1.000 | 1 | 0 |

## Artifacts

- Matrix JSON: `/Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/migration/analysis_reports/2026-02-11/fw20_endpoint_gate_matrix_diag_source3_2026-02-11/fw20_endpoint_gate_matrix.summary.json`
- Matrix TSV: `/Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/migration/analysis_reports/2026-02-11/fw20_endpoint_gate_matrix_diag_source3_2026-02-11/fw20_endpoint_gate_matrix.tsv`
- Per-cohort gate files: `/Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/migration/analysis_reports/2026-02-11/fw20_endpoint_gate_matrix_diag_source3_2026-02-11`
