# Migration Profile Cohort Classification

- Generated: `2026-02-16 14:51:14`
- Analysis dir: `aquamind/docs/progress/migration/analysis_reports/2026-02-16`
- Summary glob: `*semantic_validation*.summary.json`
- Dedupe mode: `newest-per-component`
- Cohorts classified: `3`

## Extract preflight

- Result: `PASS`
- Horizon date: `2026-01-22`
- Status/SubTransfers skew (hours): `0.00`
- OperationStage lag (days): `4.07`

## Cohort rows

| Batch | Component key | Signatures | Recommended profile | Confidence | Gates | Outside-holder | Transition alerts | Non-bridge zeros | Zero transfer actions |
| --- | --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: |
| Bakkafrost S-21 jan 25 | `B52612BD-F18B-48A4-BF21-12B5FC246803` | `clean` | `fw_default` | `high` | PASS | 0 | 0 | 0 | 0 |
| Benchmark Gen. Desembur 2024 | `1636C683-E8F2-476D-BC21-0170CA7DCEE8` | `clean` | `fw_default` | `high` | PASS | 0 | 0 | 0 | 0 |
| StofnFiskur okt. 2024 | `F7D08CC6-083F-4CB4-9271-ECABFA6D3F2C` | `clean` | `fw_default` | `high` | PASS | 0 | 0 | 0 | 0 |

## Grouped recommendations

| Recommended profile | Signature set | Cohort count | Cohorts |
| --- | --- | ---: | --- |
| `fw_default` | `clean` | 3 | Bakkafrost S-21 jan 25, Benchmark Gen. Desembur 2024, StofnFiskur okt. 2024 |

## Notes

- No summary files were skipped.
- Create new profiles only when at least 3 cohorts share a stable failure signature and the mitigation is policy-like.
- Keep `fw_default` as baseline and treat relaxed/legacy profiles as diagnostic controls unless validated by regression gates.