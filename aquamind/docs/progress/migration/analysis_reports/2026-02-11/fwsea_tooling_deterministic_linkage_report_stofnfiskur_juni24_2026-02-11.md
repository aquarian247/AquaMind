# FWSEA Deterministic Linkage Tooling Report

## Scope

- CSV directory: `scripts/migration/data/extract`
- InternalDelivery rows: 3155
- SalesOperationIDs: 3155
- InputOperationIDs (non-null): 3114
- InputOperationIDs matched in operations extract: 3114/3114
- Component scope: `EDF931F2-51CC-4A10-9002-128E7BF8067C` (id `Stofnfiskur_Juni_24_2_2024`), 145 populations

## Stage-Class Pairing (InternalDelivery rows)

| sales/input stage class | rows |
| --- | ---: |
| sales=fw, input=marine | 2704 |
| sales=fw, input=fw | 160 |
| sales=unknown, input=fw | 112 |
| sales=unknown, input=marine | 100 |
| sales=fw, input=unknown | 47 |
| sales=marine, input=marine | 30 |
| sales=unknown, input=unknown | 2 |

## ActionMetaData Parameters (InternalDelivery ops)

- Parameter 184 rows: 7489 (parseable XML: 7489, trip_id rows: 7489)
- Parameter 184 compartment fields: 0, carrier/transporter fields: 0
- Parameter 220 rows: 6229 (distinct GUIDs: 119)
- Parameter 220 GUID->Contact matches: 119 (unmatched GUIDs: 0)
- Parameter 220 GUID->TransportCarrier matches: 0
- Parameter 220 GUID->Ext_Transporters matches: 0

| Top parameter-220 contact hits | rows | contact types |
| --- | ---: | --- |
| Amhuinnsuidhe (`3ABACBFF-F796-4BC7-8345-6544B16913D8`) | 422 | 12, 13, 2, 3 |
| S04 Húsar (`5DD4D8DF-CC6C-4DCC-8C17-F8EE1D4C4ACD`) | 367 | 13, 2 |
| A71 Funningsfjørður (`02D08D43-5CFF-4070-A1D5-823229D1C5C8`) | 223 | 12, 13 |
| Geocrab (`DFFD7F8E-BECD-4033-9AA8-E952C9AF6055`) | 209 | 12, 13, 2, 3 |
| A57 Fuglafjørður (`209EE671-DAE1-4E89-9134-07ACE48D61D4`) | 189 | 12, 13 |
| A63 Árnafjørður (`97EC8BC4-6DB3-4C84-8EAC-A3FE4DB729B0`) | 177 | 12, 13 |
| A04 Lambavík (`0433A22C-4080-4220-93BE-24A1E81AEA53`) | 176 | 12, 13 |
| FW21 Couldoran (`9089A1F9-408E-41AC-A8D9-CED3E974BEEB`) | 162 | 12, 13, 2, 3 |
| A85 Nes (`3F9A2EE6-5226-45AC-A981-D902D43A2F28`) | 157 | 12, 13, 2, 3 |
| A21 Hvannasund S (`B0C22A74-DF80-4E7A-80FC-B6F0C2CBF785`) | 155 | 12, 13 |

## Operation Overlap Diagnostics

| overlap metric | count |
| --- | ---: |
| SalesOperationID present in SubTransfers | 1390 |
| InputOperationID present in SubTransfers | 1113 |
| SalesOperationID present in PopulationLink | 3037 |
| InputOperationID present in PopulationLink | 3037 |

## Component Scope Diagnostics

- InternalDelivery rows touching component populations: 15
- Sales operations touching component populations: 15
- Input operations touching component populations: 0

## Deterministic Conclusion

- Tooling evidence supports operation-level FW->Sea context in InternalDelivery/ActionMetaData. This report does not make or apply migration-policy/runtime linkage changes.
