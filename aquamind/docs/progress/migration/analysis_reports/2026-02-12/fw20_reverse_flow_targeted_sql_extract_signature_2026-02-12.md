# FW20 reverse-flow targeted SQL extract signature

Date: 2026-02-12  
Scope: source-confirm reverse-flow blocker operation signatures using read-only targeted SQL extraction for the 6 operation IDs from the reverse-flow trace target pack.

## Inputs

- Trace target pack:
  - `/Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/migration/analysis_reports/2026-02-12/fw20_reverse_flow_trace_target_pack_2026-02-12.md`
  - `/Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/migration/analysis_reports/2026-02-12/fw20_reverse_flow_trace_target_pack_2026-02-12.summary.json`

## Exact command executed

```bash
python /Users/aquarian247/Projects/AquaMind/scripts/migration/tools/targeted_action_extract.py \
  --sql-profile fishtalk_readonly \
  --operation-ids "112C6EDD-F14B-48EE-AD8E-0AB709BD6728,68E185BA-CCA3-4981-BAF1-0976CC11B8BB,7A458ED6-BC39-4F37-8071-40667F768A19,7AE24FFE-A8A6-40DE-B8B4-0776C9274637,A5D37465-7D85-4313-813E-3AD59EC2000B,CDF4B384-2F03-4827-B562-B1AF9A0A0019" \
  --include-operations \
  --output-dir "/Users/aquarian247/Projects/AquaMind/scripts/migration/data/extract/targeted_actions/fw20_reverse_flow_ops_2026-02-12"
```

Observed output:

- `Wrote 125 actions .../actions_targeted.csv`
- `Wrote 6 operations .../operations_targeted.csv`
- `Wrote 755 action metadata rows .../action_metadata_targeted.csv`

## Deterministic findings

1. All 3 blocker pairs preserve the same direction/signature as matrix diagnostics:
   - `direction_mismatch`
   - `input_to_sales`
   - stage class remains FW-only on both sides.
2. For each blocker pair:
   - sales-side operation is `OperationType=7` and has broad metadata palette including `ParameterID=220`,
   - component-side input operation is `OperationType=5` and does not carry `ParameterID=220`.
3. Full `ActionMetaData` targeted extraction reveals richer per-operation metadata than the reduced
   `internal_delivery_action_metadata.csv` (which is focused on parameters `184/220` for linkage diagnostics).

## Per-operation signature summary

| operation_id | operation_type | start_time | actions | distinct populations | metadata rows | top parameter ids |
| --- | ---: | --- | ---: | ---: | ---: | --- |
| `68E185BA-CCA3-4981-BAF1-0976CC11B8BB` | 7 | 2025-03-11 10:00:01 | 74 | 73 | 407 | `1:37,18:37,119:37,10:37,11:37,90:37` |
| `7AE24FFE-A8A6-40DE-B8B4-0776C9274637` | 5 | 2025-03-11 23:21:22 | 1 | 1 | 13 | `10:1,11:1,99:1,100:1,107:1,108:1` |
| `112C6EDD-F14B-48EE-AD8E-0AB709BD6728` | 7 | 2025-10-06 09:54:59 | 8 | 8 | 44 | `10:4,11:4,90:4,96:4,177:4,220:4` |
| `7A458ED6-BC39-4F37-8071-40667F768A19` | 5 | 2025-10-09 10:14:20 | 1 | 1 | 13 | `10:1,11:1,99:1,100:1,107:1,108:1` |
| `A5D37465-7D85-4313-813E-3AD59EC2000B` | 7 | 2025-01-06 15:08:04 | 34 | 17 | 187 | `10:17,11:17,90:17,96:17,177:17,220:17` |
| `CDF4B384-2F03-4827-B562-B1AF9A0A0019` | 5 | 2025-01-06 15:08:04 | 7 | 7 | 91 | `10:7,11:7,99:7,100:7,107:7,108:7` |

## Decision impact

- Supports existing decision: keep these cohorts excluded from FW->Sea policy evidence.
- Strengthens XE readiness: operation IDs and expected metadata signatures are now source-confirmed and reproducible.
- No runtime/API/UI change.
- No migration policy change.

## Artifacts

- `/Users/aquarian247/Projects/AquaMind/scripts/migration/data/extract/targeted_actions/fw20_reverse_flow_ops_2026-02-12/actions_targeted.csv`
- `/Users/aquarian247/Projects/AquaMind/scripts/migration/data/extract/targeted_actions/fw20_reverse_flow_ops_2026-02-12/operations_targeted.csv`
- `/Users/aquarian247/Projects/AquaMind/scripts/migration/data/extract/targeted_actions/fw20_reverse_flow_ops_2026-02-12/action_metadata_targeted.csv`

