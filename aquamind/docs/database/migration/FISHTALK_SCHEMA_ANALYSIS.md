# FishTalk Database Schema Analysis

**Date:** December 2024  
**Source:** FishTalk Database Export  

## Executive Summary

This document provides a detailed analysis of the actual FishTalk database schema based on the exported table and column information. The analysis focuses on identifying key entities and their relationships for migration to AquaMind.

## 1. Database Overview

### 1.1 Database Statistics
- **Total Tables Identified:** ~340+ tables
- **Largest Tables by Row Count:**
  - PublicPlanStatusValues: 89.4M rows
  - PublicMortalityStatus: 32.1M rows
  - Action: 12.8M rows
  - Feeding: 4.5M rows
  - Mortality: 4.4M rows
  - SensorReadings: 2.6M rows
  - UserSample: 1.1M rows

### 1.2 Key Schema Patterns
- Heavy use of GUIDs (uniqueidentifier) for primary keys
- Plan-based architecture (PlanPopulation, PlanContainer, PlanSite, etc.)
- Public vs. internal tables (Public* prefix for reporting/views)
- Extensive status tracking (StatusValues, StatusCalculation)
- FF prefix likely indicates "Fish Farming" specific tables

## 2. Core Entity Mapping

### 2.1 Population/Batch Management

**Primary Tables:**
- **Populations** - Core batch/population entity
- **PublicPlanPopulation** (563K rows) - Planning view of populations
- **PlanPopulation** (229K rows) - Detailed population planning
- **PopulationAttributes** - Additional batch attributes
- **PopulationProperty** - Extended properties
- **PopulationLink** - Relationships between populations

**Key Columns Identified:**
- PopulationID (uniqueidentifier)
- Species/SpeciesID
- StartDate/EndDate
- PopulationStatus
- ProductionStage

### 2.2 Container/Infrastructure

**Primary Tables:**
- **Containers** - Physical container entities
- **PlanContainer** (489K rows) - Container planning assignments
- **ContainerPhysics** - Physical characteristics
- **ContainerPhysicsHistory** - Historical container data
- **ACAFSContainer** - Alternative container system

**Key Columns:**
- ContainerID (uniqueidentifier)
- PlanContainerID
- PlanSiteID
- Capacity/Volume metrics

### 2.3 Site/Location Hierarchy

**Primary Tables:**
- **PlanSite** - Site planning entities
- **PlanSiteConditions** - Environmental conditions
- **SiteFallowPeriods** - Fallow management
- **ModelSiteAssignments** - Site model assignments

**Key Columns:**
- SiteID
- OrgUnitID (Organization Unit)
- LocationID
- Coordinates (likely lat/long)

### 2.4 Feed Management

**Primary Tables:**
- **Feeding** (4.5M rows) - Core feeding events
- **HWFeeding** - Hardware/automatic feeding
- **WrasseFeeding** - Cleaner fish feeding
- **FFBioFeeding** - Bio feeding records
- **PlanStatusFeedUse** (2.2M rows) - Feed usage planning
- **FeedCalibrationUnit** - Feed calibration data
- **FeedTransferCauses** - Feed movement reasons

**Key Columns:**
- FeedingID
- ContainerID/UnitID
- FeedAmount
- FeedingTime
- FeedBatchID

### 2.5 Health & Mortality

**Primary Tables:**
- **Mortality** (4.4M rows) - Mortality events
- **PublicMortalityStatus** (32.1M rows) - Mortality status tracking
- **WrasseMortality** - Cleaner fish mortality
- **MortalityResponsibility** - Mortality cause tracking
- **PublicLiceSampleData** (558K rows) - Lice sampling
- **PublicLiceSamples** - Lice count records

**Key Columns:**
- MortalityID
- Count/Number
- Cause/Reason
- Date/DateTime
- ResponsibleParty

### 2.6 Sampling & Measurements

**Primary Tables:**
- **UserSample** (1.1M rows) - User-entered samples
- **UserSampleParameterValue** (1.3M rows) - Sample parameters
- **UserSampleTypes** - Sample type definitions
- **PublicWeightSamples** - Weight sampling data

**Key Columns:**
- SampleID
- SampleDate
- ParameterID/Value
- Weight/Length measurements

### 2.7 Environmental & Sensors

**Primary Tables:**
- **SensorReadings** (2.6M rows) - Sensor data
- **SensorUnitAssignments** - Sensor to unit mapping
- **PlanConditions** - Environmental conditions
- **TidePredictionLocation** - Tidal data

**Key Columns:**
- SensorID
- ReadingTime
- Value
- UnitID/ContainerID

