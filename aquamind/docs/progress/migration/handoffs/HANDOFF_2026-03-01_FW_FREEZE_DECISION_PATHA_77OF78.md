# HANDOFF 2026-03-01 - FW freeze decision (Path A strict 77/78)

## Scope
- Execute approved **Path A** freeze flow: keep strict `77/78`, do not replay the failed key.
- Reconfirm current `migr_dev` state with fresh verification evidence.
- Publish final FW freeze recommendation with explicit risk acceptance and deterministic Sea/FWSEA next actions.

## Fresh live-state confirmation (2026-03-01)
### Commands executed
1. `python3 scripts/migration/tools/migration_counts_report.py`
2. `python3 scripts/migration/tools/migration_verification_report.py`
3. Direct live DB count check for mix tables:
   - `batch_batchmixevent`
   - `batch_batchmixeventcomponent`
4. Strict preflight re-check of the known failed key:
   - `python3 scripts/migration/tools/pilot_migrate_input_batch.py --batch-key "SSF_SF 23 Q2|2|2023" --use-csv scripts/migration/data/extract --migration-profile fw_default --skip-environmental --skip-feed-inventory`

### New artifacts captured
- `scripts/migration/output/fw78_freeze_counts_20260301_204025.txt`
- `scripts/migration/output/fw78_freeze_verification_20260301_204025.txt`
- `scripts/migration/output/fw78_freeze_mix_counts_20260301_204203.txt`
- `scripts/migration/output/fw78_freeze_failed_key_preflight_20260301_204212.txt`

### Reconfirmed key counts (current `migr_dev`)
- `batch_batchtransferworkflow = 18`
- `batch_transferaction = 280`
- `batch_batchmixevent = 169`
- `batch_batchmixeventcomponent = 473`

### Verification status (current run)
- Verification summary: `24` core tables passed, `1` core table failed.
- Expected required-table fail remains:
  - `environmental_environmentalreading = 0`
- This remains aligned with the intentional replay profile choice: `--skip-environmental`.

## Strict exception (77/78) confirmation
- Failed strict key remains:
  - `SSF_SF 23 Q2|2|2023`
- Fresh strict preflight output confirms the same mismatch family:
  - InputProjects sites: `N222 Plocrapol`, `N224 Scadabay`, `N225 Scotasay`
  - Ext_Inputs/member sites: `N222 Plocrapol`, `N225 Scotasay`
  - Failure text: station preflight mismatch; override path is `--allow-station-mismatch`.
- The failure occurs at preflight guard level and is not evidence of transfer/mix replay regression.

## Transfer + mix evidence (Path B objective)
- Execution summary artifact:
  - `scripts/migration/output/fw_pathb_fw78_execution_summary_20260228_205232.json`
- Coverage artifact:
  - `scripts/migration/output/transfer_mix_coverage_pathb_fw78_20260228_204924.json`
- Evidence remains stable and positive:
  - completed transfer actions scanned: `280`
  - `allow_mixed=True`: `169` (`60.36%`)
  - mix-event-linked actions: `169` (`60.36%`)
  - non-mix actions: `111`
  - mix events/components: `169 / 473`

## Fixed-source row-recheck (parity gate)
- Artifact:
  - `scripts/migration/output/fw_b_class_row_recheck_pathb_fw78_migrdb_20260228_204846.json`
- Board summary:
  - `before_mismatch_rows=36`
  - `after_mismatch_rows=42`
  - `delta=+6`
  - taxonomy after: `A=0, B=39, C=3, D=0`
- Gate result:
  - **A remains 0 (parity gate preserved).**

### Top residual batches (updated)
1. `StofnFiskur S-21 apr 25` -> `7` (`B`)
2. `Bakkafrost S-21 okt 25` -> `5` (`B`)
3. `Stofnfiskur Nov 2024` -> `5` (`B`)
4. `Stofnfiskur feb 2025` -> `5` (`B`)
5. `Stofnfiskur mai 2024` -> `5` (`B`)

## Final FW freeze recommendation
- **Recommendation: GO (Path A)** for FW freeze checkpoint with explicit strict-run risk acceptance.
- Rationale:
  1. Transfer objective is met and stable (`TransferAction=280`).
  2. Mix lineage objective is met and stable (`BatchMixEvent=169`, `BatchMixEventComponent=473`).
  3. Hard parity guard remains intact (`A=0`).
  4. The lone strict failure is a known station-preflight metadata mismatch, not transfer/mix path breakage.

