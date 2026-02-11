# FW20 Endpoint Gate Matrix Execution (2026-02-11)

## Scope
Executed deterministic endpoint-pairing acceptance gates across the full FW20 post-fix cohort set using the new matrix tooling runner.

- Source cohort set: `semantic_validation_*_fw20_parallel_post_fix.summary.json` (20 cohorts)
- Local-only FishTalk extract + local migration output reports
- Tooling-only operation (no runtime API/UI changes)

## Tooling command (exact)
```bash
cd /Users/aquarian247/Projects/AquaMind
python scripts/migration/tools/fwsea_endpoint_gate_matrix.py \
  --analysis-dir aquamind/docs/progress/migration/analysis_reports/2026-02-11 \
  --semantic-summary-glob 'semantic_validation_*_fw20_parallel_post_fix.summary.json' \
  --report-dir-root scripts/migration/output/input_batch_migration \
  --csv-dir scripts/migration/data/extract \
  --output-dir aquamind/docs/progress/migration/analysis_reports/2026-02-11/fw20_endpoint_gate_matrix_2026-02-11 \
  --output-md aquamind/docs/progress/migration/analysis_reports/2026-02-11/fw20_fwsea_endpoint_gate_matrix_2026-02-11.md
```

## Fixed strict gate config used
- `expected-direction=sales_to_input`
- `max-source-candidates=2`
- `max-target-candidates=1`
- `min-deterministic-coverage=0.90`
- `max-ambiguous-rows=0`
- `max-targets-per-source=1`
- `min-candidate-rows=10` with `--require-evidence`
- `--require-marine-target --min-marine-target-ratio=1.0`

## Matrix artifacts
- Matrix markdown:
  - `/Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/migration/analysis_reports/2026-02-11/fw20_fwsea_endpoint_gate_matrix_2026-02-11.md`
- Matrix JSON:
  - `/Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/migration/analysis_reports/2026-02-11/fw20_endpoint_gate_matrix_2026-02-11/fw20_endpoint_gate_matrix.summary.json`
- Matrix TSV:
  - `/Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/migration/analysis_reports/2026-02-11/fw20_endpoint_gate_matrix_2026-02-11/fw20_endpoint_gate_matrix.tsv`
- Per-cohort gate outputs:
  - `/Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/migration/analysis_reports/2026-02-11/fw20_endpoint_gate_matrix_2026-02-11/`

## Topline results
- FW20 cohorts evaluated: `20`
- PASS: `1`
- FAIL: `19`

Gate-failure totals:
- `coverage`: `18`
- `evidence`: `18`
- `marine_target`: `16`
- `uniqueness`: `5`

Notable cohorts:
- PASS: `Stofnfiskur Aug 2024` (`10/10` deterministic, coverage `1.000`)
- Near-pass but FAIL (coverage/uniqueness): `Benchmark Gen. Septembur 2024` (`13/15`, coverage `0.867`, ambiguous `2`)
- Near-pass but FAIL (evidence-only): `Stofnfiskur sept 24` (`4/4` deterministic but below min-candidate threshold)

## Compact findings table
| source | deterministic linkage found (Y/N) | coverage | confidence | recommended action |
| --- | --- | --- | --- | --- |
| FW20 endpoint gate matrix (strict config) | Partial | 1/20 cohort PASS | High | Keep NO-GO for policy promotion under current strict thresholds |
| Failing gate pattern (`evidence`,`coverage`) | Y (negative evidence) | 18/20 cohorts fail these gates | High | Treat endpoint signal as sparse/non-generalized across FW20 for now |
| Failing gate pattern (`marine_target`) | Y (negative evidence) | 16/20 fail marine-target gate | High | Avoid global fw->marine policy assumption |
| Incomplete-linkage fallback counts from semantic summaries | Y (context only) | non-zero in several cohorts | Medium | Keep fallback-regression checks in acceptance criteria before policy change |

## Deterministic decision
1. **GO**: endpoint gate matrix tooling integration and cohort-scale execution.
2. **NO-GO**: migration-policy/runtime FW/Sea auto-link promotion under current strict gate profile.

## Guardrails status
- Runtime remains FishTalk-agnostic.
- FW20 verified behavior preserved.
- External-mixing default remains `10.0`.
