# Marine Controlled Provisional Micro-Wave (2026-02-18)

## Decision mode

Operator-selected policy: `controlled_provisional`.

Objective:

- begin migration of a limited unlinked-sea subset while preserving guardrails and auditability.

## How FW->Sea mapping has been inferred so far

Evidence ladder in tooling:

1. Canonical first (`Ext_Transfers` + `SubTransfers` lineage)
2. If canonical absent, provisional temporal+geography fallback on S*->A* only

Temporal signal construction:

- FW terminal depletion `X` = latest timestamp among available FW terminal signals (`segment_end_time`, `transfer_out_last_time`, `culling_last_time`, `mortality_last_time`, `status_zero_after_nonzero_time`)
- Sea fill/start `Y` = earliest timestamp among sea fill signals (`segment_start_time`, `status_first_nonzero_time`, `fw_transfer_in_first_time`)
- `delta_days = Y - X`

Classification thresholds (implemented):

- `true_candidate`: `delta_days <= 1.0` and `fw_signal_count >= 2` and `sea_signal_count >= 2`
- `sparse_evidence`: `delta_days <= 2.0` and `fw_signal_count >= 1` and `sea_signal_count >= 1`
- otherwise `unclassified_nonzero_candidate`

Empirical deltas from actionable provisional rows (`n=3,958`):

- all provisional: min `0.000`, p25 `0.497`, p50 `0.997`, p75 `1.592`, p90 `1.950`, max `2.000`
- `true_candidate` (`n=2,138`): max `1.000` (p50 `0.522`)
- `sparse_evidence` (`n=1,820`): range `1.001..2.000` (p50 `1.678`)

Practical threshold interpretation:

- `<=1.0 day`: strongest
- `1.0-1.6 days`: plausible, weaker
- `1.6-2.0 days`: sparse fallback only
- no evidence beyond `2.0` used in this run

## Controlled provisional cohort selection

Selection constraints:

- unlinked sea tier only
- under age gate
- Faroe + Adult
- one slice per distinct base batch for a low-blast-radius micro-wave

Selected cohorts:

1. `Vár 2025|1|2025|A83A9BFF-005B-4ED2-856D-8C7BDF37B54F`
2. `Heyst 2025|1|2025|EE44DDC3-ED36-4AC7-85F0-E338C8F2EA78`
3. `Summar 2025|1|2025|6E496E90-F34B-4CD7-84DC-164EC3473A5E`

## Execution outcomes

All three migrations:

- PASS (`11/11` scripts each)
- semantic regression gates: PASS
- no synthetic stage-transition workflow generation

| Cohort key | Component key | Semantic gates | Transfer actions total | Zero-count transfer actions |
| --- | --- | --- | ---: | ---: |
| `Vár 2025|1|2025|A83A9BFF-005B-4ED2-856D-8C7BDF37B54F` | `67677EF3-C7D0-431C-9BFE-2533D67EF523` | PASS | 0 | 0 |
| `Heyst 2025|1|2025|EE44DDC3-ED36-4AC7-85F0-E338C8F2EA78` | `C78845D7-8A8D-4B31-968B-8127642563D7` | PASS | 9 | 0 |
| `Summar 2025|1|2025|6E496E90-F34B-4CD7-84DC-164EC3473A5E` | `F12F9479-E82C-499C-99E4-4BB3F5EF991F` | PASS | 12 | 0 |

Notes:

- Non-zero transfer actions for `Heyst 2025` / `Summar 2025` are source-backed from SubTransfers edges (canonical), not synthetic backfill.
- GUI/API remained healthy (`200`) during and after this wave.

## Remaining queue

- Unlinked sea queue before micro-wave: `30`
- Migrated controlled provisional cohorts: `3`
- Remaining unlinked sea queue: `27`

## Artifacts

- `scripts/migration/output/input_batch_migration/Vár_2025_1_2025_A83A9BFF-005B-4ED2-856D-8C7BDF37B54F/semantic_validation_Vár_2025_1_2025_A83A9BFF-005B-4ED2-856D-8C7BDF37B54F.md`
- `scripts/migration/output/input_batch_migration/Vár_2025_1_2025_A83A9BFF-005B-4ED2-856D-8C7BDF37B54F/semantic_validation_Vár_2025_1_2025_A83A9BFF-005B-4ED2-856D-8C7BDF37B54F.json`
- `scripts/migration/output/input_batch_migration/Heyst_2025_1_2025_EE44DDC3-ED36-4AC7-85F0-E338C8F2EA78/semantic_validation_Heyst_2025_1_2025_EE44DDC3-ED36-4AC7-85F0-E338C8F2EA78.md`
- `scripts/migration/output/input_batch_migration/Heyst_2025_1_2025_EE44DDC3-ED36-4AC7-85F0-E338C8F2EA78/semantic_validation_Heyst_2025_1_2025_EE44DDC3-ED36-4AC7-85F0-E338C8F2EA78.json`
- `scripts/migration/output/input_batch_migration/Summar_2025_1_2025_6E496E90-F34B-4CD7-84DC-164EC3473A5E/semantic_validation_Summar_2025_1_2025_6E496E90-F34B-4CD7-84DC-164EC3473A5E.md`
- `scripts/migration/output/input_batch_migration/Summar_2025_1_2025_6E496E90-F34B-4CD7-84DC-164EC3473A5E/semantic_validation_Summar_2025_1_2025_6E496E90-F34B-4CD7-84DC-164EC3473A5E.json`
