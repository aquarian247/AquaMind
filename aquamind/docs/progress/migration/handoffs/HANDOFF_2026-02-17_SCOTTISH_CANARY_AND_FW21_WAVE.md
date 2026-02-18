# HANDOFF 2026-02-17: Full Environmental Canaries + FW21 Station Wave

## Scope

Continue FishTalk -> AquaMind migration hardening under the fixed backup cutoff and profile baseline:

- Run two full environmental canaries (no `--skip-environmental`):
  - Faroe: `Bakkafrost S-21 jan 25|1|2025`
  - FW22 cohort: `SF MAR 25|1|2025`
- Semantic-gate both canaries.
- If both pass, proceed to next Scottish station wave (`<30 months`) with `--skip-environmental` for throughput.

## Non-negotiables honored

- Backup cutoff remained pinned to `2026-01-22` (not report date) for extract preflight and semantic window cap.
- AquaMind runtime code stayed FishTalk-agnostic (no runtime code changes in this session).
- Source-specific behavior remained in migration tooling/validation/reporting only.
- Profile-driven migration baseline preserved with `--migration-profile fw_default`.

## Canary Result Table (migration + semantic + runtime)

| Canary | Batch key | Component key | Migration | Semantic gates | Runtime | Runtime stage/status | Active containers |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Faroe S21 canary | `Bakkafrost S-21 jan 25|1|2025` | `B52612BD-F18B-48A4-BF21-12B5FC246803` | PASS (`13/13`, full environmental) | PASS | PASS | `Smolt / ACTIVE` | `C12, D1, D2, D3, D4, D5, D6` |
| FW22 canary | `SF MAR 25|1|2025` | `232FE340-5BBE-4C3A-96A4-0CA91C0B181A` | PASS (`13/13`, full environmental) | PASS | PASS | `Smolt / ACTIVE` | `S05, S07, S2_A1, S2_A2, S2_B3, S2_B4` |

## Scottish station-wave status summary

Wave anchor: `FW21 Couldoran`, `<30 months` from cutoff `2026-01-22`, throughput mode (`--skip-environmental`).

### Pass 1 (strict station guard)

- Cohorts attempted: `7`
- Migration success: `3/7`
- Semantic regression gates: `3/7` (all migrated cohorts passed)
- Strict-pass cohorts:
  - `NH MAY 24|2|2024`
  - `SF NOV 24|4|2024`
  - `NH FEB 25|1|2025`
- Strict-blocked cohorts (member-derived mixed sites):
  - `SF AUG 23|15|2023` (`FW21` + `FW22`)
  - `SF NOV 23|17|2023` (`FW21` + `FW22`)
  - `NH FEB 24|1|2024` (`FW21` + `BRS3`)
  - `SF AUG 24|3|2024` (`FW21` + `FW13`)

### Pass 2 (controlled mixed-site recovery)

Executed the strict-blocked set with station anchor + override:

- command shape:
  - `pilot_migrate_input_batch.py --expected-site "FW21 Couldoran" --allow-station-mismatch --skip-environmental --migration-profile fw_default --extract-horizon-date 2026-01-22`
- recovery outcome:
  - Migration success: `4/4`
  - Semantic regression gates: `4/4`
- note:
  - `SF NOV 23|17|2023` required targeted rerun with `--batch-number "SF NOV 23 17"` to avoid `batch_number` collision with pre-existing `SF NOV 23` from another component.

### Policy outcome

Inter-station freshwater transfer is now treated as normal cohort behavior in migration policy:

- strict station mode remains default for station-pure cohorts,
- controlled mixed-site override (`--allow-station-mismatch`) is approved for transfer-confirmed cohorts,
- this policy remains migration-tooling/reporting only (AquaMind runtime remains FishTalk-agnostic).

## Explicit B01/B02 regression statement

**B01/B02 regression status: NO REGRESSION OBSERVED in this session.**

