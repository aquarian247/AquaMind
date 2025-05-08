# AquaMind Data Model

## 1. Introduction

This document defines the data model for AquaMind, an aquaculture management system. It integrates the database schema details obtained from direct inspection (`inspect_db_schema.py`) and Django model introspection. It aims to provide an accurate representation of the *implemented* schema while also outlining *planned* features. The database uses PostgreSQL with the TimescaleDB extension.

**Note on Naming**: This document uses the actual database table names following the Django convention (`appname_modelname`).

## 2. Database Overview

- **Database**: PostgreSQL with TimescaleDB extension.
- **Schema**: All tables reside in the `public` schema.
- **Time-Series Data**: `environmental_environmentalreading` and `environmental_weatherdata` are TimescaleDB hypertables partitioned by their respective timestamp columns (`reading_time`, `timestamp`).
- **Implementation Status**:
  - **Implemented Apps/Domains**: `infrastructure`, `batch`, `inventory`, `health`, `environmental`, `users` (including `auth`).
  - **Planned Apps/Domains**: Broodstock Management enhancements, Operational Planning, Scenario Planning, Advanced Analytics.

## 3. Implemented Data Model Domains

### 3.1 Infrastructure Management (`infrastructure` app)
**Purpose**: Manages physical assets and locations.

#### Tables
- **`infrastructure_geography`**
  - `id`: bigint (PK, auto-increment)
  - `name`: varchar(100) (Unique)
  - `created_at`: timestamptz
  - `updated_at`: timestamptz
- **`infrastructure_area`**
  - `id`: bigint (PK, auto-increment)
  - `name`: varchar(100) (Unique)
  - `geography_id`: bigint (FK to `infrastructure_geography`, on_delete=PROTECT)
  - `latitude`: double precision (nullable)
  - `longitude`: double precision (nullable)
  - `max_biomass`: double precision (nullable)
  - `created_at`: timestamptz
  - `updated_at`: timestamptz
- **`infrastructure_freshwaterstation`**
  - `id`: bigint (PK, auto-increment)
  - `name`: varchar(100) (Unique)
  - `area_id`: bigint (FK to `infrastructure_area`, on_delete=CASCADE)
  - `location_description`: text (nullable)
  - `latitude`: double precision (nullable)
  - `longitude`: double precision (nullable)
  - `created_at`: timestamptz
  - `updated_at`: timestamptz
- **`infrastructure_hall`**
  - `id`: bigint (PK, auto-increment)
  - `name`: varchar(100)
  - `station_id`: bigint (FK to `infrastructure_freshwaterstation`, on_delete=CASCADE)
  - `created_at`: timestamptz
  - `updated_at`: timestamptz
- **`infrastructure_containertype`**
  - `id`: bigint (PK, auto-increment)
  - `name`: varchar(100) (Unique)
  - `description`: text (nullable)
  - `created_at`: timestamptz
  - `updated_at`: timestamptz
- **`infrastructure_container`**
  - `id`: bigint (PK, auto-increment)
  - `name`: varchar(100)
  - `container_type_id`: bigint (FK to `infrastructure_containertype`, on_delete=PROTECT)
  - `hall_id`: bigint (FK to `infrastructure_hall`, on_delete=CASCADE, nullable)
  - `area_id`: bigint (FK to `infrastructure_area`, on_delete=CASCADE, nullable) # Added based on schema possibility
  - `capacity_kg`: double precision (nullable)
  - `capacity_m3`: double precision (nullable) # Added based on schema possibility
  - `created_at`: timestamptz
  - `updated_at`: timestamptz
- **`infrastructure_sensor`**
  - `id`: bigint (PK, auto-increment)
  - `container_id`: bigint (FK to `infrastructure_container`, on_delete=CASCADE)
  - `sensor_id_external`: varchar(100) (Unique) # Sensor identifier in external system (e.g., WonderWare)
  - `parameter_id`: bigint (FK to `environmental_environmentalparameter`, on_delete=PROTECT) # Link to parameter type
  - `status`: varchar(50)
  - `last_reading_time`: timestamptz (nullable)
  - `created_at`: timestamptz
  - `updated_at`: timestamptz
