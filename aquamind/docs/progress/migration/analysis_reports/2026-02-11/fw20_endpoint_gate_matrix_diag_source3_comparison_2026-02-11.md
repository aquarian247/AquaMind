# FW20 Endpoint Gate Matrix Diagnostic Source3 Comparison (2026-02-11)

## Scope
Executed a diagnostic profile that changes only one strict gate:
- `max-source-candidates: 2 -> 3`
- all other strict gates unchanged.

## Diagnostic matrix command (exact)
```bash
cd /Users/aquarian247/Projects/AquaMind && python /Users/aquarian247/Projects/AquaMind/scripts/migration/tools/fwsea_endpoint_gate_matrix.py \
  --analysis-dir /Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/migration/analysis_reports/2026-02-11 \
  --semantic-summary-glob 'semantic_validation_*_fw20_parallel_post_fix.summary.json' \
  --report-dir-root /Users/aquarian247/Projects/AquaMind/scripts/migration/output/input_batch_migration \
  --csv-dir /Users/aquarian247/Projects/AquaMind/scripts/migration/data/extract \
  --output-dir /Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/migration/analysis_reports/2026-02-11/fw20_endpoint_gate_matrix_diag_source3_2026-02-11 \
  --output-md /Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/migration/analysis_reports/2026-02-11/fw20_fwsea_endpoint_gate_matrix_diag_source3_2026-02-11.md \
  --expected-direction sales_to_input \
  --max-source-candidates 3 \
  --max-target-candidates 1 \
  --min-deterministic-coverage 0.90 \
  --max-ambiguous-rows 0 \
  --max-targets-per-source 1 \
  --min-candidate-rows 10 \
  --require-evidence \
  --require-marine-target \
  --min-marine-target-ratio 1.0
```

## Diagnostic matrix command output (exact)
```text
Wrote /Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/migration/analysis_reports/2026-02-11/fw20_fwsea_endpoint_gate_matrix_diag_source3_2026-02-11.md
Wrote /Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/migration/analysis_reports/2026-02-11/fw20_endpoint_gate_matrix_diag_source3_2026-02-11/fw20_endpoint_gate_matrix.summary.json
Wrote /Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/migration/analysis_reports/2026-02-11/fw20_endpoint_gate_matrix_diag_source3_2026-02-11/fw20_endpoint_gate_matrix.tsv
Rows=20 PASS=2 FAIL=18
```

## Strict vs source3 delta command (exact)
```bash
python - << 'PY'
import json, pathlib, collections
base=pathlib.Path('/Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/migration/analysis_reports/2026-02-11')
strict=json.loads((base/'fw20_endpoint_gate_matrix_2026-02-11/fw20_endpoint_gate_matrix.summary.json').read_text())['rows']
src3=json.loads((base/'fw20_endpoint_gate_matrix_diag_source3_2026-02-11/fw20_endpoint_gate_matrix.summary.json').read_text())['rows']
sm={r['component_key']:r for r in strict}
dm={r['component_key']:r for r in src3}
keys=sorted(sm)
def stats(rows):
    pc=sum(1 for r in rows if r['overall_passed'])
    c=collections.Counter()
    for r in rows:
        for g in r['failed_gates']:
            c[g]+=1
    return pc,len(rows)-pc,dict(sorted(c.items()))
print('strict',stats(strict))
print('diag_source3',stats(src3))
print('status changes strict->source3:')
for k in keys:
    s=sm[k]; d=dm[k]
    if s['overall_passed']!=d['overall_passed']:
        print('-',s['batch_name'],s['overall_passed'],'->',d['overall_passed'],'strict_failed',s['failed_gates'],'source3_failed',d['failed_gates'])
print('gate changes strict->source3:')
for k in keys:
    s=sm[k]; d=dm[k]
    if set(s['failed_gates'])!=set(d['failed_gates']):
        print('-',s['batch_name'],'strict',s['failed_gates'],'source3',d['failed_gates'],'cand',s['candidate_rows'],'det',s['deterministic_rows'],'->',d['deterministic_rows'],'cov',s['deterministic_coverage'],'->',d['deterministic_coverage'])
PY
```

## Strict vs source3 delta output (exact)
```text
strict (1, 19, {'coverage': 18, 'evidence': 18, 'marine_target': 16, 'uniqueness': 5})
diag_source3 (2, 18, {'coverage': 16, 'evidence': 18, 'marine_target': 16, 'uniqueness': 3})
status changes strict->source3:
- Benchmark Gen. Septembur 2024 False -> True strict_failed ['uniqueness', 'coverage'] source3_failed []
gate changes strict->source3:
- Benchmark Gen. Septembur 2024 strict ['uniqueness', 'coverage'] source3 [] cand 15 det 13 -> 15 cov 0.8666666666666667 -> 1.0
- StofnFiskur okt. 2024 strict ['evidence', 'uniqueness', 'coverage'] source3 ['evidence'] cand 2 det 1 -> 2 cov 0.5 -> 1.0
```

## Cross-profile pass-set check
- Strict `PASS=1`: `Stofnfiskur Aug 2024`
- Tuned evidence profiles (`min-candidate-rows=4/1`) add: `Stofnfiskur sept 24`
- Source3 profile (`max-source-candidates=3`) adds: `Benchmark Gen. Septembur 2024`

Implication:
- Different relaxed dimensions unlock different cohorts.
- No single relaxed diagnostic profile generalizes across FW20.

## Compact findings table
| source | deterministic linkage found (Y/N) | coverage | confidence | recommended action |
| --- | --- | --- | --- | --- |
| Diagnostic source3 profile (`max-source-candidates=3`) | Partial | 2/20 PASS | High | Keep as diagnostic profile only |
| Strict vs source3 delta | Y (boundary-sensitive) | 1 additional cohort PASS (`Benchmark Gen. Septembur 2024`) | High | Do not promote as global policy evidence |
| Gate-family effect (`source_candidate_count_out_of_bounds`) | Y | `uniqueness` and `coverage` failures reduced (`5->3`, `18->16`) | High | Keep targeted blocker-family analysis in tooling |
| Cross-profile pass-set divergence | Y (negative evidence for generalization) | evidence-relaxed and source-relaxed profiles pass different cohorts | High | Keep strict profile as release guardrail |

## Decision
1. **GO**: retain source3 profile as a deterministic diagnostic lens for blocker-family B (`3->1` source consolidation).
2. **NO-GO**: no migration-policy/tooling behavior change based on source3 run.
3. **NO-GO**: no runtime API/UI changes.

## Artifacts
- `/Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/migration/analysis_reports/2026-02-11/fw20_fwsea_endpoint_gate_matrix_diag_source3_2026-02-11.md`
- `/Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/migration/analysis_reports/2026-02-11/fw20_endpoint_gate_matrix_diag_source3_2026-02-11/fw20_endpoint_gate_matrix.summary.json`
- `/Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/migration/analysis_reports/2026-02-11/fw20_endpoint_gate_matrix_diag_source3_2026-02-11/fw20_endpoint_gate_matrix.tsv`
