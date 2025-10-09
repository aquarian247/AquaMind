# FishTalk to AquaMind Data Mapping Document

**Version:** 4.0  
**Date:** December 2024  
**Status:** Refined - Based on fishtalk_column_headers Analysis  

## 1. Overview

This document provides detailed field-level mapping specifications for migrating data from FishTalk to AquaMind. Each section covers entity relationships, field transformations, and business logic required for accurate data migration.

**Key Revision Notes (v4.0):** Refined based on fishtalk_column_headers.txt (or CSV equivalent). Mappings use exact confirmed columns (e.g., Populations.StartTime). No Plan*-prefixed tables included. Where direct mappings are absent (e.g., no explicit assignments table), derive from event data (e.g., group Feeding by PopulationID/ContainerID over time to infer assignments). Assumes CSV exports for tables; load via pandas in script for transformation.

## 2. Infrastructure & Geography Mapping

### 2.1 Geography/Site Mapping (FishTalk: Sites)

| FishTalk Column (Sites) | AquaMind Target | Data Type | Transformation | Notes |
|-------------------------|-----------------|-----------|----------------|--------|
| SiteID | infrastructure_geography.id | bigint | Identity map + offset | Store original ID for reference |
| SiteName | infrastructure_geography.name | varchar(100) | Direct | Unique constraint |
| Description | infrastructure_geography.description | text | Direct | Nullable |
| Country | infrastructure_geography.description | text | Append to description | "Country: {value}" |
| CreatedDate | infrastructure_geography.created_at | timestamptz | UTC conversion | |
| ModifiedDate | infrastructure_geography.updated_at | timestamptz | UTC conversion | |

### 2.2 Area/Location Mapping (FishTalk: Locations)

| FishTalk Column (Locations) | AquaMind Target | Data Type | Transformation | Notes |
|-----------------------------|-----------------|-----------|----------------|--------|
| LocationID | infrastructure_area.id | bigint | Identity map + offset | |
| LocationName | infrastructure_area.name | varchar(100) | Direct | |
| SiteID | infrastructure_area.geography_id | bigint | FK lookup | Required |
| Latitude | infrastructure_area.latitude | numeric(9,6) | Direct | Validate range (-90 to 90) |
| Longitude | infrastructure_area.longitude | numeric(9,6) | Direct | Validate range (-180 to 180) |
| MaxBiomass | infrastructure_area.max_biomass | numeric | Unit conversion if needed | |
| Status | infrastructure_area.active | boolean | Map: Active=>true | Derive from recent activity if null |

### 2.3 Container/Unit Mapping (FishTalk: Units)

| FishTalk Column (Units) | AquaMind Target | Data Type | Transformation | Notes |
|-------------------------|-----------------|-----------|----------------|--------|
| UnitID | infrastructure_container.id | bigint | Identity map + offset | |
| UnitName | infrastructure_container.name | varchar(100) | Direct | |
| UnitType | infrastructure_container.container_type_id | bigint | Lookup/Create | Map type (see below) |
| HallID | infrastructure_container.hall_id | bigint | FK lookup | Optional |
| AreaID | infrastructure_container.area_id | bigint | FK lookup | Optional |
| Volume | infrastructure_container.volume_m3 | numeric(10,2) | Direct or convert | |
| MaxBiomass | infrastructure_container.max_biomass_kg | numeric(10,2) | Direct | |
| IsActive | infrastructure_container.active | boolean | Direct | Default true |

#### Container Type Mapping (unchanged)

## 3. Batch & Production Mapping

### 3.1 Batch Mapping (FishTalk: Populations)

| FishTalk Column (Populations) | AquaMind Target | Data Type | Transformation | Notes |
|-------------------------------|-----------------|-----------|----------------|--------|
| PopulationID | batch_batch.external_id | varchar | Store GUID as string | Reference only |
| PopulationName | batch_batch.batch_number | varchar | Prefix with "FT-" | Unique |
| SpeciesID | batch_batch.species_id | bigint | Species lookup/create | Required; confirmed column |
| StartTime | batch_batch.start_date | date | DateTime to Date | Required; convert to date |
| (Derive from events) | batch_batch.lifecycle_stage_id | bigint | Stage mapping from latest event | Via aggregation |
| (Derive from activity) | batch_batch.status | varchar | Derive: Active if recent events | See mapping below |
| (Derive from events) | batch_batch.expected_end_date | date | Not migrated | Set to null |
| (Derive from events) | batch_batch.actual_end_date | date | Set if no recent activity | Nullable |
| Notes (from PopulationProperty) | batch_batch.notes | text | Aggregate properties | JSON format |
| YearClass (from PopulationAttributes) | batch_batch.notes | text | Append as structured | JSON format |

#### Status Mapping (Derived from Activity)

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
| MAX(FeedingTime) if inactive | batch_batchcontainerassignment.departure_date | date | Latest event date if ended | Nullable |
| (Has events in last 30 days?) | batch_batchcontainerassignment.is_active | boolean | True if recent | Default true |
| MAX(SampleDate) from UserSample | batch_batchcontainerassignment.last_weighing_date | date | Most recent | Nullable |

**Derivation Note**: Group events by PopulationID/ContainerID and continuous date ranges (gaps >7 days start new assignment).

### 3.3 Lifecycle Stage Mapping (unchanged)

## 4. Feed & Inventory Mapping

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
**Document Control**
- Version: 1.0
- Status: Draft
- Last Updated: December 2024
- Next Review: [Pending]