- **`infrastructure_feedcontainer`**
  - `id`: bigint (PK, auto-increment)
  - `name`: varchar(100)
  - `station_id`: bigint (FK to `infrastructure_freshwaterstation`, on_delete=CASCADE, nullable) # Nullable if linked to Area
  - `area_id`: bigint (FK to `infrastructure_area`, on_delete=CASCADE, nullable) # Nullable if linked to Station
  - `capacity_kg`: double precision
  - `created_at`: timestamptz
  - `updated_at`: timestamptz

#### Relationships (Inferred `on_delete` where script failed)
- `infrastructure_geography` ← `infrastructure_area` (PROTECT)
- `infrastructure_area` ← `infrastructure_freshwaterstation` (CASCADE)
- `infrastructure_freshwaterstation` ← `infrastructure_hall` (CASCADE)
- `infrastructure_hall` ← `infrastructure_container` (CASCADE)
- `infrastructure_area` ← `infrastructure_container` (CASCADE) # If applicable
- `infrastructure_containertype` ← `infrastructure_container` (PROTECT)
- `infrastructure_container` ← `infrastructure_sensor` (CASCADE)
- `infrastructure_freshwaterstation` ← `infrastructure_feedcontainer` (CASCADE)
- `infrastructure_area` ← `infrastructure_feedcontainer` (CASCADE) # If applicable
- `environmental_environmentalparameter` ← `infrastructure_sensor` (PROTECT)

### 3.2 Batch Management (`batch` app)
**Purpose**: Tracks fish batches through their lifecycle.

#### Tables
- **`batch_species`**
  - `id`: bigint (PK, auto-increment)
  - `name`: varchar(100) (Unique)
  - `scientific_name`: varchar(100) (Unique)
  - `created_at`: timestamptz
  - `updated_at`: timestamptz
- **`batch_lifecyclestage`**
  - `id`: bigint (PK, auto-increment)
  - `name`: varchar(50) (Unique, e.g., "Egg", "Fry", "Parr", "Smolt", "Post-Smolt", "Adult")
  - `description`: text (nullable)
  - `order`: integer (for sequencing stages)
  - `created_at`: timestamptz
  - `updated_at`: timestamptz
- **`batch_batch`**
  - `id`: bigint (PK, auto-increment)
  - `batch_number`: varchar(50) (Unique)
  - `species_id`: bigint (FK to `batch_species`, on_delete=PROTECT)
  - `current_stage_id`: bigint (FK to `batch_lifecyclestage`, on_delete=PROTECT, nullable) # High-level indicator
  - `start_date`: date
  - `end_date`: date (nullable)
  - `origin`: varchar(100) (nullable) # e.g., hatchery name
  - `created_at`: timestamptz
  - `updated_at`: timestamptz
- **`batch_batchcontainerassignment`**
  - `id`: bigint (PK, auto-increment)
  - `batch_id`: bigint (FK to `batch_batch`, on_delete=CASCADE)
  - `container_id`: bigint (FK to `infrastructure_container`, on_delete=PROTECT)
  - `lifecycle_stage_id`: bigint (FK to `batch_lifecyclestage`, on_delete=PROTECT) # Stage *within* this container
  - `population_count`: integer
  - `avg_weight_g`: double precision # Average weight in grams
  - `biomass_kg`: double precision # Calculated: (population_count * avg_weight_g) / 1000
  - `assignment_date`: date
  - `departure_date`: date (nullable)
  - `created_at`: timestamptz
  - `updated_at`: timestamptz
- **`batch_batchcomposition`** # Tracks components if batches are mixed
  - `id`: bigint (PK, auto-increment)
  - `mixed_batch_id`: bigint (FK to `batch_batch`, related_name='components', on_delete=CASCADE) # The resulting mixed batch
  - `source_batch_id`: bigint (FK to `batch_batch`, related_name='mixed_in', on_delete=CASCADE) # The original batch component
  - `percentage`: double precision # Percentage this source contributes
  - `created_at`: timestamptz
  - `updated_at`: timestamptz
