# FW20 Part B Follow-up: High-Signal FAIL Cohorts (2026-02-12)

## Scope

Targeted follow-up on the remaining FW20 high-signal FAIL cohorts with:
- non-zero endpoint candidates, and
- persistent `coverage` and/or `marine_target` failures.

Objective:
1) deterministically separate true FW->Sea linkage candidates from reverse-flow/FW-only patterns, and  
2) determine whether a tooling-only blocker-family diagnostics enhancement is justified.

Guardrails preserved:
- Runtime remains FishTalk-agnostic.
- No runtime API/UI changes.
- No migration policy auto-link promotion changes in this pass.

## Inputs

- Combined diagnostic matrix:
  - `/Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/migration/analysis_reports/2026-02-11/fw20_endpoint_gate_matrix_diag_source3_min4_2026-02-11/fw20_endpoint_gate_matrix.summary.json`
- Strict matrix (for persistence cross-check):
  - `/Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/migration/analysis_reports/2026-02-11/fw20_endpoint_gate_matrix_2026-02-11/fw20_endpoint_gate_matrix.summary.json`
- Per-cohort gate summaries under both profile directories above.

## Command A (exact): Non-zero candidate cohort classification + reverse-flow row extraction

```bash
python - <<'PY'
import csv
import json
from collections import Counter
from pathlib import Path

base = Path('/Users/aquarian247/Projects/AquaMind')
analysis_prev = base / 'aquamind/docs/progress/migration/analysis_reports/2026-02-11'
analysis_today = base / 'aquamind/docs/progress/migration/analysis_reports/2026-02-12'
analysis_today.mkdir(parents=True, exist_ok=True)

matrix_path = analysis_prev / 'fw20_endpoint_gate_matrix_diag_source3_min4_2026-02-11/fw20_endpoint_gate_matrix.summary.json'
matrix_rows = json.loads(matrix_path.read_text())['rows']

rows_nonzero = []
reverse_flow_rows = []
classification_counts = Counter()

for row in sorted((r for r in matrix_rows if r['candidate_rows'] > 0), key=lambda x: x['batch_name']):
    gate_path = analysis_prev / 'fw20_endpoint_gate_matrix_diag_source3_min4_2026-02-11' / row['gate_summary']
    gate = json.loads(gate_path.read_text())
    direction_counts = gate.get('counts', {}).get('direction_counts', {})
    pair_stage_counts = gate.get('counts', {}).get('pair_stage_counts', {})
    reason_counts = gate.get('counts', {}).get('reason_counts', {})

    dominant_direction = max(direction_counts, key=direction_counts.get) if direction_counts else 'none'
    dominant_pair = max(pair_stage_counts, key=pair_stage_counts.get) if pair_stage_counts else 'unknown'
    primary_reason = max(reason_counts, key=reason_counts.get) if reason_counts else 'none'

    failed = set(row.get('failed_gates') or [])

    if (
        primary_reason == 'direction_mismatch'
        and dominant_direction == 'input_to_sales'
        and dominant_pair == 'fw->fw'
        and ('coverage' in failed or 'marine_target' in failed)
    ):
        classification = 'reverse_flow_fw_only'
        deterministic_linkage_found = 'N'
        confidence = 'High'
        recommended_action = 'Exclude from FW->Sea policy evidence; keep as reverse-flow blocker diagnostics only.'
    elif row['deterministic_rows'] > 0 and row['marine_target_ratio'] >= 1.0 and row['deterministic_coverage'] >= 0.9:
        if 'evidence' in failed:
            classification = 'true_fw_to_sea_sparse_evidence'
            deterministic_linkage_found = 'Y'
            confidence = 'Medium-High'
            recommended_action = 'Treat as true candidate; keep strict evidence floor for release and track as low-volume canary.'
        else:
            classification = 'true_fw_to_sea_candidate'
            deterministic_linkage_found = 'Y'
            confidence = 'High'
            recommended_action = 'Retain as positive deterministic evidence for tooling diagnostics; no global policy promotion yet.'
    else:
        classification = 'unclassified'
        deterministic_linkage_found = 'N'
        confidence = 'Medium'
        recommended_action = 'Needs manual deterministic drill-down before any policy use.'

    classification_counts[classification] += 1

    rows_nonzero.append(
        {
            'batch_name': row['batch_name'],
            'component_key': row['component_key'],
            'overall_gate': 'PASS' if row['overall_passed'] else 'FAIL',
            'failed_gates': ','.join(row.get('failed_gates') or []) or '-',
            'candidate_rows': row['candidate_rows'],
            'deterministic_rows': row['deterministic_rows'],
            'deterministic_coverage': f"{row['deterministic_coverage']:.3f}",
            'marine_target_ratio': f"{row['marine_target_ratio']:.3f}",
            'dominant_direction': dominant_direction,
            'dominant_stage_pair': dominant_pair,
            'primary_reason': primary_reason,
            'classification': classification,
            'deterministic_linkage_found': deterministic_linkage_found,
            'confidence': confidence,
            'recommended_action': recommended_action,
            'gate_summary': row['gate_summary'],
        }
    )

    if classification == 'reverse_flow_fw_only':
        for ex in gate.get('examples', []):
            reverse_flow_rows.append(
                {
                    'batch_name': row['batch_name'],
                    'component_key': row['component_key'],
                    'reason': ex.get('reason', ''),
                    'direction': ex.get('direction', ''),
                    'sales_operation_id': ex.get('sales_operation_id', ''),
                    'input_operation_id': ex.get('input_operation_id', ''),
                    'source_component_population_count': ex.get('source_component_population_count', ''),
                    'target_population_count': ex.get('target_population_count', ''),
                    'source_stage_class_counts': json.dumps(ex.get('source_stage_class_counts', {}), sort_keys=True),
                    'target_stage_class_counts': json.dumps(ex.get('target_stage_class_counts', {}), sort_keys=True),
                }
            )

out_rows_tsv = analysis_today / 'fw20_endpoint_nonzero_candidate_classification_2026-02-12.tsv'
out_reverse_tsv = analysis_today / 'fw20_endpoint_reverse_flow_rows_2026-02-12.tsv'
out_summary_json = analysis_today / 'fw20_endpoint_nonzero_candidate_classification_2026-02-12.summary.json'

fields_rows = [
    'batch_name','component_key','overall_gate','failed_gates','candidate_rows','deterministic_rows',
    'deterministic_coverage','marine_target_ratio','dominant_direction','dominant_stage_pair','primary_reason',
    'classification','deterministic_linkage_found','confidence','recommended_action','gate_summary'
]
with out_rows_tsv.open('w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=fields_rows, delimiter='\t')
    w.writeheader()
    w.writerows(rows_nonzero)

fields_reverse = [
    'batch_name','component_key','reason','direction','sales_operation_id','input_operation_id',
    'source_component_population_count','target_population_count','source_stage_class_counts','target_stage_class_counts'
]
with out_reverse_tsv.open('w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=fields_reverse, delimiter='\t')
    w.writeheader()
    w.writerows(reverse_flow_rows)

summary = {
    'matrix_source': str(matrix_path),
    'nonzero_candidate_cohort_count': len(rows_nonzero),
    'classification_counts': dict(sorted(classification_counts.items())),
    'high_signal_persistent_fail_cohort_count': sum(1 for r in rows_nonzero if ('coverage' in r['failed_gates'] or 'marine_target' in r['failed_gates']) and r['overall_gate'] == 'FAIL'),
    'reverse_flow_row_count': len(reverse_flow_rows),
    'artifacts': {
        'classification_tsv': str(out_rows_tsv),
        'reverse_flow_rows_tsv': str(out_reverse_tsv),
    },
}
out_summary_json.write_text(json.dumps(summary, indent=2, sort_keys=True))

print('Wrote', out_rows_tsv)
print('Wrote', out_reverse_tsv)
print('Wrote', out_summary_json)
print('nonzero_candidate_cohort_count', len(rows_nonzero))
print('classification_counts', dict(sorted(classification_counts.items())))
print('high_signal_persistent_fail_cohort_count', summary['high_signal_persistent_fail_cohort_count'])
print('reverse_flow_row_count', len(reverse_flow_rows))
PY
```

