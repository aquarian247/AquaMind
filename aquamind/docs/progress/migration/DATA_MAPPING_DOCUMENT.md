# FishTalk → AquaMind Data Mapping Blueprint

> **Blueprint:** This document defines field-level mapping rules. It should not contain run status or counts.

**Version:** 4.1  
**Date:** January 2026  
**Status:** Refined - Based on live FishTalk schema inspection  

## 1. Overview

This document provides detailed field-level mapping specifications for migrating data from FishTalk to AquaMind. Each section covers entity relationships, field transformations, and business logic required for accurate data migration.

### 1.1 Environments & Schema Snapshots

- **Source:** FishTalk SQL Server (Docker container `sqlserver`, port `1433`, read-only login `fishtalk_reader`).
- **Target:** `aquamind_db_migr_dev` (Django alias `migr_dev`). Keep `aquamind_db` untouched for day-to-day development—the two databases have diverged (159 vs 154 tables).
- **Schema Provenance:** Run `scripts/migration/tools/dump_schema.py` whenever the FishTalk schema changes (`--label fishtalk`) and whenever the AVEVA Historian schema is refreshed (`--label aveva --profile aveva_readonly --database RuntimeDB --container aveva-sql`). Snapshot outputs (`*_schema_snapshot.json`) live under `docs/database/migration/schema_snapshots/`. CSV/TXT exports are generated on demand and are not tracked in the repo.

**Key Revision Notes (v4.2 - 2026-01-20):** 
- **Project-Based Stitching:** FW-to-sea transfers stopped being recorded in `PublicTransfers` since January 2023. Use `(ProjectNumber, InputYear, RunningNumber)` tuple from `dbo.Populations` to group FW and sea populations into logical batches. See `project_based_stitching_report.py`.
- Updated infrastructure mappings to use OrganisationUnit + Ext_GroupedOrganisation_v2 (hall-per-container-group with Høll→Hall normalization) and clarified geography resolution. 
- Mappings use exact confirmed columns (e.g., Populations.StartTime). No Plan*-prefixed tables included. 
- Where direct mappings are absent (e.g., no explicit assignments table), derive from event data (e.g., group Feeding by PopulationID/ContainerID over time to infer assignments).

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

| FishTalk Source | AquaMind Target | Data Type | Transformation | Notes |
|----------------|----------------|-----------|----------------|-------|
| OrganisationUnit.OrgUnitID | ExternalIdMap (OrganisationUnitStation) | uuid | Store for idempotency | `source_identifier = OrgUnitID` |
| Ext_GroupedOrganisation_v2.Site / OrganisationUnit.Name | infrastructure_freshwaterstation.name | varchar(100) | Prefer `Site`, fallback to `OrgUnit.Name` | Trim to 100 chars |
| OrganisationUnit.LocationID → Locations.Latitude/Longitude | infrastructure_freshwaterstation.latitude / longitude | numeric(9,6) | Direct | Default `0` if missing |
| Derived | infrastructure_freshwaterstation.station_type | varchar(20) | `FRESHWATER` | | 
| Geography (from 2.1) | infrastructure_freshwaterstation.geography_id | bigint | FK lookup | |

### 2.3 Hall Mapping (FishTalk: Ext_GroupedOrganisation_v2 + Containers)

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

**Problem Discovered (2026-01-20):** FishTalk's `PublicTransfers` table stopped recording FW-to-sea transfers since January 2023. The original stitching approach relied on this table, causing batch fragmentation.

**Solution:** Project-Based Stitching using `(ProjectNumber, InputYear, RunningNumber)` from `dbo.Populations`:

```sql
-- Groups all populations for a logical batch
SELECT ProjectNumber, InputYear, RunningNumber, PopulationID, PopulationName
FROM dbo.Populations
WHERE ProjectNumber IS NOT NULL AND InputYear IS NOT NULL
```

This groups FW populations (Egg→Smolt) with their sea counterparts (Ongrowing→Harvest) because they share the same project tuple.

**Scripts:**
- `project_based_stitching_report.py` - Generates `project_batches.csv` and `recommended_batches.csv`
- `pilot_migrate_project_batch.py` - Migrates a single project-based batch through the full pipeline

**Output:** Batches with 5-6 lifecycle stages spanning FW and sea, with proper transfer workflows typed as `LIFECYCLE_TRANSITION`.

### 3.1 Batch Mapping (FishTalk: Populations)

