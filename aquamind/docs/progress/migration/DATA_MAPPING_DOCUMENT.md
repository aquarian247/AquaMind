# FishTalk → AquaMind Data Mapping Blueprint

> **Blueprint:** This document defines field-level mapping rules. It should not contain run status or counts.

**Version:** 4.4  
**Date:** 2026-01-22  
**Status:** Updated - aligned with input-based stitching + verified FishTalk schemas  

## 1. Overview

This document provides detailed field-level mapping specifications for migrating data from FishTalk to AquaMind. Each section covers entity relationships, field transformations, and business logic required for accurate data migration.

### 1.1 Environments & Schema Snapshots

- **Source:** FishTalk SQL Server (Docker container `sqlserver`, port `1433`, read-only login `fishtalk_reader`).
- **Target:** `aquamind_db_migr_dev` (Django alias `migr_dev`). Keep `aquamind_db` untouched for day-to-day development—the two databases have diverged (159 vs 154 tables).
- **Schema Provenance:** Run `scripts/migration/tools/dump_schema.py` whenever the FishTalk schema changes (`--label fishtalk`) and whenever the AVEVA Historian schema is refreshed (`--label aveva --profile aveva_readonly --database RuntimeDB --container aveva-sql`). Snapshot outputs (`*_schema_snapshot.json`) live under `docs/database/migration/schema_snapshots/`. CSV/TXT exports are generated on demand and are not tracked in the repo.

**Key Revision Notes (v4.4 - 2026-01-22):** 
- **Input-Based Stitching:** Use `Ext_Inputs_v2` (InputName + InputNumber + YearClass) as the biological batch key. Project tuples are administrative and can mix year-classes.
- **Feeding Schema Corrected:** `dbo.Feeding` is ActionID‑based and has no PopulationID/ContainerID columns; join via `Action` and `Operations`.
- **Health Journal Corrected:** Use `UserSample` + `Action` join path (one JournalEntry per ActionID), not `HealthLog`.
- **Environmental Sources Updated:** Use `Ext_DailySensorReadings_v2` + `Ext_SensorReadings_v2` (with `is_manual` distinction).
- **Assignments:** Populate counts/biomass from `PublicStatusValues` snapshots (prefer non‑zero after start).

## 2. Infrastructure & Geography Mapping

### 2.1 Geography Mapping (FishTalk: Locations + Site Grouping)

| FishTalk Source | AquaMind Target | Data Type | Transformation | Notes |
|----------------|----------------|-----------|----------------|-------|
| Locations.NationID | infrastructure_geography.name | varchar(100) | Direct | Fallback geography if site grouping fails |
| Ext_GroupedOrganisation_v2.SiteGroup / Site | infrastructure_geography.name | varchar(100) | Resolve to `Faroe Islands` or `Scotland` | SiteGroup takes precedence; see resolution order below |

**Geography resolution order**
1. `SiteGroup` in `{West, North, South}` ⇒ **Faroe Islands**
2. `SiteGroup` present (any other value) ⇒ **Scotland**
3. Site name membership in curated lists (FAROE_SITES_* / SCOTLAND_SITES_*) ⇒ **Faroe Islands** or **Scotland**
4. `Locations.NationID`
5. `Unknown`

### 2.2 Freshwater Station Mapping (FishTalk: OrganisationUnit + Locations + Ext_GroupedOrganisation_v2)

**Reality check (2026-01-22):** `OrganisationUnit.LocationID` is sparsely populated (4106/4215 missing). Geography and station naming should rely primarily on `Ext_GroupedOrganisation_v2.Site/SiteGroup` with `OrganisationUnit.Name` as fallback.

| FishTalk Source | AquaMind Target | Data Type | Transformation | Notes |
|----------------|----------------|-----------|----------------|-------|
| OrganisationUnit.OrgUnitID | ExternalIdMap (OrganisationUnitStation) | uuid | Store for idempotency | `source_identifier = OrgUnitID` |
| Ext_GroupedOrganisation_v2.Site / OrganisationUnit.Name | infrastructure_freshwaterstation.name | varchar(100) | Prefer `Site`, fallback to `OrgUnit.Name` | Trim to 100 chars |
| OrganisationUnit.LocationID → Locations.Latitude/Longitude | infrastructure_freshwaterstation.latitude / longitude | numeric(9,6) | Direct | Default `0` if missing |
| Derived | infrastructure_freshwaterstation.station_type | varchar(20) | `FRESHWATER` | | 
| Geography (from 2.1) | infrastructure_freshwaterstation.geography_id | bigint | FK lookup | |

### 2.3 Hall Mapping (FishTalk: Ext_GroupedOrganisation_v2 + Containers)

**Coverage note (2026-01-22):** `Ext_GroupedOrganisation_v2` has 10,183 rows vs 17,066 containers; ~6,883 containers will not have hall metadata and must fall back to `Containers.OfficialID` or remain unmapped.

| FishTalk Source | AquaMind Target | Data Type | Transformation | Notes |
|----------------|----------------|-----------|----------------|-------|
| Ext_GroupedOrganisation_v2.ContainerGroup | infrastructure_hall.name | varchar(100) | Normalize whitespace; `A Høll` → `Hall A` | `Høll` is Faroese for Hall |
| Containers.OfficialID | infrastructure_hall.name | varchar(100) | Fallback: prefix before `;`, normalize | Used when `ContainerGroup` is empty |
| Ext_GroupedOrganisation_v2.ContainerGroupID | ExternalIdMap (OrganisationUnitHall) | uuid | Store `OrgUnitID:ContainerGroupID` | Ensures per-station uniqueness |
| OrganisationUnit.OrgUnitID | infrastructure_hall.freshwater_station_id | bigint | FK lookup | Hall belongs to station |

### 2.4 Sea Area Mapping (FishTalk: OrganisationUnit + Locations)

| FishTalk Source | AquaMind Target | Data Type | Transformation | Notes |
|----------------|----------------|-----------|----------------|-------|
| OrganisationUnit.Name / Ext_GroupedOrganisation_v2.Site | infrastructure_area.name | varchar(100) | Prefer `Site`, fallback to `OrgUnit.Name` | Trim to 100 chars |
| OrganisationUnit.LocationID → Locations.Latitude/Longitude | infrastructure_area.latitude / longitude | numeric(9,6) | Direct | Default `0` if missing |
| Derived | infrastructure_area.max_biomass | numeric | Default `0` | |
| Geography (from 2.1) | infrastructure_area.geography_id | bigint | FK lookup | |
| Derived | infrastructure_area.active | boolean | `true` | |

### 2.5 Container Mapping (FishTalk: Containers + Ext_GroupedOrganisation_v2)

**Reality check (2026-01-22):** `Containers` contains `OrgUnitID` but not `LocationID`; join path is `Containers.OrgUnitID → OrganisationUnit.LocationID → Locations`. Location is usually missing, so geography should be derived from `Ext_GroupedOrganisation_v2` first.

| FishTalk Source | AquaMind Target | Data Type | Transformation | Notes |
|----------------|----------------|-----------|----------------|-------|
| Containers.ContainerID | infrastructure_container (ExternalIdMap) | uuid | Store for idempotency | `source_model = Containers` |
| Containers.ContainerName | infrastructure_container.name | varchar(100) | Prefix with `FT` | Trim to 100 chars |
| Containers.ContainerType | infrastructure_container.container_type_id | bigint | Map to `FishTalk Imported Tank` / `FishTalk Imported Pen` | Created during migration |
| Ext_GroupedOrganisation_v2.ProdStage | classification | - | `MARINE`/`SEA` ⇒ sea | Otherwise freshwater |
| Ext_GroupedOrganisation_v2.ContainerGroup / Containers.OfficialID | infrastructure_container.hall_id | bigint | Assign hall for freshwater | Uses hall mapping above |
| Derived | infrastructure_container.area_id | bigint | Assign area for sea | Uses sea area mapping |

**Notes**
- Infrastructure phase uses `ProdStage` + hall label presence to classify sea vs freshwater; pilot component migration uses population stages (sea if any member stage is sea).
- Container ExternalIdMap metadata stores `site`, `site_group`, `company`, `prod_stage`, `container_group`, `container_group_id`, `stand_name`, `stand_id`.

#### Container Type Mapping (unchanged)

## 3. Batch & Production Mapping

### 3.0 Population Stitching Strategy (Critical)

#### 3.0.0 NEW RECOMMENDED APPROACH: Input-Based Stitching via Ext_Inputs_v2 (2026-01-22)

**CRITICAL DISCOVERY:** The `Ext_Inputs_v2` table tracks **egg inputs/deliveries** — the best available biological input key **for a lifecycle phase**. This is superior to project tuples for identifying the biological cohort at that phase.

**Why Input-Based Stitching:**
- Project tuple `(ProjectNumber, InputYear, RunningNumber)` is a **financial/administrative grouping** that can mix multiple year-classes
- `Ext_Inputs_v2` tracks actual egg deliveries from suppliers (Stofnfiskur, Bakkafrost, etc.)
- The `InputName` field corresponds to "Árgangur" (year-class) shown in FishTalk exports
- A batch should stay in ONE station → ONE area (geography changes are biologically impossible)
- FishTalk `Populations` represent **container/time segments** (often transfers within the same stage), not biological batch identities

| Source | Purpose | Records | Status |
|--------|---------|---------|--------|
| **`dbo.Ext_Inputs_v2`** | Egg input tracking | Links to ~350K populations | **NEW PRIMARY KEY** |
| `dbo.Populations` | Population segments (container/time) | ~350K | Linked via PopulationID |
| `SubTransfers` | Physical movements | ~205K | Transfer workflows |

**Ext_Inputs_v2 Table Structure:**

| Column | Type | Description |
|--------|------|-------------|
| PopulationID | uniqueidentifier | **Direct link to Populations** |
| InputName | nvarchar | Batch name (e.g., "Stofnfiskur S21 okt 25", "BM Jun 24") |
| InputNumber | int | Numeric identifier for the input (opaque; part of batch key) |
| YearClass | nvarchar | Year class (e.g., "2025", "2024") |
| Supplier | uniqueidentifier | Egg supplier ID |
| StartTime | datetime | When eggs arrived |
| InputCount | float | Number of eggs |
| InputBiomass | float | Input biomass |
| Species | int | Species identifier |

**Batch Key:** `InputName + InputNumber + YearClass`

```sql
-- Input-based batch identification
SELECT 
    i.InputName, i.InputNumber, i.YearClass,
    COUNT(DISTINCT i.PopulationID) as pop_count,
    MIN(i.StartTime) as earliest,
    MAX(i.StartTime) as latest,
    DATEDIFF(day, MIN(i.StartTime), MAX(i.StartTime)) as span_days,
    SUM(i.InputCount) as input_count_estimate
FROM dbo.Ext_Inputs_v2 i
WHERE i.InputName IS NOT NULL AND i.YearClass IS NOT NULL
GROUP BY i.InputName, i.InputNumber, i.YearClass
ORDER BY input_count_estimate DESC
-- Result: input_count_estimate is an aggregate; validate with domain knowledge
```

