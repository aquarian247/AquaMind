# FW U30 Blocked Unblock Pass (2026-03-25)

## Goal

- Advance FW-only `<30 months` work from the broadened two-geography blocked bucket without resuming FW->Sea.
- Prefer narrow, auditable steps:
  - materialize missing `input_batch_migration` report dirs without DB writes;
  - validate that `PopulationComponent` seeding unblocks transfer replay on the corrected baseline.

## 1. Missing Report-Dir Materialization

- Proof batch:
  - `Rogn aug. 2023|2|2023`
  - `pilot_migrate_input_batch.py --dry-run` passed extract preflight, passed station preflight, and created:
    - `scripts/migration/output/input_batch_migration/Rogn_aug._2023_2_2023`
- Scope pass:
  - scope file: `scripts/migration/output/fw_u30_missing_report_scope_20260325.csv`
  - log: `scripts/migration/output/fw_u30_missing_report_materialization_20260325.log`
  - attempted: `46`
  - succeeded: `40`
  - failed: `6`

### Remaining report-dir failures

- `Rogn okt 2023|3|2023`
  - member descendants cross `L01 Við Áir -> L02 Skopun`
- `MG_SF 23 Q3|3|2023`
  - member descendants cross `S331 GlenanBay -> S341 GobaBharra`
- `NH 2023|1|2024`
  - `InputProjects` shows `BRS3 Geocrab` + `FW13 Geocrab`, but `Ext_Inputs` shows only `BRS3 Geocrab`
- `GE_NH Sentinel 24 Q2|4|2024`
  - member descendants cross `N322 MaragayMor -> N324 Maaey`
- `Strip 5|5|2024`
  - member descendants cross `BRS2 Langass -> FW24 KinlochMoidart`
- `Strip 6|6|2024`
  - member descendants cross `BRS2 Langass -> FW24 KinlochMoidart`

Interpretation:

- These are not extract-freshness failures.
- They are station-preflight blockers exposed by descendant expansion.
- Any further progress on these six needs either:
  - an intentional `--allow-station-mismatch` decision, or
  - a tighter descendant/materialization rule for these cohorts, or
  - operator review in FishTalk/AquaMind.

## 2. Refreshed FW U30 Scope After Report Materialization

- Rebuilt artifact prefix:
  - `scripts/migration/output/fw_u30_two_geo_scope_post_materialization_20260325`
- Summary:
  - strict scope total: `161`
  - blocked total: `99`
  - blocked split:
    - missing `PopulationComponent` map: `93`
    - missing report dir: `6`

Interpretation:

- The report-dir backlog mostly converted into report-ready rows.
- The dominant remaining blocker is now clearly upstream component materialization, not missing derived scope artifacts.

## 3. Component-Seeding Pilot

Logs live under:

- `scripts/migration/output/fw_u30_component_seed_20260325/logs`

### Faroe pilot: `Bakkafrost S-21 aug23|4|2023`

- component key: `BCD6C51F-044C-436C-A07B-302E4C129156`
- component log:
  - `Bakkafrost_S-21_aug23_4_2023.component.log`
- result:
  - `PopulationComponent` map created
  - target batch id: `1363`
  - batch number: `Bakkafrost S-21 aug23`
- component summary:
  - conserved populations: `246`
  - outside-component edge populations: `194`
  - same-stage superseded populations: `179`
  - assignments created/updated: `246`

Transfer replay:

- transfer log:
  - `Bakkafrost_S-21_aug23_4_2023.transfer.log`
- result:
  - success
  - raw SubTransfers: `237`
  - expanded scoped edges: `346`
  - workflows created: `7`
  - actions created: `321`
  - destination assignments canonicalized: `45`
  - source count backfilled: `33`
  - skipped edges: `25` (`self_loop_assignment_edge`)

### Scotland pilot: `SF AUG 23|15|2023`

- component key: `5EB7F4A5-E96F-46BF-964F-05101C02B502`
- component log:
  - `SF_AUG_23_15_2023.component.log`