- **`batch_batchtransfer`**
  - `id`: bigint (PK, auto-increment)
  - `batch_id`: bigint (FK to `batch_batch`, on_delete=CASCADE)
  - `from_container_id`: bigint (FK to `infrastructure_container`, on_delete=PROTECT, nullable) # Null if initial placement
  - `to_container_id`: bigint (FK to `infrastructure_container`, on_delete=PROTECT)
  - `population_count`: integer
  - `avg_weight_g`: double precision
  - `transfer_date`: date
  - `transfer_type`: varchar(50) # e.g., Split, Merge, Move
  - `reason`: text (nullable)
  - `created_at`: timestamptz
  - `updated_at`: timestamptz
- **`batch_mortalityevent`**
  - `id`: bigint (PK, auto-increment)
  - `assignment_id`: bigint (FK to `batch_batchcontainerassignment`, on_delete=CASCADE) # Link to specific assignment
  - `event_date`: date
  - `count`: integer
  - `reason_id`: bigint (FK to `health_mortalityreason`, on_delete=PROTECT, nullable) # Link to health app
  - `notes`: text (nullable)
  - `created_at`: timestamptz
  - `updated_at`: timestamptz
- **`batch_growthsample`**
    - `id`: bigint (PK, auto-increment)
    - `assignment_id`: bigint (FK to `batch_batchcontainerassignment`, on_delete=CASCADE)
    - `sample_date`: date
    - `sample_size`: integer
    - `avg_weight_g`: decimal(7, 2) (nullable) # Calculated average weight in grams
    - `std_deviation_weight`: decimal(7, 2) (nullable) # Calculated standard deviation of weight
    - `min_weight_g`: decimal(7, 2) (nullable) # Calculated minimum weight
    - `max_weight_g`: decimal(7, 2) (nullable) # Calculated maximum weight
    - `avg_length_cm`: decimal(5, 2) (nullable) # Calculated average length in cm
    - `std_deviation_length`: decimal(5, 2) (nullable) # Calculated standard deviation of length
    - `min_length_cm`: decimal(5, 2) (nullable) # Calculated minimum length
    - `max_length_cm`: decimal(5, 2) (nullable) # Calculated maximum length
    - `condition_factor`: decimal(5, 2) (nullable) # Calculated condition factor (K)
    - `notes`: text (nullable)
    - `created_at`: timestamptz
    - `updated_at`: timestamptz
- **`batch_batchhistory`** (Likely handled by audit logging tools like django-auditlog, may not be a separate model)
- **`batch_batchmedia`** (Potentially generic relation via ContentType or dedicated model)

#### Relationships (Inferred `on_delete` where script failed)
- `batch_species` ← `batch_batch` (PROTECT)
- `batch_lifecyclestage` ← `batch_batch` (PROTECT, for `current_stage_id`)
- `batch_batch` ← `batch_batchcontainerassignment` (CASCADE)
- `infrastructure_container` ← `batch_batchcontainerassignment` (PROTECT)
- `batch_lifecyclestage` ← `batch_batchcontainerassignment` (PROTECT)
- `batch_batch` ← `batch_batchcomposition` (CASCADE, both FKs)
- `batch_batch` ← `batch_batchtransfer` (CASCADE)
- `infrastructure_container` ← `batch_batchtransfer` (PROTECT, both FKs)
- `batch_batchcontainerassignment` ← `batch_mortalityevent` (CASCADE)
- `health_mortalityreason` ← `batch_mortalityevent` (PROTECT)
- `batch_batchcontainerassignment` ← `batch_growthsample` (CASCADE)

### 3.3 Feed and Inventory Management (`inventory` app)
**Purpose**: Manages feed resources and feeding events.

#### Tables
- **`inventory_feed`**
  - `id`: bigint (PK, auto-increment)
  - `name`: varchar(100) (Unique)
  - `manufacturer`: varchar(100) (nullable)
  - `feed_type`: varchar(50) # e.g., Pellet, Crumble
  - `pellet_size_mm`: double precision (nullable)
  - `nutritional_composition`: jsonb (nullable) # Store protein, fat, etc.
  - `suitable_for_stages`: ManyToManyField to `batch_lifecyclestage` (creates `inventory_feed_suitable_for_stages` table)
  - `created_at`: timestamptz
  - `updated_at`: timestamptz
