# HANDOFF 2026-02-25 - FW B wave19 117 egg-cluster4 override + row-recheck

## Scope
- Continue FW B stabilization from wave18 with evidence-first focus on persistent non-movers:
  - `117` (primary), then `139`, `109`, `128`, `90`.
- Validate a single minimal deterministic extension only if row-level FishTalk evidence is convincing.
- Preserve guardrails:
  - class `A` must remain `0`
  - no class-`C` expansion
  - no schema changes.

## Baseline reproduced (from latest row-recheck artifact)
- Baseline artifact:
  - `scripts/migration/output/fw_b_class_row_recheck_wave18_next5_delayed_input_override_migrdb_20260225_151512.json`
- Confirmed totals:
  - `after_mismatch_rows=28`
  - taxonomy: `A=0, B=24, C=4, D=0`
- Fixed source mismatch-set board retained:
  - `scripts/migration/output/fw_policy_scope_tiebreak_postwave_wave10_next5_20260225_090255.json`

## Focused FishTalk evidence pass (117/139/109/128/90)
- Evidence pack generated:
  - `scripts/migration/output/fw_b_residual_evidence_wave18_focus_20260225_164158.json`
  - `scripts/migration/output/fw_b_residual_evidence_wave18_focus_20260225_164158.csv`
  - `scripts/migration/output/fw_b_residual_evidence_wave18_focus_20260225_164158.md`

Key evidence outcome:
- `117` (`AquaGen juni 25`) shows a coherent delayed-input pattern:
  - all 4 residual rows have exact-start `0`
  - first non-zero status appears ~`12.75h` after start
  - delivery/source link absent
  - supplier continuity with component start present
  - no near-start SubTransfers touch
  - cluster size is `4` (fails current `>=8` gate only).

## Minimal deterministic candidate validated
- Candidate:
  - Keep delayed-input rule unchanged for `cluster>=8`.
  - Add narrow extension for Egg-token rows at `cluster>=4`.

## Code changes
- `scripts/migration/tools/pilot_migrate_component.py`
  - Added Egg-token cluster threshold extension (`>=4`) while keeping base delayed-input threshold (`>=8`) and all other guards unchanged.
  - No changes in `etl_loader.py`.

## Single-batch validation first (117)
- Replay command executed for `117` (exit `0`).
- Validation artifacts:
  - `scripts/migration/output/fw_b117_delayed_input_egg_cluster4_validation_migrdb_20260225_164604.json`
  - `scripts/migration/output/fw_b117_delayed_input_egg_cluster4_validation_migrdb_20260225_164604.md`
- Single-batch result:
  - `117`: `4 -> 0` (`-4`) under validated egg-cluster4 override criteria.

## Targeted cohort replay (after single-batch validation)
- Cohort replayed: `117, 139, 109, 128, 90`
- Replay artifact:
  - `scripts/migration/output/fw_b_class_targeted_replay_wave19_next5_20260225_164625.json`
  - `scripts/migration/output/fw_b_class_targeted_replay_wave19_next5_20260225_164625.md`
- Execution status:
  - all five replays exited `0`.

## Post-wave19 row-recheck board (same fixed source board)
- Board artifacts:
  - `scripts/migration/output/fw_b_class_row_recheck_wave19_next5_delayed_input_egg_cluster4_override_migrdb_20260225_165424.json`
  - `scripts/migration/output/fw_b_class_row_recheck_wave19_next5_delayed_input_egg_cluster4_override_migrdb_20260225_165424.md`
  - `scripts/migration/output/fw_b_class_row_recheck_wave19_next5_delayed_input_egg_cluster4_override_migrdb_20260225_165424.csv`
- Totals:
  - `before_mismatch_rows=36`
  - `after_mismatch_rows=24`
  - `delta=-12`
  - `rule_match_rows=12` (base `8` + new extension `4`)
- Remaining taxonomy:
  - `A=0`
  - `B=20`
  - `C=4`
  - `D=0`

## Targeted cohort delta (wave19)
- Delta artifacts:
  - `scripts/migration/output/fw_b_class_targeted_delta_wave19_next5_20260225_165424.json`
  - `scripts/migration/output/fw_b_class_targeted_delta_wave19_next5_20260225_165424.md`
- Result:
  - cohort total: `12 -> 8` (`-4`)
  - per batch:
    - `117`: `4 -> 0` (`-4`)
    - `139`: `2 -> 2` (`0`)
    - `109`: `2 -> 2` (`0`)
    - `128`: `2 -> 2` (`0`)
    - `90`: `2 -> 2` (`0`)

## Ranked residual board (post-wave19)
- Culprit artifacts:
  - `scripts/migration/output/fw_fishtalk_culprits_wave19_top20_20260225_165424.csv`
  - `scripts/migration/output/fw_fishtalk_culprits_wave19_top20_20260225_165424.md`

Top remaining:
1. `139` Bakkafrost Okt 2023 (`2`)
2. `109` 24Q1 LHS (`2`)
3. `128` Fiskaaling sep 2022 (`2`)
4. `90` 24Q1 LHS ex-LC (`2`, class `C`)
5. `104` SF MAR 25 (`2`)
6. `118` Gjógv/Fiskaaling mars 2023 (`2`)
7. `129` YC 23 (`2`)

## Exact files changed in this session
- `scripts/migration/tools/pilot_migrate_component.py`
- `aquamind/docs/progress/migration/handoffs/HANDOFF_2026-02-25_FW_B_WAVE19_117_EGG_CLUSTER4_OVERRIDE_AND_ROWRECHECK.md`

## Go / No-go
- Decision: **FW not yet ready** for marine continuation.
- Rationale:
  - `A` remains protected at `0`.
  - residuals improved (`28 -> 24`), but `B=20` + `C=4` still requires targeted evidence closure.

## Precise FT inspection questions for persistent non-movers
For `139` (`0F40F5BD...`, `F6DE2C4B...`) and `128` (`23E5E1D0...`, `C29979CC...`):
1. At exact start timestamps, are these two-row fanouts true delayed input placements or expected-zero placeholders?
2. Is there any FT-side delivery linkage (Delivery/SourceContainer) for these starts that is absent in extract?
3. Should these starts inherit the same delayed-input authority semantics as `117`, or are they operationally distinct?

For `109` (`E1260FE3...`, `71CAFC18...`):
1. Do these rows represent a validated 3-way delayed seed split where only two rows remain mismatched?
2. If yes, is there operator acceptance to treat this pattern deterministically (cluster `3`) or keep it out of scope?

For `90` (`66CDC526...`, `13180D8E...`, class `C`):
1. Are these inactive departure rows expected historical companions for the same holder chain, or should one be suppressed?
2. Is there a definitive FT holder-of-record at transition times (`2023-10-26`, `2023-11-17`) that should close this residual?

## Recommended next step
- Keep this wave19 extension locked.
- Run a focused FT evidence pass for `139/109/128/90` using the listed population IDs and start times.
- Propose exactly one next deterministic candidate only after FT confirms whether fanout-2/3 rows are true delayed-input starts vs expected-zero placeholders.