- result:
  - `PopulationComponent` map created
  - target batch id: `1364`
  - batch number: `SF AUG 23`
- component summary:
  - conserved populations: `120`
  - outside-component edge populations: `112`
  - same-stage superseded populations: `56`
  - assignments created/updated: `120`

Transfer replay:

- transfer log:
  - `SF_AUG_23_15_2023.transfer.log`
- result:
  - success
  - raw SubTransfers: `125`
  - expanded scoped edges: `153`
  - initial stage-bucket result:
    - workflows created: `1`
    - actions created: `6`
    - skipped edges: `147`
    - skipped reasons:
      - `missing_hall_stage_mapping=138`
      - `station_mismatch_or_missing=9`

Operator evidence received after this pilot:

- `FW21 Couldoran / Hatchery` is `Egg&Alevin`
- `FW21 Couldoran / RAS` is `Smolt`
- `FW22 Applecross / D2` is `Post-Smolt`
- the `A`-`F` hall semantics inside `FW21` are not stable enough to treat as deterministic lifecycle-stage mapping

Narrow corrective rerun:

- reran the same component with:
  - `pilot_migrate_component_transfers.py --workflow-grouping operation`
- operation-grouping result:
  - log: `SF_AUG_23_15_2023.transfer_operation.log`
  - workflows created: `32`
  - prior under-migrated workflow pruned: `1`
  - actions created: `150`
  - prior under-migrated actions pruned: `6`
  - skipped edges: `3`
  - skipped reason:
    - `self_loop_assignment_edge=3`

Post-rerun live DB state for AquaMind batch `1364`:

- transfer workflows: `32`
- transfer actions: `150`

Interpretation:

- Faroe pilot behaved as hoped: missing map was the real blocker, and transfer replay then succeeded cleanly.
- Scotland pilot also proves the missing map was a real blocker, but it exposed a second-order transfer-quality blocker:
  - `stage-bucket` replay drops real FW21 complexity when hall-stage semantics are unstable.
- For this batch, `operation` grouping is the narrow justified fix.
- This remains a concrete blocker class for broader Scotland seeding, but it is not evidence of missing SQL extract.

## 4. Effective Blocked State After This Pass

Starting point for this pass:

- blocked rows after post-materialization rebuild: `99`

Rows newly unblocked from that blocked snapshot:

- `Bakkafrost S-21 aug23|4|2023`
- `SF AUG 23|15|2023`

Effective current blocked total relative to that snapshot:

- `97`
  - missing `PopulationComponent` map: `91`
  - missing report dir: `6`

## 5. Focused FW Review Follow-Through

Operator guidance narrowed the active Scotland/Faroe victory scope to:

- Scotland `FW*` stations
- Faroe `S*` stations

Broodstock-oriented `BRS*` / `L*` rows remain useful evidence, but they are no longer part of the core FW victory queue unless explicitly re-admitted.

### `SF JUL 23|3|2023` -> AquaMind batch `1365`

- component key:
  - `06158D82-187B-411B-872D-41D97FC59D7E`
- transfer replay:
  - `stage-bucket` remained acceptable
  - workflows: `7`
  - actions: `179`
  - skipped edges: `56`
    - `self_loop_assignment_edge=30`
    - `zero_estimated_transfer=26`
- operator review:
  - transfer layout looked correct, including the `FW22 Applecross / D2 / S2_A1` tail
- narrow culling completion:
  - log: `SF_JUL_23_3_2023.culling.log`
  - created culling events: `1203`
- exact tail confirmation:
  - assignment `39211`
  - `FW22 Applecross / D2 / S2_A1`
  - lifecycle stage: `Smolt`
  - assignment count: `28142`
  - assignment departure date: `2024-04-30`
  - explicit culling event on `2024-04-30`: `28142`
  - description:
    - `FishTalk culling; cause=04 Sjúka; CulledAll=0; system failure`

Interpretation:

- The user-visible tail was not a false visual cue.
- The missing piece was simply that the dedicated culling pass had not yet been replayed for this newly seeded batch.

### `NH FEB 24|1|2024` -> AquaMind batch `1366`

- component key:
  - `A75471B6-FCB1-4719-8F63-0210AF14B4BE`
- transfer replay:
  - initial `stage-bucket` run dropped all scoped edges
  - corrective rerun used `operation` grouping
  - final result:
    - workflows: `49`
    - actions: `193`
    - skipped edges: `19`
    - skipped reason:
      - `self_loop_assignment_edge=19`
- operator review:
  - batch looked correct
  - cross-station branch into `BRS3 Geocrab` matched FT
  - remaining `FW21 Couldoran` branch was visibly culled in `RAS`
- narrow culling completion:
  - log: `NH_FEB_24_1_2024.culling.log`
  - created culling events: `22`
- live DB confirmation:
  - total culling count now present: `1261785`
  - the `2024-10-29` `FW21 Couldoran / RAS` cull wave is explicit in AquaMind
  - largest same-day rows include:
    - `CR10`: `106984`
    - `CR05`: `101446`
    - `CR02`: `98071`
    - `CR08`: `97522`
    - `CR07`: `97509`

Interpretation:

- This batch is a pass on both transfer structure and explicit culling persistence.
- It is also a second proven Scotland `operation`-grouping case.

### `SF MAY 24|3|2024` -> AquaMind batch `1367`

- component key:
  - `AE4B5246-AA42-48FF-A7AF-0610F3F55752`
- transfer replay:
  - initial `stage-bucket` result under-migrated the batch
  - corrective rerun used `operation` grouping
  - final result:
    - workflows: `30`
    - actions: `129`
    - skipped edges: `0`
- operator review:
  - AquaMind batch `1367` looked partly correct, but the early `FW22 Applecross` pre-smolt stages appeared missing
- narrow culling completion:
  - log: `SF_MAY_24_3_2024.culling.log`
  - created culling events: `537`
  - skipped: `1`

Companion-batch evidence:

- `SF MAY 24` exists in the stitched scope as two separate FW input rows:
  - `SF MAY 24|3|2024` -> AquaMind batch `1367`
  - `SF MAY 24|6|2024` -> AquaMind batch `1336` (`SF MAY 24 [6]`)
- `1367` is mainly the `FW24 KinlochMoidart` side:
  - stations:
    - `FW24 KinlochMoidart`: `94` assignments
    - `FW22 Applecross`: `16` assignments
  - halls:
    - `Hatchery`, `Parr`, `Smolt (RAS1)`, `Smolt (RAS2)`, plus `FW22 / D1`
- `1336` contains the early `FW22 Applecross` footprint the operator expected:
  - station:
    - `FW22 Applecross`: `234` assignments
  - halls:
    - `A1`: `67`
    - `B1`: `67`
    - `C1`: `60`
    - `D2`: `22`
    - `E2`: `18`

Interpretation:

- The early `FW22` stages are not absent from AquaMind.
- They are persisted on the existing companion batch `1336`, not on `1367`.
- So this is not currently evidenced as a transfer replay defect.
- It is a split-identity/stitching presentation issue:
  - FishTalk operator semantics read this as one practical cohort
  - the current migration mechanics still preserve two separate FW input identities

### `SF MAY 24|6|2024` / AquaMind batch `1336` stage-correction follow-up

Operator review then found a real semantic defect on the companion batch:

- `FW22 Applecross / E2 / LS2_A1`
- `FW22 Applecross / E2 / LS2_A2`
- `FW22 Applecross / E2 / LS2_B3`
- `FW22 Applecross / E2 / LS2_B4`

These rows were visible in AquaMind, but the long late assignments were incorrectly labeled `Parr` after `Post-Smolt`.

Root cause:

- not a transfer replay defect
- not missing extract data
- the incorrect `Parr` stage was already present in the generated
  `scripts/migration/output/input_batch_migration/SF_MAY_24_6_2024/population_members.csv`
