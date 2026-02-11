# FW20 Endpoint Gate Matrix Tuned Sparse Comparison (2026-02-11)

## Scope
Executed a diagnostic tuned-profile matrix run (sparse-cohort sensitivity) and compared against the strict FW20 profile.

- Strict profile reference:
  - `/Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/migration/analysis_reports/2026-02-11/fw20_fwsea_endpoint_gate_matrix_2026-02-11.md`
- Tuned profile output:
  - `/Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/migration/analysis_reports/2026-02-11/fw20_fwsea_endpoint_gate_matrix_tuned_sparse_2026-02-11.md`

## Tuned matrix command (exact)
```bash
cd /Users/aquarian247/Projects/AquaMind && python /Users/aquarian247/Projects/AquaMind/scripts/migration/tools/fwsea_endpoint_gate_matrix.py \
  --analysis-dir /Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/migration/analysis_reports/2026-02-11 \
  --semantic-summary-glob 'semantic_validation_*_fw20_parallel_post_fix.summary.json' \
  --report-dir-root /Users/aquarian247/Projects/AquaMind/scripts/migration/output/input_batch_migration \
  --csv-dir /Users/aquarian247/Projects/AquaMind/scripts/migration/data/extract \
  --output-dir /Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/migration/analysis_reports/2026-02-11/fw20_endpoint_gate_matrix_tuned_sparse_2026-02-11 \
  --output-md /Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/migration/analysis_reports/2026-02-11/fw20_fwsea_endpoint_gate_matrix_tuned_sparse_2026-02-11.md \
  --expected-direction sales_to_input \
  --max-source-candidates 2 \
  --max-target-candidates 1 \
  --min-deterministic-coverage 0.90 \
  --max-ambiguous-rows 0 \
  --max-targets-per-source 1 \
  --min-candidate-rows 4 \
  --require-evidence \
  --require-marine-target \
  --min-marine-target-ratio 1.0
```

## Tuned matrix command output (exact)
```text
Wrote /Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/migration/analysis_reports/2026-02-11/fw20_fwsea_endpoint_gate_matrix_tuned_sparse_2026-02-11.md
Wrote /Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/migration/analysis_reports/2026-02-11/fw20_endpoint_gate_matrix_tuned_sparse_2026-02-11/fw20_endpoint_gate_matrix.summary.json
Wrote /Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/migration/analysis_reports/2026-02-11/fw20_endpoint_gate_matrix_tuned_sparse_2026-02-11/fw20_endpoint_gate_matrix.tsv
Rows=20 PASS=2 FAIL=18
```

## Strict vs tuned delta command (exact)
```bash
python - << 'PY'
import json, pathlib, collections
base=pathlib.Path('/Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/migration/analysis_reports/2026-02-11')
strict_p=base/'fw20_endpoint_gate_matrix_2026-02-11'/'fw20_endpoint_gate_matrix.summary.json'
tuned_p=base/'fw20_endpoint_gate_matrix_tuned_sparse_2026-02-11'/'fw20_endpoint_gate_matrix.summary.json'
strict=json.loads(strict_p.read_text())['rows']
tuned=json.loads(tuned_p.read_text())['rows']
sm={r['component_key']:r for r in strict}
tm={r['component_key']:r for r in tuned}
keys=sorted(set(sm)|set(tm))
sc=collections.Counter(); tc=collections.Counter()
for r in strict:
    for g in r.get('failed_gates',[]): sc[g]+=1
for r in tuned:
    for g in r.get('failed_gates',[]): tc[g]+=1
print('strict pass/fail', sum(1 for r in strict if r.get('overall_passed')), sum(1 for r in strict if not r.get('overall_passed')))
print('tuned pass/fail', sum(1 for r in tuned if r.get('overall_passed')), sum(1 for r in tuned if not r.get('overall_passed')))
print('strict gates', dict(sorted(sc.items())))
print('tuned gates', dict(sorted(tc.items())))
print('delta cohorts (status changed):')
for k in keys:
    s=sm.get(k); t=tm.get(k)
    if bool(s.get('overall_passed'))!=bool(t.get('overall_passed')):
        print('-', s.get('batch_name'), '|', s.get('overall_passed'),'->',t.get('overall_passed'),'| strict_failed',s.get('failed_gates'),'| tuned_failed',t.get('failed_gates'),'| strict cand',s.get('candidate_rows'),'| tuned cand',t.get('candidate_rows'))
print('all cohorts evidence gate strict->tuned changes:')
for k in keys:
    s=sm[k]; t=tm[k]
    if ('evidence' in s.get('failed_gates',[])) != ('evidence' in t.get('failed_gates',[])):
        print('-', s['batch_name'], '| evidence:', 'strict_fail' if 'evidence' in s['failed_gates'] else 'strict_pass', '->', 'tuned_fail' if 'evidence' in t['failed_gates'] else 'tuned_pass', '| cand', s.get('candidate_rows'), '->', t.get('candidate_rows'))
PY
```

## Strict vs tuned delta output (exact)
```text
strict pass/fail 1 19
tuned pass/fail 2 18
strict gates {'coverage': 18, 'evidence': 18, 'marine_target': 16, 'uniqueness': 5}
tuned gates {'coverage': 18, 'evidence': 17, 'marine_target': 16, 'uniqueness': 5}
delta cohorts (status changed):
- Stofnfiskur sept 24 | False -> True | strict_failed ['evidence'] | tuned_failed [] | strict cand 4 | tuned cand 4
all cohorts evidence gate strict->tuned changes:
- Stofnfiskur sept 24 | evidence: strict_fail -> tuned_pass | cand 4 -> 4
```

## Deterministic interpretation
- Strict profile remains broad-fail (`1/20` PASS).
- Tuned sparse profile improves by exactly one cohort (`2/20` PASS).
- Improvement mechanism is limited to the evidence-threshold boundary; no improvement in `coverage`, `marine_target`, or `uniqueness` gate totals.

## Compact findings table
| source | deterministic linkage found (Y/N) | coverage | confidence | recommended action |
| --- | --- | --- | --- | --- |
| Strict profile matrix (`min-candidate-rows=10`) | Partial | 1/20 PASS | High | Keep strict profile as release guardrail |
| Tuned sparse profile (`min-candidate-rows=4`) | Partial | 2/20 PASS | High | Use only as diagnostic lens for sparse cohorts |
| Strict vs tuned delta | Y (boundary-sensitive) | 1 cohort status flip | High | Do not generalize as policy evidence |
| Gate totals (`coverage`,`marine_target`,`uniqueness`) | Y (negative evidence) | unchanged in tuned run | High | Keep FW/Sea unlinked by default in policy/tooling |

## Decision
1. **GO**: keep tuned sparse profile available for deterministic diagnostics.
2. **NO-GO**: no migration-policy/tooling behavior change based on this tuned run.
3. **NO-GO**: no runtime API/UI changes (guardrail preserved).