- **`inventory_feedpurchase`**
  - `id`: bigint (PK, auto-increment)
  - `feed_id`: bigint (FK to `inventory_feed`, on_delete=PROTECT)
  - `supplier`: varchar(100) (nullable)
  - `purchase_date`: date
  - `quantity_kg`: double precision
  - `unit_cost`: decimal (max_digits=10, decimal_places=2)
  - `total_cost`: decimal (max_digits=12, decimal_places=2)
  - `lot_number`: varchar(100) (nullable)
  - `created_at`: timestamptz
  - `updated_at`: timestamptz
- **`inventory_feedstock`**
  - `id`: bigint (PK, auto-increment)
  - `feed_id`: bigint (FK to `inventory_feed`, on_delete=PROTECT)
  - `feed_container_id`: bigint (FK to `infrastructure_feedcontainer`, on_delete=CASCADE)
  - `quantity_kg`: double precision
  - `last_updated`: timestamptz
  - `created_at`: timestamptz
  - `updated_at`: timestamptz
- **`inventory_feedingevent`**
  - `id`: bigint (PK, auto-increment)
  - `assignment_id`: bigint (FK to `batch_batchcontainerassignment`, on_delete=CASCADE) # Link to specific assignment
  - `feed_id`: bigint (FK to `inventory_feed`, on_delete=PROTECT)
  - `quantity_kg`: double precision
  - `event_time`: timestamptz
  - `created_at`: timestamptz
  - `updated_at`: timestamptz
- **`inventory_batchfeedingsummary`**
  - `id`: bigint (PK, auto-increment)
  - `batch_id`: bigint (FK to `batch_batch`, on_delete=CASCADE, unique=True) # One summary per batch
  - `total_feed_kg`: double precision
  - `start_date`: date
  - `end_date`: date (nullable)
  - `calculated_fcr`: double precision (nullable) # Feed Conversion Ratio
  - `last_calculated`: timestamptz (nullable)
  - `created_at`: timestamptz
  - `updated_at`: timestamptz
- **`inventory_feedrecommendation`** (NEW - based on recent features)
  - `id`: bigint (PK, auto-increment)
  - `batch_id`: bigint (FK to `batch_batch`, on_delete=CASCADE)
  - `recommendation_date`: date
  - `recommended_feed_id`: bigint (FK to `inventory_feed`, on_delete=PROTECT)
  - `recommended_quantity_kg`: double precision
  - `reasoning`: text (nullable)
  - `created_at`: timestamptz
  - `updated_at`: timestamptz

#### Relationships (Inferred `on_delete` where script failed)
- `inventory_feed` ← `inventory_feedpurchase` (PROTECT)
- `inventory_feed` ← `inventory_feedstock` (PROTECT)
- `infrastructure_feedcontainer` ← `inventory_feedstock` (CASCADE)
- `batch_batchcontainerassignment` ← `inventory_feedingevent` (CASCADE)
- `inventory_feed` ← `inventory_feedingevent` (PROTECT)
- `batch_batch` ← `inventory_batchfeedingsummary` (CASCADE)
- `batch_batch` ← `inventory_feedrecommendation` (CASCADE)
- `inventory_feed` ← `inventory_feedrecommendation` (PROTECT)
- `inventory_feed` ↔ `batch_lifecyclestage` (ManyToMany)

### 3.4 Health Monitoring (`health` app)
**Purpose**: Tracks health observations, treatments, and mortality.

#### Tables
- **`health_mortalityreason`**
  - `id`: bigint (PK, auto-increment)
  - `name`: varchar(100) (Unique)
  - `description`: text (nullable)
  - `category`: varchar(50) (nullable, e.g., Disease, Environment, Handling)
  - `created_at`: timestamptz
  - `updated_at`: timestamptz
- **`health_vaccinationtype`**
  - `id`: bigint (PK, auto-increment)
  - `name`: varchar(100) (Unique)
  - `description`: text (nullable)
  - `manufacturer`: varchar(100) (nullable)
  - `target_diseases`: text (nullable)
  - `created_at`: timestamptz
  - `updated_at`: timestamptz
