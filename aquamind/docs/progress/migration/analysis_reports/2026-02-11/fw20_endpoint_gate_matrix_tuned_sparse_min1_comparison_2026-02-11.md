# FW20 Endpoint Gate Matrix Tuned Sparse Min1 Comparison (2026-02-11)

## Scope
Executed a second diagnostic sparse-profile matrix run (`min-candidate-rows=1`) and compared strict vs tuned(4) vs tuned(min1). Then ran row-level deterministic drill-down for tuned-only PASS cohorts.

## Min1 matrix command (exact)
```bash
cd /Users/aquarian247/Projects/AquaMind && python /Users/aquarian247/Projects/AquaMind/scripts/migration/tools/fwsea_endpoint_gate_matrix.py \
  --analysis-dir /Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/migration/analysis_reports/2026-02-11 \
  --semantic-summary-glob 'semantic_validation_*_fw20_parallel_post_fix.summary.json' \
  --report-dir-root /Users/aquarian247/Projects/AquaMind/scripts/migration/output/input_batch_migration \
  --csv-dir /Users/aquarian247/Projects/AquaMind/scripts/migration/data/extract \
  --output-dir /Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/migration/analysis_reports/2026-02-11/fw20_endpoint_gate_matrix_tuned_sparse_min1_2026-02-11 \
  --output-md /Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/migration/analysis_reports/2026-02-11/fw20_fwsea_endpoint_gate_matrix_tuned_sparse_min1_2026-02-11.md \
  --expected-direction sales_to_input \
  --max-source-candidates 2 \
  --max-target-candidates 1 \
  --min-deterministic-coverage 0.90 \
  --max-ambiguous-rows 0 \
  --max-targets-per-source 1 \
  --min-candidate-rows 1 \
  --require-evidence \
  --require-marine-target \
  --min-marine-target-ratio 1.0
```

## Min1 matrix command output (exact)
```text
Wrote /Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/migration/analysis_reports/2026-02-11/fw20_fwsea_endpoint_gate_matrix_tuned_sparse_min1_2026-02-11.md
Wrote /Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/migration/analysis_reports/2026-02-11/fw20_endpoint_gate_matrix_tuned_sparse_min1_2026-02-11/fw20_endpoint_gate_matrix.summary.json
Wrote /Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/migration/analysis_reports/2026-02-11/fw20_endpoint_gate_matrix_tuned_sparse_min1_2026-02-11/fw20_endpoint_gate_matrix.tsv
Rows=20 PASS=2 FAIL=18
```

## Three-profile delta command (exact)
```bash
python - << 'PY'
import json, pathlib, collections
base=pathlib.Path('/Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/migration/analysis_reports/2026-02-11')
paths={
 'strict': base/'fw20_endpoint_gate_matrix_2026-02-11'/'fw20_endpoint_gate_matrix.summary.json',
 'tuned4': base/'fw20_endpoint_gate_matrix_tuned_sparse_2026-02-11'/'fw20_endpoint_gate_matrix.summary.json',
 'min1': base/'fw20_endpoint_gate_matrix_tuned_sparse_min1_2026-02-11'/'fw20_endpoint_gate_matrix.summary.json',
}
rows={k:json.loads(p.read_text())['rows'] for k,p in paths.items()}
by={k:{r['component_key']:r for r in v} for k,v in rows.items()}
keys=sorted(by['strict'])
for name in ['strict','tuned4','min1']:
    v=rows[name]
    pass_count=sum(1 for r in v if r['overall_passed'])
    fail_count=len(v)-pass_count
    c=collections.Counter()
    for r in v:
        for g in r['failed_gates']:
            c[g]+=1
    print(name,'rows',len(v),'pass',pass_count,'fail',fail_count,'gates',dict(sorted(c.items())))
print('status_change_strict_to_tuned4:')
for k in keys:
    s=by['strict'][k]; t=by['tuned4'][k]
    if s['overall_passed'] != t['overall_passed']:
        print('-',s['batch_name'],s['overall_passed'],'->',t['overall_passed'],'strict_failed',s['failed_gates'],'tuned4_failed',t['failed_gates'])
print('status_change_tuned4_to_min1:')
for k in keys:
    t=by['tuned4'][k]; m=by['min1'][k]
    if t['overall_passed'] != m['overall_passed']:
        print('-',t['batch_name'],t['overall_passed'],'->',m['overall_passed'],'tuned4_failed',t['failed_gates'],'min1_failed',m['failed_gates'])
print('evidence_gate_removed_tuned4_to_min1:')
for k in keys:
    t=by['tuned4'][k]; m=by['min1'][k]
    if 'evidence' in t['failed_gates'] and 'evidence' not in m['failed_gates']:
        print('-',t['batch_name'],'candidate_rows',t['candidate_rows'],'tuned4_failed',t['failed_gates'],'min1_failed',m['failed_gates'])
PY
```