**Sample Results:**

| InputName | InputNumber | YearClass | Pops | Span (days) | InputCount (est) |
|-----------|-------------|-----------|------|-------------|------|
| 22S1 LHS | 2 | 2021 | 317 | 42 | 6.9M* |
| Heyst 2023 | 1 | 2023 | 108 | 275 | 6.3M* |
| Stofnfiskur Aug 22 | 3 | 2022 | 40 | 21 | 5.1M* |
| Rogn okt 2023 | 3 | 2023 | 567 | 19 | 4.7M* |

*`InputCount` is recorded per population segment; summing provides an estimate and must be validated against expected egg counts.

**Algorithm:**
1. Group all populations by `(InputName, InputNumber, YearClass)` from Ext_Inputs_v2
2. Each unique combination = one AquaMind Batch **for that lifecycle phase**
3. Validate: single geography, reasonable time span, and that `InputCount` totals align with expected egg counts (flag for review if not)
4. Map populations to BatchContainerAssignments; use SubTransfers to create transfer workflows

### 3.0.0.1 Supplier Codes & Naming Conventions (2026-01-22)

FishTalk uses supplier abbreviations in reporting. These map to full `InputName` values:

| Abbreviation | Supplier | Station(s) | Example InputName |
|--------------|----------|------------|-------------------|
| **BM** | Benchmark Genetics | S24 Strond | "Benchmark Gen. Juni 2024" |
| **BF** | Bakkafrost | S08 Gjógv, S21 Viðareiði | "Bakkafrost S-21 sep24" |
| **SF** | Stofnfiskur | S03, S16, S21 | "Stofnfiskur Juni 24" |
| **AG** | AquaGen | S03 Norðtoftir | "AquaGen juni 25" |

**Display Name Format:** `{Supplier Code} {Month} {Year}` (e.g., "BM Jun 24").
Note: some fish groups retain the full `InputProjects.ProjectName` (e.g., “Benchmark Gen. Desembur 2024”) in UI exports; treat abbreviations as **presentation**, not identity.

**Mixed Batches:** When two inputs are combined (e.g., "BF/BM Mai 2024" or "BM Mar/Jun 24"), use `batch_batchcomposition` to track source batches.

**Benchmark Gen. Desembur 2024 (example, verified 2026‑01‑29):**
- `InputProjects.ProjectName`: **Benchmark Gen. Desembur 2024** (fish group label in UI)
- `InputProjectID`: **FE206D1D-C98D-4362-8E19-E18B388E43F3**
- `YearClass`: **2024**
- `ProjectNumber`: **4**
- `Site`: **S24 Strond**
- Supplier code mapping: **BM** (Benchmark Genetics)

### 3.0.0.2 InputName Changes at FW→Sea Transition

**Observed behavior (verify per fish group):**
1. A **new PopulationID** is created when fish transfer between environments (FW → Sea).
2. **InputName continuity is not guaranteed** in `Ext_Inputs_v2`; sea populations often lack `InputName` rows even when FW identity is known.
3. `Ext_Transfers_v2` can contain **explicit FW → MarineSite edges**; when present, it is the canonical, non‑inferred linkage.

**Canonical FW→Sea linkage (CSV extracts, verified 2026‑02‑03):**
- **Full scan (current extract):** `analysis_reports/2026-02-03/fw_to_sea_linkage_scan_2026-02-03.md`
  - `Ext_Transfers_v2` contains **283** FW→MarineSite edges (SourceStage in `{FreshWater, SmoltProduction, Hatchery}`, DestStage = `MarineSite`, classified via `Grouped_Organisation.ProdStage`).
  - **0** of those edges have `SourcePop` or `DestPop` directly in `Ext_Inputs_v2`.
  - **2** edges yield a **unique** `Ext_Inputs_v2` root **via SubTransfers lineage** (`DestPopAfter → SourcePopBefore`).
  - These two unique-root examples are **historical (2010–2011)**; see **Live DB scan** note below for timing.

**Example A (InputName salmoBreed/Bolaks | 1 | 2011):**
- **Ext_Inputs_v2 root:** `6188822A-FC18-4336-B25E-97B014AB4F95`
- **Lineage (SubTransfers):** `45E48633-6E15-4E8C-AD86-919586B0B936 → A702F922-F3DA-41C2-9205-1860DBE384E7 → 5BC9B35B-9D44-4ECD-9B94-15D4BF2828C5 → 6188822A-FC18-4336-B25E-97B014AB4F95`
- **FW population (source):** `45E48633-6E15-4E8C-AD86-919586B0B936`
  - Container: `T5m-28`
  - `Grouped_Organisation.Site = FW11 Barvas`, `ProdStage = Hatchery`
- **Sea population (dest):** `94B34C30-DF7F-4F62-A46C-FDD4AABD6CEF`
  - Container: `MM12`
  - `Grouped_Organisation.Site = S342 MeallMhor`, `ProdStage = MarineSite`
- **Transfer evidence:** `Ext_Transfers_v2` row `SourcePop → DestPop` with `TransferredCount = 23754`, `TransferredBiomassKg = 1683.64`
- **Operation time (SubTransfers):** `OperationID = AB58187A-E38A-442B-BB4B-D607A8F34428`, `OperationTime = 2011‑11‑14 15:28:24`

**Example B (InputName SalmoBreed/Bolaks | 2 | 2010):**
- **Ext_Inputs_v2 root:** `4FDB8EDA-47F5-40CF-97DB-F6E0929D3E55`
- **Lineage (SubTransfers):** `9E3C28A2-9ED6-49A5-AA44-4E06C9CF0CD1 → FB880D26-69EA-41AC-903E-3ED2DC5B913A → 69459EF4-C70B-4B67-8757-FDAD1F7F8CE5 → 7BC27B95-A0AB-4BA5-8B65-60EC1229C39D → 9A39B301-1CE6-4FC8-9F9E-8182659A7D88 → EC7D5D77-8060-4677-8111-C696A49C69F0 → A1AB24B7-E372-4C1A-8E2C-65FCBA00790B → 47AFAE00-AA8C-4D6B-A726-4B6733DAE953 → 4FDB8EDA-47F5-40CF-97DB-F6E0929D3E55`
- **FW population (source):** `9E3C28A2-9ED6-49A5-AA44-4E06C9CF0CD1`
  - Container: `T5m-07`
  - `Grouped_Organisation.Site = FW11 Barvas`, `ProdStage = Hatchery`
- **Sea population (dest):** `F3A4F0AE-8A20-4B3C-86A1-8C99066C5C84`
  - Container: `VB11`
  - `Grouped_Organisation.Site = VuiaBeag`, `ProdStage = MarineSite`
- **Transfer evidence:** `Ext_Transfers_v2` row `SourcePop → DestPop` with `TransferredCount = 19225`, `TransferredBiomassKg = 1463.02`
- **Operation time (SubTransfers):** `OperationID = B45601EF-CE22-42BD-8754-73CCE4A5BF7D`, `OperationTime = 2011‑03‑28 10:46:55`

**Live DB scan (schema + timing, verified 2026‑02‑03):**
- See `analysis_reports/2026-02-03/fishtalk_schema_scan_fw_sea_2026-02-03.md`.
- `PublicTransfers` (base table) contains **311,366** rows and **283** FW→MarineSite edges (same count as `Ext_Transfers_v2`).
- FW→Sea `OperationTime` years in current backup: **2010 (38)**, **2011 (190)**, **2012 (54)**, **2014 (1)**. **No FW→Sea edges exist in 2023+** in the current backup (2026‑01‑22).
- `Ext_Transfers_v2` view definition is **not readable** with `fishtalk_reader` (no `sp_helptext` output), but its columns are visible and its FW→Sea edge count matches `PublicTransfers`.

**Stofnfiskur Aug 2024 (no FW→Sea linkage in current extracts; verified 2026‑01‑29 with 2026‑01‑22 backup):**
- FW anchor (fish group label): `InputProjects.ProjectName = "Stofnfiskur Aug 2024"`
- `InputProjectID`: **AEEDBACC-168E-454E-9C7C-84FAE328D604**
- `YearClass`: **2024**, `ProjectNumber`: **4**, `Site`: **S16 Glyvradalur**
- `Ext_Inputs_v2`: `InputName = "Stofnfiskur Aug 2024"`, `InputNumber = 4`, `YearClass = 2024`, `StartTime = 2024‑08‑08`
- `FishGroupHistory` yields **183 PopulationIDs**, all at **S16 Glyvradalur** (no sea sites)

**Sea populations observed in `Ext_Populations_v2` (name‑based evidence only, not a proven link):**
- **A25 Gøtuvík**: `S01 S16 SF NOV 25 (AUG 24) (*MO)` (container S01)
- **A47 Gøtuvík**: `N01 S16 SF NOV 25 (AUG 24) (*MO)` / `N01 S16 SF NOV 25 (AUG 24) (*½MO)` / `N03 S16 SF NOV 25 (AUG 24)`
- **A11 Hvannasund S**: `03 S16 SF DES 25 (AUG 24) (*MO)`
- **A21 Hvannasund S**: `05 S16 SF DES 25 (AUG 24) (*MO)`

**Linking check (current CSV extracts):**
- `PopulationLinks` and `TransferEdges` show **no cross‑site links** from **S16 Glyvradalur → A25/A47/A21/A11** for this cohort.
- `InputProjects` has **no entries** for the sea population names; `Ext_Inputs_v2` has **no InputName rows** for these sea populations.
- `InternalDelivery` (3155 rows total) contains **10 rows** with `InputSiteID = S16 Glyvradalur`; all **InputOperationID are null**, and none of the linked `SalesOperationID` actions reference **Stofnfiskur Aug 2024** populations (no overlap with `FishGroupHistory` for `AEEDBACC-168E-454E-9C7C-84FAE328D604`).
- `Ext_Transfers_v2` includes cross‑site transfers overall, but **no S16 Glyvradalur cross‑site edges** for this cohort were found in the current extract.
- Backtrace from sea populations (`S16 .* (AUG 24)` in A25/A47/A21/A11) using `Ext_Transfers_v2` yields **only MarineSite→MarineSite** edges within A25/A47 (no FW or S16 sources). See `analysis_reports/2026-01-30/sea_transfer_backtrace_stofnfiskur_aug_2024_2026-01-30.md`.

**Activity Explorer “Input” chain check (S03 → A11 example, verified 2026‑02‑04):**
- **GUI row:** Source `S03 Norðtoftir / Hall 18 Høll A / Unit 1802` → Destination `A11 Hvannasund S / Ring 07 / Official ID A‑11;01093`, Fish group `“07 S03 SF JAN 26 (SEP 24) (MO)”`, Carrier `Tangi 3`, trip `1`, compartment `1`.
- **Container mapping (current CSV extract):**
  - Source container `1802` → `ContainerID = 8197B471-F78A-47B5-A21E-BFE8050DE65E`, `Grouped_Organisation.Site = S03 Norðtoftir`, `ContainerGroup = 18 Høll A`.
  - Destination container `07` → `ContainerID = 468A8053-2CDE-4B9E-AE87-1E5A3FD64D2E`, `OfficialID = A‑11;01093`, `Grouped_Organisation.Site = A11 Hvannasund S`.
