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
    - `avg_weight_g`: double precision
    - `avg_length_cm`: double precision (nullable)
    - `sample_size`: integer
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
- **`health_journalentry`**
  - `id`: bigint (PK, auto-increment)
  - `assignment_id`: bigint (FK to `batch_batchcontainerassignment`, on_delete=CASCADE) # Link to specific assignment
  - `entry_type`: varchar(50) # Observation, Diagnosis, Treatment, Vaccination, Sample
  - `entry_time`: timestamptz
  - `created_by_id`: integer (FK to `auth_user`, on_delete=SET_NULL, nullable)
  - `summary`: varchar(255)
  - `description`: text (nullable)
  - `health_scores`: jsonb (nullable) # Stores quantifiable health scores (e.g., {'gill_health': 1, 'eye_condition': 2})
  - `created_at`: timestamptz
  - `updated_at`: timestamptz
- **`health_healthobservation`**
  - `id`: bigint (PK, auto-increment)
  - `score`: integer
  - `created_at`: timestamptz
  - `updated_at`: timestamptz
  - `journal_entry_id`: bigint (FK to `health_journalentry`, on_delete=CASCADE)
  - `parameter_id`: bigint (FK to `health_healthparameter`, on_delete=PROTECT)
  - `fish_identifier`: integer (nullable)
- **`health_licecount`** # Linked to a JournalEntry
  - `id`: bigint (PK, auto-increment)
  - `journal_entry_id`: bigint (FK to `health_journalentry`, on_delete=CASCADE)
  - `lice_stage`: varchar(50) # e.g., Adult Female, Mobile, Chalimus
  - `count`: integer
  - `sample_size`: integer # Number of fish sampled
  - `avg_per_fish`: double precision # Calculated
  - `created_at`: timestamptz
  - `updated_at`: timestamptz
- **`health_mortalityrecord`** # Linked to a JournalEntry
  - `id`: bigint (PK, auto-increment)
  - `journal_entry_id`: bigint (FK to `health_journalentry`, on_delete=CASCADE)
  - `count`: integer
  - `reason_id`: bigint (FK to `health_mortalityreason`, on_delete=PROTECT, nullable)
  - `created_at`: timestamptz
  - `updated_at`: timestamptz
- **`health_treatment`** # Linked to a JournalEntry
  - `id`: bigint (PK, auto-increment)
  - `journal_entry_id`: bigint (FK to `health_journalentry`, on_delete=CASCADE)
  - `treatment_type`: varchar(100) # e.g., Medication, Bath, Physical
  - `product_name`: varchar(100) (nullable)
  - `dosage`: varchar(50) (nullable)
  - `duration_days`: integer (nullable)
  - `withdrawal_period_days`: integer (nullable)
  - `created_at`: timestamptz
  - `updated_at`: timestamptz
- **`health_vaccinationrecord`** (Likely part of `health_treatment` or linked to `health_journalentry`)
- **`health_samplerecord`** (Likely linked to `health_journalentry`)

#### Relationships (Inferred `on_delete` where script failed)
- `batch_batchcontainerassignment` ← `health_journalentry` (CASCADE)
- `auth_user` ← `health_journalentry` (SET_NULL)
- `health_journalentry` ← `health_licecount` (CASCADE)
- `health_journalentry` ← `health_mortalityrecord` (CASCADE)
- `health_mortalityreason` ← `health_mortalityrecord` (PROTECT)
- `health_journalentry` ← `health_treatment` (CASCADE)

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

### `health_healthparameter`

Represents quantifiable health parameters measured during observations.

| Field                 | Type              | Null | Default | Unique | Description                                      |
|-----------------------|-------------------|------|---------|--------|--------------------------------------------------|
| `id`                  | `bigserial` (PK)  |      |         |        | Unique identifier for the health parameter.      |
| `name`                | `varchar(100)`    |      |         | ✓      | Unique name of the health parameter.             |
| `description_score_1` | `text`            |      |         |        | Description of the parameter condition for score 1. |
| `description_score_2` | `text`            |      |         |        | Description of the parameter condition for score 2. |
| `description_score_3` | `text`            |      |         |        | Description of the parameter condition for score 3. |
| `description_score_4` | `text`            |      |         |        | Description of the parameter condition for score 4. |
| `description_score_5` | `text`            | ✓    | `''`    |        | Description of the parameter condition for score 5. |
| `is_active`           | `boolean`         |      | `true`  |        | Indicates if the parameter is currently in use.  |

### `health_healthobservation`

Records a specific health parameter score for a journal entry.

| Field             | Type              | Null | Default | Unique | Description                                                        |
|-------------------|-------------------|------|---------|--------|--------------------------------------------------------------------|
| `id`              | `bigserial` (PK)  |      |         |        | Unique identifier for the health observation.                      |
| `journal_entry`   | `bigint` (FK)     |      |         |        | Reference to the journal entry (`health_journalentry.id`).       |
| `parameter`       | `bigint` (FK)     |      |         |        | Reference to the health parameter (`health_healthparameter.id`). |
| `score`           | `integer`         |      |         |        | Score assigned (1-5, validated by model).                          |
| `fish_identifier` | `varchar(100)`    | ✓    |         |        | Optional identifier for a specific fish within a sample/batch.     |
| `created_at`      | `timestamptz`     |      | `now()` |        | Timestamp when the observation was created.                      |
| `updated_at`      | `timestamptz`     |      | `now()` |        | Timestamp when the observation was last updated.                 |

