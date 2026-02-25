# HANDOFF 2026-02-25 - FW B wave12 next5 execution and row-recheck board

## Scope
- Continue FW B-class reduction after wave11 supplier-guard run.
- Execute targeted replay cohort: `140, 152, 153, 154, 155`.
- Preserve guardrails (`A=0`, no class-C expansion).

## Inputs
- Source board for mismatch-row recheck:
  - `scripts/migration/output/fw_policy_scope_tiebreak_postwave_wave10_next5_20260225_090255.json`
- Prior row-recheck reference:
  - `scripts/migration/output/fw_policy_scope_tiebreak_postwave_wave11_supplier_guard_row_recheck_20260225_113208.json`
- Target cohort:
  - `140` Bakkafrost feb 2024
  - `152` Bakkafrost S-21 sep24
  - `153` StofnFiskur S-21 apr 25
  - `154` StofnFiskur S-21 juli25
  - `155` Stofnfiskur S-21 feb24

## Wave12 targeted replay result
- Source mismatches: `36`
- Remaining mismatches: `8`
- Delta: `-28`

| Batch ID | Batch | Source mism | Remaining mism | Delta |
| ---: | --- | ---: | ---: | ---: |
| 140 | Bakkafrost feb 2024 | 8 | 8 | 0 |
| 152 | Bakkafrost S-21 sep24 | 7 | 0 | -7 |
| 153 | StofnFiskur S-21 apr 25 | 7 | 0 | -7 |
| 154 | StofnFiskur S-21 juli25 | 7 | 0 | -7 |
| 155 | Stofnfiskur S-21 feb24 | 7 | 0 | -7 |

## Post-wave board (row-recheck of source mismatch set)
- Source mismatch rows: `184`
- Remaining mismatch rows: `146`
- Delta vs source: `-38`
- Delta vs wave11 row-recheck (`174`): `-28`

Taxonomy (remaining):
- `A=0`
- `B=142`
- `C=4`
- `D=0`

Top remaining rationale counts:
- `component_initial_window_expected_zero=97`
- `component_seed_expected_zero=27`
- `fanout_expected_zero_bucket_size_8=8`
- `fanout_expected_zero_bucket_size_2=6`
- `fanout_expected_zero_bucket_size_4=4`
- `inactive_departure_matches_latest_nonzero_status=4`

## Updated top FishTalk culprits (post-wave12 row-recheck)
1. `140` Bakkafrost feb 2024 (`8`)
2. `156` Stofnfiskur S-21 juni24 (`7`)
3. `157` Stofnfiskur S-21 nov23 (`7`)
4. `139` Bakkafrost Okt 2023 (`6`)
5. `98` SF NOV 24 (`5`)

## Artifacts generated
- Targeted replay:
  - `scripts/migration/output/fw_b_class_targeted_replay_wave12_next5_20260225_120629.json`
  - `scripts/migration/output/fw_b_class_targeted_replay_wave12_next5_20260225_120629.md`
- Board row-recheck:
  - `scripts/migration/output/fw_policy_scope_tiebreak_postwave_wave12_next5_row_recheck_20260225_120629.json`
  - `scripts/migration/output/fw_policy_scope_tiebreak_postwave_wave12_next5_row_recheck_20260225_120629.md`
  - `scripts/migration/output/fw_policy_scope_tiebreak_postwave_wave12_next5_row_recheck_20260225_120629.csv`
- FishTalk culprits:
  - `scripts/migration/output/fw_fishtalk_culprits_wave12_top20_20260225_120629.csv`
  - `scripts/migration/output/fw_fishtalk_culprits_wave12_top20_20260225_120629.md`

## Files changed this wave
- `aquamind/docs/progress/migration/handoffs/HANDOFF_2026-02-25_FW_B_WAVE12_NEXT5_EXECUTION_AND_ROWRECHECK.md`

## Go / No-go
- Decision: **FW not yet ready** for marine continuation.
- Rationale: class-A remains `0`, but residual class-B volume is still material (`B=142` on the rechecked source mismatch set), with `140` still a confirmed non-mover.

## Recommended next step
- Run next targeted cohort:
  - `140, 156, 157, 139, 98`
- For `140`, add the next deterministic refinement for valid same-supplier multi-anchor starts across distinct dates/object hierarchies (tray/rack + standard containers), then replay `140` first before broader cohort expansion.