- **InternalDelivery evidence:**
  - `InternalDelivery` row: `SalesOperationID = 08F2E1FF-C12F-4ABA-AA79-581F0E170DC7`, `InputSiteID = A11 Hvannasund S`, `InputOperationID = NULL`, `PlannedActivityID = 9E7F2816-E2DC-4325-8A40-B02F54CB758D`.
  - `PlannedActivities` row: `DueDate = 2026‑01‑21 13:29:40`, `Description = "Internal delivery from site S03 Norðtoftir"` (site = A11 Hvannasund S).
  - `internal_delivery_actions` for `SalesOperationID` map **only** to source populations in container `1802` (PopulationIDs `C55D88A4‑B5EA‑4277‑9FE7‑0CCF4E685FA6`, `3D809DA5‑A0E1‑4288‑B4D1‑FF452F65BBE0`); **no actions** found for destination container `07`.
- **Transport metadata:** No carrier/trip/compartment fields appear in `Operations` or `PlannedActivities`, and the schema snapshot contains **no** transport trip/compartment tables or columns. `Ext_Inputs_v2.Transporter` is **null** for all rows in the current extract.
- **Transport tables (CSV, 2026‑02‑04):** `TransportCarrier` now extracted; **Tangi 3** exists (`TransportCarrierID = E3E6DA23‑7A3C‑4E82‑8AA5‑49827D33CE4A`), but there is **no** join path from `InternalDelivery`/`Operations` to this carrier in the current schema/extract.
- **Conclusion (no inference):** The current CSV extract provides a **site‑level internal delivery record** (S03 → A11) but **does not** provide a deterministic link to the destination population or carrier/trip/compartment metadata. This **cannot** be used as canonical FW→Sea linkage yet.

**Implication:** `Ext_Transfers_v2` / `PublicTransfers` + `Populations` + `Grouped_Organisation` provide the **only proven FW→Sea linkage** in current extracts (when present). `Ext_Inputs_v2` remains the **only** deterministic batch identity, but it does **not** appear directly on FW→Sea endpoints; identity must be **back‑traced via SubTransfers** when a unique root exists. Do **not** infer FW→Sea linkage purely from naming; it must be proven via transfer/sales tables.

**Active‑batch constraint (current backup):**
- `InputProjects.Active` exists in the extract (948 active, 1227 inactive as of 2026‑01‑22).
- **No FW→Sea edges exist in 2023+**, so **active cohorts cannot be stitched** via `Ext_Transfers_v2`/`PublicTransfers` in the current backup.
- If we migrate **active batches only**, FW and Sea segments will remain **unlinked** until a newer FishTalk dataset or explicit transfer report provides deterministic FW→Sea linkage.

**Non‑canonical heuristic candidates (review only, 2026‑02‑03):**
- `analysis_reports/2026-02-03/fw_to_sea_heuristic_candidates_postsmolt_2026-02-03.md` (summary) and `fw_to_sea_heuristic_candidates_postsmolt_2026-02-03.csv` (top‑5 candidates per sea population).
- Method (heuristic): parse sea `PopulationName` pattern (e.g., `S07 S21 SF NOV 25 (JUN 24)`), match FW station code to `Grouped_Organisation.Site`, and rank FW candidates by **date proximity** (FW `EndTime` vs sea `StartTime`) with **optional count alignment** (`status_values.csv` last FW count vs first sea count).
- **Overlay applied:** FW candidates restricted to **Post‑Smolt halls** using qualified Faroe hall mappings.
- **Result (2026‑02‑03 run):** 1,315 sea populations matched the naming pattern with post‑smolt FW candidates; **0** candidates matched `Benchmark Gen. Juni 2024` (BM/JUN 2024) and **0** matched `Bakkafrost S‑21 sep24` (BF/SEP 2024). Heuristic stitching for those two batches produced **0** FW→Sea additions.
- **Heuristic validation (non‑canonical, 2026‑02‑03):**
  - **Bakkafrost feb 2024|1|2024:** 4 heuristic additions (**2 sea + 2 FW**) when using default `--heuristic-min-score 70` (sea names: `21 S16 BF JUN 25 (FEB 24)` and `22 S16 BF JUN 25 (FEB 24)` at **A13 Borðoyavík**; FW source halls in **S16 Glyvradalur** `E1/E2 Høll` with day deltas ~‑2 to ‑1 and count ratios ~1.2–1.4 where counts exist). See `scripts/migration/output/input_stitching/full_lifecycle_population_members_Bakkafrost_feb_2024_1_2024.csv` (flag `heuristic_fw_sea`) and `heuristic_fw_sea_links_Bakkafrost_feb_2024_1_2024.csv` (all scored candidate pairs).
  - **Migration run (heuristic, 2026‑02‑03):** Full‑lifecycle migration for `Bakkafrost feb 2024|1|2024` completed against `aquamind_db_migr_dev` using CSV‑only + heuristic stitching (`--full-lifecycle --heuristic-fw-sea --heuristic-min-score 70 --include-fw-batch 'Bakkafrost feb 2024|1|2024' --max-fw-batches 1 --max-pre-smolt-batches 0`). Resulting batch: **id 347**, `batch_number = "Bakkafrost feb 2024"`. Counts: **assignments 24**, **transfer workflows 3 / actions 20** (stage workflows), **feeding 263**, **growth samples 84**, **mortality 720**. Treatments/lice/journal were **skipped** (CSV‑only mode), and environmental/feed‑inventory were **explicitly skipped**. GUI: `http://localhost:5002/batch-details/347`.
  - **Resulting stage totals (DB‑verified, 2026‑02‑03):** Egg&Alevin **1,440,000**; Fry **359,684**; Post‑Smolt **260,803**; Adult **284,810**. (Smolt/Parr absent in this run.)
  - **Important limitation (qualified):** S16 hall `Uppstilling broytt ‑ A Høll` remains **unmapped**; any populations in that hall still rely on FishTalk stage fallback (last stage). Confirming this hall’s stage is needed for full accuracy.
  - **Stofnfiskur Juni 2023|2|2023:** 169 heuristic additions (flagged in `full_lifecycle_population_members_Stofnfiskur_Juni_2023_2_2023.csv`). Candidate scores/ratios in `heuristic_fw_sea_links_Stofnfiskur_Juni_2023_2_2023.csv` are broad and require manual verification.
  - **Stofnfiskur Septembur 2023|3|2023:** 82 heuristic additions (flagged in `full_lifecycle_population_members_Stofnfiskur_Septembur_2023_3_2023.csv`). Candidate scores/ratios in `heuristic_fw_sea_links_Stofnfiskur_Septembur_2023_3_2023.csv` are broad and require manual verification.
- **Do not use** for deterministic stitching; this is a **review aid** only until a transfer report or newer backup provides canonical linkage.

**Linkage sources (ranked):**
- **Primary (edge):** `PublicTransfers` / `Ext_Transfers_v2` + `Populations` + `Grouped_Organisation` (filter FW‑stage → `MarineSite`)
- **Primary (identity):** `SubTransfers` lineage (`DestPopAfter → SourcePopBefore`) to a **unique** `Ext_Inputs_v2` root
- **Fallback candidates:** `InternalDelivery` (SalesOperationID / InputSiteID / InputOperationID), Sales/Delivery/Closing tables if present
- **Activity Explorer “Input” (GUI‑observed):** Appears to encode FW unit → Sea unit moves with **TransportCarrier / trip / compartment** metadata. CSV extracts now include `TransportCarrier`, `TransportMethods`, `Ext_Transporters_v2` (2026‑02‑04), but there is **no** join path from `InternalDelivery`/`Operations` to these transport tables, and `Ext_Inputs_v2.Transporter` is **null** in the 2026‑01‑22 extract. Still missing: Input/Transport operation tables tied to `InternalDelivery.InputOperationID`, and any trip/compartment tables if they exist.
- **Name hints only:** `Ext_Populations_v2.PopulationName`

Use `SubTransfers` for lineage stitching (including FW→Sea). It **can** include FW→MarineSite transitions in the current extract.

### 3.0.0.3 AquaMind Batch Naming Strategy

**Scope:** This section documents how migration tooling assigns `batch_batch.batch_number`. It is not a FishTalk field.

**Verified behavior (migration scripts, 2026‑01‑30):**
- `scripts/migration/tools/pilot_migrate_input_batch.py` sets `batch_number = args.batch_number or batch_info.input_name` → **default is `Ext_Inputs_v2.InputName`** for the batch key.
- `scripts/migration/tools/pilot_migrate_component.py` uses `--batch-number` if provided; otherwise defaults to `FT-{component_key[:8]}-{slug}` (slug derived from the representative population label), truncated to 50 chars.
- `Batch.batch_number` max length is 50; current `ext_inputs.csv` has **max InputName length = 39** (no values > 50 in the 2026‑01‑22 extract).

**History & traceability (code‑verified):**
- `Batch` is tracked by `django-simple-history` (`history = HistoricalRecords()`), and migration scripts use `save_with_history` when creating/updating batches, so **batch_number changes are recorded** in `HistoricalBatch`.
- `ExternalIdMap` entries for `source_model = "PopulationComponent"` store `metadata.batch_number` at creation time (from `pilot_migrate_component.py`).

**Not implemented in migration scripts:**
- No automatic rename to supplier‑code display format is present; any rename would require an explicit `--batch-number` override or a post‑migration edit.

### 3.0.0.4 Ext_Populations_v2 - Supplementary Batch Data

**Observed columns (current extract, 2026‑01‑22 backup):**

| Column | Type | Description |
|--------|------|-------------|
| PopulationID | uniqueidentifier | Links to `Populations` |
| ContainerID | uniqueidentifier | Container location |
| PopulationName | nvarchar | Free‑text label (heterogeneous formats) |
| SpeciesID | int | Species identifier |
| StartTime | datetime | Population segment start |
| EndTime | datetime | Population segment end (nullable) |
| InputYear | char(2) | Project tuple field (two‑char code, digits or letters) |
| InputNumber | char | Project tuple field (digits or letters) |
| RunningNumber | int | Project tuple field |
| Fishgroup | nvarchar | Fish group number/code (always populated in extract) |

**Field behavior (observed in extract):**
- `StartTime/EndTime` in `Ext_Populations_v2` **match `Populations.StartTime/EndTime` exactly** for all 184,234 rows (0 mismatches).
- `EndTime` is **missing in 1,682 rows**; treat these as open segments until closed in source data.
- `PopulationName` is **not uniform**; 5 rows are blank.
- `InputYear` is **always 2 characters**; 5,889 rows use **non‑digit codes** (e.g., `AA`, `AB`).
- `InputNumber` can be **digits or letters**; 13,418 rows are non‑numeric.

**PopulationName patterns (MarineSite only, observed—not guaranteed):**
Examples from the current extract include:
- `07 S16 SF OKT 24 (APR 23)`
- `HS_SB 20 S1`
- `Vár 2009`
- `S08-FA`

