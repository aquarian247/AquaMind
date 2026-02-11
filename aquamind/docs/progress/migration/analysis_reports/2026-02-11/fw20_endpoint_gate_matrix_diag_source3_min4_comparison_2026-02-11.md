# FW20 Endpoint Gate Matrix Diagnostic Source3+Min4 Comparison (2026-02-11)

## Scope
Executed combined diagnostic profile to map overlap of the two identified blocker families:
- `max-source-candidates=3`
- `min-candidate-rows=4`
- all other strict gates unchanged.

## Diagnostic matrix command (exact)
```bash
cd /Users/aquarian247/Projects/AquaMind && python /Users/aquarian247/Projects/AquaMind/scripts/migration/tools/fwsea_endpoint_gate_matrix.py \
  --analysis-dir /Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/migration/analysis_reports/2026-02-11 \
  --semantic-summary-glob 'semantic_validation_*_fw20_parallel_post_fix.summary.json' \
  --report-dir-root /Users/aquarian247/Projects/AquaMind/scripts/migration/output/input_batch_migration \
  --csv-dir /Users/aquarian247/Projects/AquaMind/scripts/migration/data/extract \
  --output-dir /Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/migration/analysis_reports/2026-02-11/fw20_endpoint_gate_matrix_diag_source3_min4_2026-02-11 \
  --output-md /Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/migration/analysis_reports/2026-02-11/fw20_fwsea_endpoint_gate_matrix_diag_source3_min4_2026-02-11.md \
  --expected-direction sales_to_input \
  --max-source-candidates 3 \
  --max-target-candidates 1 \
  --min-deterministic-coverage 0.90 \
  --max-ambiguous-rows 0 \
  --max-targets-per-source 1 \
  --min-candidate-rows 4 \
  --require-evidence \
  --require-marine-target \
  --min-marine-target-ratio 1.0
```

## Diagnostic matrix command output (exact)
```text
Wrote /Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/migration/analysis_reports/2026-02-11/fw20_fwsea_endpoint_gate_matrix_diag_source3_min4_2026-02-11.md
Wrote /Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/migration/analysis_reports/2026-02-11/fw20_endpoint_gate_matrix_diag_source3_min4_2026-02-11/fw20_endpoint_gate_matrix.summary.json
Wrote /Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/migration/analysis_reports/2026-02-11/fw20_endpoint_gate_matrix_diag_source3_min4_2026-02-11/fw20_endpoint_gate_matrix.tsv
Rows=20 PASS=3 FAIL=17
```

## Multi-profile comparison command (exact)
```bash
python - << 'PY'
import json,pathlib,collections
base=pathlib.Path('/Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/migration/analysis_reports/2026-02-11')
profiles={
 'strict': base/'fw20_endpoint_gate_matrix_2026-02-11/fw20_endpoint_gate_matrix.summary.json',
 'tuned4': base/'fw20_endpoint_gate_matrix_tuned_sparse_2026-02-11/fw20_endpoint_gate_matrix.summary.json',
 'min1': base/'fw20_endpoint_gate_matrix_tuned_sparse_min1_2026-02-11/fw20_endpoint_gate_matrix.summary.json',
 'source3': base/'fw20_endpoint_gate_matrix_diag_source3_2026-02-11/fw20_endpoint_gate_matrix.summary.json',
 'source3_min4': base/'fw20_endpoint_gate_matrix_diag_source3_min4_2026-02-11/fw20_endpoint_gate_matrix.summary.json',
}
data={k:json.loads(p.read_text())['rows'] for k,p in profiles.items()}
by={k:{r['component_key']:r for r in v} for k,v in data.items()}
keys=sorted(by['strict'])

for k,v in data.items():
    pc=sum(1 for r in v if r['overall_passed'])
    c=collections.Counter()
    for r in v:
        for g in r['failed_gates']: c[g]+=1
    print(k,'PASS',pc,'FAIL',len(v)-pc,'gates',dict(sorted(c.items())))

print('\\npass cohorts by profile:')
for k,v in data.items():
    ps=[r['batch_name'] for r in v if r['overall_passed']]
    print(k,ps)

print('\\nstatus changes strict->source3_min4:')
for key in keys:
    s=by['strict'][key]; d=by['source3_min4'][key]
    if s['overall_passed']!=d['overall_passed']:
        print('-',s['batch_name'],s['overall_passed'],'->',d['overall_passed'],'strict_failed',s['failed_gates'],'diag_failed',d['failed_gates'])

print('\\ngate changes source3->source3_min4:')
for key in keys:
    a=by['source3'][key]; b=by['source3_min4'][key]
    if set(a['failed_gates'])!=set(b['failed_gates']) or a['overall_passed']!=b['overall_passed']:
        print('-',a['batch_name'],'source3',a['failed_gates'],'-> source3_min4',b['failed_gates'],'cand',a['candidate_rows'])
PY
```

