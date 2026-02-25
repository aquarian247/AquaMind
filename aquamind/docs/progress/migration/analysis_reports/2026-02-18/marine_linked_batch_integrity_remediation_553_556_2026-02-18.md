# Linked Marine Integrity Remediation (553-556)

> Update (2026-02-19): This first remediation ledger has been superseded by
> `marine_linked_batch_integrity_regression_fix_r2_553_556_2026-02-19.md`
> after a second pass fixed stale component-assignment carryover on reruns.

## Scope

Rebuilt linked marine batches `553-556` after deterministic stitching, component-scoped assignment mapping, and linked-only synthetic stage-transition transfer policy updates.

## Validation outcomes

| Batch | Batch ID stable | Stage coverage after remediation (assignment rows) | Transfer history after remediation | Semantic regression gates |
| --- | --- | --- | --- | --- |
| `Vetur 2024` | `553 (unchanged)` | `Fry:39; Adult:586` | workflows=`1`, actions=`586` | `PASS` |
| `Vetur 2024/2025` | `554 (unchanged)` | `Egg&Alevin:7; Fry:5; Parr:1; Adult:44` | workflows=`3`, actions=`50` | `PASS` |
| `Heyst 2023` | `555 (unchanged)` | `Egg&Alevin:36; Fry:6; Adult:12` | workflows=`2`, actions=`18` | `PASS` |
| `Vetur 2025` | `556 (unchanged)` | `Egg&Alevin:51; Adult:27` | workflows=`1`, actions=`27` | `PASS` |

## Before vs after ledger

| Batch | Assignments (before) | Assignments (after) | Creation actions (before) | Creation actions (after) | Workflows (before) | Workflows (after) | Actions (before) | Actions (after) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `Vetur 2024` | 586 | 625 | 567 | 606 | 0 | 1 | 0 | 586 |
| `Vetur 2024/2025` | 50 | 57 | 4 | 8 | 0 | 3 | 0 | 50 |
| `Heyst 2023` | 6 | 54 | 4 | 44 | 0 | 2 | 0 | 18 |
| `Vetur 2025` | 27 | 78 | 7 | 58 | 0 | 1 | 0 | 27 |

## Notes

- Before snapshot is taken from `marine_guarded_linked_fw_in_scope_completion_2026-02-18.md` (pre-remediation counts).
- Transfer history is now present for all four linked batches via linked-only synthetic stage-transition workflows/actions.
- Container volume sourcing was also upgraded: FishTalk `ContainerPhysics` ParameterID `6` (overridden volume m3) is now extracted and mapped to `infrastructure.container.volume_m3` when present.
