# FW→Sea Linkage Scan (CSV extracts, 2026-02-03)

**Scope:** FishTalk CSV extracts in `scripts/migration/data/extract/` from the 2026-01-22 backup. No live DB used.

## Method (qualified)
1. **Identify FW→Sea edges** in `ext_transfers.csv` by joining:
   - `populations.csv` → `containers.csv` → `grouped_organisation.csv` (ProdStage)
   - Filter `SourceStage in {FreshWater, SmoltProduction, Hatchery}` and `DestStage = MarineSite`.
2. **Anchor cohort identity** by backtracing each FW→Sea transfer via `sub_transfers.csv`:
   - Follow `DestPopAfter → SourcePopBefore` edges (lineage) until a population appears in `ext_inputs.csv`.
   - Only accept **unique** roots (single `ext_inputs` population reachable).

## Results (current extract)
- **FW→MarineSite edges in `ext_transfers.csv`: 283**
- **FW→Sea edges with SourcePop or DestPop directly in `ext_inputs.csv`: 0**
- **FW→Sea edges with a unique `ext_inputs` root via SubTransfers lineage: 2**

## Canonical FW→Sea examples (unique ext_inputs roots)

### Example A (InputName salmoBreed/Bolaks | 1 | 2011)
- **Ext_Inputs_v2 root:** `6188822A-FC18-4336-B25E-97B014AB4F95` → `InputName = "salmoBreed/Bolaks"`, `InputNumber = 1`, `YearClass = 2011`
- **Lineage path (SubTransfers):**
  - `45E48633-6E15-4E8C-AD86-919586B0B936`
    → `A702F922-F3DA-41C2-9205-1860DBE384E7`
    → `5BC9B35B-9D44-4ECD-9B94-15D4BF2828C5`
    → `6188822A-FC18-4336-B25E-97B014AB4F95`
- **FW population (SourcePop):** `45E48633-6E15-4E8C-AD86-919586B0B936`
  - Container: `T5m-28`
  - Site (`grouped_organisation.Site`): **FW11 Barvas**
  - ProdStage: **Hatchery** (Freshwater Archive)
- **Sea population (DestPop):** `94B34C30-DF7F-4F62-A46C-FDD4AABD6CEF`
  - Container: `MM12`
  - Site: **S342 MeallMhor**
  - ProdStage: **MarineSite** (Marine)
- **Transfer evidence:**
  - `ext_transfers.csv`: `SourcePop → DestPop` with `TransferredCount = 23754`, `TransferredBiomassKg = 1683.64`
  - `sub_transfers.csv`: `OperationID = AB58187A-E38A-442B-BB4B-D607A8F34428`, `OperationTime = 2011-11-14 15:28:24`

### Example B (InputName SalmoBreed/Bolaks | 2 | 2010)
- **Ext_Inputs_v2 root:** `4FDB8EDA-47F5-40CF-97DB-F6E0929D3E55` → `InputName = "SalmoBreed/Bolaks"`, `InputNumber = 2`, `YearClass = 2010`
- **Lineage path (SubTransfers):**
  - `9E3C28A2-9ED6-49A5-AA44-4E06C9CF0CD1`
    → `FB880D26-69EA-41AC-903E-3ED2DC5B913A`
    → `69459EF4-C70B-4B67-8757-FDAD1F7F8CE5`
    → `7BC27B95-A0AB-4BA5-8B65-60EC1229C39D`
    → `9A39B301-1CE6-4FC8-9F9E-8182659A7D88`
    → `EC7D5D77-8060-4677-8111-C696A49C69F0`
    → `A1AB24B7-E372-4C1A-8E2C-65FCBA00790B`
    → `47AFAE00-AA8C-4D6B-A726-4B6733DAE953`
    → `4FDB8EDA-47F5-40CF-97DB-F6E0929D3E55`
- **FW population (SourcePop):** `9E3C28A2-9ED6-49A5-AA44-4E06C9CF0CD1`
  - Container: `T5m-07`
  - Site: **FW11 Barvas**
  - ProdStage: **Hatchery** (Freshwater Archive)
- **Sea population (DestPop):** `F3A4F0AE-8A20-4B3C-86A1-8C99066C5C84`
  - Container: `VB11`
  - Site: **VuiaBeag**
  - ProdStage: **MarineSite** (Marine)
- **Transfer evidence:**
  - `ext_transfers.csv`: `SourcePop → DestPop` with `TransferredCount = 19225`, `TransferredBiomassKg = 1463.02`
  - `sub_transfers.csv`: `OperationID = B45601EF-CE22-42BD-8754-73CCE4A5BF7D`, `OperationTime = 2011-03-28 10:46:55`

## Notes
- None of the FW→Sea transfer endpoints (SourcePop/DestPop) in these examples appear directly in `ext_inputs.csv`.
- The lineage to `ext_inputs.csv` is only recoverable by chaining `sub_transfers.csv` via `DestPopAfter → SourcePopBefore`.
- These two examples are the **only** FW→Sea edges in the current extract that yield a **unique** `ext_inputs` root using this lineage method.
