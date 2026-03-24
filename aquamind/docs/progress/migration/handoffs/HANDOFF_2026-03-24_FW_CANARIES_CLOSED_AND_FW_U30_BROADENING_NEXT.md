# FW Canaries Closed And FW U30 Broadening Next (2026-03-24)

## Why this handoff exists

- The FW hardening review loop is now closed at the canary level.
- This handoff captures the exact replay hardenings that made the canaries pass, the one non-migration GUI finding from `1352`, and the approved next step.
- The next agent should broaden FW-only scope deliberately across both geographies, not resume broad FW->Sea work.

## Executive state

- FW canaries `1344`, `1348`, `1349`, and `1352` are now `PASS`.
- The decisive replay baseline fixes are now in `scripts/migration/tools/pilot_migrate_component_transfers.py`:
  - same-day superseded destination canonicalization onto genuinely longer-lived companion assignments only,
  - preservation of explicit `DestPopBefore -> DestPopAfter` bridge continuity edges during `source-in-scope` replay,
  - self-loop assignment-edge suppression after destination resolution.
- Wave 2 transfer-only reruns remain complete for the `15` eligible mapped-scope rows; the `4` manual-reconstruction exceptions remain intentionally excluded from bulk rerun.
- The missing Hall `J` / post-smolt tail observed in `1352` was a frontend pagination/render issue, not a backend migration defect.
- Broad FW->Sea continuation remains paused.

## What changed in this session

### 1. `1348` exposed dead-end same-day destination binding

- Result: `REAL MIGRATION DEFECT`
- Symptom: `R1`-`R4` looked like they terminated instead of flowing into the later fry/parr network.
- Cause: transfer replay bound first-leg actions onto short-lived same-day dead-end `5M` relay assignments instead of the surviving same-container companions that actually carry downstream lineage.
- Fix:
  - added same-day superseded destination canonicalization in `pilot_migrate_component_transfers.py`,
  - replay now promotes only onto a genuinely longer-lived same-day companion.
- User rechecked the GUI and confirmed the corrected egg->fry trace.

Evidence:
- `aquamind/docs/progress/migration/analysis_reports/2026-03-24/fw_1348_same_stage_superseded_destination_trace_fix_2026-03-24.md`

### 2. `1349` exposed the deeper destination-lane continuity defect

- Result: `REAL MIGRATION DEFECT`
- Initial symptom: same dead-end `R -> 5M` pattern as `1348`.
- Deeper symptom after first fix: `5M 1` arrived at `A01/A03`, but later parr redistributions were disconnected or only short-lived.
- Cause: `source-in-scope` replay kept root-source conservation edges, but dropped explicit FishTalk `DestPopBefore -> DestPopAfter` bridge continuity inside staged/0-day destination lanes.
- Fix:
  - preserve explicit `DestPopBefore -> DestPopAfter` bridge edges when both sides are in scope and distinct,
  - keep earlier contributors connected as FishTalk rolls a destination lane into successor populations.
- User rechecked the GUI and confirmed the downstream mixing/fanout looked solid after fry.

Evidence:
- `aquamind/docs/progress/migration/analysis_reports/2026-03-24/fw_1349_same_stage_superseded_destination_trace_fix_2026-03-24.md`
- `aquamind/docs/progress/migration/analysis_reports/2026-03-24/fw_1349_dest_before_bridge_continuity_fix_2026-03-24.md`

### 3. `1344` surfaced a replay regression from the new baseline

- Result: `REAL MIGRATION DEFECT`
- Symptom: canonicalization started collapsing legitimate same-day parallel siblings onto the same assignment, manufacturing assignment-to-itself transfer actions.
- Cause: same-day destination canonicalization was too broad; it did not require a truly longer-lived companion and could collapse real parallel split siblings.
- Fix:
  - canonicalize only when a longer-lived same-day companion exists,
  - skip edges where `source_assignment == dest_assignment`.
- User rechecked the GUI and confirmed `1344` looked very good, including correct final post-smolt counts.

Evidence:
- `aquamind/docs/progress/migration/analysis_reports/2026-03-24/fw_1344_bridge_baseline_rerun_and_self_loop_guard_2026-03-24.md`

### 4. `1352` verified the stabilized replay baseline

- Transfer rerun result was structurally clean:
  - no assignment-to-itself transfer actions remained,
  - no actions still targeted same-day superseded destination assignments.
- The later Hall `J` / post-smolt tail existed in both the source extract and `migr_dev`.
- The apparent UI cutoff was therefore **not a migration defect**.
- Follow-up frontend investigation confirmed the visible cutoff was caused by frontend pagination/render behavior.
- With that UI issue fixed, the user confirmed `1352` looks correct.

Evidence:
- `aquamind/docs/progress/migration/analysis_reports/2026-03-24/fw_1352_bridge_baseline_rerun_and_post_smolt_presence_check_2026-03-24.md`

## Documentation updates completed

- `aquamind/docs/progress/migration/DATA_MAPPING_DOCUMENT.md`
  - now captures the same-day superseded destination canonicalization contract,
  - the `DestPopBefore -> DestPopAfter` bridge continuity contract,
  - and the self-loop assignment-edge guard.
- `aquamind/docs/progress/migration/MIGRATION_CANONICAL.md`
  - now reflects the 2026-03-24 evidence-backed FW state and points to the new canary reports.

## Important interpretation rules for the next agent

- Treat the code as the mechanical source of truth.
- Treat handoffs as dated evidence only.
- Treat `scripts/migration/tools/README.md` as the operator runbook.
- Treat `MIGRATION_CANONICAL.md` as the policy/invariants file.
- Treat `DATA_MAPPING_DOCUMENT.md` as the mapping/mechanics document.
- Do not treat same-day zero-count rows alone as defects.
- Do treat it as a defect if a material stage-entry lane is fed only by zero-count bridge residue.
- Do not resume broad FW->Sea work until the broader FW-only `<30 months` scope is stabilized and accepted.
- Do not reopen the `1352` Hall `J` issue as a migration problem; that one belonged to the frontend layer.

## Approved next move

1. Stay inside **freshwater-only** migration.
2. Broaden scope from the current mapped Faroe tranche to **all FW batches `<30 months` from backup cutoff `2026-01-22` across both geographies**.
3. Build or verify a deterministic two-geography FW-only scope artifact from the existing input-stitching outputs.
4. Classify that broadened scope into:
   - eligible mapped / replay-safe rows,
   - manual-reconstruction exceptions,
   - rows blocked by missing report-dir / missing mapping evidence / other concrete prerequisites.
5. Rerun the eligible transfer-bearing rows on the corrected baseline.
6. Continue batch-by-batch manual GUI verification only after the rerun set is in place.
7. Return to FW->Sea batch mapping only after the broadened FW-only scope is accepted.

## Recommended kickoff for the next session

- Start from this handoff plus:
  - `aquamind/docs/progress/migration/MIGRATION_CANONICAL.md`
  - `aquamind/docs/progress/migration/DATA_MAPPING_DOCUMENT.md`
  - `scripts/migration/tools/README.md`
- Then:
  1. inventory the existing FW-only `<30 months` scope artifacts,
  2. expand them to both geographies if needed,
  3. build the broadened FW replay queue,
  4. keep FW->Sea paused.