- S21 canary (`B52612BD-F18B-48A4-BF21-12B5FC246803`) completed full environmental migration (`13/13`) and semantic regression gates `PASS`.
- Regression gate metrics for the canary remained clean (`transition_alert_count=0`, `zero_count_transfer_actions=0`, `non_bridge_zero_assignments=0`).
- Runtime state for `batch_id=464` remains `ACTIVE` at lifecycle stage `Smolt` with active containers `C12, D1..D6`, matching expected post-hardening occupancy.
- Prior anchor artifact reference remains:
  - `aquamind/docs/progress/migration/analysis_reports/2026-02-16/S21_Bakkafrost_S21_jan25_B01_B02_regression_anchor_check_after_outside_holder_fix_2026-02-16.json`

## Artifact index

- Canary result table:
  - `aquamind/docs/progress/migration/analysis_reports/2026-02-17/Scottish_canary_result_table_2026-02-17.md`
  - `aquamind/docs/progress/migration/analysis_reports/2026-02-17/Scottish_canary_result_table_2026-02-17.json`
- Canary semantic outputs:
  - `aquamind/docs/progress/migration/analysis_reports/2026-02-17/S21_Bakkafrost_S21_jan25_semantic_validation_full_environmental_canary_2026-02-17.md`
  - `aquamind/docs/progress/migration/analysis_reports/2026-02-17/S21_Bakkafrost_S21_jan25_semantic_validation_full_environmental_canary_2026-02-17.summary.json`
  - `aquamind/docs/progress/migration/analysis_reports/2026-02-17/FW22_SF_MAR_25_1_2025_semantic_validation_full_environmental_canary_2026-02-17.md`
  - `aquamind/docs/progress/migration/analysis_reports/2026-02-17/FW22_SF_MAR_25_1_2025_semantic_validation_full_environmental_canary_2026-02-17.summary.json`
- Canary runtime snapshot:
  - `aquamind/docs/progress/migration/analysis_reports/2026-02-17/canary_runtime_snapshot_2026-02-17.json`
- FW21 station-wave summary:
  - `aquamind/docs/progress/migration/analysis_reports/2026-02-17/FW21_station_wave_migration_summary_2026-02-17.md`
  - `aquamind/docs/progress/migration/analysis_reports/2026-02-17/FW21_station_wave_migration_summary_2026-02-17.json`
- FW21 controlled mixed-site recovery summary:
  - `aquamind/docs/progress/migration/analysis_reports/2026-02-17/FW21_allow_station_mismatch_recovery_summary_2026-02-17.md`
  - `aquamind/docs/progress/migration/analysis_reports/2026-02-17/FW21_allow_station_mismatch_recovery_summary_2026-02-17.json`
- FW21 transfer evidence matrix:
  - `aquamind/docs/progress/migration/analysis_reports/2026-02-17/FW21_transfer_evidence_matrix_2026-02-17.md`
- SF NOV targeted rerun semantic outputs:
  - `aquamind/docs/progress/migration/analysis_reports/2026-02-17/FW21_allow_mismatch_SF_NOV_23_17_2023_semantic_validation_2026-02-17.md`
  - `aquamind/docs/progress/migration/analysis_reports/2026-02-17/FW21_allow_mismatch_SF_NOV_23_17_2023_semantic_validation_2026-02-17.summary.json`
- Mapping blueprint policy update:
  - `aquamind/docs/progress/migration/DATA_MAPPING_DOCUMENT.md` (v4.8, 2026-02-17)
- FW21 per-cohort semantic artifacts directory:
  - `aquamind/docs/progress/migration/analysis_reports/2026-02-17/`

## Recommended next step

Scale the same two-pass strategy to the next Scottish station wave:

1. Run strict station pass first (`--expected-site`, no mismatch override).
2. For strict-blocked, transfer-confirmed cohorts, rerun with controlled override (`--allow-station-mismatch`) and semantic gates.

Follow-on execution handoff:

- `aquamind/docs/progress/migration/handoffs/HANDOFF_2026-02-17_FW24_TWO_PASS_STATION_WAVE.md`
- `aquamind/docs/progress/migration/handoffs/HANDOFF_2026-02-17_FW13_TWO_PASS_STATION_WAVE.md`