Only **1,667 of 56,800** MarineSite names match the previously assumed
`"{Ring} {Station} {Supplier} {Month} {Year} ({YearClass})"` pattern. Treat `PopulationName` as a **hint only**; do not rely on it for deterministic FW→Sea or batch identity.

**Usage guidance (qualified):**
- `PopulationName`, `InputYear`, `InputNumber`, `RunningNumber`, and `Fishgroup` are **project‑tuple attributes**, not a biological batch key (see 3.0.1).
- Use `Ext_Populations_v2` mainly for **additional labeling/context** and for verifying `PopulationID → ContainerID` + time ranges.

### 3.0.0.5 FishGroupHistory + InputProjects (Fish group anchor)

**Purpose (schema‑level):** `FishGroupHistory` maps `PopulationID → InputProjectID`. `InputProjects` holds the project attributes for each `InputProjectID`.

**Key facts (current extract, 2026‑01‑22 backup):**
- `FishGroupHistory` has **2 columns**: `PopulationID`, `InputProjectID` (232,007 rows; 205,010 unique PopulationIDs; 2,078 unique InputProjectIDs).
- All `FishGroupHistory.PopulationID` values exist in `Populations` (**0 missing**).
- All `FishGroupHistory.InputProjectID` values exist in `InputProjects` (**0 missing**).
- `InputProjects` columns in extract: `InputProjectID`, `SiteID`, `Species`, `YearClass`, `ProjectNumberOld`, `ProjectName`, `Active`, `ProjectNumber`.
- `Ext_Populations_v2` includes a `Fishgroup` code column (0 blanks in extract) and **does not include a FishGroupName column**.

**Recommended usage (for container history tracing, qualified):**
1. If you have an `InputProjectID`, use `FishGroupHistory` to collect all `PopulationID` values.
2. Join those populations to `Populations` / `Ext_Populations_v2` for container/time and to `Ext_GroupedOrganisation_v2` for hall/site context.
3. If you need a **human‑readable label**, use `InputProjects.ProjectName` (this is how the batch overview reports label fish groups; UI parity is not asserted here).

**Identity note:** `InputProjects` is a project‑level grouping, not a biological batch key (see 3.0.1). Use `Ext_Inputs_v2` for biological batch identification.

#### 3.0.0.6 Population Semantics (Migration Handling, 2026-01-30)

**What the extracts show (current CSVs):**
- Many operational tables are keyed by `PopulationID` (e.g., `feeding_actions.csv`, `mortality_actions.csv`, `public_weight_samples.csv`, `ext_weight_samples_v2.csv`, `status_values.csv`).
- `Ext_Transfers_v2` links **SourcePop → DestPop** (both PopulationIDs). In the current extract: 311,366 rows and **0 self‑edges** (`SourcePop != DestPop` for all rows).
- `SubTransfers` tracks `SourcePopBefore/After` and `DestPopBefore/After` (PopulationIDs), implying before/after segment IDs are distinct in transfer history.

**Migration behavior (code‑verified):**
- `pilot_migrate_component.py` creates **one `batch_batchcontainerassignment` per PopulationID** and stores an `ExternalIdMap` entry with `source_model = "Populations"`.
- Batches are created **per component** (`PopulationComponent`) or **per input key** (`Ext_Inputs_v2.InputName|InputNumber|YearClass`), not per PopulationID (see `pilot_migrate_component.py` and `pilot_migrate_input_batch.py`).

**Implications (migration policy):**
- Treat `PopulationID` as the **atomic assignment/transfer node** used by event tables and transfer edges.
- Do **not** create `batch_batch` per PopulationID; batch identity comes from `Ext_Inputs_v2` (biological input) or the stitched component key.

#### 3.0.1 Deprecated: Project-Based Stitching (Legacy Only)

**Status:** Not used in current migration flow. Kept for historical context and to discourage reuse.

**What “project‑based” means:** Grouping populations by the tuple `(ProjectNumber, InputYear, RunningNumber)` from `Populations` / `Ext_Populations_v2`.

**Why deprecated (policy):** The current migration pipeline uses **input‑based** or **component‑based** identifiers instead of project tuples.

**Current strategy (code‑verified):**
- **Input‑based:** `Ext_Inputs_v2` key `InputName|InputNumber|YearClass` via `scripts/migration/tools/pilot_migrate_input_batch.py`.
- **Component‑based:** `PopulationComponent` key via `scripts/migration/tools/pilot_migrate_component.py`.

**Legacy tooling (do not use for new runs):**
- `scripts/migration/legacy/tools/pilot_migrate_project_batch.py`
- `scripts/migration/legacy/tools/project_based_stitching_report.py`

#### 3.0.2 Transfer Workflows (SubTransfers‑based, current extracts)

**What’s in the extract (2026‑01‑22 backup):**
- `sub_transfers.csv`: 204,788 rows
- `transfer_operations.csv`: 71,287 rows
- `transfer_edges.csv`: 307,417 rows
- `operation_stage_changes.csv`: 26,937 rows (stage change events; used by analysis tooling, not transfer migration)

**SubTransfers structure (from extract):**
- Keys: `SubTransferID`, `OperationID`
- Edges: `SourcePopBefore/After`, `DestPopBefore/After` (PopulationIDs)
- Timing: `OperationTime`
- Shares: `ShareCountFwd`, `ShareBiomFwd`, `ShareCountBwd`, `ShareBiomBwd`

**Observed behavior (qualified):**
- Using `Grouped_Organisation.ProdStage` as environment classification, `SubTransfers` contains **283 FW→MarineSite edges** in the current extract (SourcePopBefore → DestPopAfter). This means SubTransfers **can** include FW→Sea transitions in this dataset.

**Migration usage (code‑verified):**
- `scripts/migration/tools/pilot_migrate_component_transfers.py` uses SubTransfers when `--use-subtransfers` is supplied.
- PublicTransfers are **not present in current CSV extracts**; the script’s PublicTransfers path requires live SQL and is not validated here.

**Notes:**
- `transfer_edges.csv` / `transfer_operations.csv` are available in extracts but are **not used** by `pilot_migrate_component_transfers.py` as of 2026‑01‑30.

#### 3.0.3 Deprecated: Hybrid Cross‑Project Linking (Legacy Only)

**Status:** Not used in current migration flow. Kept to discourage re‑introducing project‑tuple chaining.

**What it was:** A legacy attempt to connect SubTransfers chains across project tuples, aggregating multiple populations into a single batch.

**Why deprecated (policy):** Current migration identifies batches via **input‑based** (`Ext_Inputs_v2`) or **component‑based** (`PopulationComponent`) keys. Chaining by project tuple is inconsistent with that strategy.

**Operational guidance:** Do not use the legacy `--link-by-project` flag (if encountered in older scripts or notes).

### 3.1 Batch Mapping (FishTalk: Ext_Inputs_v2 + derived aggregates)

**Current migration behavior (code‑verified):**

| Source / Derivation | AquaMind Target | Data Type | Transformation | Notes |
|---------------------|-----------------|-----------|----------------|-------|
| `PopulationComponent` key | `ExternalIdMap` (Batch) | uuid | `source_model = "PopulationComponent"`, `source_identifier = component_key` | Idempotency anchor for batches in `pilot_migrate_component.py`. |
| `--batch-number` argument (if supplied) | `batch_batch.batch_number` | varchar(50) | Direct | Overrides default naming. |
| `InputName` (input‑based pipeline default) | `batch_batch.batch_number` | varchar(50) | Direct | Set by `pilot_migrate_input_batch.py` when `--batch-number` is not provided. |
| Component fallback (no `--batch-number`) | `batch_batch.batch_number` | varchar(50) | `FT-{component_key[:8]}-{slug}` | Used by `pilot_migrate_component.py` when no override is supplied. |
| `members` (stitched populations) | `batch_batch.start_date` | date | `min(member.start_time).date()` | Derived from population start times. |
| Latest member stage | `batch_batch.lifecycle_stage_id` | bigint | `fishtalk_stage_to_aquamind(current_member.last_stage or first_stage)` | Uses stage mapping from 3.3; requires LifeCycleStage records to exist. |
| Activity window (see below) | `batch_batch.status` | varchar | `ACTIVE` / `COMPLETED` | Based on latest status vs active window. |
| Activity window (see below) | `batch_batch.actual_end_date` | date | `component_status_time.date()` or latest member end date | Only set when batch is not active. |
| Script notes | `batch_batch.notes` | text | `FishTalk stitched component {component_key}; representative='{representative}'` | Current migration note string. |
| Defaults | `batch_batch.batch_type` | varchar | Model default | No explicit assignment in migration script. |
| Defaults | `batch_batch.expected_end_date` | date | None | Not set by migration scripts. |

#### Status Mapping (Derived from Activity)

- Source: `PublicStatusValues` (`status_values.csv` in extracts).
- The script computes `global_status_time = max(StatusTime)` across all populations.
- `active_cutoff = global_status_time - active_window_days` (default 365; `--active-window-days`).
- `component_status_time = max(latest_status_time_by_pop)` for the batch’s member populations.
- If `component_status_time >= active_cutoff`, set `status = ACTIVE`; otherwise `COMPLETED`.
- If no status data is available, the script falls back to `any(member.end_time is None)` to mark active.
- `actual_end_date` is set only when not active; it uses `component_status_time.date()` if available, else latest member `end_time`.

### 3.2 Container Assignment Mapping (Stitching Output + PublicStatusValues)

Assignments are created **per PopulationID** from the component stitching output (`population_members.csv`), and enriched with status snapshots from `status_values.csv`.

**Source files used by `pilot_migrate_component.py` (CSV mode):**
- `population_members.csv` (generated by `pilot_migrate_input_batch.py` or legacy stitching): `population_id`, `container_id`, `start_time`, `end_time`, `first_stage`, `last_stage`
- `containers.csv` (container FK resolution)
- `status_values.csv` (biomass snapshots; count fallback only)
- `ext_inputs.csv` (InputCount seed for conservation-based counts)
- `sub_transfers.csv` (ShareCountFwd propagation for conservation-based counts)

**Field mapping (code‑verified):**

| Source / Derivation | AquaMind Target | Data Type | Transformation | Notes |
|---------------------|-----------------|-----------|----------------|-------|
| `population_id` | `ExternalIdMap` (Populations) | uuid | `source_model = "Populations"` | Idempotency for assignments. |
| `container_id` | `batch_batchcontainerassignment.container_id` | bigint | FK lookup | Required. |
| `start_time` | `batch_batchcontainerassignment.assignment_date` | date | `start_time.date()` | Required; rows without start_time are skipped upstream. |
| `first_stage` / `last_stage` | `batch_batchcontainerassignment.lifecycle_stage_id` | bigint | `fishtalk_stage_to_aquamind(last_stage or first_stage)` | Falls back to batch lifecycle stage if no match. |
| SubTransfers propagation (see below) | `batch_batchcontainerassignment.population_count` | int | Seed with `Ext_Inputs_v2.InputCount`, propagate via `SubTransfers.ShareCountFwd`; fallback to status snapshot if no conserved count, **or if conserved count resolves to 0 while snapshot is non‑zero**. If a population is superseded by a **same‑stage** SubTransfer (SourcePopBefore/DestPopBefore → same-stage after), set count to 0 to avoid double‑counting within stage. | Conservation-based within the component; ignores external mixing rows. |
| Status snapshot (see below) | `batch_batchcontainerassignment.biomass_kg` | numeric | `CurrentBiomassKg` quantized to 0.01 | Defaults to 0.00 if missing. |
| Derived | `batch_batchcontainerassignment.avg_weight_g` | numeric | `None` | Not set by migration. |
| Derived | `batch_batchcontainerassignment.is_active` | boolean | See rules below | Ensures only one active assignment per container. |
| Derived | `batch_batchcontainerassignment.departure_date` | date | See rules below | Nullable. |
| Derived | `batch_batchcontainerassignment.notes` | text | `FishTalk PopulationID={population_id}` | Debug trace. |