- **`health_sampletype`**
  - `id`: bigint (PK, auto-increment)
  - `name`: varchar(100) (Unique)
  - `description`: text (nullable)
  - `unit`: varchar(50) (nullable) # e.g., cells/mL, mg/L
  - `created_at`: timestamptz
  - `updated_at`: timestamptz
- **`health_healthparameter`**
  - `id`: bigint (PK, auto-increment)
  - `name`: varchar(100) (Unique)
  - `description_score_1`: text
  - `description_score_2`: text
  - `description_score_3`: text
  - `description_score_4`: text
  - `description_score_5`: text
  - `is_active`: boolean
  - `created_at`: timestamptz
  - `updated_at`: timestamptz
- **`health_healthsamplingevent`**
  - `id`: bigint (PK, auto-increment)
  - `assignment_id`: bigint (FK to `batch_batchcontainerassignment`, on_delete=CASCADE) # Link to specific assignment
  - `sampling_date`: date # Date of the sampling event
  - `number_of_fish_sampled`: integer # Total number of fish physically sampled in this event
  - `sampled_by_id`: integer (FK to `users_customuser`, on_delete=SET_NULL, nullable) # User who performed the sampling
  - `notes`: text (nullable)
  - `avg_weight_g`: decimal(7, 2) (nullable) # Calculated average weight in grams
  - `std_dev_weight_g`: decimal(7, 2) (nullable) # Calculated standard deviation of weight
  - `min_weight_g`: decimal(7, 2) (nullable) # Calculated minimum weight
  - `max_weight_g`: decimal(7, 2) (nullable) # Calculated maximum weight
  - `avg_length_cm`: decimal(5, 2) (nullable) # Calculated average length in cm
  - `std_dev_length_cm`: decimal(5, 2) (nullable) # Calculated standard deviation of length
  - `min_length_cm`: decimal(5, 2) (nullable) # Calculated minimum length
  - `max_length_cm`: decimal(5, 2) (nullable) # Calculated maximum length
  - `avg_k_factor`: decimal(5, 2) (nullable) # Calculated average K-factor
  - `uniformity_percentage`: decimal(5, 2) (nullable) # Calculated uniformity percentage
  - `calculated_sample_size`: integer (nullable) # Number of fish with complete data for metric calculations
  - `created_at`: timestamptz
  - `updated_at`: timestamptz
- **`health_individualfishobservation`** (NEW - Detailed observation for a single fish within a sampling event)
  - `id`: bigint (PK, auto-increment)
  - `sampling_event_id`: bigint (FK to `health_healthsamplingevent`, on_delete=CASCADE)
  - `fish_identifier`: integer # Identifier for the fish within this sampling event (e.g., 1, 2, 3...)
  - `length_cm`: decimal(5,2) (nullable)
  - `weight_g`: decimal(7,2) (nullable)
  - `condition_factor`: decimal(5,3) (nullable) # Calculated: (weight_g / (length_cm^3)) * 100
  - `is_culled`: boolean (default=False)
  - `notes`: text (nullable)
  - `created_at`: timestamptz
  - `updated_at`: timestamptz
- **`health_fishparameterscore`** (NEW - Specific health parameter score for an individual fish observation)
  - `id`: bigint (PK, auto-increment)
  - `individual_fish_observation_id`: bigint (FK to `health_individualfishobservation`, on_delete=CASCADE)
  - `parameter_id`: bigint (FK to `health_healthparameter`, on_delete=PROTECT)
  - `score`: integer # Typically 1-5 based on HealthParameter descriptions
  - `comment`: text (nullable)
  - `created_at`: timestamptz
  - `updated_at`: timestamptz
- **`health_licecount`** # Potentially linked to HealthSamplingEvent
  - `id`: bigint (PK, auto-increment)
  - `sampling_event_id`: bigint (FK to `health_healthsamplingevent`, on_delete=CASCADE, nullable) # REVISED LINKAGE
  # `journal_entry_id`: bigint (FK to `health_journalentry`, on_delete=CASCADE) # OLD LINKAGE
  - `assignment_id`: bigint (FK to `batch_batchcontainerassignment`, on_delete=CASCADE, nullable) # Alternative or additional context
  - `lice_stage`: varchar(50) # e.g., Adult Female, Mobile, Chalimus
  - `count`: integer
  - `sample_size`: integer # Number of fish sampled for this count
  - `avg_per_fish`: double precision # Calculated
  - `created_at`: timestamptz
  - `updated_at`: timestamptz
