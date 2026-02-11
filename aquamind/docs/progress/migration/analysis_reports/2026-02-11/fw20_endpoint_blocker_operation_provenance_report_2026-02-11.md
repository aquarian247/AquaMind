# FW20 Endpoint Blocker Operation Provenance (2026-02-11)

## Scope
Targeted deterministic provenance drill-down for strict-profile FW20 blocker cohorts with non-zero candidate rows and failed `coverage` and/or `marine_target` gates.

Selected cohorts (`5`):
- BF mars 2025
- BF oktober 2025
- Bakkafrost S-21 jan 25
- Benchmark Gen. Septembur 2024
- StofnFiskur okt. 2024

## Command A (exact): CSV-based blocker provenance extraction
```bash
python - << 'PY'
import json,csv,pathlib,collections
base=pathlib.Path('/Users/aquarian247/Projects/AquaMind')
analysis=base/'aquamind/docs/progress/migration/analysis_reports/2026-02-11'
out_tsv=analysis/'fw20_endpoint_blocker_operation_provenance_2026-02-11.tsv'
out_json=analysis/'fw20_endpoint_blocker_operation_provenance_2026-02-11.summary.json'

matrix=json.loads((analysis/'fw20_endpoint_gate_matrix_2026-02-11/fw20_endpoint_gate_matrix.summary.json').read_text())['rows']
selected=[r for r in matrix if r['candidate_rows']>0 and (('coverage' in r['failed_gates']) or ('marine_target' in r['failed_gates']))]

extract=base/'scripts/migration/data/extract'
def load_csv(name):
    with (extract/name).open() as f:
        return list(csv.DictReader(f))

ops_by={r['OperationID'].upper():r for r in load_csv('internal_delivery_operations.csv') if r.get('OperationID')}

op_to_pops=collections.defaultdict(list)
for r in load_csv('internal_delivery_actions.csv'):
    op=(r.get('OperationID') or '').upper(); pop=(r.get('PopulationID') or '').upper()
    if op and pop: op_to_pops[op].append(pop)

op_to_paramids=collections.defaultdict(collections.Counter)
op_to_220_guids=collections.defaultdict(set)
for r in load_csv('internal_delivery_action_metadata.csv'):
    op=(r.get('OperationID') or '').upper(); pid=(r.get('ParameterID') or '').strip(); guid=(r.get('ParameterGuid') or '').upper()
    if op and pid: op_to_paramids[op][pid]+=1
    if op and pid=='220' and guid: op_to_220_guids[op].add(guid)

contact_name_by_id={(r.get('ContactID') or '').upper():(r.get('Name') or '').strip() for r in load_csv('contacts.csv') if r.get('ContactID')}
op_to_pl=collections.Counter((r.get('OperationID') or '').upper() for r in load_csv('population_links.csv') if r.get('OperationID'))
op_to_st=collections.Counter((r.get('OperationID') or '').upper() for r in load_csv('sub_transfers.csv') if r.get('OperationID'))
pop_to_container={(r.get('PopulationID') or '').upper():(r.get('ContainerID') or '').upper() for r in load_csv('populations.csv') if r.get('PopulationID')}
container_to_stage={(r.get('ContainerID') or '').upper():(r.get('ProdStage') or '').strip() for r in load_csv('grouped_organisation.csv') if r.get('ContainerID')}
optype_text={(r.get('OperationType') or '').strip():(r.get('Text') or '').strip() for r in load_csv('public_operation_types.csv')}

def stage_class(prod):
    up=(prod or '').upper()
    if 'MARINE' in up: return 'marine'
    if 'HATCHERY' in up or 'FRESH' in up or 'FW' in up: return 'fw'
    return 'unknown'
def op_stage_mix(opid):
    c=collections.Counter()
    for pid in op_to_pops.get(opid,[]):
        c[stage_class(container_to_stage.get(pop_to_container.get(pid,''),''))]+=1
    return dict(c)
def top_params(opid,limit=10):
    c=op_to_paramids.get(opid,collections.Counter())
    return ';'.join(f"{k}:{v}" for k,v in c.most_common(limit))
def param220_contacts(opid):
    vals=[]
    for gid in sorted(op_to_220_guids.get(opid,set())):
        vals.append(contact_name_by_id.get(gid,f'UNKNOWN:{gid}'))
    return ';'.join(vals)

records=[]; reason_counts=collections.Counter(); reason_by_batch=collections.defaultdict(collections.Counter)
for r in selected:
    gate=json.loads((analysis/'fw20_endpoint_gate_matrix_2026-02-11'/r['gate_summary']).read_text())
    for ex in gate.get('examples',[]):
        if ex.get('deterministic'): continue
        reason=ex.get('reason','') or ''
        reason_counts[reason]+=1; reason_by_batch[r['batch_name']][reason]+=1
        sales=(ex.get('sales_operation_id') or '').upper(); inp=(ex.get('input_operation_id') or '').upper()
        srow=ops_by.get(sales,{}); irow=ops_by.get(inp,{})
        records.append({
            'batch_name': r['batch_name'],'component_key': r['component_key'],'failed_gates': ','.join(r.get('failed_gates') or []),
            'candidate_rows': r.get('candidate_rows'),'deterministic_rows': r.get('deterministic_rows'),'deterministic_coverage': r.get('deterministic_coverage'),'ambiguous_rows': r.get('ambiguous_rows'),
            'reason': reason,'direction': ex.get('direction',''),'source_component_population_count': ex.get('source_component_population_count',''),'target_population_count': ex.get('target_population_count',''),
            'sales_operation_id': sales,'input_operation_id': inp,
            'sales_operation_type': srow.get('OperationType',''),'sales_operation_type_text': optype_text.get(srow.get('OperationType',''),''),
            'input_operation_type': irow.get('OperationType',''),'input_operation_type_text': optype_text.get(irow.get('OperationType',''),''),
            'sales_start_time': srow.get('StartTime',''),'input_start_time': irow.get('StartTime',''),
            'sales_stage_mix': json.dumps(op_stage_mix(sales), sort_keys=True),'input_stage_mix': json.dumps(op_stage_mix(inp), sort_keys=True),
            'sales_params': top_params(sales),'input_params': top_params(inp),
            'sales_has_184': '184' in op_to_paramids.get(sales,{}),'sales_has_220': '220' in op_to_paramids.get(sales,{}),'input_has_184': '184' in op_to_paramids.get(inp,{}),'input_has_220': '220' in op_to_paramids.get(inp,{}),
            'sales_220_contacts': param220_contacts(sales),'input_220_contacts': param220_contacts(inp),
            'sales_population_link_rows': op_to_pl.get(sales,0),'input_population_link_rows': op_to_pl.get(inp,0),
            'sales_subtransfer_rows': op_to_st.get(sales,0),'input_subtransfer_rows': op_to_st.get(inp,0),
        })

fields=['batch_name','component_key','failed_gates','candidate_rows','deterministic_rows','deterministic_coverage','ambiguous_rows','reason','direction','source_component_population_count','target_population_count','sales_operation_id','input_operation_id','sales_operation_type','sales_operation_type_text','input_operation_type','input_operation_type_text','sales_start_time','input_start_time','sales_stage_mix','input_stage_mix','sales_params','input_params','sales_has_184','sales_has_220','input_has_184','input_has_220','sales_220_contacts','input_220_contacts','sales_population_link_rows','input_population_link_rows','sales_subtransfer_rows','input_subtransfer_rows']
with out_tsv.open('w', newline='') as f:
    w=csv.DictWriter(f, fieldnames=fields, delimiter='\t'); w.writeheader(); w.writerows(records)
summary={'selected_cohort_count':len(selected),'selected_cohorts':[{'batch_name':r['batch_name'],'component_key':r['component_key'],'failed_gates':r.get('failed_gates'),'candidate_rows':r.get('candidate_rows'),'deterministic_rows':r.get('deterministic_rows'),'deterministic_coverage':r.get('deterministic_coverage'),'ambiguous_rows':r.get('ambiguous_rows')} for r in selected],'non_deterministic_row_count':len(records),'reason_counts':dict(reason_counts),'reason_counts_by_batch':{k:dict(v) for k,v in reason_by_batch.items()},'records_tsv':str(out_tsv)}
out_json.write_text(json.dumps(summary, indent=2, sort_keys=True))
print('Wrote',out_tsv)
print('Wrote',out_json)
print('selected_cohort_count',len(selected))
print('non_deterministic_row_count',len(records))
print('reason_counts',dict(reason_counts))
PY
```

