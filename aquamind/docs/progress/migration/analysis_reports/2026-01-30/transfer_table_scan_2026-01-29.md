# Transfer Table Scan

Generated: 2026-01-29 16:23:51

## Extract Counts
- ext_transfers.csv: 311,366
- plan_transfers.csv: 36,357
- reason_for_transfer.csv: 7
- wrasse_pop_transfers.csv: 591
- wrasse_transfers.csv: 0
- ff_bio_transfers.csv: 2,404
- ff_costing_bio_transfers.csv: 25,052
- ff_costing_bio_transfer_attribute_counts.csv: 0

## Ext_Transfers_v2 (cross-site)
- Cross-site edges: 13,946
- S16 Glyvradalur cross-site edges: 0

Sample site pairs (cross-site):
- BRS2 Langass -> FW24 KinlochMoidart
- BRS1 Langass -> Loch Geirean
- HSU -> Dunblane Loch
- FW21 Couldoran -> FW23 Loch Damph South
- Tullich -> FW22 Russel Burn
- N224 Scadabay -> N222 Plocrapol
- S212 Geasgill -> S221 EastTarbertBay
- FW13 Geocrab -> N222 Plocrapol
- FW22 Applecross -> FW22 Russel Burn
- FW13 Geocrab -> FW14 Harris Lochs
- N331 Greanamul -> N312 Trenay
- N222 Plocrapol -> S222 DruimyeonBay
- HO Hatchery -> HSU
- N112 Taranaish -> N113 Vacasay
- FW22 Russel Burn -> FW23 Loch Damph South

## Notes
- PlanTransfer uses PlanPopulation IDs (planning layer), not Production PopulationIDs.
- FF* tables are financial rollups; they do not encode direct PopulationID links.
- Wrasse* tables are species-specific and likely unrelated to salmon FW→Sea transfer linkage.
