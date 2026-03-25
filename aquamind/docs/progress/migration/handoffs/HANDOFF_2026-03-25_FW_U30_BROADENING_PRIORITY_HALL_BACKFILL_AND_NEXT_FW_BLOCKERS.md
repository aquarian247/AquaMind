# FW U30 Broadening, Priority-Hall Backfill, And Next FW Blockers (2026-03-25)

## Why this handoff exists

- The 2026-03-24 handoff said the next step was FW-only `<30 months` broadening across both geographies.
- That work is now done.
- This handoff captures:
  - the broadened FW-only state,
  - the Scotland/Faroe review outcomes,
  - the newly discovered priority-hall stage bug class and its completed backfill,
  - and the exact stop point before the next session resumes FW-only blocker work.

## Executive state

- Broad FW->Sea continuation remains paused.
- FW-only `<30 months` scope from cutoff `2026-01-22` was broadened across both geographies.
- Initial strict FW scope:
  - total rows: `161`
  - eligible: `58`
  - manual exceptions: `4`
  - blocked: `99`
- Eligible corrected-baseline transfer reruns:
  - final queue: `52`
  - result: `52/52` success
- Scotland review produced two concrete `operation`-grouping cases:
  - `SF AUG 23|15|2023`
  - `NH FEB 24|1|2024`
- A separate priority-hall stage bug class was discovered and fully closed:
  - source-side canonicalizer added,
  - `67` report dirs backfilled,
  - `63` mapped live batches backfilled,
  - final residual audits are `0` for both report artifacts and mapped live assignment stages.

## What changed in this session

### 1. Broadened FW-only scope was built and executed

- Two-geography FW-only broadening artifacts were built under `scripts/migration/output/`.
- The decisive transfer baseline from the 2026-03-24 canary closeout was reused.
- Eligible transfer-bearing FW rows were rerun successfully on that corrected baseline.

Primary evidence:

- `aquamind/docs/progress/migration/analysis_reports/2026-03-25/fw_u30_two_geo_scope_and_transfer_rerun_2026-03-25.md`

### 2. Scotland review produced real grouping evidence

- `SF AUG 23|15|2023` was initially under-migrated in `stage-bucket` mode because `FW21` hall semantics are unstable.
- Operator review established:
  - `Hatchery = Egg&Alevin`
  - `RAS = Smolt`
  - `FW22 / D2 = Post-Smolt`
  - `A`-`F` halls in `FW21` are not deterministic enough for static stage-bucket grouping
- Narrow corrective rerun in `operation` grouping restored the missing transfer complexity.
- `NH FEB 24|1|2024` became the second proven Scotland `operation`-grouping case.

Implication:

- Do not assume `stage-bucket` is safe for all Scotland `FW*` rows.
- Classify Scotland rows deliberately before transfer replay.

### 3. Priority-hall stage bug class was discovered and closed

This was the important surprise of the session.

- The bug was **not** transfer replay.
- It was stale/raw stage canonicalization in generated report artifacts.
- The user’s `SF MAY 24 [6]` review exposed it first, but the deterministic audit proved it was widespread.

What was implemented:

- shared hall-stage canonicalizer:
  - `scripts/migration/tools/hall_stage_rules.py`
- source-side input runner fix:
  - `scripts/migration/tools/pilot_migrate_input_batch.py`
- source-side stitching fix:
  - `scripts/migration/tools/input_based_stitching_report.py`
- deterministic report audit:
  - `scripts/migration/tools/audit_priority_hall_stage_reports.py`
- deterministic backfill runner:
  - `scripts/migration/tools/backfill_priority_hall_stage_queue.py`
- deterministic mapped-assignment audit:
  - `scripts/migration/tools/audit_priority_hall_assignment_stages.py`

Audit/backfill outcome:

- initial report audit:
  - `11251` mismatch rows
  - `67` affected report dirs
  - `63` already mapped live batches
- mapped batch backfill:
  - `63/63` succeeded
  - `10045` report rows corrected
  - `377` assignment lifecycle stages corrected
  - `25` batch lifecycle stages corrected
- residual report-only cleanup:
  - remaining `64` stale report rows across `4` unmapped report dirs corrected
- final audits:
  - report mismatches: `0`
  - mapped assignment mismatches: `0`

Primary evidence:

- `aquamind/docs/progress/migration/analysis_reports/2026-03-25/fw_u30_blocked_unblock_pass_2026-03-25.md`

Final verification artifacts:

- `scripts/migration/output/priority_hall_stage_audit_final_20260325.json`
- `scripts/migration/output/priority_hall_assignment_audit_final_20260325.json`