## Accepted residual risks (explicit)
1. Strict completion stamp remains `77/78` until optional one-key replay with override.
2. Verification will continue to show `environmental_environmentalreading=0` while using `--skip-environmental`.
3. Residual board remains non-zero (`B=39`, `C=3`), though parity gate `A=0` is preserved.
4. `migration_semantic_validation_report.py` remains component-scoped (no single global no-arg gate).

## Deterministic next actions for Sea + FWSEA linkage (no heuristics)
### 1) Build directional parity evidence (sales-out vs input-in)
```bash
stamp=$(date +%Y%m%d_%H%M%S) && python3 scripts/migration/tools/fwsea_sales_directional_parity_extract.py \
  --sql-profile fishtalk_readonly \
  --only-fw-sources \
  --output-csv "scripts/migration/output/fwsea_sales_directional_parity_${stamp}.csv" \
  --summary-json "scripts/migration/output/fwsea_sales_directional_parity_${stamp}.json" \
  --summary-md "scripts/migration/output/fwsea_sales_directional_parity_${stamp}.md"
```

### 2) Build deterministic linkage scoring extract
```bash
stamp=$(date +%Y%m%d_%H%M%S) && python3 scripts/migration/tools/fwsea_sales_linkage_scoring_extract.py \
  --sql-profile fishtalk_readonly \
  --only-fw-sources \
  --output-csv "scripts/migration/output/fwsea_sales_linkage_scoring_${stamp}.csv" \
  --summary-json "scripts/migration/output/fwsea_sales_linkage_scoring_${stamp}.json" \
  --summary-md "scripts/migration/output/fwsea_sales_linkage_scoring_${stamp}.md"
```

### 3) Run per-component deterministic endpoint gate checks
```bash
python3 scripts/migration/tools/fwsea_endpoint_pairing_gate.py \
  --csv-dir scripts/migration/data/extract \
  --report-dir <component_report_dir> \
  --component-key <component_key> \
  --expected-direction sales_to_input \
  --require-evidence \
  --require-marine-target \
  --check-gates \
  --output scripts/migration/output/fwsea_endpoint_gate_<component_key>.md \
  --summary-json scripts/migration/output/fwsea_endpoint_gate_<component_key>.summary.json
```

### 4) Generate cohort gate matrix
```bash
stamp=$(date +%Y%m%d_%H%M%S) && python3 scripts/migration/tools/fwsea_endpoint_gate_matrix.py \
  --analysis-dir aquamind/docs/progress/migration/analysis_reports \
  --report-dir-root scripts/migration/output/input_batch_migration \
  --csv-dir scripts/migration/data/extract \
  --output-dir "scripts/migration/output/fwsea_endpoint_gate_matrix_${stamp}" \
  --output-md "scripts/migration/output/fwsea_endpoint_gate_matrix_${stamp}.md"
```

### 5) Build deterministic trace-target pack from matrix output
```bash
stamp=$(date +%Y%m%d_%H%M%S) && python3 scripts/migration/tools/fwsea_trace_target_pack.py \
  --matrix-summary-json <matrix_output_dir>/fw20_endpoint_gate_matrix.summary.json \
  --csv-dir scripts/migration/data/extract \
  --output-md "scripts/migration/output/fwsea_trace_target_pack_${stamp}.md" \
  --summary-json "scripts/migration/output/fwsea_trace_target_pack_${stamp}.json"
```

### 6) Publish deterministic linkage evidence report (component-scoped or broad)
```bash
stamp=$(date +%Y%m%d_%H%M%S) && python3 scripts/migration/tools/fwsea_deterministic_linkage_report.py \
  --csv-dir scripts/migration/data/extract \
  --output "scripts/migration/output/fwsea_deterministic_linkage_report_${stamp}.md" \
  --summary-json "scripts/migration/output/fwsea_deterministic_linkage_report_${stamp}.json"
```

### Hard rule for Sea/FWSEA continuation
- Keep linkage strictly deterministic and operation-evidence-backed.
- Do not enable or rely on heuristic FWSEA linkage paths for freeze decisioning.

## Optional fallback (only if leadership requires strict 78/78 stamp)
- Replay only the failed key with explicit override:
  - `--allow-station-mismatch`
- Then rerun:
  - `pilot_backfill_transfer_mix_events.py`
  - `migration_counts_report.py`
  - `migration_verification_report.py`
  - fixed-source row-recheck pipeline
- Accept fallback only if transfer/mix counts remain non-regressive and parity gate remains `A=0`.