### 2.8 Operations & Actions

**Primary Tables:**
- **Action** (12.8M rows) - Operational actions
- **ActionMetaData** (5.9M rows) - Action details
- **Operations** (7M rows) - Operational records
- **PlannedActivitiesUsers** (1M rows) - User activities
- **ConnectTreatmentAndFeedingOps** - Treatment linkage

### 2.9 Planning & Status

**Primary Tables:**
- **PublicPlanStatusValues** (89.4M rows) - Largest table, status tracking
- **PublicStatusValues** (7.3M rows) - Status definitions
- **StatusCalculation** (7.2M rows) - Calculated statuses
- **PlanAction** (572K rows) - Planned actions
- **PlanFolder** - Planning organization

## 3. Data Type Patterns

### Common Data Types:
- **uniqueidentifier** - Primary/Foreign keys (GUIDs)
- **nvarchar(max/-1)** - Text fields
- **datetime** - Timestamp fields
- **float** - Numeric measurements
- **int** - Counts and enumerations
- **bit** - Boolean flags

### Nullable Patterns:
- Most foreign keys are nullable
- Descriptive fields often nullable
- Core IDs and dates typically NOT NULL

## 4. Critical Migration Considerations

### 4.1 Active Data Identification
Based on table sizes and patterns:
- Focus on recent **Populations** (not all 89M status records)
- Filter **Feeding** and **Mortality** by date range
- Consider only active **Containers** and **PlanSite**
- Prioritize recent **SensorReadings** (last 12 months)

### 4.2 Key Relationships to Preserve
1. Population → Container assignments (via PlanContainer)
2. Container → Site hierarchy
3. Population → Feeding events
4. Population → Mortality records
5. Population → Sample data
6. Container → Sensor readings

### 4.3 Data Volume Considerations
- **PublicPlanStatusValues** (89M rows) - Likely contains historical status snapshots, filter aggressively
- **PublicMortalityStatus** (32M rows) - May contain duplicates or historical states
- **Action/Operations** (12-13M rows) - Audit trail, may not need full migration

### 4.4 Naming Convention Mappings
- Plan* tables → Planning/scheduling entities
- Public* tables → Reporting views or denormalized data
- FF* tables → Fish farming specific
- HW* tables → Hardware/automation related
- Wrasse* tables → Cleaner fish specific (may not apply to all operations)

## 5. Recommended Migration Approach

### Phase 1: Core Entities
1. **Sites/Locations** - Establish geographic hierarchy
2. **Containers** - Physical infrastructure
3. **Populations** (filtered) - Active batches only

### Phase 2: Operational Data
1. **Feeding** (recent) - Last 12-24 months
2. **Mortality** (recent) - Last 12-24 months
3. **UserSample** - Growth and health samples

### Phase 3: Environmental
1. **SensorReadings** - Recent readings only
2. **Environmental conditions** - Current state

### Phase 4: Planning (Optional)
1. **PlanAction** - Future planned activities
2. **PlannedActivitiesUsers** - User assignments

## 6. Data Quality Concerns

### Potential Issues:
- Large status tables may contain redundant data
- Public* tables might be denormalized views
- Multiple feeding tables (Feeding, HWFeeding, WrasseFeeding) need consolidation
- GUID primary keys will need mapping tables
- Nullable foreign keys may indicate optional relationships

### Validation Requirements:
- Row count reconciliation after filtering
- Foreign key integrity checking
- Date range validation
- Duplicate detection in Public* tables

## Appendix A: Table Size Reference

| Table Name | Row Count | Priority |
|------------|-----------|----------|
| PublicPlanStatusValues | 89.4M | Low (historical) |
| PublicMortalityStatus | 32.1M | Medium (filter) |
| Action | 12.8M | Low (audit) |
| Feeding | 4.5M | High |
| Mortality | 4.4M | High |
| SensorReadings | 2.6M | High (recent) |
| UserSample | 1.1M | High |
| PublicPlanPopulation | 564K | High |
| PlanContainer | 489K | High |
| Populations | 400K | Critical |
| Containers | 10K | Critical |

## Appendix B: Key Field Mappings

| FishTalk Field Type | AquaMind Equivalent | Notes |
|---------------------|---------------------|--------|
| uniqueidentifier | UUID/varchar | Store original, generate new |
| nvarchar(max) | text | Direct mapping |
| datetime | timestamptz | Add timezone |
| float | decimal/numeric | Precision consideration |
| int | integer | Direct mapping |
| bit | boolean | Direct mapping |

---
**Document Status:** Complete
**Next Steps:** Update migration scripts with actual table/column names

