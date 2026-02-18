# HANDOFF 2026-02-12 - FWSEA Part B High-Signal FAIL Cohort Classification

## Scope completed

Executed Part B follow-up focused on the remaining FW20 high-signal FAIL cohorts with:
- non-zero endpoint candidates, and
- persistent `coverage`/`marine_target` failures.

No runtime API/UI code changes were made.

## Evidence report

Primary report:
- `/Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/migration/analysis_reports/2026-02-12/fw20_partb_high_signal_fail_cohort_followup_2026-02-12.md`

Supporting artifacts:
- `/Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/migration/analysis_reports/2026-02-12/fw20_endpoint_nonzero_candidate_classification_2026-02-12.tsv`
- `/Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/migration/analysis_reports/2026-02-12/fw20_endpoint_reverse_flow_rows_2026-02-12.tsv`
- `/Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/migration/analysis_reports/2026-02-12/fw20_endpoint_nonzero_candidate_classification_2026-02-12.summary.json`
- `/Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/migration/analysis_reports/2026-02-12/fw20_endpoint_gate_matrix_blocker_family_tooling_integration_2026-02-12.md`
- `/Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/migration/analysis_reports/2026-02-12/fw20_endpoint_gate_matrix_with_blocker_family_2026-02-12/fw20_endpoint_gate_matrix.summary.json`
- `/Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/migration/analysis_reports/2026-02-12/fw20_endpoint_gate_matrix_diag_source3_min4_with_blocker_family_2026-02-12/fw20_endpoint_gate_matrix.summary.json`
- `/Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/migration/analysis_reports/2026-02-12/fw20_reverse_flow_trace_target_pack_2026-02-12.md`
- `/Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/migration/analysis_reports/2026-02-12/fw20_reverse_flow_trace_target_pack_2026-02-12.summary.json`
- `/Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/migration/analysis_reports/2026-02-12/fw20_reverse_flow_targeted_sql_extract_signature_2026-02-12.md`
- `/Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/migration/analysis_reports/2026-02-12/fw20_reverse_flow_xe_capture_readiness_2026-02-12.md`
- `/Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/migration/analysis_reports/2026-02-12/fw20_reverse_flow_xe_capture_selftest_2026-02-12.summary.json`
- `/Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/migration/analysis_reports/2026-02-12/fw20_reverse_flow_xe_session_status_2026-02-12.summary.json`

## Exact outcomes

1. Non-zero candidate cohorts in combined diagnostic profile (`source3 + min4`): `7`.
2. Deterministic family split:
   - `true_fw_to_sea_candidate`: `3`
   - `true_fw_to_sea_sparse_evidence`: `1`
   - `reverse_flow_fw_only`: `3`
3. Remaining high-signal persistent FAIL cohorts (`3`) are all reverse-flow/FW-only:
   - `BF mars 2025`
   - `BF oktober 2025`
   - `Bakkafrost S-21 jan 25`
4. Strict-vs-combined cross-check confirms persistence:
   - reason remains `direction_mismatch`
   - stage-pair remains `fw->fw`
   - no profile-specific drift.

## Compact findings table

| source | deterministic linkage found (Y/N) | coverage | confidence | recommended action |
| --- | --- | --- | --- | --- |
| Combined non-zero candidate cohort classification | Y (split) | `4/7` true FW->Sea, `3/7` reverse-flow FW-only | High | Keep blocker family split explicit in acceptance reporting |
| High-signal persistent FAIL cohort set (`3`) | N (for FW->Sea) | all `coverage=0.000`, `marine_target=0.000` | High | Exclude from FW->Sea policy evidence; keep as reverse-flow diagnostics |
| True FW->Sea sparse cohort (`StofnFiskur okt. 2024`) | Y | `2/2` deterministic rows but below evidence floor | Medium-High | Keep strict evidence floor; treat as low-volume candidate only |
| Strict vs combined persistence cross-check | Y (negative evidence) | reverse-flow signature unchanged | High | Treat reverse-flow blockers as structural, not threshold artifacts |

## GO / NO-GO

1. **GO (tooling diagnostics integration):**
   - Add blocker-family classification to acceptance reporting artifacts.
2. **NO-GO (migration policy):**
   - No global FW/Sea auto-link promotion based on this follow-up.
3. **NO-GO (runtime):**
   - No runtime API/UI coupling changes.

## Unresolved risks

1. FishTalk DB still may not expose all application-derived semantics for endpoint intent.
2. Sparse-candidate positive cohorts remain sensitive to evidence-floor policy.
3. Overall strict-profile FW20 pass coverage remains low.

## Next deterministic step

1. DONE: blocker-family fields are now published in `fwsea_endpoint_gate_matrix` JSON/TSV/markdown outputs.
2. DONE: strict + combined (`source3 + min4`) reruns completed with stable family-level split.
3. DONE: deterministic reverse-flow trace-target pack published for all persistent blocker cohorts (`3` rows, `6` operation IDs), including operation type, timing, stage-class and metadata signatures.
4. DONE: read-only targeted SQL extraction for the same `6` operation IDs confirms stable reverse-flow operation signatures directly from source tables.
5. DONE: local Extended Events tooling helper is in place and validated with self-test capture + operation-id hit detection.
6. Next: run Activity Explorer GUI interactions while XE session is armed, then reconcile post-GUI captured SQL signatures against `InternalDelivery`/`ActionMetaData` evidence before any policy changes.

## Guardrails preserved

- Runtime remains FishTalk-agnostic.
- FW and Sea remain unlinked by default in migration policy/tooling release behavior.
- External-mixing default remains `10.0`.
