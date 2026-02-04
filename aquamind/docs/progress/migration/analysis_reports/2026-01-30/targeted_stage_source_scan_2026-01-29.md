# Targeted Stage Source Scan (2026-01-29)

## Goal
Identify authoritative FishTalk fields/tables that provide lifecycle stage labels (beyond Egg/Alevin/Fry) for fish group histories and hall timelines.

## Schema scan (columns containing “Stage” / “Production” / “ProdStage”)
Only the following objects surfaced as relevant to production stages:

- **ProductionStages** (StageID, StageName, StageOrder)
- **PopulationProductionStages** (PopulationID, StageID, StartTime)
- **OperationProductionStageChange** (PPSPopID, PPSStageID, PPSStartTime, OperationID)
- **Ext_GroupedOrganisation_v2 / Ext_Organisation_v2** (ProdStage)

Other “Stage” hits were lice‑specific tables (LiceStages, LiceStageGroups) and do not describe production lifecycle.

## Targeted checks (Benchmark Gen. Desembur 2024)

### ProductionStages reference list (exists and includes later stages)
ProductionStages includes **Egg, Green egg, Eye‑egg, Sac Fry/Alevin, Fry, Parr, Smolt, Large Smolt, Ongrowing, Grower, Grilse, Broodstock**.

### PopulationProductionStages coverage for fish group
For InputProjectID `FE206D1D-C98D-4362-8E19-E18B388E43F3`:
- Stage names recorded: **Eye‑egg**, **Sac Fry/Alevin**, **Fry**
- **No Parr / Smolt / Post‑Smolt / Adult entries** recorded

### OperationProductionStageChange coverage
For the same InputProject:
- Stage names recorded: **Eye‑egg**, **Sac Fry/Alevin**
- **No later stage change events**

### Ext_GroupedOrganisation_v2.ProdStage (S24 Strond)
All S24 halls (A–J) have **ProdStage = “Hatchery”**.
This does not differentiate Parr/Smolt/Post‑Smolt in the FishTalk data.

## Conclusion
For “Benchmark Gen. Desembur 2024” the FishTalk stage tables only capture **early lifecycle stages**. There is **no authoritative FishTalk stage label** for later halls (D/E/F/G/H/I/J) in the tables scanned.

## Next options
1. **Manual station mapping** (hall → stage) with versioning by time.
2. **Inference** based on hall conventions + weight thresholds.
3. Continue scanning for alternative sources (if any) in planning modules, but current evidence suggests no stage fields beyond the tables above.
