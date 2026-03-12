# FW Hardening Canaries + Next Session Start (2026-03-09)

## Why this handoff exists

- The latest March 5 handoffs stop before the FW hardening work done in this session.
- This session found that several FW cohorts that looked directionally correct still had real transfer and assignment-semantic defects.
- The next session should continue FW hardening first, then resume FW->Sea only from a cleaner base.

## Executive state

- FW->Sea discovery result still stands:
  - FishTalk sales/InternalDelivery evidence is the strongest deterministic FW->Sea linkage signal.
  - When explicit sales evidence is absent, endpoint semantics can still be used, but only as lower-confidence evidence.
- Broad FW->Sea continuation should remain paused until the current FW canaries are manually reviewed.
- The replay-safe FW transfer default is now:
  - `--expand-subtransfer-descendants --transfer-edge-scope source-in-scope`
- Two important FW defects were fixed in code:
  - chained SubTransfers split-leg loss under older `internal-only` replay,
  - misleading same-container same-stage culling-only residual tail assignments.

## What was done

### 1. FW transfer split-leg bug fixed

- Root cause:
  - older replay behavior could preserve only the first direct SubTransfers leg and miss sibling split legs in chains like `SourcePopBefore -> SourcePopAfter -> DestPopAfter`.
  - this showed up clearly in S03 canary batch `1344`, where legs like `806 -> 903`, `802 -> 901`, and `801 -> 901` were missing.
- Fix:
  - `scripts/migration/tools/pilot_migrate_component_transfers.py` now expands root-source conservation edges before scope filtering.
  - `scripts/migration/tools/pilot_migrate_input_batch.py` and the runbooks now treat `source-in-scope` as the replay-safe FW default.

### 2. Wave 1 FW transfer reruns executed

- Transfer-only reruns were applied for:
  - `1344` `Stofnfiskur Des 23 - Vár 2024` (`S03 Norðtoftir`)
  - `1348` `Stofnfiskur S-21 feb24 - Vár 2024` (`S21 Viðareiði`)
  - `1349` `Stofnfiskur S-21 juni24 - Summar 2024` (`S21 Viðareiði`)
  - `1352` `Stofnfiskur desembur 2023 - Vár 2024` (`S24 Strond`)
- Result artifact:
  - `aquamind/docs/progress/migration/analysis_reports/2026-03-06/fw_wave1_transfer_rerun_result_2026-03-06.md`

### 3. `1352` cleanup and false FW->Sea experiment removal

- The manual experimental `Stofnfiskur Mars 2023` targeted apply produced a non-canonical dev batch (`1361`) with incomplete FW stage coverage.
- That experimental batch was removed from `migr_dev`.
- `1352` was checked instead and the real defect was repaired:
  - its `Egg&Alevin` assignments existed but had zero counts.
- Cleanup artifacts:
  - `aquamind/docs/progress/migration/analysis_reports/2026-03-06/s24_fw_batch_1352_and_manual_1361_cleanup_notes.md`
  - `aquamind/docs/progress/migration/analysis_reports/2026-03-06/creation_assignment_repair_run_2026-03-06.json`
  - `aquamind/docs/progress/migration/analysis_reports/2026-03-06/creation_assignment_repair_guarded_dryrun_2026-03-06.json`

### 4. `1344` culling-tail semantic defect fixed

- Problem:
  - small trailing fry assignments in containers like `501`, `502`, `503`, `505`, `506`, `507`, `510`, `511` looked like real assignment fragments in AquaMind, but in FishTalk they were effectively culling tails.
- Fix:
  - fold same-container same-stage residual `SourcePopAfter` rows back into the predecessor assignment when they exist only to be fully culled.
  - reattach the culling `MortalityEvent` to the predecessor assignment.
- Result:
  - `17` eligible culling tails were folded back for `1344`.
  - the misleading standalone tail assignments are gone as a defect class.
- Artifacts:
  - `aquamind/docs/progress/migration/analysis_reports/2026-03-09/1344_culling_tail_analysis.md`
  - `aquamind/docs/progress/migration/analysis_reports/2026-03-09/1344_culling_tail_foldback_result.md`

### 5. FW hardening queue materialized as code + report

- The remaining FW cleanup work is now classified by defect class instead of relying on transcript memory.
- Queue tool:
  - `scripts/migration/tools/build_fw_hardening_queue.py`
- Queue artifacts:
  - `aquamind/docs/progress/migration/analysis_reports/2026-03-06/fw_hardening_queue_2026-03-06.md`
  - `aquamind/docs/progress/migration/analysis_reports/2026-03-06/fw_hardening_queue_2026-03-06.json`

## Current canary review state

- `1344` `Stofnfiskur Des 23 - Vár 2024` (`S03 Norðtoftir`)
  - human review in progress,
  - overall FW progression looks promising,
  - transfer split-leg loss fixed,
  - culling-tail semantics fixed,
  - zero-count bridge rows may still remain as a separate caveat.
- `1348` `Stofnfiskur S-21 feb24 - Vár 2024` (`S21 Viðareiði`)
  - pending manual review.
- `1349` `Stofnfiskur S-21 juni24 - Summar 2024` (`S21 Viðareiði`)
  - pending manual review.
- `1352` `Stofnfiskur desembur 2023 - Vár 2024` (`S24 Strond`)
  - pending manual review after egg-count repair and transfer rerun.

## Policy/doc state for next session

- Treat handoffs as dated evidence only.
- Treat `scripts/migration/tools/README.md` as the operator runbook.
- Treat `aquamind/docs/progress/migration/MIGRATION_CANONICAL.md` as the policy/invariants file.
- Treat the code as the mechanical source of truth.
- `aquamind/docs/progress/migration/DATA_MAPPING_DOCUMENT.md` has been corrected so transfer-rich replay now points to `source-in-scope` and the culling-tail fold-back rule is documented.

## Recommended next move

1. Finish manual AquaMind vs FishTalk review of the four FW canaries:
   - `1344`, `1348`, `1349`, `1352`
2. If the canaries are acceptable, run Wave 2 transfer-only reruns for the remaining `17` exposed mapped-scope FW batches from the hardening queue.
3. Do not resume broad FW->Sea continuation yet.
4. When FW->Sea work resumes:
   - prefer sales/InternalDelivery evidence first,
   - treat semantic endpoint-pairing as secondary evidence where sales are absent,
   - do not force a single `FW batch -> Sea batch` naming assumption when FishTalk actually emits many marine-side cohorts.

## Suggested next-session starter prompt

Read only:
- `aquamind/docs/progress/migration/handoffs/HANDOFF_2026-03-09_FW_HARDENING_CANARIES_AND_NEXT_SESSION_START.md`
- `scripts/migration/tools/README.md`
- `aquamind/docs/progress/migration/MIGRATION_CANONICAL.md`
- `aquamind/docs/progress/migration/DATA_MAPPING_DOCUMENT.md`
- `aquamind/docs/progress/migration/analysis_reports/2026-03-06/fw_hardening_queue_2026-03-06.md`

Then:
- continue manual FW review of canaries `1344`, `1348`, `1349`, `1352` in AquaMind vs FishTalk,
- record concrete defects only,
- if the canaries pass, execute Wave 2 FW transfer-only reruns from the hardening queue,
- keep FW->Sea broad continuation paused until FW review is accepted.
