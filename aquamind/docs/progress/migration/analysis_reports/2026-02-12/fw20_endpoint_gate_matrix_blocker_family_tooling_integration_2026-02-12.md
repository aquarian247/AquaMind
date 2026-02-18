# FW20 endpoint gate matrix blocker-family tooling integration

Date: 2026-02-12  
Scope: integrate deterministic blocker-family classification into matrix tooling outputs (diagnostic-only), then rerun strict and combined profiles.

## What changed

Updated `scripts/migration/tools/fwsea_endpoint_gate_matrix.py` to emit blocker-family diagnostics directly in matrix artifacts:

- per-row fields:
  - `dominant_direction`
  - `dominant_stage_pair`
  - `primary_reason`
  - `classification`
  - `deterministic_linkage_found`
  - `classification_confidence`
  - `recommended_action`
- summary-level fields:
  - `nonzero_candidate_count`
  - `classification_counts`
  - `high_signal_persistent_fail_count`
- TSV and markdown now include classification columns.

Classification rules are diagnostic-only and policy-neutral:

- `reverse_flow_fw_only`
- `true_fw_to_sea_candidate`
- `true_fw_to_sea_sparse_evidence`
- `unclassified_nonzero_candidate`
- `no_candidate_rows` (for zero-candidate cohorts)

## Exact commands executed

```bash
python /Users/aquarian247/Projects/AquaMind/scripts/migration/tools/fwsea_endpoint_gate_matrix.py \
  --analysis-dir "/Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/migration/analysis_reports/2026-02-11" \
  --semantic-summary-glob "semantic_validation_*_fw20_parallel_post_fix.summary.json" \
  --report-dir-root "/Users/aquarian247/Projects/AquaMind/scripts/migration/output/input_batch_migration" \
  --csv-dir "/Users/aquarian247/Projects/AquaMind/scripts/migration/data/extract" \
  --output-dir "/Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/migration/analysis_reports/2026-02-12/fw20_endpoint_gate_matrix_with_blocker_family_2026-02-12" \
  --output-md "/Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/migration/analysis_reports/2026-02-12/fw20_fwsea_endpoint_gate_matrix_with_blocker_family_2026-02-12.md"
```

Observed output:

- `Rows=20 PASS=1 FAIL=19`

```bash
python /Users/aquarian247/Projects/AquaMind/scripts/migration/tools/fwsea_endpoint_gate_matrix.py \
  --analysis-dir "/Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/migration/analysis_reports/2026-02-11" \
  --semantic-summary-glob "semantic_validation_*_fw20_parallel_post_fix.summary.json" \
  --report-dir-root "/Users/aquarian247/Projects/AquaMind/scripts/migration/output/input_batch_migration" \
  --csv-dir "/Users/aquarian247/Projects/AquaMind/scripts/migration/data/extract" \
  --max-source-candidates 3 \
  --min-candidate-rows 4 \
  --output-dir "/Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/migration/analysis_reports/2026-02-12/fw20_endpoint_gate_matrix_diag_source3_min4_with_blocker_family_2026-02-12" \
  --output-md "/Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/migration/analysis_reports/2026-02-12/fw20_fwsea_endpoint_gate_matrix_diag_source3_min4_with_blocker_family_2026-02-12.md"
```

Observed output:

- `Rows=20 PASS=3 FAIL=17`

## Findings

### Strict profile (`max-source-candidates=2`, `min-candidate-rows=10`)

- `nonzero_candidate_count=7`
- `classification_counts`:
  - `reverse_flow_fw_only=3`
  - `true_fw_to_sea_candidate=1`
  - `true_fw_to_sea_sparse_evidence=1`
  - `unclassified_nonzero_candidate=2`
- `high_signal_persistent_fail_count=5`

### Combined diagnostic (`max-source-candidates=3`, `min-candidate-rows=4`)

- `nonzero_candidate_count=7`
- `classification_counts`:
  - `reverse_flow_fw_only=3`
  - `true_fw_to_sea_candidate=3`
  - `true_fw_to_sea_sparse_evidence=1`
- `high_signal_persistent_fail_count=3`

Combined-profile class membership:

- `reverse_flow_fw_only`: `BF mars 2025`, `BF oktober 2025`, `Bakkafrost S-21 jan 25`
- `true_fw_to_sea_candidate`: `Benchmark Gen. Septembur 2024`, `Stofnfiskur Aug 2024`, `Stofnfiskur sept 24`
- `true_fw_to_sea_sparse_evidence`: `StofnFiskur okt. 2024`

## Compact findings table

| source | deterministic linkage found (Y/N) | coverage | confidence | recommended action |
|---|---|---|---|---|
| reverse-flow FW-only blocker family (`input_to_sales`, `fw->fw`, `direction_mismatch`) | N | fails high-signal (`coverage` / `marine_target`) | High | exclude from FW->Sea policy evidence; keep as blocker diagnostics |
| true FW->Sea candidate family | Y | deterministic + marine-target pass | High | retain as positive deterministic diagnostics evidence; no global promotion yet |
| true FW->Sea sparse evidence family | Y | deterministic coverage + marine-target pass, evidence floor fails | Medium-High | keep strict evidence floor; treat as low-volume candidate canary |

## Decision

- **GO**: blocker-family classification integrated into acceptance reporting tooling artifacts.
- **NO-GO**: no runtime/API/UI change.
- **NO-GO**: no global FW/Sea policy promotion from this step alone.