## Three-profile delta output (exact)
```text
strict rows 20 pass 1 fail 19 gates {'coverage': 18, 'evidence': 18, 'marine_target': 16, 'uniqueness': 5}
tuned4 rows 20 pass 2 fail 18 gates {'coverage': 18, 'evidence': 17, 'marine_target': 16, 'uniqueness': 5}
min1 rows 20 pass 2 fail 18 gates {'coverage': 18, 'evidence': 13, 'marine_target': 16, 'uniqueness': 5}
status_change_strict_to_tuned4:
- Stofnfiskur sept 24 False -> True strict_failed ['evidence'] tuned4_failed []
status_change_tuned4_to_min1:
evidence_gate_removed_tuned4_to_min1:
- BF mars 2025 candidate_rows 1 tuned4_failed ['evidence', 'uniqueness', 'coverage', 'marine_target'] min1_failed ['uniqueness', 'coverage', 'marine_target']
- Bakkafrost S-21 jan 25 candidate_rows 1 tuned4_failed ['evidence', 'uniqueness', 'coverage', 'marine_target'] min1_failed ['uniqueness', 'coverage', 'marine_target']
- BF oktober 2025 candidate_rows 1 tuned4_failed ['evidence', 'uniqueness', 'coverage', 'marine_target'] min1_failed ['uniqueness', 'coverage', 'marine_target']
- StofnFiskur okt. 2024 candidate_rows 2 tuned4_failed ['evidence', 'uniqueness', 'coverage'] min1_failed ['uniqueness', 'coverage']
```

## Tuned-only PASS row drill-down command (exact)
```bash
python - << 'PY'
import json, pathlib
p=pathlib.Path('/Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/migration/analysis_reports/2026-02-11/fw20_endpoint_gate_matrix_tuned_sparse_min1_2026-02-11/fwsea_endpoint_gate_Stofnfiskur_sept_24_3_2024.summary.json')
d=json.loads(p.read_text())
print('component_key',d['component_key'])
print('metrics',d['metrics'])
print('gates',d['gates'])
print('reason_counts',d['counts']['reason_counts'])
print('direction_counts',d['counts']['direction_counts'])
print('pair_stage_counts',d['counts']['pair_stage_counts'])
print('deterministic_pairs:')
for r in d['examples']:
    if r.get('deterministic'):
        print('-',r.get('sales_operation_id'),'->',r.get('input_operation_id'),'direction',r.get('direction'),'source_stage',r.get('source_stage_class_counts'),'target_stage',r.get('target_stage_class_counts'),'target_all_marine',r.get('target_all_marine'))
print('non_deterministic_examples:')
for r in d['examples']:
    if not r.get('deterministic'):
        print('-',r)
PY
```