### Command A output (exact)
```text
Wrote /Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/migration/analysis_reports/2026-02-11/fw20_endpoint_blocker_operation_provenance_2026-02-11.tsv
Wrote /Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/migration/analysis_reports/2026-02-11/fw20_endpoint_blocker_operation_provenance_2026-02-11.summary.json
selected_cohort_count 5
non_deterministic_row_count 6
reason_counts {'direction_mismatch': 3, 'source_candidate_count_out_of_bounds': 3}
```

## Command B (exact): local SQL provenance cross-check for blocker operation IDs
```bash
cat /Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/migration/analysis_reports/2026-02-11/fw20_endpoint_blocker_operation_provenance_query_2026-02-11.sql \
  | docker exec -i sqlserver /opt/mssql-tools18/bin/sqlcmd \
      -b -C -S localhost,1433 -U sa -P '<REDACTED>' -d FishTalk -W -w 400 -s $'\t' \
  > /Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/migration/analysis_reports/2026-02-11/fw20_endpoint_blocker_operation_provenance_sql_2026-02-11.txt
```

### Command B output excerpt (exact)
```text
OP_SUMMARY ... CDF4B384-2F03-4827-B562-B1AF9A0A0019 5 Input ... ActionCount=7 Param184Rows=7 Param220Rows=0
OP_SUMMARY ... A5D37465-7D85-4313-813E-3AD59EC2000B 7 Sale ... ActionCount=34 Param184Rows=1 Param220Rows=17
...
PARAM220_CONTACT_DISTINCT ... 68E185BA-CCA3-4981-BAF1-0976CC11B8BB ... S08 Gjógv ... 37
PARAM220_CONTACT_DISTINCT ... A5D37465-7D85-4313-813E-3AD59EC2000B ... S21 Viðareiði ... 17
...
OP_EDGE_COUNTS ... 68E185BA-CCA3-4981-BAF1-0976CC11B8BB PopulationLinkRows=37 SubTransferRows=36
OP_EDGE_COUNTS ... A5D37465-7D85-4313-813E-3AD59EC2000B PopulationLinkRows=17 SubTransferRows=0
```