- the bad label entered through `pilot_migrate_input_batch.py` descendant expansion:
  - descendant members were preserving raw FishTalk stage tokens
  - for `FW22 Applecross / E2`, hall semantics are deterministic and should override tokens to `Post-Smolt`

Narrow fix:

- patched `scripts/migration/tools/pilot_migrate_input_batch.py`
  - added hall-aware descendant stage canonicalization for `FW22 Applecross`
  - `E2` descendants now materialize as `Post-Smolt` in regenerated report rows
- regenerated only `SF MAY 24|6|2024` report artifacts
  - log: `scripts/migration/output/fw_u30_component_seed_20260325/logs/SF_MAY_24_6_2024.report_refresh.log`
- reran only the component rebuild for the existing batch `1336`
  - component key: `18213D77-EE34-4780-9EBE-0F202D5E4DF0`
  - log: `scripts/migration/output/fw_u30_component_seed_20260325/logs/SF_MAY_24_6_2024.component_rerun.log`

Post-fix live DB confirmation:

- batch `1336` lifecycle stage:
  - `Post-Smolt`
- corrected long Applecross `E2` assignments:
  - `LS2_B3`: `2025-05-22 -> 2025-09-09`, `333464`, `Post-Smolt`
  - `LS2_B4`: `2025-05-22 -> 2025-09-04`, `325477`, `Post-Smolt`
  - `LS2_A1`: all six `E2` rows now `Post-Smolt`
  - `LS2_A2`: all four `E2` rows now `Post-Smolt`

Interpretation:

- the operator callout was correct
- the previous “graph-only” explanation was incomplete
- the real defect sat in descendant stage derivation for this Applecross hall
- the correction is now applied in both:
  - regenerated report artifacts
  - live AquaMind assignment data for batch `1336`

## 6. Recommended Next Steps

1. Continue component-seeding on high-signal Faroe map-missing rows first.
   - Evidence says this path is productive and clean on Faroe.
2. Treat `SF AUG 23|15|2023` as a proven Scotland operation-grouping exception.
   - Do not revert it back to `stage-bucket`.
3. Treat `NH FEB 24|1|2024` as a second proven Scotland operation-grouping case.
   - `stage-bucket` is not reliable enough for all Scotland FW rows.
4. For operator review of `SF MAY 24`, inspect `1367` together with companion batch `1336`.
   - Do not classify the missing early `FW22` stages as a transfer defect unless the paired view is still semantically wrong.
5. Do not bulk-seed Scotland blindly yet.
   - First classify which remaining Scotland rows share the same unstable hall-stage pattern and therefore need `operation` grouping.
6. Resolve the six remaining report-dir failures explicitly.
   - They are now a compact, reviewable station-mismatch set.
7. Keep FW->Sea paused.

## 7. Priority-Hall Stage Backfill Safeguard

The `SF MAY 24 [6]` defect showed that manual swimlane review is not a safe primary detector for hall-stage drift. A durable safeguard is now in place:

- shared hall-stage source-side helper:
  - `scripts/migration/tools/hall_stage_rules.py`
- input-batch descendant expansion now uses the shared canonicalizer:
  - `scripts/migration/tools/pilot_migrate_input_batch.py`
- input stitching now also writes priority-hall rows through the same canonicalizer:
  - `scripts/migration/tools/input_based_stitching_report.py`
- deterministic audit tool:
  - `scripts/migration/tools/audit_priority_hall_stage_reports.py`

Audit run on current generated report dirs:

- command output artifact:
  - `scripts/migration/output/priority_hall_stage_audit_20260325.csv`
  - `scripts/migration/output/priority_hall_stage_audit_20260325.json`
- backfill queue artifact:
  - `scripts/migration/output/priority_hall_stage_backfill_queue_20260325.csv`
