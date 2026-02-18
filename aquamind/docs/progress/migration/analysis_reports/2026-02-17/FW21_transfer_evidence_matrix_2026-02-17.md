# FW21 Transfer Evidence Matrix (2026-02-17)

- Scope: strict-blocked FW21 cohorts rerun with controlled mismatch override.
- Source policy: inter-station FW->FW transfer treated as normal cohort behavior when evidenced.
- Backup horizon: `2026-01-22`

| Cohort | Station anchor | Member-derived sites | Recovery migration | Recovery semantic | Transfer evidence status |
| --- | --- | --- | --- | --- | --- |
| `SF AUG 23\|15\|2023` | `FW21 Couldoran` | ['FW21 Couldoran', 'FW22 Applecross'] | PASS | PASS | Confirmed in FT export (Couldoran -> Applecross) |
| `SF NOV 23\|17\|2023` | `FW21 Couldoran` | ['FW21 Couldoran', 'FW22 Applecross'] | PASS | PASS | Confirmed in FT export (Couldoran -> Applecross) |
| `NH FEB 24\|1\|2024` | `FW21 Couldoran` | ['BRS3 Geocrab', 'FW21 Couldoran'] | PASS | PASS | Not directly confirmed in provided FT screenshots; migration preflight shows mixed sites |
| `SF AUG 24\|3\|2024` | `FW21 Couldoran` | ['FW13 Geocrab', 'FW21 Couldoran'] | PASS | PASS | Confirmed in FT export (Couldoran -> Geocrab) |

## Notes

- `SF NOV 23|17|2023` required batch-number override (`SF NOV 23 17`) due existing `SF NOV 23` name collision.
- This matrix is tooling/reporting evidence only; AquaMind runtime remains FishTalk-agnostic.

