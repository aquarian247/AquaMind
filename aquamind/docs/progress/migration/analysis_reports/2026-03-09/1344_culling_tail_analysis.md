# 1344 Culling-Tail Analysis

Date: 2026-03-09

Batch:
- AquaMind batch id `1344`
- Batch number `Stofnfiskur Des 23 - Vár 2024`

Question:
- Are the small fry-stage trailing rows in AquaMind container history a transfer bug, or correctly modeled culling?

Verdict:
- This is **not primarily a transfer-action migration bug**.
- It is a **component-assignment policy choice** in [pilot_migrate_component.py](/Users/aquarian247/Projects/AquaMind/scripts/migration/tools/pilot_migrate_component.py#L2913) and [pilot_migrate_component.py](/Users/aquarian247/Projects/AquaMind/scripts/migration/tools/pilot_migrate_component.py#L4081).
- The culling pilot is behaving consistently with the AquaMind data model: FishTalk culling is migrated into `MortalityEvent` on the resolved assignment in [pilot_migrate_component_culling.py](/Users/aquarian247/Projects/AquaMind/scripts/migration/tools/pilot_migrate_component_culling.py#L494).

What is happening:
- `pilot_migrate_component.py` identifies same-stage superseded populations and normally suppresses short bridge rows.
- It explicitly keeps superseded rows that have operational activity.
- Culling is counted as operational activity in [pilot_migrate_component.py](/Users/aquarian247/Projects/AquaMind/scripts/migration/tools/pilot_migrate_component.py#L677).
- Result: short residual `SourcePopAfter` populations that remain in the same container and are later fully culled survive as visible AquaMind assignments.

1344-specific evidence:
- In `migr_dev`, the fry tails at containers `501`, `502`, `503`, `505`, `506`, `507`, `510`, and `511` each have:
  - a dedicated short-lived `BatchContainerAssignment`
  - no inbound or outbound `TransferAction`
  - exactly one `FishTalk culling` `MortalityEvent`
  - `MortalityEvent.count == assignment.population_count`
- The source member list shows these are real FishTalk populations in the same container, usually immediately after a transfer split:
  - [population_members.csv](/Users/aquarian247/Projects/AquaMind/scripts/migration/output/input_batch_migration/Stofnfiskur_Des_23_6_2023/population_members.csv#L48)
  - [population_members.csv](/Users/aquarian247/Projects/AquaMind/scripts/migration/output/input_batch_migration/Stofnfiskur_Des_23_6_2023/population_members.csv#L50)
  - [population_members.csv](/Users/aquarian247/Projects/AquaMind/scripts/migration/output/input_batch_migration/Stofnfiskur_Des_23_6_2023/population_members.csv#L54)
  - [population_members.csv](/Users/aquarian247/Projects/AquaMind/scripts/migration/output/input_batch_migration/Stofnfiskur_Des_23_6_2023/population_members.csv#L67)
  - [population_members.csv](/Users/aquarian247/Projects/AquaMind/scripts/migration/output/input_batch_migration/Stofnfiskur_Des_23_6_2023/population_members.csv#L71)
  - [population_members.csv](/Users/aquarian247/Projects/AquaMind/scripts/migration/output/input_batch_migration/Stofnfiskur_Des_23_6_2023/population_members.csv#L77)
  - [population_members.csv](/Users/aquarian247/Projects/AquaMind/scripts/migration/output/input_batch_migration/Stofnfiskur_Des_23_6_2023/population_members.csv#L83)
- The ETL shows the same populations are created as `SourcePopAfter` residuals in `SubTransfers`, then fully culled in `culling.csv`:
  - [sub_transfers.csv](/Users/aquarian247/Projects/AquaMind/scripts/migration/data/extract/sub_transfers.csv#L180225)
  - [sub_transfers.csv](/Users/aquarian247/Projects/AquaMind/scripts/migration/data/extract/sub_transfers.csv#L180226)
  - [sub_transfers.csv](/Users/aquarian247/Projects/AquaMind/scripts/migration/data/extract/sub_transfers.csv#L180286)
  - [sub_transfers.csv](/Users/aquarian247/Projects/AquaMind/scripts/migration/data/extract/sub_transfers.csv#L180304)
  - [sub_transfers.csv](/Users/aquarian247/Projects/AquaMind/scripts/migration/data/extract/sub_transfers.csv#L180305)
  - [sub_transfers.csv](/Users/aquarian247/Projects/AquaMind/scripts/migration/data/extract/sub_transfers.csv#L180310)
  - [sub_transfers.csv](/Users/aquarian247/Projects/AquaMind/scripts/migration/data/extract/sub_transfers.csv#L180471)
  - [sub_transfers.csv](/Users/aquarian247/Projects/AquaMind/scripts/migration/data/extract/sub_transfers.csv#L180473)
  - [culling.csv](/Users/aquarian247/Projects/AquaMind/scripts/migration/data/extract/culling.csv)

Interpretation:
- Mechanically, the migration is internally consistent.
- Semantically, AquaMind likely should not show these rows as meaningful assignment phases if the only purpose of the residual population is later culling in the same container and stage.
- In AquaMind terms, these are better understood as **post-transfer residual culling tails**, not meaningful container moves.

Recommended handling policy:
- Keep the current culling migration into `MortalityEvent`.
- Change assignment creation policy, not the culling pilot:
  - collapse same-container, same-stage superseded populations back into the immediately preceding assignment when all of the following hold:
  - the successor population is created as `SourcePopAfter`
  - it has culling activity
  - it has no inbound or outbound transfer actions as its own assignment
  - the culling total fully consumes the successor assignment count
  - it has no other operational activity beyond culling
- When collapsed:
  - attach the culling `MortalityEvent` to the predecessor assignment
  - extend predecessor `departure_date` if needed
  - suppress the culling-tail assignment row from history

Scope check:
- The four current FW transfer canaries were checked in `migr_dev`.
- This exact defect class appears in `1344` with `17` culling-tail assignments.
- It did not appear in `1348`, `1349`, or `1352`.

Next step:
- Implement a narrow suppression/fold-back rule in `pilot_migrate_component.py` for culling-only same-stage residual tails.
- Do not change `pilot_migrate_component_culling.py` first; the assignment selection policy is the source of the semantic mismatch.