- **`health_mortalityrecord`** # Potentially linked to HealthSamplingEvent or BatchContainerAssignment directly
  - `id`: bigint (PK, auto-increment)
  - `sampling_event_id`: bigint (FK to `health_healthsamplingevent`, on_delete=CASCADE, nullable) # REVISED LINKAGE - if mortality observed during sampling
  # `journal_entry_id`: bigint (FK to `health_journalentry`, on_delete=CASCADE) # OLD LINKAGE
  - `assignment_id`: bigint (FK to `batch_batchcontainerassignment`, on_delete=CASCADE, nullable) # More common for general mortality
  - `record_date`: date # Date mortality was recorded
  - `count`: integer
  - `reason_id`: bigint (FK to `health_mortalityreason`, on_delete=PROTECT, nullable)
  - `created_at`: timestamptz
  - `updated_at`: timestamptz
- **`health_treatment`** # Potentially linked to HealthSamplingEvent or BatchContainerAssignment
  - `id`: bigint (PK, auto-increment)
  - `sampling_event_id`: bigint (FK to `health_healthsamplingevent`, on_delete=CASCADE, nullable) # REVISED LINKAGE - if treatment decision from sampling
  # `journal_entry_id`: bigint (FK to `health_journalentry`, on_delete=CASCADE) # OLD LINKAGE
  - `assignment_id`: bigint (FK to `batch_batchcontainerassignment`, on_delete=CASCADE, nullable) # More common for group treatments
  - `treatment_type`: varchar(100) # e.g., Medication, Bath, Physical
  - `product_name`: varchar(100) (nullable)
  - `dosage`: varchar(50) (nullable)
  - `application_method`: varchar(100) (nullable)
  - `start_date`: date
  - `end_date`: date (nullable)
  - `duration_days`: integer (nullable)
  - `withdrawal_period_days`: integer (nullable)
  - `created_at`: timestamptz
  - `updated_at`: timestamptz
- **`health_vaccinationrecord`** (Review: May be a type of Treatment or linked to HealthSamplingEvent)
- **`health_samplerecord`** (Review: May be covered by HealthSamplingEvent and IndividualFishObservation or relate to lab samples)
- **`health_healthlabsample`**
  - `id`: bigint (PK, auto-increment)
  - `batch_container_assignment_id`: bigint (FK to `batch_batchcontainerassignment`, on_delete=PROTECT)
  - `sample_type_id`: bigint (FK to `health_sampletype`, on_delete=PROTECT)
  - `sample_date`: date
  - `date_sent_to_lab`: date (nullable)
  - `date_results_received`: date (nullable)
  - `lab_reference_id`: varchar(100) (nullable)
  - `findings_summary`: text (nullable)
  - `quantitative_results`: jsonb (nullable)
  - `attachment`: FileField (upload_to='health/lab_samples/%Y/%m/')
  - `notes`: text (nullable)
  - `recorded_by_id`: bigint (FK to `users_customuser`, on_delete=SET_NULL, nullable)
  - `created_at`: timestamptz
  - `updated_at`: timestamptz

#### Relationships (Inferred `on_delete` where script failed)
- `batch_batchcontainerassignment` ← `health_healthsamplingevent` (CASCADE)
- `users_customuser` ← `health_healthsamplingevent` (SET_NULL)
- `health_healthsamplingevent` ← `health_individualfishobservation` (CASCADE)
- `health_individualfishobservation` ← `health_fishparameterscore` (CASCADE)
- `health_healthparameter` ← `health_fishparameterscore` (PROTECT)
- `health_healthsamplingevent` ← `health_licecount` (CASCADE, if applicable)
- `batch_batchcontainerassignment` ← `health_licecount` (CASCADE, if applicable)
- `health_healthsamplingevent` ← `health_mortalityrecord` (CASCADE, if applicable)
- `batch_batchcontainerassignment` ← `health_mortalityrecord` (CASCADE, if applicable)
- `health_mortalityreason` ← `health_mortalityrecord` (PROTECT)
- `health_healthsamplingevent` ← `health_treatment` (CASCADE, if applicable)
- `batch_batchcontainerassignment` ← `health_treatment` (CASCADE, if applicable)
- `batch_batchcontainerassignment` ← `health_healthlabsample` (PROTECT)
- `health_sampletype` ← `health_healthlabsample` (PROTECT)
- `users_customuser` ← `health_healthlabsample` (SET_NULL)