**Status snapshot selection (code‑verified):**
- If `member.end_time` is **None** and a latest status time exists → snapshot **at latest status time**.
- Otherwise → snapshot **near member.start_time**.
- In CSV mode, if the nearest snapshot has **zero count and biomass**, the loader attempts the **first non‑zero snapshot after** the target time. In SQL mode, the loader uses the nearest snapshot (no non‑zero filtering).
- **Usage:** snapshots provide `biomass_kg` for all assignments; they only provide `population_count` when no conservation‑based count could be derived.

**Conservation-based count flow (code‑verified, 2026‑02‑02):**
1. **Seed** populations with `Ext_Inputs_v2.InputCount` when present.
2. **Propagate** via `SubTransfers.ShareCountFwd` (`SourcePopBefore → SourcePopAfter` and `DestPopBefore → DestPopAfter`).
3. **Fallback** to status snapshot count when no conserved count exists, or when the conserved count is **0** but the snapshot is non‑zero.
4. **Same‑stage suppression:** if a SubTransfer moves fish **within the same lifecycle stage** (source and dest stages match), the **source population assignment is zeroed** to avoid double‑counting within a stage.

**Diagnostics:** see `analysis_reports/2026-02-02/conservation_counts_diagnostics_2026-02-02.md`.

**Active assignment rules (code‑verified):**
1. If the batch itself is not active → all assignments are inactive.
2. Else, if `latest_status_time` is present → active if `latest_status_time >= (global_max_status_time - assignment_active_window_days)`.
3. Else → active if `member.end_time` is None.
4. Additional guards:
   - If assignment lifecycle stage ≠ batch lifecycle stage → force inactive.
   - Only the **latest** population per container (by latest status time, else end_time, else start_time) can be active.

**Departure date rules (code‑verified):**
- If assignment is active → `departure_date = None`.
- Else, if `latest_status_time` exists → `departure_date = latest_status_time.date()`.
- Else, if `member.end_time` exists → `departure_date = member.end_time.date()`.
- Else → `departure_date = None`.

### 3.3 Lifecycle Stage Mapping (ProductionStages / PopulationStages)

**Source tables in extract:**
- `production_stages.csv` (StageID → StageName)
- `population_stages.csv` (PopulationID → StageID → StartTime)
- `operation_stage_changes.csv` (PopulationID → StageID → StageStartTime, OperationTime)

**Observed StageName values (current extract):**
`Egg`, `Green egg`, `Eye-egg`, `Alevin`, `Sac Fry/Alevin`, `Fry`, `Parr`, `Smolt`, `Large Smolt`, `Ongrowing`, `Grower`, `Grilse`, `Broodstock`

**Current mapping logic (code‑verified):**

Order below uses the migration script’s stage order (`STAGE_ORDER = Egg&Alevin → Fry → Parr → Smolt → Post‑Smolt → Adult`). Broodstock is **not** part of that order in code.

| Order | FishTalk StageName token (case‑insensitive) | AquaMind target | Evidence |
|---:|---|---|---|
| 1 | EGG, ALEVIN, SAC | Egg&Alevin | `fishtalk_stage_to_aquamind` in `pilot_migrate_component.py` |
| 2 | FRY | Fry | same |
| 3 | PARR | Parr | same |
| 4 | SMOLT | Smolt | same |
| 5 | SMOLT + (POST or LARGE) | Post‑Smolt | same (only “Large Smolt” matches in current extract) |
| 6 | ONGROW, GROWER, GRILSE | Adult | same |
| — | BROODSTOCK | **No explicit mapping** → returns `None` | verified in code |
| — | Unrecognized | `None` | code default return |

**Coverage notes (extract‑verified):**
- `production_stages.csv` has **13 unique stage names** and **no “Post‑Smolt” literal** string.
- “Large Smolt” is the only stage name that maps to **Post‑Smolt** under current logic.
- `population_stages.csv` covers **102,473 of 355,024** populations (stage data is incomplete in the extract).

**Known accuracy issue (reported by you, not yet resolved in code):**
- You report that **Post‑Smolt is the final freshwater stage after Smolt**. Current mapping assigns “Post‑Smolt” to a separate lifecycle stage but only when “POST”/“LARGE” is present. There is **no “Post‑Smolt” label** in the extract, so this stage is rarely produced by the mapper.

**Hall‑based override (code‑verified, qualified):**
- When a hall mapping exists, it **overrides** the token mapping. Hall labels are taken from `Ext_GroupedOrganisation_v2.ContainerGroup` (these are the same labels shown in the FishTalk GUI; “Høll” = “Hall”).
- **S24 Strond (qualified 2026‑01‑30):**
  - A Høll → Egg&Alevin
  - B Høll → Fry
  - C Høll, D Høll → Parr
  - E Høll, F Høll → Smolt
  - G Høll, H Høll, I Høll, J Høll → Post‑Smolt
- **S03 Norðtoftir (qualified mapping, 2026‑02‑02):**
  - 5 M Høll → Fry
  - 11 Høll A, 11 Høll B → Smolt
  - 18 Høll A, 18 Høll B → Post‑Smolt
  - 800 Høll, 900 Høll → Parr
- **S08 Gjógv (qualified mapping, 2026‑02‑02):**
  - Kleking → Egg&Alevin
  - Startfóðring → Fry
  - T‑Høll → Post‑Smolt
- **S16 Glyvradalur (qualified mapping, 2026‑02‑02; updated 2026‑02‑03):**
  - A Høll → Egg&Alevin
  - B Høll → Fry
  - C Høll → Parr
  - D Høll → Smolt
  - E1 Høll, E2 Høll → Post‑Smolt
  - Klekihøll → Egg&Alevin
  - Startfóðringshøll → Fry
  - Klekihøll → Egg&Alevin
  - Startfóðringshøll → Fry
- **S21 Viðareiði (qualified mapping, 2026‑02‑02):**
  - 5M, A → Fry
  - BA, BB → Parr
  - C, D → Smolt
  - E, F → Post‑Smolt
  - Rogn → Egg&Alevin
- **FW22 Applecross (qualified mapping, Scotland, 2026‑02‑02):**
  - A1, A2 → Egg&Alevin
  - B1, B2 → Fry
  - C1, C2 → Parr
  - D1 → Smolt
  - E1, E2 → Post‑Smolt

**Scotland hall inventory (FishTalk GUI export, 2026‑02‑02; stage not explicitly provided):**
- **FW13 Geocrab:** GradingTank, Hatchery, Parr, Smolt
- **FW21 Couldoran:** A Row, B Row, C Row, D Row, E Row, F Row, Hatchery, RAS
- **FW23 KinlochMoidart:** Archive, Hatchery, Parr, Smolt (RAS 1), Smolt (RAS 2)

Note: several Scotland hall labels are **self‑describing** (e.g., “Parr”, “Smolt”), but **no explicit stage column** was provided in the report. These are **inventory only** until a rule is approved.

**Known gaps / not yet mapped (explicitly left unmapped to avoid guesswork):**
- **S08 Gjógv:** R‑Høll (listed as Parr/Smolt in the source), Úti (no stage provided).
- **S16 Glyvradalur:** Gamalt, Uppstilling broytt ‑ A Høll (no stage provided).
- **S16 Glyvradalur:** Gamalt, Uppstilling broytt ‑ A Høll (no stage provided).
- **S21 Viðareiði:** C gamla, CD, Gamalt (no stage provided).
- **S04 Húsar:** 801–812 (not present in `ContainerGroup` in current extract; only Gamalt appears).
- **S10 Svínoy:** station listed, no hall mapping provided.
- **FW22 Applecross:** D2 labeled “Smolt/post Smolt” (ambiguous; not mapped).
- **Scotland sites:** FW13 Geocrab, FW21 Couldoran, FW23 KinlochMoidart (hall inventory only; stage mapping not provided).

**Remediation options (qualified):**
1. Collect explicit hall → stage mappings for the “gap” halls above (preferred).
2. If approved, add a **“self‑describing hall” rule** (e.g., ContainerGroup == Fry/Parr/Smolt) with explicit sign‑off, and explicitly decide how to treat labels like “Hatchery”, “RAS”, and “Smolt/post Smolt”.
3. Extend hall inference to **StandName/OfficialID** only if a qualified mapping for those labels is provided (not currently in use).

**Progress note (2026‑02‑02):**
- InputProjectID‑based membership + S21 hall mapping resolved stage‑missing failures for **Bakkafrost S‑21 sep24** and enabled full‑lifecycle migration (transfers + feeding + mortality populated).
- Full hall inventory captured for Faroe + Scotland stations; only the Faroe list and FW22 Applecross have **explicit stage** mappings so far.

**Domain note (qualitative, not encoded in migration):**
- Broodstock is a separate breeding division supplying eggs (e.g., Bakkafrost inputs; see 3.0.0.1). Treating Broodstock as a **pre‑Egg&Alevin** stage would require an explicit mapping change plus a controlled re‑run.
- Some stations use a deeper physical hierarchy for egg/alevin handling (Hall → Skáp → Incubation Tray). AquaMind does not currently model this hierarchy; representing it would require a schema/workflow extension.

**Guidance (qualified):**
- The migration now **fails** if a population’s stage cannot be resolved via token mapping or hall mapping; this is intentional to avoid guesswork.
- Any correction to the Post‑Smolt rule requires a code change and a controlled re‑run.
- Do **not** use `Ext_GroupedOrganisation_v2.ProdStage` for lifecycle stage—this field is an organizational bucket, not a biological stage (observed to be coarse in prior analyses).

### 3.4 Transfer Workflow Type Mapping (FishTalk: SubTransfers/PublicTransfers)

**Cross‑reference (context):**
- PRD batch workflow section: `docs/prd.md` → 3.1.2 / 3.1.2.1
- Data model tables: `docs/database/data_model.md` → `batch_batchtransferworkflow`, `batch_transferaction`, `batch_batchcontainerassignment`

**Data Source Selection (code‑verified):**
- **SubTransfers** when `--use-subtransfers` is supplied (CSV or SQL).
  - CSV path uses `sub_transfers.csv` and converts `SourcePopBefore → DestPopAfter` with `OperationTime` as the operation timestamp.