| FishTalk Column (Populations) | AquaMind Target | Data Type | Transformation | Notes |
|-------------------------------|-----------------|-----------|----------------|--------|
| PopulationID | batch_batch.external_id | varchar | Store GUID as string | Reference only |
| PopulationName | batch_batch.batch_number | varchar | Prefix with "FT-" | Unique |
| SpeciesID | batch_batch.species_id | bigint | Species lookup/create | Required; confirmed column |
| StartTime | batch_batch.start_date | date | DateTime to Date | Required; convert to date |
| (Derive from events) | batch_batch.lifecycle_stage_id | bigint | Stage mapping from latest event | Via aggregation |
| (Derive from activity) | batch_batch.status | varchar | Derive: Active if latest status is recent | See mapping below |
| (Derive from events) | batch_batch.expected_end_date | date | Not migrated | Set to null |
| (Derive from events) | batch_batch.actual_end_date | date | Set if no recent activity | Nullable |
| Notes (from PopulationProperty) | batch_batch.notes | text | Aggregate properties | JSON format |
| YearClass (from PopulationAttributes) | batch_batch.notes | text | Append as structured | JSON format |

#### Status Mapping (Derived from Activity)

- Use `PublicStatusValues.StatusTime` as the activity signal.
- Compute the latest `StatusTime` per component (across all member populations).
- Compute a global max `StatusTime` and define `active_cutoff = global_max - active_window_days` (default: 365 days).
- Set `batch_batch.status = ACTIVE` when component max ≥ `active_cutoff`, else `COMPLETED`.
- Set `batch_batch.actual_end_date` from the component max status time (fallback to latest population end time if missing).

### 3.2 Container Assignment Mapping (Derived from Events, e.g., Feeding Grouped by PopulationID/ContainerID)

| Derived from FishTalk Events (e.g., Feeding) | AquaMind Target | Data Type | Transformation | Notes |
|----------------------------------------------|-----------------|-----------|----------------|--------|
| (Group by PopulationID/ContainerID) | batch_batchcontainerassignment.id | bigint | Generate new | Derive from events |
| PopulationID | batch_batchcontainerassignment.batch_id | bigint | FK lookup | Required; confirmed in Feeding |
| ContainerID | batch_batchcontainerassignment.container_id | bigint | FK lookup | Required; confirmed in Feeding |
| ProductionStage (from PopulationAttributes) | batch_batchcontainerassignment.lifecycle_stage_id | bigint | Stage lookup | |
| (Aggregate SUM(FeedAmount) as proxy) | batch_batchcontainerassignment.population_count | integer | Derive from event volume | Required |
| (From linked samples) | batch_batchcontainerassignment.avg_weight_g | numeric | Convert to grams | |
| (Calculate: population * avg_weight / 1000) | batch_batchcontainerassignment.biomass_kg | numeric | Calculate post-load | |
| MIN(FeedingTime) for group | batch_batchcontainerassignment.assignment_date | date | Earliest event date | Required |
| MAX(FeedingTime) if inactive | batch_batchcontainerassignment.departure_date | date | Latest status time (fallback end time) | Nullable |
| (Latest PublicStatusValues.StatusTime) | batch_batchcontainerassignment.is_active | boolean | Active if within active window; only newest population per container stays active | Default true |
| MAX(SampleDate) from UserSample | batch_batchcontainerassignment.last_weighing_date | date | Most recent | Nullable |

**Derivation Note**: Group events by PopulationID/ContainerID and continuous date ranges (gaps >7 days start new assignment).

### 3.3 Lifecycle Stage Mapping (FishTalk ProductionStages/PopulationAttributes)

| FishTalk Stage Name (token match, case‑insensitive) | AquaMind Target | Notes |
|------------------------------------------------------|----------------|-------|
| EGG, ALEVIN, SAC, SAC FRY, GREEN EGG, EYE‑EGG | Egg&Alevin | Egg/alevin phases |
| FRY | Fry | |
| PARR | Parr | |
| POST‑SMOLT, LARGE SMOLT | Post‑Smolt | Explicit Post‑Smolt bucket |
| SMOLT | Smolt | Standard smolt stage |
| ONGROW, GROWER, GRILSE, BROODSTOCK, HARVEST | Adult | Sea/on‑growing/harvest stages |

**Notes**
- Stage names are read from `PopulationProductionStages` → `ProductionStages.StageName` (timeline) and from `PopulationAttributes.ProductionStage` as a fallback.
- Token matching is applied anywhere in the stage name; unrecognized stages default to `Smolt` for batch/assignment creation, while transfer workflows fall back to the existing assignment stage if mapping returns `None`.