## Tuned-only PASS row drill-down output (exact)
```text
component_key E9F7C414-399C-4F17-879F-087899496683
metrics {'ambiguous_rows': 0, 'both_side_touch_rows': 0, 'candidate_rows': 4, 'deterministic_coverage': 1.0, 'deterministic_rows': 4, 'incomplete_linkage_fallback_count': 0, 'marine_target_deterministic_rows': 4, 'marine_target_ratio': 1.0, 'max_targets_per_source_observed': 1, 'sources_with_multiple_targets': 0, 'touched_rows': 5}
gates {'coverage': {'actual_deterministic_coverage': 1.0, 'min_deterministic_coverage': 0.9, 'passed': True}, 'evidence': {'actual_candidate_rows': 4, 'applicable': True, 'min_candidate_rows': 1, 'passed': True}, 'incomplete_linkage_fallback': {'actual': 0, 'applicable': False, 'passed': True, 'semantic_summary_json': '/Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/migration/analysis_reports/2026-02-11/semantic_validation_stofnfiskur_sept_24_2026-02-11_fw20_parallel_post_fix.summary.json', 'threshold': None}, 'marine_target': {'actual_marine_target_ratio': 1.0, 'applicable': True, 'min_marine_target_ratio': 1.0, 'passed': True}, 'overall_passed': True, 'stability': {'actual_max_targets_per_source': 1, 'max_targets_per_source': 1, 'passed': True, 'sources_with_multiple_targets': 0}, 'uniqueness': {'actual_ambiguous_rows': 0, 'max_ambiguous_rows': 0, 'passed': True}}
reason_counts {'deterministic': 4, 'no_counterpart_populations': 1}
direction_counts {'sales_to_input': 5}
pair_stage_counts {'fw->marine': 4}
deterministic_pairs:
- FF9E6BC4-97C6-48F4-8D25-06EA3453F543 -> 873F281E-C866-4E9E-A323-4DD87807CE64 direction sales_to_input source_stage {'fw': 1} target_stage {'marine': 1} target_all_marine True
- B99975CA-CB64-4805-8FB6-39E452A26B9C -> 32D4008F-E998-4A4E-B089-576300CEED74 direction sales_to_input source_stage {'fw': 2} target_stage {'marine': 1} target_all_marine True
- CF54E496-1F4F-4D31-A713-BB193BB73CE1 -> F0A5FE1F-3C30-48F6-BF3F-7C108C3A66AC direction sales_to_input source_stage {'fw': 1} target_stage {'marine': 1} target_all_marine True
- E7E0067C-0AA7-4F01-BD9C-DD2604911C37 -> 70BCF48E-D287-46EE-B366-92374B42A0DE direction sales_to_input source_stage {'fw': 2} target_stage {'marine': 1} target_all_marine True
non_deterministic_examples:
- {'deterministic': False, 'direction': 'sales_to_input', 'input_component_population_count': 0, 'input_operation_id': '', 'input_operation_population_count': 0, 'reason': 'no_counterpart_populations', 'sales_component_population_count': 2, 'sales_operation_id': '08F2E1FF-C12F-4ABA-AA79-581F0E170DC7', 'sales_operation_population_count': 2, 'source_component_population_count': 2, 'target_population_count': 0}
```

## Artifacts
- Matrix markdown:
  - `/Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/migration/analysis_reports/2026-02-11/fw20_fwsea_endpoint_gate_matrix_tuned_sparse_min1_2026-02-11.md`
- Matrix JSON:
  - `/Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/migration/analysis_reports/2026-02-11/fw20_endpoint_gate_matrix_tuned_sparse_min1_2026-02-11/fw20_endpoint_gate_matrix.summary.json`
- Matrix TSV:
  - `/Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/migration/analysis_reports/2026-02-11/fw20_endpoint_gate_matrix_tuned_sparse_min1_2026-02-11/fw20_endpoint_gate_matrix.tsv`

## Compact findings table
| source | deterministic linkage found (Y/N) | coverage | confidence | recommended action |
| --- | --- | --- | --- | --- |
| Strict profile (`min-candidate-rows=10`) | Partial | 1/20 PASS | High | Keep strict profile as release guardrail |
| Tuned profile (`min-candidate-rows=4`) | Partial | 2/20 PASS | High | Use as diagnostic profile only |
| Tuned profile (`min-candidate-rows=1`) | Partial | 2/20 PASS | High | No policy change; evidence relax alone does not improve core gate failures |
| Tuned-only PASS row drill-down (`Stofnfiskur sept 24`) | Y | 4 deterministic of 4 candidate rows; 1 non-candidate row | High | Keep cohort-specific note only; do not generalize linkage policy |

## Deterministic interpretation
- Lowering evidence threshold from 4 to 1 removed `evidence` gate failures for four sparse cohorts, but did not change PASS/FAIL status for any cohort.
- Primary blockers remain `coverage`, `marine_target`, and `uniqueness`.
- Tuned-only PASS remains a single cohort boundary case (`Stofnfiskur sept 24`) and does not provide broad FW20 generalization evidence.

## Decision
1. **GO**: keep tuned profiles (`min-candidate-rows=4` and `1`) as deterministic diagnostics.
2. **NO-GO**: no migration-policy/tooling linkage change based on current matrix evidence.
3. **NO-GO**: no runtime API/UI changes (FishTalk-agnostic runtime guardrail preserved).
