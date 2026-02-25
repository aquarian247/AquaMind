# FW->Sea Marine Ingress Candidate Matrix

## Scope

- Source CSV dir: `scripts/migration/data/extract`
- Candidate matrix CSV: `aquamind/docs/progress/migration/analysis_reports/2026-02-18/fwsea_marine_ingress_candidate_matrix_2026-02-18.csv`
- Provisional temporal window days: `2`

## Topline

- Total rows: `216357`
- Canonical rows: `212399`
- Provisional rows: `3958`
- Boundary S*->A* true rows: `3958`

## Classification Counts

- `reverse_flow_fw_only`: 211978
- `true_candidate`: 2138
- `sparse_evidence`: 1820
- `unclassified_nonzero_candidate`: 421

## Evidence-Type Counts

- `canonical`: 212399
- `provisional_temporal_geography`: 3958

## Marine Age-Aware Tier Gate

- Age gate: `<30 months` from cutoff `2026-01-22` (window start `2023-07-22`)
- Sea cohorts under age gate: `34`
- Tier `unlinked_sea`: 30
- Tier `linked_fw_in_scope`: 4

## Explicitly Excluded Flow Families

- `L* -> S*`: 0
- `FW -> FW`: 211978
- `Marine -> Marine`: 0

## Top Candidate Rows