## Multi-profile comparison output (exact)
```text
strict PASS 1 FAIL 19 gates {'coverage': 18, 'evidence': 18, 'marine_target': 16, 'uniqueness': 5}
tuned4 PASS 2 FAIL 18 gates {'coverage': 18, 'evidence': 17, 'marine_target': 16, 'uniqueness': 5}
min1 PASS 2 FAIL 18 gates {'coverage': 18, 'evidence': 13, 'marine_target': 16, 'uniqueness': 5}
source3 PASS 2 FAIL 18 gates {'coverage': 16, 'evidence': 18, 'marine_target': 16, 'uniqueness': 3}
source3_min4 PASS 3 FAIL 17 gates {'coverage': 16, 'evidence': 17, 'marine_target': 16, 'uniqueness': 3}

pass cohorts by profile:
strict ['Stofnfiskur Aug 2024']
tuned4 ['Stofnfiskur Aug 2024', 'Stofnfiskur sept 24']
min1 ['Stofnfiskur Aug 2024', 'Stofnfiskur sept 24']
source3 ['Benchmark Gen. Septembur 2024', 'Stofnfiskur Aug 2024']
source3_min4 ['Benchmark Gen. Septembur 2024', 'Stofnfiskur Aug 2024', 'Stofnfiskur sept 24']

status changes strict->source3_min4:
- Benchmark Gen. Septembur 2024 False -> True strict_failed ['uniqueness', 'coverage'] diag_failed []
- Stofnfiskur sept 24 False -> True strict_failed ['evidence'] diag_failed []

gate changes source3->source3_min4:
- Stofnfiskur sept 24 source3 ['evidence'] -> source3_min4 [] cand 4
```

## Deterministic interpretation
- Combined diagnostic profile is the union effect of the two independent relaxations:
  - source-relax (`max-source-candidates=3`) captures `Benchmark Gen. Septembur 2024`
  - evidence-relax (`min-candidate-rows=4`) captures `Stofnfiskur sept 24`
- Primary blocker remains unchanged at cohort scale:
  - `marine_target` fails remain `16/20`
  - `coverage` fails remain high (`16/20`) even after combined relaxation.

## Compact findings table
| source | deterministic linkage found (Y/N) | coverage | confidence | recommended action |
| --- | --- | --- | --- | --- |
| Combined diagnostic profile (`source3 + min4`) | Partial | 3/20 PASS | High | Keep as evidence-mapping profile only |
| Strict -> combined delta | Y (boundary-sensitive) | 2 additional PASS cohorts | High | Do not promote to policy behavior |
| Cross-profile pass divergence | Y (negative evidence for generalization) | different relaxations unlock different cohorts | High | Maintain strict profile as release gate |
| Remaining broad failures (`marine_target`,`coverage`) | Y (negative evidence) | 16/20 coverage fails, 16/20 marine_target fails | High | Keep FW/Sea unlinked by default in policy/tooling |

## Decision
1. **GO**: use combined profile for diagnostics/documentation of blocker-family overlap.
2. **NO-GO**: no migration-policy/tooling behavior change based on combined profile.
3. **NO-GO**: no runtime API/UI changes.

## Artifacts
- `/Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/migration/analysis_reports/2026-02-11/fw20_fwsea_endpoint_gate_matrix_diag_source3_min4_2026-02-11.md`
- `/Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/migration/analysis_reports/2026-02-11/fw20_endpoint_gate_matrix_diag_source3_min4_2026-02-11/fw20_endpoint_gate_matrix.summary.json`
- `/Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/migration/analysis_reports/2026-02-11/fw20_endpoint_gate_matrix_diag_source3_min4_2026-02-11/fw20_endpoint_gate_matrix.tsv`