- **PublicTransfers** only when **not** using `--use-subtransfers` **and** running with SQL (no CSV path).
- `transfer_edges.csv` / `transfer_operations.csv` are **not used** by `pilot_migrate_component_transfers.py`.

**Pre‑conditions (code‑verified):**
- Requires `ExternalIdMap` entries for `source_model = "Populations"` created by `pilot_migrate_component.py`.
- Edges are filtered to those where **both** SourcePop and DestPop belong to the current component.

**Workflow typing logic (code‑verified):**
- For each `OperationID`, determine source/dest lifecycle stage:
  - Baseline from `BatchContainerAssignment.lifecycle_stage` (source/dest assignments).
  - Optional override from `PopulationProductionStages` (via `population_stages.csv` → `stage_at` at operation time), mapped with the transfer script’s `fishtalk_stage_to_aquamind`.
- If mapped source and dest stages differ → `workflow_type = LIFECYCLE_TRANSITION`.
- Else → `workflow_type = CONTAINER_REDISTRIBUTION`.
- **Fallback:** If no assignment stage exists, the script uses `LifeCycleStage.objects.first()` (requires master data).

**TransferAction creation (code‑verified):**
- One `TransferAction` per edge (`SourcePop → DestPop`) grouped by `OperationID`.
- Counts/biomass are **estimated** from status snapshots at `OperationStartTime` using `ShareCountForward` / `ShareBiomassForward` (clamped to 0–1).
- For multiple edges from the same source, the script **sequentially reduces** remaining count/biomass to avoid double‑counting.
- Idempotency uses `ExternalIdMap` with `source_model = "PublicTransferEdge"` and `source_identifier = "{OperationID}:{SourcePop}:{DestPop}"` (used for both SubTransfers and PublicTransfers paths).

**Synthetic lifecycle transitions (code‑verified):**
- After edge workflows, the script synthesizes lifecycle transition workflows **from assignment lifecycle stages**, not from `OperationProductionStageChange`.
- It orders stages by `STAGE_ORDER` and creates `BatchTransferWorkflow` + `TransferAction` pairs for consecutive stages present in assignments.
- Idempotency uses `ExternalIdMap` with `source_model = "PopulationStageTransition"` / `"PopulationStageTransitionAction"`.

**SubTransfers Fields (CSV extract):**
| Field | Description |
|-------|-------------|
| SourcePopBefore | Population ID before transfer (source) |
| SourcePopAfter | Population ID after transfer (remnant in source container) |
| DestPopAfter | Population ID after transfer (fish moved to new location) |
| ShareCountFwd | Fraction of count transferred (0–1) |
| ShareBiomFwd | Fraction of biomass transferred (0–1) |

### 3.5 Batch Creation Workflow Mapping (FishTalk: Stitched Components)

FishTalk does not capture a formal “creation workflow.” For each stitched component migrated into a batch, synthesize a creation workflow that represents initial egg placement into the first assignments.

| Derived Source | AquaMind Target | Data Type | Transformation | Notes |
|----------------|----------------|-----------|----------------|--------|
| Component key | batch_creationworkflow.workflow_number | varchar(50) | `CRT-{batch_number}` trimmed to 50 chars; append `-{component_prefix}` if needed | Deterministic per batch |
| Component key | batch_creationworkflow.external_supplier_batch_number | varchar(100) | Direct | Store component key for traceability |
| Synthetic | batch_creationworkflow.egg_source_type | varchar(20) | `EXTERNAL` | Placeholder for FishTalk legacy eggs |
| Synthetic supplier | batch_creationworkflow.external_supplier_id | bigint | Ensure `EggSupplier` named `FishTalk Legacy Supplier` exists | Create if missing |
| Initial assignments | batch_creationworkflow.total_eggs_planned | integer | Sum of `assignment.population_count` for initial set | Defaults to 0 if none |
| Initial assignments | batch_creationworkflow.total_eggs_received | integer | Same as planned | No DOA data available |
| Initial assignments | batch_creationworkflow.total_actions | integer | Count of initial assignments | One action per assignment |
| Initial assignments | batch_creationworkflow.actions_completed | integer | Same as total_actions | Set to completed on migration |
| Initial assignments | batch_creationworkflow.planned_start_date | date | Earliest assignment start date | Also used for actual_start_date |
| Initial assignments | batch_creationworkflow.planned_completion_date | date | Latest assignment start date | Also used for actual_completion_date |
| Synthetic | batch_creationworkflow.status | varchar(20) | `COMPLETED` when actions exist, else `PLANNED` | No in-progress state from source |

**Initial assignment selection rules**
- Prefer populations whose `start_time.date()` equals the batch start date and whose stage maps to the batch’s initial lifecycle stage.
- If none match stage, include all populations starting on the batch start date.
- If still empty, fall back to the earliest population in the component.

**Creation actions**
- Create one `CreationAction` per initial assignment:
  - `dest_assignment` = assignment
  - `egg_count_planned` / `egg_count_actual` = assignment `population_count`
  - `expected_delivery_date` / `actual_delivery_date` = assignment `assignment_date`
  - `status` = `COMPLETED`
- Record idempotency via `ExternalIdMap`:
  - `source_model = PopulationComponentCreationWorkflow` (component key → creation workflow)
  - `source_model = PopulationCreationAction` (population id → creation action)

### 3.6 Input‑Based Stitching Report (Batch Selection & Validation)

**Purpose:** Generate `input_batches.csv` and `input_population_members.csv` for input‑based migration (`pilot_migrate_input_batch.py`). This report runs against the **FishTalk SQL source**, not CSV extracts.

**Script (code‑verified):**
- `scripts/migration/tools/input_based_stitching_report.py`

**Outputs (code‑verified):**
- `input_batches.csv` — one row per batch key (`InputName|InputNumber|YearClass`)
- `input_population_members.csv` — population‑level membership with container/time/stage metadata
- `input_records.csv` — raw Ext_Inputs_v2 rows grouped by batch key

**Validation logic (code‑verified):**
- `is_valid` is **True** if:
  - single geography (excluding `Unknown`), **and**
  - `span_days <= max_span_days` (default 900)
- Additional checks **do not invalidate** the batch but are recorded in `validation_issues`:
  - `total_fish < min_fish` (default 100,000)
  - stage progression out of order

**Filters (code‑verified CLI flags):**
- `--since YYYY-MM-DD` → filters Ext_Inputs_v2 by `StartTime`
- `--min-populations` (default 2)
- `--min-fish` (default 100,000)
- `--max-span-days` (default 900)
- `--valid-only` → keep only `is_valid=True`
- `--require-sea` → require sea stages (`Adult`/`Post‑Smolt`)
- `--active-only` → require `latest_activity.year >= 2024`

**Note:** These validations/filters **shape the report output**; `pilot_migrate_input_batch.py` consumes that output but does not re‑validate.

## 4. Feed & Inventory Mapping

### 4.0 Source of Truth (FishTalk)

- **Purchases:** FishTalk does not have a `FeedPurchase` table. Use `FeedReceptions` (header) and
  `FeedReceptionBatches` (line items) as the canonical purchase source.
- **Feed stock:** Use `FeedStore` + `FeedStoreUnitAssignment` to map feed stores to containers and
  `FeedBatch` + `FeedReceptionBatches` to identify the feed lots in stock.

### 4.1 Feed Type Mapping (FishTalk: FeedType)

| FishTalk Column (FeedType) | AquaMind Target | Data Type | Transformation | Notes |
|----------------------------|-----------------|-----------|----------------|--------|
| FeedID | inventory_feed.id | bigint | Identity map | Confirmed column |
| FeedName | inventory_feed.name | varchar(100) | Direct | |
| Brand | inventory_feed.brand | varchar(100) | Direct | |
| Size | inventory_feed.pellet_size_mm | decimal(5,2) | Direct | |
| SizeCategory | inventory_feed.size_category | varchar(20) | Map to choices | |
| Protein | inventory_feed.protein_percentage | decimal(5,2) | Direct | |
| Fat | inventory_feed.fat_percentage | decimal(5,2) | Direct | |
| Carbs | inventory_feed.carbohydrate_percentage | decimal(5,2) | Direct | |
| Description | inventory_feed.description | text | Direct | |
| Active | inventory_feed.is_active | boolean | Direct | |

### 4.2 Feeding Event Mapping (FishTalk: Feeding, HWFeeding)

FishTalk `dbo.Feeding` is **ActionID-based** (no PopulationID or ContainerID columns).

| FishTalk Source | AquaMind Target | Data Type | Transformation | Notes |
|-----------------|-----------------|-----------|----------------|--------|
| Feeding.ActionID | ExternalIdMap (Feeding) | uuid | Store for idempotency | Key for replay |
| Action.PopulationID | inventory_feedingevent.batch_assignment_id | bigint | ExternalIdMap (Populations) → BatchContainerAssignment | Container inferred from assignment |
| COALESCE(Operations.StartTime, Feeding.OperationStartTime) | feeding_date / feeding_time | date / time | Split datetime | |
| Feeding.FeedAmount | amount_kg | decimal(10,4) | **grams → kg** | Confirmed by pilot |
| FeedBatch + FeedTypes | feed_id | bigint | get_or_create Feed | Use feed name + batch number |
| PublicStatusValues before/after | batch_biomass_kg | decimal(10,2) | Prefer non‑zero snapshot | Avoid zero biomass overflow |
| Feeding.ImportedFrom or HWFeeding | method | varchar(20) | AUTO vs MANUAL | Normalize |
| Operations.Comment | notes | text | Include ActionID + PopulationID | Traceability |

### 4.3 FCR Calculation Mapping
### 4.4 Feed Purchase Mapping (FishTalk: FeedReceptions + FeedReceptionBatches)

| FishTalk Source | AquaMind Target | Data Type | Transformation | Notes |
|-----------------|-----------------|-----------|----------------|--------|
| FeedReceptionBatches.FeedReceptionID | inventory_feedpurchase.id | bigint | Generate new | Source identifier in ExternalIdMap |
| FeedReceptionBatches.FeedBatchID | inventory_feedpurchase.batch_number | varchar | Prefer SuppliersBatchNumber/ReceiptNumber | Fallback to FeedBatch.BatchNumber |
| FeedReceptions.ReceptionTime | inventory_feedpurchase.purchase_date | date | Date part | |
| FeedReceptionBatches.ReceptionAmount | inventory_feedpurchase.quantity_kg | decimal | **grams → kg** | Confirm units per source system |
| FeedReceptionBatches.PricePerKg | inventory_feedpurchase.cost_per_kg | decimal | Direct | |
| FeedReceptions.SupplierID | inventory_feedpurchase.supplier | varchar | Store SupplierID string | Replace with Supplier name if table found |
| FeedReceptionBatches.OutOfDate | inventory_feedpurchase.expiry_date | date | Date part | Nullable |
| FeedReceptionBatches.SuppliersBatchNumber | inventory_feedpurchase.batch_number | varchar | Direct | Preferred over ReceiptNumber |
| FeedReceptionBatches.ReceiptNumber | inventory_feedpurchase.batch_number | varchar | Direct | Fallback |
| FeedBatch.FeedTypeID / FeedTypes.Name | inventory_feedpurchase.feed_id | bigint | FK lookup/create | Use FeedTypes.Name in feed name |

