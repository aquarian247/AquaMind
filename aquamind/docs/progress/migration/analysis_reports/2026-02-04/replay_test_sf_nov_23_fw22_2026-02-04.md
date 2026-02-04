# Replay Test: SF NOV 23 (FW22 Applecross)

Date: 2026-02-04
InputProjectID: EC44DBBA-067D-4B34-89CD-630BAFFC5BE9
ProjectName: SF NOV 23
YearClass: 2023
Population count: 130

Window tested: 2023-11-01 to 2024-06-01 (Operations.StartTime)

---

## Summary Metrics

- First operation: 2023-11-16 15:11:07
- Last operation: 2024-05-31 14:53:07
- Distinct operations: 1239
- SubTransfers in window: 62

---

## ActionType counts (Actions joined to Operations)

| ActionType | Count |
|---|---|
| 3 | 1703 |
| 5 | 813 |
| 25 | 703 |
| 16 | 490 |
| 57 | 65 |
| 58 | 65 |
| 28 | 52 |
| 4 | 52 |
| 22 | 16 |

Notes
- Known mappings: 3=Mortality, 5=Feeding, 16=Culling, 58=Treatment (see action_type_mapping report).
- Unknown in current mapping: 4, 25, 28, 57.

---

## OperationType counts (Operations joined via Actions)

| OperationType | PublicOperationTypes.Text | Count |
|---|---|---|
| 4 | Mortality | 1703 |
| 12 | Culling | 980 |
| 3 | Feeding | 813 |
| 16 | Treatment | 130 |
| 22 | Hatching | 104 |
| 10 | Weight sample | 99 |
| 1 | Transfer | 62 |
| 5 | Input | 52 |
| 17 | Vaccination | 16 |

---

## OperationType -> ActionType pairs

| OperationType | Text | ActionType | Count |
|---|---|---|---|
| 1 | Transfer | 25 | 62 |
| 3 | Feeding | 5 | 813 |
| 4 | Mortality | 3 | 1703 |
| 5 | Input | 4 | 52 |
| 10 | Weight sample | 25 | 99 |
| 12 | Culling | 16 | 490 |
| 12 | Culling | 25 | 490 |
| 16 | Treatment | 57 | 65 |
| 16 | Treatment | 58 | 65 |
| 17 | Vaccination | 22 | 16 |
| 22 | Hatching | 25 | 52 |
| 22 | Hatching | 28 | 52 |

Notes
- ActionType 25 appears across Transfer, Hatching, Culling, and Weight sample operations.
- ActionType 4 is the only ActionType seen on Input operations in this window.
- Vaccination operations map to ActionType 22 in this sample.

---

## Observations

- The event chain (InputProjects -> FishGroupHistory -> Populations -> Action -> Operations) produces a coherent sequence for SF NOV 23.
- SubTransfers count (62) matches the Transfer OperationType count (62) in this window, supporting SubTransfers as the movement lineage table.
- ActionType mapping is incomplete. ActionType 25 appears to be a high-frequency type attached to several OperationTypes and needs targeted mapping.

---

## Next Steps

- Run the same replay query set for the FW halls listed in the transfer report (S03, S24, S16, S08) in the 2025-12 to 2026-02 window.
- Identify what ActionType 25 represents by sampling its ActionIDs against domain tables or ActionMetaData.
- Attempt to connect SubTransfers in that window to sea populations at A11/A21 (if any).