Full output:
- `/Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/migration/analysis_reports/2026-02-11/fw20_endpoint_blocker_operation_provenance_sql_2026-02-11.txt`

## Deterministic blocker patterns
1. `direction_mismatch` blockers (`3` rows across `3` cohorts) are all `input_to_sales`, not `sales_to_input`.
2. Those mismatch rows are `OperationType 7 (Sale)` paired with `OperationType 5 (Input)` where both sides remain FW-class (`sales_stage_mix` and `input_stage_mix` are FW-only).
3. `source_candidate_count_out_of_bounds` blockers (`3` rows across `2` cohorts) are all `sales_to_input` with `source_component_population_count=3`, `target_population_count=1`, and marine target stage on the input side.
4. All six blocker rows carry the same metadata shape: Sale-side ops include `ParameterID 184 + 220`; Input-side ops include `184` only.

## Compact findings table
| source | deterministic linkage found (Y/N) | coverage | confidence | recommended action |
| --- | --- | --- | --- | --- |
| Strict FW20 blocker row provenance (5 cohorts, 6 rows) | Y | All blocker rows classified into 2 deterministic failure families | High | Keep strict policy NO-GO; treat blockers as known structural families |
| Family A: `direction_mismatch` (`input_to_sales`) | Y (negative evidence) | 3/6 blocker rows | High | Keep expected direction strict for release gates; use as diagnostics for reverse-flow cases |
| Family B: `source_candidate_count_out_of_bounds` (`3->1`) | Y (partial positive) | 3/6 blocker rows | High | Evaluate optional diagnostic profile with `max-source-candidates=3` only; do not change release gate yet |
| SQL cross-check (`Operations`,`ActionMetaData`,`PopulationLink`,`SubTransfers`) | Y | 12 blocker operations validated | High | Keep provenance checks in tooling/reporting; no runtime coupling |

## Decision
1. **GO**: integrate blocker-provenance report artifacts into migration-tooling evidence workflow.
2. **NO-GO**: no migration-policy/tooling behavior change for FW/Sea auto-linking from these results.
3. **NO-GO**: no runtime API/UI changes.

## Artifacts
- `/Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/migration/analysis_reports/2026-02-11/fw20_endpoint_blocker_operation_provenance_2026-02-11.tsv`
- `/Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/migration/analysis_reports/2026-02-11/fw20_endpoint_blocker_operation_provenance_2026-02-11.summary.json`
- `/Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/migration/analysis_reports/2026-02-11/fw20_endpoint_blocker_operation_provenance_query_2026-02-11.sql`
- `/Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/migration/analysis_reports/2026-02-11/fw20_endpoint_blocker_operation_provenance_sql_2026-02-11.txt`