### Command A output (exact)

```text
Wrote /Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/migration/analysis_reports/2026-02-12/fw20_endpoint_nonzero_candidate_classification_2026-02-12.tsv
Wrote /Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/migration/analysis_reports/2026-02-12/fw20_endpoint_reverse_flow_rows_2026-02-12.tsv
Wrote /Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/migration/analysis_reports/2026-02-12/fw20_endpoint_nonzero_candidate_classification_2026-02-12.summary.json
nonzero_candidate_cohort_count 7
classification_counts {'reverse_flow_fw_only': 3, 'true_fw_to_sea_candidate': 3, 'true_fw_to_sea_sparse_evidence': 1}
high_signal_persistent_fail_cohort_count 3
reverse_flow_row_count 3
```

## Command B (exact): strict vs combined persistence check for high-signal persistent FAIL cohort set

```bash
python - <<'PY'
import json
from pathlib import Path
base=Path('/Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/migration/analysis_reports/2026-02-11')
strict_dir=base/'fw20_endpoint_gate_matrix_2026-02-11'
combo_dir=base/'fw20_endpoint_gate_matrix_diag_source3_min4_2026-02-11'
combo_rows=json.loads((combo_dir/'fw20_endpoint_gate_matrix.summary.json').read_text())['rows']
sel=[r for r in combo_rows if (not r['overall_passed']) and r['candidate_rows']>0 and (('coverage' in r['failed_gates']) or ('marine_target' in r['failed_gates']))]
print('persistent_fail_cohorts',len(sel))
for r in sorted(sel,key=lambda x:x['batch_name']):
    c=json.loads((combo_dir/r['gate_summary']).read_text())
    s=json.loads((strict_dir/r['gate_summary']).read_text())
    print('\t'.join([
        r['batch_name'],
        'strict_reason=' + ';'.join(f"{k}:{v}" for k,v in (s.get('counts',{}).get('reason_counts',{}) or {}).items()),
        'combined_reason=' + ';'.join(f"{k}:{v}" for k,v in (c.get('counts',{}).get('reason_counts',{}) or {}).items()),
        'strict_pair=' + ';'.join(f"{k}:{v}" for k,v in (s.get('counts',{}).get('pair_stage_counts',{}) or {}).items()),
        'combined_pair=' + ';'.join(f"{k}:{v}" for k,v in (c.get('counts',{}).get('pair_stage_counts',{}) or {}).items()),
    ]))
PY
```