- result:
  - mismatch rows: `11251`
  - affected report dirs: `67`
  - focus split:
    - `Faroe_S`: `9543`
    - `Scotland_FW`: `1708`
  - already mapped live AquaMind batches: `63/67`

Examples proving this is broader than one batch:

- `Bakkafrost_S-21_aug23_4_2023` -> AquaMind `1363`: `240` mismatched rows
- `SF_JUL_23_3_2023` -> AquaMind `1365`: `197` mismatched rows
- `SF_MAY_24_6_2024` -> AquaMind `1336`: `151` mismatched rows
- `SF_SEP_24_7_2024` -> AquaMind `1340`: `223` mismatched rows
- `Stofnfiskur_Septembur_2023_3_2023` -> AquaMind `1351`: `611` mismatched rows

Interpretation:

- this bug class was easy to miss manually because the swimlanes still looked mostly plausible
- it is not isolated to Applecross
- the right response is not more manual review
- the right response is:
  1. keep the shared source-side canonicalizer in place for future report builds
  2. use the audit as a deterministic detector on existing report dirs
  3. backfill the `63` mapped batches from the generated queue with the narrow priority-hall stage runner
  4. rerun transfer workflows only where follow-up evidence shows stage-sensitive workflow distortion

## 8. Executed Priority-Hall Backfill

Rather than brute-force full component reruns for all affected batches, the actual executed backfill used the narrower defect-targeted path:

- report + DB backfill runner:
  - `scripts/migration/tools/backfill_priority_hall_stage_queue.py`
- live assignment audit:
  - `scripts/migration/tools/audit_priority_hall_assignment_stages.py`

### 8.1 Mapped live batches

Applied run:

- output dir:
  - `scripts/migration/output/priority_hall_stage_backfill_apply_20260325`
- queue:
  - `scripts/migration/output/priority_hall_stage_backfill_queue_20260325.csv`
- result:
  - attempted: `63`
  - succeeded: `63`
  - failed: `0`
  - changed report rows: `10045`
  - changed assignment lifecycle stages: `377`
  - missing assignment maps: `0`
  - batch lifecycle-stage changes: `25`

Representative corrected batch-stage shifts:

- `Benchmark Gen. Juni 2024` (`1326`): `Smolt -> Post-Smolt`
- `Stofnfiskur S-21 nov23` (`1350`): `Fry -> Post-Smolt`
- `SF SEP 24` (`1340`): `Parr -> Post-Smolt`
- `SF DEC 24` (`1331`): `Parr -> Post-Smolt`
- `AG FEB 24` (`1310`): `Smolt -> Post-Smolt`

### 8.2 Unmapped residual report dirs

After the mapped pass, residual report-only mismatches remained on four unmapped report dirs:

- `Vetur_2025_1_2025`
- `Heyst_2023_1_2024`
- `SF_SEP_23_4_2023`
- `AG_JAN_24_2_2024`

Applied cleanup:

- output dir:
  - `scripts/migration/output/priority_hall_stage_backfill_apply_all_reports_20260325`
- result:
  - attempted: `67`
  - succeeded: `67`
  - changed report rows: `64`
  - changed assignment stages: `0` (expected, unmapped residuals were report-only)

### 8.3 Final verification

Final report-artifact audit:

- artifacts:
  - `scripts/migration/output/priority_hall_stage_audit_final_20260325.csv`
  - `scripts/migration/output/priority_hall_stage_audit_final_20260325.json`
- result:
  - mismatch rows: `0`
  - affected report dirs: `0`

Final live DB assignment audit on mapped batches:

- artifact:
  - `scripts/migration/output/priority_hall_assignment_audit_final_20260325.json`
- result:
  - mapped report count audited: `63`
  - residual assignment mismatches: `0`
  - affected reports: `0`

Interpretation:

- this priority-hall stage bug class is now backfilled in both:
  - generated report artifacts
  - live mapped AquaMind assignment data
- future recurrence is guarded by the shared source-side canonicalizer
- the remaining migration work can move forward without needing manual swimlane review to catch this specific class again