**Extraction rules**
- Join chain: `FeedStoreUnitAssignment → FeedStore → FeedBatch → FeedReceptionBatches → FeedReceptions`.
- Limit to feed stores assigned to the component’s containers (assignment date range overlap with component window).
- By default, `ReceptionTime` must fall inside the component window; use `--include-all-receptions` to bypass the time filter when validating historical purchases.

### 4.5 Feed Container Stock Mapping (FishTalk: FeedStore + FeedStoreUnitAssignment + FeedBatch)

| FishTalk Source | AquaMind Target | Data Type | Transformation | Notes |
|-----------------|-----------------|-----------|----------------|--------|
| FeedStore.FeedStoreID | infrastructure_feedcontainer.id | bigint | Generate new | Source identifier in ExternalIdMap |
| FeedStore.Name | infrastructure_feedcontainer.name | varchar | Direct | |
| FeedStore.Capacity | infrastructure_feedcontainer.capacity_kg | decimal | Direct | Assume kg | 
| FeedStoreUnitAssignment.ContainerID | infrastructure_feedcontainer.hall/area | FK | Map to container's hall/area | Use container mapping |
| FeedReceptionBatches.ReceptionAmount | inventory_feedcontainerstock.quantity_kg | decimal | **grams → kg** | | 
| FeedReceptions.ReceptionTime | inventory_feedcontainerstock.entry_date | datetime | UTC | |
| FeedReceptionBatches → FeedPurchase | inventory_feedcontainerstock.feed_purchase_id | FK | From 4.4 | |

Notes:
- Feed store assignments are **not present** for many FishTalk containers; expect partial coverage.
- `FeedTransfer` can be used later to update stock movements between stores.

| FishTalk Source | AquaMind Target | Data Type | Transformation | Notes |
|-----------------|-----------------|-----------|----------------|--------|
| FCR.ProjectID | inventory_batchfeedingsummary.batch_id | bigint | FK lookup | |
| FCR.PeriodStart | inventory_batchfeedingsummary.period_start | date | Direct | |
| FCR.PeriodEnd | inventory_batchfeedingsummary.period_end | date | Direct | |
| FCR.TotalFeed | inventory_batchfeedingsummary.total_feed_kg | decimal(12,3) | Direct | |
| FCR.StartBiomass | inventory_batchfeedingsummary.total_starting_biomass_kg | decimal(12,2) | Direct | |
| FCR.EndBiomass | inventory_batchfeedingsummary.total_ending_biomass_kg | decimal(12,2) | Direct | |
| FCR.Growth | inventory_batchfeedingsummary.total_biomass_gain_kg | decimal(10,2) | Calculate | |
| FCR.FCRValue | inventory_batchfeedingsummary.fcr | decimal(5,3) | Direct or calc | |

## 5. Health & Medical Mapping

> **Master Data Gaps:**
> - Align FishTalk `MortalityCause` codes with `health_mortalityreason` records before migration.
> - Health parameter labels/scores must match `health_healthparameter` + `health_parameterscoredefinition`; seed any missing entries.
> - Treatment types/vaccine categories require lookup harmonisation (see Sections 5.3 and 5.4).

### 5.1 Health Journal Entry Mapping (FishTalk: UserSample)

FishTalk does not expose a clean `HealthLog` table; health observations are inferred from **UserSample** actions.
We create **one JournalEntry per ActionID**.

| FishTalk Source | AquaMind Target | Data Type | Transformation | Notes |
|-----------------|-----------------|-----------|----------------|--------|
| UserSample.ActionID | ExternalIdMap (UserSampleAction) | uuid | Store for idempotency | One entry per ActionID |
| Action.PopulationID | health_journalentry.batch_id | bigint | FK lookup | Required |
| Action.PopulationID | health_journalentry.container_id | bigint | FK lookup | Optional (via assignment) |
| Operations.StartTime | health_journalentry.entry_date | timestamptz | UTC conversion | |
| UserSampleTypes + UserSampleType | health_journalentry.category | varchar(20) | Map from sample type | Multi-type → summary text |
| Aggregated samples | health_journalentry.description | text | Summary (n fish, avg weight, key parameters) | |
| UserSample.ActionID | health_journalentry.user_id | integer | User lookup | If available |

### 5.2 Mortality Record Mapping

| FishTalk Source | AquaMind Target | Data Type | Transformation | Notes |
|-----------------|-----------------|-----------|----------------|--------|
| Mortality.MortID | batch_mortalityevent.id | bigint | Identity map | |
| Mortality.ProjectID | batch_mortalityevent.batch_id | bigint | FK lookup | Required |
| Mortality.Date | batch_mortalityevent.event_date | date | Direct | |
| Mortality.Count | batch_mortalityevent.count | integer | Direct | |
| Mortality.Cause | batch_mortalityevent.cause | varchar(100) | Direct or map | |
| Mortality.Description | batch_mortalityevent.description | text | Direct | |

### 5.3 Treatment Mapping

| FishTalk Source | AquaMind Target | Data Type | Transformation | Notes |
|-----------------|-----------------|-----------|----------------|--------|
| Treatment.TreatmentID | health_treatment.id | bigint | Identity map | |
| Treatment.ProjectID | health_treatment.batch_id | bigint | FK lookup | |
| Treatment.UnitID | health_treatment.container_id | bigint | FK lookup | |
| Treatment.TreatmentDate | health_treatment.treatment_date | timestamptz | UTC conversion | |
| Treatment.Type | health_treatment.treatment_type | varchar(20) | Map to choices | |
| Treatment.Description | health_treatment.description | text | Direct | |
| Treatment.Dosage | health_treatment.dosage | varchar(100) | Direct | |
| Treatment.Duration | health_treatment.duration_days | integer | Direct | |
| Treatment.Withdrawal | health_treatment.withholding_period_days | integer | Direct | |

## 6. Environmental Data Mapping

> **Master Data Gaps:** Sensor parameter codes in FishTalk must be mapped to `environmental_environmentalparameter` (e.g., DO, Temp, Sal). Add missing parameters plus unit metadata before replaying readings.
>
> **Temporary Source Strategy:** AVEVA historian access is currently pending, so sensor object metadata and early readings will be extracted from FishTalk. Treat FishTalk sensor names as canonical for now—they must remain aligned with the eventual AVEVA sensor catalog. When AVEVA access becomes available, reconcile the two sources and record any divergences in `migration_support.ExternalIdMap` so the loaders can pivot to AVEVA without duplicating historical FishTalk records.

### 6.1 Sensor Reading Mapping (FishTalk: Ext_SensorReadings_v2 / Ext_DailySensorReadings_v2) - TimescaleDB

| FishTalk Source | AquaMind Target | Data Type | Transformation | Notes |
|-----------------|-----------------|-----------|----------------|--------|
| Ext_SensorReadings_v2.ReadingTime | environmental_environmentalreading.reading_time | timestamptz | UTC conversion | Time‑series |
| Ext_DailySensorReadings_v2.Date | environmental_environmentalreading.reading_time | timestamptz | Date → UTC midnight | Daily aggregates |
| SensorID | environmental_environmentalreading.sensor_id | bigint | FK lookup/create | Sensor per (ContainerID, SensorID) |
| Reading | environmental_environmentalreading.value | numeric | Direct | |
| ContainerID | environmental_environmentalreading.container_id | bigint | FK lookup | Via container mapping |
| Derived | environmental_environmentalreading.is_manual | boolean | Daily = True, Time‑series = False | Critical for TGC |

### 6.2 Environmental Parameters

| FishTalk Parameter | AquaMind Parameter | Unit | Range Validation |
|--------------------|-------------------|------|------------------|
| Temperature | Temperature | °C | -5 to 40 |
| Oxygen | Dissolved Oxygen | mg/L | 0 to 20 |
| Salinity | Salinity | ppt | 0 to 40 |
| pH | pH | - | 0 to 14 |
| Turbidity | Turbidity | NTU | 0 to 1000 |
| Ammonia | Ammonia | mg/L | 0 to 10 |

### 6.3 Historian Tag Catalog Bridge

To keep AVEVA data ingestion isolated from AquaMind’s core domain we added a three-table bridge:

- `historian_tag` – canonical catalog (15,399 rows) copied directly from `_Tag`. Stores `tag_id`, `tag_name`, key metadata, plus the untouched AVEVA payload in `metadata`.
- `historian_tag_history` – 5,033 snapshots imported from `TagHistory` (FK is nullable to allow entries for tags that have been deleted upstream).
- `historian_tag_link` – manual mapping table that ties a historian tag to `infrastructure_sensor`, `infrastructure_container`, and/or `environmental_environmentalparameter`.

Workflow:
1. `python manage.py load_historian_tags --profile aveva_readonly --using <db>` refreshes the catalog for either `aquamind_db` or `aquamind_db_migr_dev`.
2. The AVEVA team populates `historian_tag_link` via CSV to associate tags with real AquaMind assets.
3. When block files are parsed, the loader uses the link table to write directly into `environmental_environmentalreading` (Timescale hypertable) without duplicating the historian schema.

## 7. User & Access Control Mapping

### 7.1 User Account Mapping

| FishTalk Source | AquaMind Target | Data Type | Transformation | Notes |
|-----------------|-----------------|-----------|----------------|--------|
| User.UserID | auth_user.id | integer | Identity map | |
| User.Username | auth_user.username | varchar(150) | Lowercase, validate | Unique |
| User.Email | auth_user.email | varchar(254) | Validate format | |
| User.FirstName | auth_user.first_name | varchar(150) | Direct | |
| User.LastName | auth_user.last_name | varchar(150) | Direct | |
| User.Active | auth_user.is_active | boolean | Direct | |
| User.Password | - | - | Reset required | Email reset link |
| User.LastLogin | auth_user.last_login | timestamptz | UTC conversion | |
| User.CreatedDate | auth_user.date_joined | timestamptz | UTC conversion | |

### 7.2 User Profile Mapping

| FishTalk Source | AquaMind Target | Data Type | Transformation | Notes |
|-----------------|-----------------|-----------|----------------|--------|
| User.UserID | users_userprofile.user_id | integer | FK to auth_user | One-to-One |
| User.Role | users_userprofile.role | varchar(100) | Map roles | |
| User.Site | users_userprofile.geography_id | bigint | FK lookup | |
| User.Department | users_userprofile.subsidiary | varchar(100) | Map subsidiary | |
| User.Phone | users_userprofile.phone_number | varchar(20) | Format validation | |

### 7.3 Role Mapping

| FishTalk Role | AquaMind Role | Permissions Group | Notes |
|---------------|---------------|-------------------|--------|
| Administrator | Admin | admin_group | Full access |
| Manager | Manager | manager_group | Site management |
| Operator | Operator | operator_group | Daily operations |
| Viewer | Operator | operator_group | Read-only variant |
| Veterinarian | Veterinarian | vet_group | Health access |