*Note: The previous `unique_together` constraint on `journal_entry` and `parameter` has been removed to allow multiple observations of the same parameter within a single journal entry (e.g., for different individual fish).* 

### `batch_growthsample`

Stores growth sample data for a batch within a specific container assignment.

| Field                  | Type                 | Null | Default | Unique | Description                                                                                                                             |
|------------------------|----------------------|------|---------|--------|-----------------------------------------------------------------------------------------------------------------------------------------|
| `id`                   | `bigserial` (PK)     |      |         |        | Unique identifier for the growth sample.                                                                                              |
| `assignment`           | `bigint` (FK)        |      |         |        | Reference to the batch container assignment (`batch_batchcontainerassignment.id`).                                                     |
| `sample_date`          | `date`               |      |         |        | Date the sample was taken.                                                                                                              |
| `sample_size`          | `integer`            |      |         |        | Number of fish sampled. Must be <= population count in the assignment.                                                                  |
| `avg_weight_g`         | `decimal(10, 2)`     | ✓    |         |        | Average weight in grams. Calculated from `individual_weights` if provided via serializer, otherwise stores manually entered value.      |
| `std_deviation_weight` | `decimal(10, 2)`     | ✓    |         |        | Standard deviation of weight in grams. Calculated from `individual_weights` if provided via serializer, otherwise stores manually entered value. |
| `min_weight_g`         | `decimal(10, 2)`     | ✓    |         |        | Minimum weight observed in the sample.                                                                                                  |
| `max_weight_g`         | `decimal(10, 2)`     | ✓    |         |        | Maximum weight observed in the sample.                                                                                                  |
| `avg_length_cm`        | `decimal(10, 2)`     | ✓    |         |        | Average length in centimeters. Calculated from `individual_lengths` if provided via serializer, otherwise stores manually entered value.     |
| `std_deviation_length` | `decimal(10, 2)`     | ✓    |         |        | Standard deviation of length in centimeters. Calculated from `individual_lengths` if provided via serializer, otherwise stores manually entered value.|
| `min_length_cm`        | `decimal(10, 2)`     | ✓    |         |        | Minimum length observed in the sample.                                                                                                  |
| `max_length_cm`        | `decimal(10, 2)`     | ✓    |         |        | Maximum length observed in the sample.                                                                                                  |
| `condition_factor`     | `decimal(10, 2)`     | ✓    |         |        | Condition Factor (K). Calculated from average weight/length, or average of individual K-factors if both lists provided via serializer. |
| `notes`                | `text`               | ✓    |         |        | Additional notes about the sample.                                                                                                      |
| `created_at`           | `timestamptz`        |      | `now()` |        | Timestamp when the sample record was created.                                                                                           |
| `updated_at`           | `timestamptz`        |      | `now()` |        | Timestamp when the sample record was last updated.                                                                                      |

## 5. Relationship Clarifications

### 5.1 JournalEntry and GrowthSample Relationship

#### Important Relationship Structure

One critical relationship that requires explicit clarification is between `health_journalentry` and `batch_growthsample` models. This relationship is **indirect** and operates through `batch_batchcontainerassignment`:

```
JournalEntry (health app) → BatchContainerAssignment (batch app) ← GrowthSample (batch app)
```

**Key Points:**

1. **No Direct Foreign Key:** There is no direct FK from `batch_growthsample` to `health_journalentry` or vice versa. The association is logical, not enforced at the database level.

2. **Relationship Flow:**
   - A `health_journalentry` record is created for a specific batch and container (targeting a specific `batch_batchcontainerassignment`)
   - A `batch_growthsample` is also associated with a specific `batch_batchcontainerassignment` (via the `assignment` FK field)
   - The serializers (`JournalEntrySerializer` and `GrowthSampleSerializer`) handle creating/linking these records during API operations

3. **Implementation Considerations:**
   - The `JournalEntrySerializer` includes a nested `GrowthSampleSerializer` for convenient creation/updates
   - However, this is API-level convenience, not a database-level relationship
   - Date fields (`sample_date` on GrowthSample, `entry_date` on JournalEntry) must be properly converted between date/datetime formats

4. **Potential Misunderstandings:**
   - The current implementation had assumed a direct relationship model, which led to bugs in serializers
   - Trying to associate a GrowthSample directly with a JournalEntry (via a non-existent `journal_entry` field) caused errors
   - The correct pattern is to use the common `batch_batchcontainerassignment` as the linking entity

This indirect relationship design allows GrowthSample records to exist independently in the batch app while still being referenced from health journal entries as needed.