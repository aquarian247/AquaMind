# FWSEA Trace Target Pack

## Scope

- Matrix summary: `/Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/migration/analysis_reports/2026-02-12/fw20_endpoint_gate_matrix_diag_source3_min4_with_blocker_family_2026-02-12/fw20_endpoint_gate_matrix.summary.json`
- CSV directory: `/Users/aquarian247/Projects/AquaMind/scripts/migration/data/extract`
- Classification filter: reverse_flow_fw_only
- Trace target rows: 3
- Unique operation IDs: 6

## Target Mix

- classification `reverse_flow_fw_only`: 3
- reason `direction_mismatch`: 3
- direction `input_to_sales`: 3

| batch | class | reason | direction | sales op (type/time) | input op (type/time) | sales params | input params | sales stage mix | input stage mix | delta min |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | ---: |
| BF mars 2025 | reverse_flow_fw_only | direction_mismatch | input_to_sales | 68E185BA-CCA3-4981-BAF1-0976CC11B8BB (t7 @ 2025-03-11 10:00:01) | 7AE24FFE-A8A6-40DE-B8B4-0776C9274637 (t5 @ 2025-03-11 23:21:22) | 184:1,220:37 | 184:1 | fw:73 | fw:1 | 801 |
| BF oktober 2025 | reverse_flow_fw_only | direction_mismatch | input_to_sales | 112C6EDD-F14B-48EE-AD8E-0AB709BD6728 (t7 @ 2025-10-06 09:54:59) | 7A458ED6-BC39-4F37-8071-40667F768A19 (t5 @ 2025-10-09 10:14:20) | 184:1,220:4 | 184:1 | fw:8 | fw:1 | 4339 |
| Bakkafrost S-21 jan 25 | reverse_flow_fw_only | direction_mismatch | input_to_sales | A5D37465-7D85-4313-813E-3AD59EC2000B (t7 @ 2025-01-06 15:08:04) | CDF4B384-2F03-4827-B562-B1AF9A0A0019 (t5 @ 2025-01-06 15:08:04) | 184:1,220:17 | 184:7 | fw:17 | fw:7 | 0 |

## XE Target Operation IDs

Use this ID set in `OperationID` predicates for SQL trace capture.

- `112C6EDD-F14B-48EE-AD8E-0AB709BD6728`
- `68E185BA-CCA3-4981-BAF1-0976CC11B8BB`
- `7A458ED6-BC39-4F37-8071-40667F768A19`
- `7AE24FFE-A8A6-40DE-B8B4-0776C9274637`
- `A5D37465-7D85-4313-813E-3AD59EC2000B`
- `CDF4B384-2F03-4827-B562-B1AF9A0A0019`

## Artifacts

- Trace target TSV: `/Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/migration/analysis_reports/2026-02-12/fw20_reverse_flow_trace_target_pack_2026-02-12.tsv`
- Trace target JSON: `/Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/migration/analysis_reports/2026-02-12/fw20_reverse_flow_trace_target_pack_2026-02-12.summary.json`