### 3.4 Transfer Workflow Type Mapping (FishTalk: PublicTransfers)

- For each `PublicTransfers.OperationID`, determine the stage at operation time for source/destination populations using `PopulationProductionStages` (via `stage_at`), with assignment lifecycle stage as fallback.
- If mapped source and destination stages differ → `BatchTransferWorkflow.workflow_type = LIFECYCLE_TRANSITION`.
- Otherwise → `BatchTransferWorkflow.workflow_type = CONTAINER_REDISTRIBUTION`.
- Lifecycle transitions are also synthesized from ordered `PopulationProductionStages` events across project/year/run groups so stage changes exist even without transfers.

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

### 4.2 Feeding Event Mapping (FishTalk: Feeding, HWFeeding, WrasseFeeding)

| FishTalk Column (Feeding) | AquaMind Target | Data Type | Transformation | Notes |
|---------------------------|-----------------|-----------|----------------|--------|
| FeedingID | - | uniqueidentifier | Generate new | Store mapping |
| PopulationID | inventory_feedingevent.batch_id | bigint | FK lookup | Confirmed |
| ContainerID | inventory_feedingevent.container_id | bigint | FK lookup | Confirmed |
| FeedBatchID | inventory_feedingevent.feed_id | bigint | FK lookup | Confirmed |
| FeedingTime | inventory_feedingevent.feeding_date | date | DateTime to Date | Confirmed |
| FeedingTime | inventory_feedingevent.feeding_time | time | DateTime to Time | |
| FeedAmount | inventory_feedingevent.amount_kg | decimal(10,4) | Direct | Confirmed |
| (Derive from batch) | inventory_feedingevent.batch_biomass_kg | decimal(10,2) | Derive post-load | |
| FeedPercent | inventory_feedingevent.feeding_percentage | decimal(8,6) | Calculate if null | Confirmed |
| Method | inventory_feedingevent.method | varchar(20) | Map to choices | Confirmed in HWFeeding |
| Notes | inventory_feedingevent.notes | text | Direct | Confirmed |
| UserID | inventory_feedingevent.recorded_by_id | integer | User lookup | Confirmed |

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

### 5.1 Health Journal Entry Mapping

| FishTalk Source | AquaMind Target | Data Type | Transformation | Notes |
|-----------------|-----------------|-----------|----------------|--------|
| HealthLog.LogID | health_journalentry.id | bigint | Identity map | |
| HealthLog.ProjectID | health_journalentry.batch_id | bigint | FK lookup | Required |
| HealthLog.UnitID | health_journalentry.container_id | bigint | FK lookup | Nullable |
| HealthLog.LogDate | health_journalentry.entry_date | timestamptz | UTC conversion | |
| HealthLog.Category | health_journalentry.category | varchar(20) | Map to choices | |
| HealthLog.Severity | health_journalentry.severity | varchar(10) | Map to choices | |
| HealthLog.Description | health_journalentry.description | text | Direct | |
| HealthLog.Resolution | health_journalentry.resolution_status | boolean | Map to boolean | |
| HealthLog.ResNotes | health_journalentry.resolution_notes | text | Direct | |
| HealthLog.UserID | health_journalentry.user_id | integer | User lookup | |

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

### 6.1 Sensor Reading Mapping (FishTalk: SensorReadings, SensorUnitAssignments) - TimescaleDB

| FishTalk Source | AquaMind Target | Data Type | Transformation | Notes |
|-----------------|-----------------|-----------|----------------|--------|
| SensorReadings.ReadingTime | environmental_environmentalreading.reading_time | timestamptz | UTC conversion | PK part 1 |
| SensorReadings.SensorID | environmental_environmentalreading.sensor_id | bigint | FK lookup | PK part 2 |
| SensorReadings.ParameterType | environmental_environmentalreading.parameter_id | bigint | Param lookup | |
| SensorReadings.Value | environmental_environmentalreading.value | numeric | Direct | |
| SensorUnitAssignments.UnitID | environmental_environmentalreading.container_id | bigint | FK lookup | Via JOIN |
| PlanContainer.PopulationID | environmental_environmentalreading.batch_id | bigint | FK lookup | Via JOIN |
| SensorReadings.IsManual | environmental_environmentalreading.is_manual | boolean | Direct | |
| SensorReadings.Notes | environmental_environmentalreading.notes | text | Direct | |

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
| 100.0 - 500.0 | Post-Smolt | 180 |
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
- Version: 4.3
- Status: Revised
- Last Updated: January 2026
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