## 8. Broodstock Specific Mappings

### 8.1 Broodstock Fish Mapping

| FishTalk Source | AquaMind Target | Data Type | Transformation | Notes |
|-----------------|-----------------|-----------|----------------|--------|
| Broodstock.FishID | broodstock_broodstockfish.id | bigint | Identity map | |
| Broodstock.PitTag | broodstock_broodstockfish.external_id | varchar | Direct | Unique |
| Broodstock.UnitID | broodstock_broodstockfish.container_id | bigint | FK lookup | |
| Broodstock.Sex | broodstock_broodstockfish.traits | JSON | {"sex": value} | |
| Broodstock.Weight | broodstock_broodstockfish.traits | JSON | {"weight": value} | |
| Broodstock.Status | broodstock_broodstockfish.health_status | varchar(20) | Map status | |

### 8.2 Breeding Event Mapping

| FishTalk Source | AquaMind Target | Data Type | Transformation | Notes |
|-----------------|-----------------|-----------|----------------|--------|
| Spawning.SpawnID | broodstock_breedingpair.id | bigint | Identity map | |
| Spawning.MaleID | broodstock_breedingpair.male_fish_id | bigint | FK lookup | |
| Spawning.FemaleID | broodstock_breedingpair.female_fish_id | bigint | FK lookup | |
| Spawning.SpawnDate | broodstock_breedingpair.pairing_date | timestamptz | UTC conversion | |
| Spawning.EggCount | broodstock_breedingpair.progeny_count | integer | Direct | |

## 9. Financial/Harvest Mapping (If Applicable)

### 9.1 Harvest Event Mapping

| FishTalk Source | AquaMind Target | Data Type | Transformation | Notes |
|-----------------|-----------------|-----------|----------------|--------|
| Harvest.HarvestID | harvest_harvestevent.id | bigint | Identity map | |
| Harvest.ProjectID | harvest_harvestevent.batch_id | bigint | FK lookup | |
| Harvest.Date | harvest_harvestevent.event_date | timestamptz | UTC conversion | |
| Harvest.LiveWeight | harvest_harvestlot.live_weight_kg | decimal | Direct | |
| Harvest.GuttedWeight | harvest_harvestlot.gutted_weight_kg | decimal | Direct | |
| Harvest.Count | harvest_harvestlot.unit_count | integer | Direct | |

## 10. Data Validation Rules

### 10.1 Mandatory Field Validation
```python
REQUIRED_FIELDS = {
    'batch_batch': ['batch_number', 'species_id', 'lifecycle_stage_id', 'status', 'start_date'],
    'batch_batchcontainerassignment': ['batch_id', 'container_id', 'population_count', 'assignment_date'],
    'infrastructure_container': ['name', 'container_type_id', 'active'],
    'inventory_feedingevent': ['batch_id', 'container_id', 'feed_id', 'feeding_date', 'amount_kg']
}
```

### 10.2 Range Validations
```python
RANGE_VALIDATIONS = {
    'latitude': (-90, 90),
    'longitude': (-180, 180),
    'temperature': (-5, 40),
    'ph': (0, 14),
    'percentage': (0, 100),
    'fcr': (0.5, 3.0)
}
```

### 10.3 Business Rule Validations
- Batch assignment dates must be >= batch start date
- Container capacity must not be exceeded
- FCR values must be positive and typically < 3.0
- Mortality count cannot exceed population
- Feed amount must be positive

## 11. Transformation Functions

### 11.1 Date/Time Conversion
```python
def convert_to_utc(dt_value, source_tz='Europe/London'):
    """Convert FishTalk datetime to UTC for AquaMind"""
    if pd.isna(dt_value):
        return None
    local_dt = pd.to_datetime(dt_value)
    local_dt = local_dt.tz_localize(source_tz)
    return local_dt.tz_convert('UTC')
```

### 11.2 Weight Conversion
```python
def convert_weight_to_grams(weight_kg):
    """Convert kg to grams for individual fish weights"""
    if weight_kg is None or pd.isna(weight_kg):
        return None
    return round(weight_kg * 1000, 2)
```

### 11.3 Status Mapping
```python
def map_status(fishtalk_status, mapping_dict):
    """Map FishTalk status to AquaMind status"""
    default_status = 'INACTIVE'
    if pd.isna(fishtalk_status):
        return default_status
    return mapping_dict.get(fishtalk_status, default_status)
```

## 12. Audit & Tracking

### 12.1 Migration Metadata
Each migrated record should include:
```json
{
    "migration_metadata": {
        "source_system": "FishTalk",
        "source_id": "original_id",
        "migration_date": "2024-12-01T00:00:00Z",
        "migration_batch": "BATCH_001",
        "migration_version": "1.0"
    }
}
```

### 12.2 Audit Trail Continuity
- Preserve original created/modified dates
- Store original user IDs for reference
- Maintain change history where available
- Create migration user for system changes

## 13. Error Handling

### 13.1 Error Categories
1. **Critical Errors** - Stop migration
   - Missing required fields
   - Foreign key violations
   - Duplicate key violations

2. **Warnings** - Log and continue
   - Data truncation
   - Default value substitution
   - Unmapped values

3. **Information** - Log only
   - Successful transformations
   - Row counts
   - Performance metrics

### 13.2 Error Logging Format
```json
{
    "timestamp": "2024-12-01T10:00:00Z",
    "level": "ERROR",
    "source_table": "FishTalk.Project",
    "source_id": 12345,
    "target_table": "batch_batch",
    "field": "species_id",
    "error": "Species 'AtlanticCod' not found in reference table",
    "action": "Record skipped"
}
```

---

## 14. Scenario Model Mapping (TGC, FCR, Temperature)

**Purpose:** Migrate growth model master data to enable AquaMind's projection and planning features.

### 14.1 Temperature Profile Mapping (FishTalk: TemperatureTables + TemperatureTableEntries)

| FishTalk Source | AquaMind Target | Data Type | Transformation | Notes |
|-----------------|-----------------|-----------|----------------|-------|
| TemperatureTables.TemperatureTableID | ExternalIdMap | uuid | Store for idempotency | `source_model = TemperatureTables` |
| "FT-TempProfile-{ID[:8]}" | scenario_temperatureprofile.name | varchar(255) | Generated | Unique name |
| TemperatureTableEntries.IntervalStart | scenario_temperaturereading.day_number | int | Direct (already day-based) | 1-900 range |
| TemperatureTableEntries.Temperature | scenario_temperaturereading.temperature | float | Direct | Celsius |

**Row counts:** 20 profiles, 240 readings

### 14.2 TGC Model Mapping (FishTalk: GrowthModels + TGCTableEntries)

| FishTalk Source | AquaMind Target | Data Type | Transformation | Notes |
|-----------------|-----------------|-----------|----------------|-------|
| GrowthModels.GrowthModelID | ExternalIdMap | uuid | `source_model = GrowthModels_TGC` | Separate from FCR mapping |
| GrowthModels.Comment | scenario_tgcmodel.name | varchar(255) | Prefix with "FT-TGC-" | Trim to 255 chars |
| AVG(TGCTableEntries.TGC) | scenario_tgcmodel.tgc_value | float | Average of day-specific values | Per model |
| "FishTalk Import" | scenario_tgcmodel.location | varchar(255) | Static | |
| "Year-round" | scenario_tgcmodel.release_period | varchar(255) | Static | |
| 0.33 | scenario_tgcmodel.exponent_n | float | Default | Standard exponent |
| 0.66 | scenario_tgcmodel.exponent_m | float | Default | Standard exponent |
| (first available) | scenario_tgcmodel.profile_id | FK | Default profile | Required FK |

**Note:** TGCTableEntries contains day-specific TGC values (7,530 rows). These are averaged to produce a single `tgc_value` per model since AquaMind uses a simpler model structure.

### 14.3 FCR Model Mapping (FishTalk: GrowthModels + FCRTableEntries)

| FishTalk Source | AquaMind Target | Data Type | Transformation | Notes |
|-----------------|-----------------|-----------|----------------|-------|
| GrowthModels.GrowthModelID | ExternalIdMap | uuid | `source_model = GrowthModels_FCR` | |
| GrowthModels.Comment | scenario_fcrmodel.name | varchar(255) | Prefix with "FT-FCR-" | |

**Stage derivation:** FCRTableEntries contains weight/temperature-specific FCR values. Aggregate to lifecycle stages:

| Weight Range (g) | AquaMind Stage | Duration (days) |
|-----------------|----------------|-----------------|
| 0.0 - 0.5 | Egg&Alevin | 90 |
| 0.5 - 5.0 | Fry | 60 |
| 5.0 - 30.0 | Parr | 120 |
| 30.0 - 100.0 | Smolt | 90 |
| 100.0 - 500.0 | Post-Smolt | 90 |
| 500.0+ | Adult | 360 |

| FishTalk Source | AquaMind Target | Data Type | Transformation | Notes |
|-----------------|-----------------|-----------|----------------|-------|
| AVG(FCRTableEntries.FCR) per stage | scenario_fcrmodelstage.fcr_value | float | Weight-bucketed average | |
| (lookup) | scenario_fcrmodelstage.stage_id | FK | LifecycleStage lookup | |
| (from mapping table) | scenario_fcrmodelstage.duration_days | int | Default per stage | |

**Row counts:** 120 GrowthModels → 120 FCRModels, up to 6 stages each

### 14.4 Mortality Model Mapping

FishTalk does not have dedicated mortality model tables. Create default mortality models:

| Name | Frequency | Rate (%) | Purpose |
|------|-----------|----------|---------|
| FT-Mortality-Low | daily | 0.01 | Low mortality scenario |
| FT-Mortality-Standard | daily | 0.05 | Standard mortality |
| FT-Mortality-High | daily | 0.10 | High mortality scenario |

### 14.5 ExternalIdMap Source Models

| source_model | Description |
|--------------|-------------|
| `TemperatureTables` | Temperature profile mapping |
| `GrowthModels_TGC` | TGC model mapping |
| `GrowthModels_FCR` | FCR model mapping |

---

**Document Control**
- Version: 4.4
- Status: Revised
- Last Updated: 2026-01-22
- Next Review: [Pending]

## 15. External ID Mapping Tables

AquaMind now persists source-to-target identifier mappings in the `apps.migration_support.ExternalIdMap` model. Each row captures the FishTalk identifier (`source_system='FishTalk'`) and the AquaMind object it produced.

| Field | Description |
| --- | --- |
| source_system | External system name (e.g., `FishTalk`, `Aveva`). |
| source_model | Source table/entity (Populations, Feeding, etc.). |
| source_identifier | Primary key in the source system (PopulationID, FeedingID...). |
| target_app_label / target_model | Django app + model storing the migrated row. |
| target_object_id | Primary key of the AquaMind object. |
| metadata | JSON payload for auxiliary context (batch numbers, timestamps, etc.). |

Use this table to de-duplicate replays, troubleshoot migrations, and produce reconciliation reports. The mapping scripts should always look up existing entries before creating new AquaMind records to keep migrations idempotent.