### 3.5 Environmental Monitoring (`environmental` app)
**Purpose**: Captures time-series data for environmental conditions.

#### Tables
- **`environmental_environmentalparameter`**
  - `id`: bigint (PK, auto-increment)
  - `name`: varchar(100) (Unique) # e.g., Temperature, Dissolved Oxygen, Salinity
  - `unit`: varchar(20) # e.g., °C, mg/L, ppt
  - `description`: text (nullable)
  - `created_at`: timestamptz
  - `updated_at`: timestamptz
- **`environmental_environmentalreading`** (TimescaleDB Hypertable)
  - `id`: bigint (PK) # Managed by TimescaleDB
  - `sensor_id`: bigint (FK to `infrastructure_sensor`, on_delete=CASCADE)
  - `parameter_id`: bigint (FK to `environmental_environmentalparameter`, on_delete=PROTECT) # Redundant? Sensor already linked. Check design.
  - `value`: double precision
  - `reading_time`: timestamptz (Hypertable partitioning key, Index)
  - `created_at`: timestamptz
  - `updated_at`: timestamptz
- **`environmental_weatherdata`** (TimescaleDB Hypertable)
  - `id`: bigint (PK) # Managed by TimescaleDB
  - `area_id`: bigint (FK to `infrastructure_area`, on_delete=CASCADE)
  - `source`: varchar(50) # e.g., OpenWeatherMap, Sensor
  - `temperature_c`: double precision (nullable)
  - `humidity_percent`: double precision (nullable)
  - `precipitation_mm`: double precision (nullable)
  - `wind_speed_mps`: double precision (nullable)
  - `wind_direction_deg`: double precision (nullable)
  - `cloud_cover_percent`: double precision (nullable)
  - `timestamp`: timestamptz (Hypertable partitioning key, Index)
  - `created_at`: timestamptz
  - `updated_at`: timestamptz
- **`environmental_photoperioddata`** (NEW)
    - `id`: bigint (PK, auto-increment)
    - `area_id`: bigint (FK to `infrastructure_area`, on_delete=CASCADE)
    - `date`: date (Unique per area)
    - `sunrise_time`: time
    - `sunset_time`: time
    - `daylight_hours`: double precision
    - `created_at`: timestamptz
    - `updated_at`: timestamptz
- **`environmental_stagetransitionenvironmental`** (NEW - likely for planning/simulation)
    - `id`: bigint (PK, auto-increment)
    - `from_stage_id`: bigint (FK to `batch_lifecyclestage`, on_delete=CASCADE)
    - `to_stage_id`: bigint (FK to `batch_lifecyclestage`, on_delete=CASCADE)
    - `parameter_id`: bigint (FK to `environmental_environmentalparameter`, on_delete=CASCADE)
    - `min_value`: double precision (nullable)
    - `max_value`: double precision (nullable)
    - `optimal_value`: double precision (nullable)
    - `created_at`: timestamptz
    - `updated_at`: timestamptz

#### Relationships (Inferred `on_delete` where script failed)
- `infrastructure_sensor` ← `environmental_environmentalreading` (CASCADE)
- `environmental_environmentalparameter` ← `environmental_environmentalreading` (PROTECT)
- `infrastructure_area` ← `environmental_weatherdata` (CASCADE)
- `infrastructure_area` ← `environmental_photoperioddata` (CASCADE)
- `batch_lifecyclestage` ← `environmental_stagetransitionenvironmental` (CASCADE, both FKs)
- `environmental_environmentalparameter` ← `environmental_stagetransitionenvironmental` (CASCADE)