## Documentation state

Updated:

- `aquamind/docs/progress/migration/MIGRATION_CANONICAL.md`
- `aquamind/docs/progress/migration/DATA_MAPPING_DOCUMENT.md`
- `scripts/migration/tools/README.md`

These now capture:

- the FW-only broadening result and current stop point,
- the priority-hall source-stage canonicalization contract,
- the deterministic audit/backfill loop,
- and the warning not to rely on manual swimlane review for this bug class.

## Important interpretation rules for the next agent

- Treat handoffs as dated evidence only.
- Treat `scripts/migration/tools/README.md` as the operator runbook.
- Treat `MIGRATION_CANONICAL.md` as policy/invariants.
- Treat `DATA_MAPPING_DOCUMENT.md` as mapping/mechanics.
- Treat the code as the mechanical source of truth.
- Prefer evidence over assumptions.
- Do not reopen already-closed canary findings unless new evidence contradicts them.
- Do not manually re-review batches for the priority-hall stage bug class before running the deterministic audits first.
- Keep FW->Sea paused.

## What the next session should accomplish

Return to the remaining **real** FW-only blocker work, not today’s closed stage-drift class.

Priority order:

1. Rebuild or refresh the current FW-only `<30 months` blocker queue from the post-backfill state.
2. Keep the user’s scope policy:
   - active victory scope = Scotland `FW*` + Faroe `S*`
   - broodstock-oriented `BRS*` / `L*` rows remain outside the core FW victory queue unless explicitly re-admitted
3. Continue unblocking the remaining mapped/missing-map FW rows.
4. For Scotland rows, classify transfer replay mode deliberately:
   - `stage-bucket` only when hall semantics are stable,
   - `operation` when evidence shows unstable hall-stage meaning.
5. Only after FW-only scope is stabilized and accepted should FW->Sea batch mapping restart.

## Recommended kickoff prompt for the next session

Use this prompt shape:

> Continue the AquaMind FishTalk migration from the 2026-03-25 FW U30 broadening + priority-hall backfill closeout state.
>
> Read first:
> - `aquamind/docs/progress/migration/handoffs/HANDOFF_2026-03-25_FW_U30_BROADENING_PRIORITY_HALL_BACKFILL_AND_NEXT_FW_BLOCKERS.md`
> - `aquamind/docs/progress/migration/handoffs/HANDOFF_2026-03-24_FW_CANARIES_CLOSED_AND_FW_U30_BROADENING_NEXT.md`
> - `scripts/migration/tools/README.md`
> - `aquamind/docs/progress/migration/MIGRATION_CANONICAL.md`
> - `aquamind/docs/progress/migration/DATA_MAPPING_DOCUMENT.md`
>
> Operating rules:
> - Treat handoffs as dated evidence only.
> - Treat README.md as the operator runbook.
> - Treat MIGRATION_CANONICAL.md as policy/invariants.
> - Treat DATA_MAPPING_DOCUMENT.md as mapping/mechanics.
> - Treat the code as the mechanical source of truth.
> - Prefer evidence over assumptions.
> - Keep FW->Sea paused.
> - Do not reopen the priority-hall stage bug class by manual GUI review alone; use the deterministic audits first if needed.
>
> Current state already established:
> - FW canaries `1344`, `1348`, `1349`, and `1352` are PASS.
> - Two-geography FW-only `<30 months` broadening from cutoff `2026-01-22` was executed.
> - The corrected-baseline eligible transfer queue reran successfully.
> - Priority-hall source-stage drift has been backfilled to zero residual report and mapped-assignment mismatches.
> - Scotland has at least two proven `operation`-grouping rows: `SF AUG 23|15|2023` and `NH FEB 24|1|2024`.
>
> Goal for this session:
> - Stay inside freshwater-only migration.
> - Refresh the remaining FW-only blocker queue after the priority-hall backfill.
> - Continue unblocking the real remaining FW blockers inside the active victory scope (`FW*` Scotland + `S*` Faroe).
> - Separate:
>   - replay-safe rows ready for component/transfer execution,
>   - rows requiring Scotland `operation` grouping,
>   - manual exceptions,
>   - and hard blockers with concrete reasons.
>
> Execution guidance:
> - Prefer narrow, auditable reruns over broad blind replay.
> - If a new defect appears, trace the exact cause in code/artifacts, implement the narrowest justified fix, rerun the narrowest affected slice, and update evidence.
> - Record only concrete defects, concrete passes, and concrete blockers.
> - Do not restart FW->Sea mapping work in this session.