### Command B output (exact)

```text
persistent_fail_cohorts 3
BF mars 2025	strict_reason=direction_mismatch:1	combined_reason=direction_mismatch:1	strict_pair=fw->fw:1	combined_pair=fw->fw:1
BF oktober 2025	strict_reason=direction_mismatch:1	combined_reason=direction_mismatch:1	strict_pair=fw->fw:1	combined_pair=fw->fw:1
Bakkafrost S-21 jan 25	strict_reason=direction_mismatch:1	combined_reason=direction_mismatch:1	strict_pair=fw->fw:1	combined_pair=fw->fw:1
```

## Deterministic findings

1. **Remaining high-signal persistent FAIL cohort set is narrow and homogeneous** (`3` cohorts):
   - `BF mars 2025`
   - `BF oktober 2025`
   - `Bakkafrost S-21 jan 25`

2. All three are deterministic **reverse-flow / FW-only** patterns:
   - `direction = input_to_sales`
   - stage-pair signature `fw->fw`
   - reason `direction_mismatch`
   - coverage remains `0.000`, marine target ratio remains `0.000`.

3. The non-zero candidate cohort set (`7`) separates cleanly into two families:
   - **True FW->Sea evidence family**: `4` cohorts (`3` full + `1` sparse-evidence)
   - **Reverse-flow FW-only family**: `3` cohorts (the persistent high-signal FAIL set above)