| evidence | class | geography | fw population | sea population | delta_days | boundary | fw component | sea component |
| --- | --- | --- | --- | --- | ---: | --- | --- | --- |
| provisional_temporal_geography | true_candidate | Faroe Islands | 036168E8-1A59-4B53-9A55-5386A09083BB | 4922DCF8-C402-46A8-8D78-ECDD2E08C94B | 0.000 | true | Fiskaaling des09|0|2010 | S-04 FA Mai10|3|2010 |
| provisional_temporal_geography | true_candidate | Faroe Islands | 04CCD129-D226-4E20-A4FC-59B71FC5B257 | 22AA355D-6711-4851-BB35-7635AFEED482 | 0.000 | true | Fiskaaling Nov08|3|2009 | S03 FA Jun11|2|2009 |
| provisional_temporal_geography | true_candidate | Faroe Islands | 077C11F1-9C8C-465D-8EAC-8B9A3B241043 | 2BD0F09A-AAA9-4A50-AD2F-FC9BA7F65694 | 0.000 | true | 2008 st01|0|2008 | Vár 2008|0|2008 |
| provisional_temporal_geography | true_candidate | Faroe Islands | 083CC85D-A087-437C-AD02-31F09B618244 | 4C1D52E0-D4F9-4C1B-952D-924F7C9B8A76 | 0.000 | true | Stofnfiskur Sep12|2|2012 | S04 SF nov12|1|2012 |
| provisional_temporal_geography | true_candidate | Faroe Islands | 10C81542-2ABB-406B-8243-DFAA5898E38D | 59A44EE5-604C-4120-AEFA-5E789C77A2EF | 0.000 | true | 2007 - st03|1|2007 | S03 FA Jun11|0|2007 |
| provisional_temporal_geography | true_candidate | Faroe Islands | 16AEF848-5793-4D55-A590-AC9703EB8954 | 4C1D52E0-D4F9-4C1B-952D-924F7C9B8A76 | 0.000 | true | Stofnfiskur Sep12|2|2012 | S04 SF nov12|1|2012 |
| provisional_temporal_geography | true_candidate | Faroe Islands | 17C7D100-4405-42A2-BFB0-3A49B367C27F | 4C1D52E0-D4F9-4C1B-952D-924F7C9B8A76 | 0.000 | true | Stofnfiskur Sep12|2|2012 | S04 SF nov12|1|2012 |
| provisional_temporal_geography | true_candidate | Faroe Islands | 1B8294D8-AAEC-467F-9AC6-8FDB3A657186 | 97EAD84A-555B-4A82-93BB-DBC4422146B7 | 0.000 | true | 2008 st01|0|2008 | Røkt vár 2008|1|2008 |
| provisional_temporal_geography | true_candidate | Faroe Islands | 1BC3C698-E103-47FE-A7DF-D1A46B90840A | 229BE294-DC42-4091-8475-94F1F7437A60 | 0.000 | true | Fiskaæling Des 10|0|2011 | S08 FA Mai11|0|2011 |
| provisional_temporal_geography | true_candidate | Faroe Islands | 1F089E4D-8867-4B8C-B41B-7C1B3AD85A31 | 8E420FC7-16FB-4571-B705-31203EAE44D8 | 0.000 | true | Fiskaaling Mar11|0|2011 | S08 FA Mai11|0|2011 |
| provisional_temporal_geography | true_candidate | Faroe Islands | 1F089E4D-8867-4B8C-B41B-7C1B3AD85A31 | A084EE78-2498-46CA-A756-05496F18D644 | 0.000 | true | Fiskaaling Mar11|0|2011 | S04 FA Mai11 Test|2|2011 |
| provisional_temporal_geography | true_candidate | Faroe Islands | 2006C3DA-E007-47C6-8AA6-F25ACA2A865F | 9851ED51-63AA-4281-99CF-0784696C31A1 | 0.000 | true | Stofn sep. 2015|2|2016 | S03S10 FA/ST Jul16|2|2016 |
| provisional_temporal_geography | true_candidate | Faroe Islands | 2019F2C8-593B-4ED5-8058-62B4634D6EB4 | 2614295A-7AE3-441F-B782-3EA8EFCF9B88 | 0.000 | true | AquaGenJan10|1|2010 | S21 SF Aug10|1|2010 |
| provisional_temporal_geography | true_candidate | Faroe Islands | 2108A9E6-1739-4D7D-9664-B160CC9F8E08 | B0188A81-388F-4944-870E-5824FEA8889E | 0.000 | true | Stofnfiskur Juli15|1|2015 | 03-Íslenks|0|2015 |
| provisional_temporal_geography | true_candidate | Faroe Islands | 21269CA4-AD90-4D62-984B-4BCA81117D69 | A310B1E1-4C91-4F38-B647-B1CDB95B327D | 0.000 | true | Fiskaaling|0|2007 | S03 FA Jun11|0|2007 |
| provisional_temporal_geography | true_candidate | Faroe Islands | 21924BAC-8F2D-418E-B19C-3A8CFAFCD6E7 | B0188A81-388F-4944-870E-5824FEA8889E | 0.000 | true | Stofnfiskur Juli15|1|2015 | 03-Íslenks|0|2015 |
| provisional_temporal_geography | true_candidate | Faroe Islands | 227A7DC3-504C-4964-9717-68BD0E560C82 | FC3A110F-5CA3-4E15-953B-B439A49C74A2 | 0.000 | true | AquaGenJan10|1|2010 | S16 SF Aug10|0|2010 |
| provisional_temporal_geography | true_candidate | Faroe Islands | 23928DBB-0F16-451F-9F70-93F43139D4C5 | 4C1D52E0-D4F9-4C1B-952D-924F7C9B8A76 | 0.000 | true | Stofnfiskur Sep12|2|2012 | S04 SF nov12|1|2012 |
| provisional_temporal_geography | true_candidate | Faroe Islands | 24182592-E867-4668-A666-1E4BBDE1EF08 | 4DD7CD16-D0D5-4DF1-9138-8B80811F5FAA | 0.000 | true | Fiskaaling des10|2|2010 | S04 AG Test|1|2011 |
| provisional_temporal_geography | true_candidate | Faroe Islands | 25AC13DE-3644-4D34-A7A2-1BA27E4EFF42 | 018E6668-08FB-4582-9D94-4D56613D6B1D | 0.000 | true | Stofnfiskur sep 08|2|2008 | S16-FA|0|2009 |
| provisional_temporal_geography | true_candidate | Faroe Islands | 28B1AD2B-A8B8-40CC-8AB8-5F88A2FD4074 | 229BE294-DC42-4091-8475-94F1F7437A60 | 0.000 | true | Fiskaæling Des 10|0|2011 | S08 FA Mai11|0|2011 |
| provisional_temporal_geography | true_candidate | Faroe Islands | 2E4B493C-FF18-4D91-94CC-860DFA2101E5 | 4B4951D8-997A-4A9E-8BFF-96B911EE760E | 0.000 | true | Stofnfiskur Des12|1|2012 | S16-FA|2|2013 |
| provisional_temporal_geography | true_candidate | Faroe Islands | 364B3B22-3D6D-43D1-AFE9-294B893D35BD | 59A44EE5-604C-4120-AEFA-5E789C77A2EF | 0.000 | true | 2007 - st03|1|2007 | S03 FA Jun11|0|2007 |
| provisional_temporal_geography | true_candidate | Faroe Islands | 376FC46B-CD0C-4C1F-B2EE-670EEE51D6E9 | B0188A81-388F-4944-870E-5824FEA8889E | 0.000 | true | Stofnfiskur Juli15|1|2015 | 03-Íslenks|0|2015 |
| provisional_temporal_geography | true_candidate | Faroe Islands | 3A1AFE1F-33FC-4185-9B92-8A914768DA4B | 2BD0F09A-AAA9-4A50-AD2F-FC9BA7F65694 | 0.000 | true | 2008 st01|0|2008 | Vár 2008|0|2008 |
| provisional_temporal_geography | true_candidate | Faroe Islands | 3A5E3E20-BBCA-4B59-B5EC-1FF4A30214A3 | FAB72710-119F-441F-9D55-919CCE4094CC | 0.000 | true | FA Mars13|0|2013 | Vár 2013|0|2013 |
| provisional_temporal_geography | true_candidate | Faroe Islands | 3A90E610-B306-4B4A-A6D2-666C1D97EEA5 | 361EAD27-AF98-4AA7-9A55-3EB32FF9C21F | 0.000 | true | Stofn aug 16|3|2016 | S21 SF Sep16|1|2016 |
| provisional_temporal_geography | true_candidate | Faroe Islands | 3D4F6F67-E9FE-4D21-9060-B07865A9BA9E | 4C1D52E0-D4F9-4C1B-952D-924F7C9B8A76 | 0.000 | true | Stofnfiskur Sep12|2|2012 | S04 SF nov12|1|2012 |
| provisional_temporal_geography | true_candidate | Faroe Islands | 3DEEB4F8-711F-4BB0-9813-C7A6A4112EBE | 361EAD27-AF98-4AA7-9A55-3EB32FF9C21F | 0.000 | true | Stofn aug 16|3|2016 | S21 SF Sep16|1|2016 |
| provisional_temporal_geography | true_candidate | Faroe Islands | 3F8922A5-27C2-4DCC-B5FA-629C29133659 | 59A44EE5-604C-4120-AEFA-5E789C77A2EF | 0.000 | true | 2007 - st03|1|2007 | S03 FA Jun11|0|2007 |

## Pilot Recommendation

- Recommended evidence: `provisional_temporal_geography` class=`true_candidate`
- FW endpoint: `036168E8-1A59-4B53-9A55-5386A09083BB` (component `Fiskaaling des09|0|2010`)
- Sea endpoint: `4922DCF8-C402-46A8-8D78-ECDD2E08C94B` (component `S-04 FA Mai10|3|2010`)
- Delta days: `0.000`

## Guardrail Note

- Provisional rows are migration-tooling evidence only and not runtime truth.
