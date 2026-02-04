# FishTalk Schema Scan (FW→Sea context, 2026-02-03)

**Scope:** Live FishTalk SQL Server (Docker, DB = `FISHTALK`) with `fishtalk_reader`. Focused on schema elements related to FW→Sea linkage. No data modifications.

## Key objects discovered

### Base tables
- `Populations`
- `SubTransfers`
- `PublicTransfers`
- `Operations`
- `PopulationLink`
- `FishGroupHistory`
- `InputProjects`
- `InternalDelivery`

### Ext_* views (extract-backed)
- `Ext_Transfers_v2`
- `Ext_Inputs_v2`
- `Ext_Populations_v2`
- `Ext_GroupedOrganisation_v2`
- `Ext_StatusValues_v2`

> Note: `sp_helptext` / `sys.sql_modules.definition` returned **no view text** for `Ext_Transfers_v2` (not readable with `fishtalk_reader`). Columns are readable via `SELECT TOP 0 *`.

## Foreign keys (observed)
- `FishGroupHistory.PopulationID → Populations.PopulationID`
- `FishGroupHistory.InputProjectID → InputProjects.InputProjectID`
- `SubTransfers.SourcePopBefore/After/DestPopBefore/DestPopAfter → Populations.PopulationID`
- `SubTransfers.OperationID → Operations.OperationID`
- `PopulationLink.FromPopulationID/ToPopulationID → Populations.PopulationID`
- `PopulationLink.OperationID → Operations.OperationID`
- `InternalDelivery.SalesOperationID → Operations.OperationID`
- `InternalDelivery.InputOperationID → Operations.OperationID`

No FK from `PublicTransfers.OperationID` → `Operations.OperationID` was found in `sys.foreign_keys`, but the join works on data.

## FW→Sea edges in PublicTransfers (live DB)

Classification method:
- `PublicTransfers.SourcePop` / `DestPop` → `Populations.ContainerID` → `Ext_GroupedOrganisation_v2.ProdStage`
- FW stage = `{FreshWater, SmoltProduction, Hatchery}`, Sea stage = `MarineSite`

**Counts:**
- `PublicTransfers` rows: **311,366**
- FW→MarineSite edges: **283**

**Operation years (FW→Sea edges):**
- 2010: **38**
- 2011: **190**
- 2012: **54**
- 2014: **1**

**No FW→Sea edges occur in 2023+** in the current backup (Jan 22, 2026).

## Implications for migration (qualified)
- `Ext_Transfers_v2` appears to reflect `PublicTransfers` (same FW→Sea count), but its view definition is not readable with `fishtalk_reader`.
- FW→Sea edges in the current dataset are **historical only (2010–2014)**; there is **no evidence** of FW→Sea transfer edges for active 2023–2026 cohorts.
- For active batches, FW→Sea linkage will require **other sources** (e.g., alternative tables not extracted or a FishTalk report export), or will remain **unlinked** in migration.