### 3.6 User Management (`auth` and `users` apps)
**Purpose**: Manages user accounts and access control.

#### Tables
- **`auth_user`** (Django built-in)
  - `id`: integer (PK, auto-increment)
  - `password`: varchar(128)
  - `last_login`: timestamptz (nullable)
  - `is_superuser`: boolean
  - `username`: varchar(150) (Unique)
  - `first_name`: varchar(150)
  - `last_name`: varchar(150)
  - `email`: varchar(254)
  - `is_staff`: boolean
  - `is_active`: boolean
  - `date_joined`: timestamptz
- **`auth_group`** (Django built-in)
  - `id`: integer (PK, auto-increment)
  - `name`: varchar(150) (Unique)
- **`auth_permission`** (Django built-in)
  - `id`: integer (PK, auto-increment)
  - `name`: varchar(255)
  - `content_type_id`: integer (FK to `django_content_type`)
  - `codename`: varchar(100)
- **`auth_user_groups`** (ManyToMany link table)
- **`auth_user_user_permissions`** (ManyToMany link table)
- **`auth_group_permissions`** (ManyToMany link table)
- **`users_userprofile`** (Custom profile model)
  - `id`: bigint (PK, auto-increment)
  - `user_id`: integer (FK to `auth_user`, on_delete=CASCADE, unique=True) # One-to-One
  - `role`: varchar(100) (nullable)
  - `geography_id`: bigint (FK to `infrastructure_geography`, on_delete=SET_NULL, nullable)
  - `subsidiary`: varchar(100) (nullable) # Assuming this might be a choice field or simple text for now
  - `phone_number`: varchar(20) (nullable)
  - `created_at`: timestamptz
  - `updated_at`: timestamptz

#### Relationships
- `auth_user` ← `users_userprofile` (CASCADE, One-to-One)
- `infrastructure_geography` ← `users_userprofile` (SET_NULL)
- `auth_user` ↔ `auth_group` (ManyToMany)
- `auth_user` ↔ `auth_permission` (ManyToMany)
- `auth_group` ↔ `auth_permission` (ManyToMany)

## 4. Planned Data Model Domains (Not Yet Implemented)

### 4.1 Broodstock Management
**Purpose**: Manage genetic lines and breeding programs.
**Tables**: `broodstock`, `genetic_trait`, `batch_genetic_profile`, `breeding_program`, `breeding_pair`, `genetic_scenario`, `trait_tradeoff`, `snp_panel`, `breeding_value`, `photoperiod_regime`, `temperature_regime`. (Details omitted for brevity - refer to PRD/previous draft).

### 4.2 Operational Planning
**Purpose**: Provide operational recommendations.
**Tables**: `batch_operational_plan`, `planning_recommendation`. (Details omitted).

### 4.3 Scenario Planning
**Purpose**: Simulate hypothetical scenarios.
**Tables**: `batch_scenario`, `scenario_model`. (Details omitted).

### 4.4 Analytics
**Purpose**: Support AI/ML predictions.
**Tables**: `analytics_model`, `prediction`. (Details omitted).

## 5. Data Governance

- **Audit Trails**: Standard `created_at`, `updated_at` fields exist. Consider integrating `django-auditlog` for comprehensive tracking.
- **Validation**: ORM-level validation exists. Database constraints (Foreign Keys, Uniqueness) are enforced. `on_delete` behavior specified where known/inferred.
- **Partitioning and Indexing**: TimescaleDB hypertables are partitioned. Relevant indexes exist on Foreign Keys and timestamp columns.

## 6. Appendix: Developer Notes

- **TimescaleDB Setup**: Ensure `timescaledb` extension is enabled. Use Django migrations (potentially with `RunSQL`) or manual commands (`SELECT create_hypertable(...)`) to manage hypertables.
- **Calculated Fields**: Fields like `batch_batchcontainerassignment.biomass_kg` are calculated in the application logic (e.g., model `save()` method or serializers), not stored directly unless denormalized.
- **User Profile**: Access extended user information via `user.userprofile`. Geography is linked via FK, subsidiary requires clarification (FK or CharField?).