4. The reverse-flow family remains unchanged across strict and combined diagnostics, so this is not a profile artifact.

## Compact findings table

| source | deterministic linkage found (Y/N) | coverage | confidence | recommended action |
| --- | --- | --- | --- | --- |
| Combined non-zero candidate cohort classification (`7` cohorts) | Y (split) | `4/7` true FW->Sea, `3/7` reverse-flow FW-only | High | Keep family split explicit in acceptance reporting; do not aggregate into one policy signal |
| Persistent FAIL cohort set with `coverage`/`marine_target` failures (`3` cohorts) | N (for FW->Sea) | `0/3` deterministic FW->Sea; all `input_to_sales`, `fw->fw` | High | Exclude from FW->Sea policy evidence and track as reverse-flow blockers |
| Reverse-flow row evidence (`3` rows) | N (for FW->Sea) | source/target stage counts are FW-only (`{"fw":x}` -> `{"fw":y}`) | High | Keep as diagnostics only; no auto-link promotion |
| True FW->Sea candidate family (`3` PASS + `1` sparse) | Y | deterministic coverage `1.000`, marine ratio `1.000` on all `4` | High (3 PASS), Medium-High (1 sparse) | Use as tooling evidence only; maintain strict evidence floor for release |
| Strict vs combined persistence check | Y (negative evidence stability) | reverse-flow signature unchanged in both profiles | High | Treat blocker family as structural, not threshold tuning noise |

## Tooling-only diagnostics enhancement (proposal)

Justified by deterministic evidence above.

Proposed enhancement to acceptance reporting (`fwsea_endpoint_gate_matrix` outputs):
1. Add per-cohort `blocker_family` classification:
   - `reverse_flow_fw_only`
   - `true_fw_to_sea_candidate`
   - `true_fw_to_sea_sparse_evidence`
   - `source_consolidation_candidate`
   - `other_or_unknown`
2. Add matrix-level family totals and family-specific cohort lists in markdown + JSON.
3. Add `policy_evidence_eligible` flag (`true` only for FW->Sea candidate families).

This remains tooling-only diagnostics and does not alter runtime behavior.

## GO / NO-GO decision

1. **GO (tooling diagnostics only):**
   - proceed with blocker-family classification in acceptance reporting artifacts.
2. **NO-GO (migration policy):**
   - no global FW/Sea auto-link policy promotion from this follow-up alone.
3. **NO-GO (runtime):**
   - no runtime API/UI FishTalk coupling changes.

## Unresolved risks

1. FishTalk DB evidence remains strong but not complete for all application semantics; GUI-derived behavior may still include app-layer interpretation not fully materialized in SQL artifacts.
2. One true FW->Sea candidate cohort (`StofnFiskur okt. 2024`) remains low-volume (`candidate_rows=2`) and below strict evidence floor.
3. Broad FW20 cohort-level PASS coverage remains limited under strict acceptance profile.

## Next deterministic step

1. Implement blocker-family classification directly in matrix tooling outputs (diagnostic-only).
2. Re-run strict + diagnostic matrix and verify:
   - reverse-flow family remains excluded from FW->Sea policy evidence,
   - candidate family totals are explicit and reproducible.
3. For any cohort that remains ambiguous after family classification, run local SQL tracing (Extended Events) on corresponding Activity Explorer workflows before policy changes.

## Artifacts

- `/Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/migration/analysis_reports/2026-02-12/fw20_partb_high_signal_fail_cohort_followup_2026-02-12.md`
- `/Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/migration/analysis_reports/2026-02-12/fw20_endpoint_nonzero_candidate_classification_2026-02-12.tsv`
- `/Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/migration/analysis_reports/2026-02-12/fw20_endpoint_reverse_flow_rows_2026-02-12.tsv`
- `/Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/migration/analysis_reports/2026-02-12/fw20_endpoint_nonzero_candidate_classification_2026-02-12.summary.json`
