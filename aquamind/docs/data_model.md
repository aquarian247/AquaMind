# AquaMind Data Model

## 1. Introduction

This document defines the data model for AquaMind, an aquaculture management system. It integrates the database schema details obtained from direct inspection (`inspect_db_schema.py`) and Django model introspection. It aims to provide an accurate representation of the *implemented* schema while also outlining *planned* features. The database uses PostgreSQL with the TimescaleDB extension.

**Note on Naming**: This document uses the actual database table names following the Django convention (`appname_modelname`).

## 2. Database Overview

- **Database**: PostgreSQL with TimescaleDB extension.
- **Schema**: All tables reside in the `public` schema.
- **Time-Series Data**: `environmental_environmentalreading` and `environmental_weatherdata` are TimescaleDB hypertables partitioned by their respective timestamp columns (`reading_time`, `timestamp`).
- **Audit Trails**: Comprehensive change tracking implemented via django-simple-history for critical models (`batch_batch`, `infrastructure_container`, `inventory_feedstock`), providing regulatory compliance and operational transparency.
- **Implementation Status**:
  - **Implemented Apps/Domains**: `infrastructure`, `batch`, `inventory`, `health`, `environmental`, `users` (including `auth`).
  - **Planned Apps/Domains**: Broodstock Management enhancements, Operational Planning, Scenario Planning, Advanced Analytics.
  - **Removed Components**: Advanced audit analytics functionality (Core app) was removed to prioritize system stability and core operational features.

## 3. Audit Trail Implementation

### 3.1 Django Simple History Integration
AquaMind implements comprehensive audit trails using django-simple-history to track changes to critical models for regulatory compliance and operational transparency.

#### Tracked Models
- **`batch_batch`**: Complete change history for batch lifecycle management
- **`infrastructure_container`**: Container modifications and status changes
- **`inventory_feedstock`**: Feed inventory level changes and stock movements

#### Historical Tables
- **`batch_historicalbatch`**: Stores historical versions of batch records
- **`infrastructure_historicalcontainer`**: Stores historical versions of container records  
- **`inventory_historicalfeedstock`**: Stores historical versions of feed stock records

#### Features
- **Automatic Tracking**: All changes to tracked models are automatically recorded
- **User Attribution**: Changes are linked to the user who made them
- **Timestamp Tracking**: Precise timestamps for all modifications
- **Admin Integration**: Historical records viewable through Django admin interface
- **API Access**: Historical data accessible via Django admin and can be extended to API endpoints

#### Benefits
- **Regulatory Compliance**: Complete audit trail for regulatory reporting
- **Operational Transparency**: Full visibility into system changes
- **Data Recovery**: Ability to view and potentially restore previous states
- **Change Analysis**: Track patterns and trends in operational changes

## 4. Implemented Data Model Domains

### 4.1 Infrastructure Management (`infrastructure` app)
**Purpose**: Manages physical assets and locations.

#### Tables
- **`infrastructure_geography`**
  - `id`: bigint (PK, auto-increment)
  - `name`: varchar(100) (Unique)
  - `description`: text (blank=True)
  - `created_at`: timestamptz
  - `updated_at`: timestamptz
- **`infrastructure_area`**
  - `id`: bigint (PK, auto-increment)
  - `name`: varchar(100)
  - `geography_id`: bigint (FK to `infrastructure_geography`, on_delete=PROTECT)
  - `latitude`: numeric(9,6) (validators: -90 to 90)
  - `longitude`: numeric(9,6) (validators: -180 to 180)
  - `max_biomass`: numeric
  - `active`: boolean
  - `created_at`: timestamptz
  - `updated_at`: timestamptz
- **`infrastructure_freshwaterstation`**
  - `id`: bigint (PK, auto-increment)
  - `name`: varchar(100)
  - `station_type`: varchar(20)
  - `geography_id`: bigint (FK to `infrastructure_geography`, on_delete=PROTECT)
  - `latitude`: numeric(9,6) (nullable)
  - `longitude`: numeric(9,6) (nullable)
  - `description`: text (blank=True)
  - `active`: boolean
  - `created_at`: timestamptz
  - `updated_at`: timestamptz
- **`infrastructure_hall`**
  - `id`: bigint (PK, auto-increment)
  - `name`: varchar(100)
  - `freshwater_station_id`: bigint (FK to `infrastructure_freshwaterstation`, on_delete=CASCADE)
  - `description`: text (blank=True)
  - `area_sqm`: numeric (nullable)
  - `active`: boolean
  - `created_at`: timestamptz
  - `updated_at`: timestamptz
- **`infrastructure_containertype`**
  - `id`: bigint (PK, auto-increment)
  - `name`: varchar(100)
  - `category`: varchar(20) (choices: 'TANK', 'PEN', 'TRAY', 'OTHER')
  - `max_volume_m3`: numeric(10,2)
  - `description`: text (blank=True)
  - `created_at`: timestamptz
  - `updated_at`: timestamptz
- **`infrastructure_container`**
  - `id`: bigint (PK, auto-increment)
  - `name`: varchar(100)
  - `container_type_id`: bigint (FK to `infrastructure_containertype`, on_delete=PROTECT)
  - `hall_id`: bigint (FK to `infrastructure_hall`, on_delete=CASCADE, nullable)
  - `area_id`: bigint (FK to `infrastructure_area`, on_delete=CASCADE, nullable)
  - `volume_m3`: numeric(10,2)
  - `max_biomass_kg`: numeric(10,2)
  - `active`: boolean
  - `created_at`: timestamptz
  - `updated_at`: timestamptz
- **`infrastructure_sensor`**
  - `id`: bigint (PK, auto-increment)
  - `name`: varchar(100)
  - `sensor_type`: varchar(20)
  - `container_id`: bigint (FK to `infrastructure_container`, on_delete=CASCADE)
  - `serial_number`: varchar(100)
  - `manufacturer`: varchar(100)
  - `installation_date`: date (nullable)
  - `last_calibration_date`: date (nullable)
  - `active`: boolean
  - `created_at`: timestamptz
  - `updated_at`: timestamptz
- **`infrastructure_feedcontainer`**
  - `id`: bigint (PK, auto-increment)
  - `name`: varchar(100)
  - `container_type`: varchar(20)
  - `area_id`: bigint (FK to `infrastructure_area`, on_delete=CASCADE, nullable)
  - `hall_id`: bigint (FK to `infrastructure_hall`, on_delete=CASCADE, nullable)
  - `capacity_kg`: numeric(10,2)
  - `active`: boolean
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

### 4.2 Batch Management (`batch` app)
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
  # Note: Key metrics like population count, biomass, and average weight are derived from associated `batch_batchcontainerassignment` records.
  - `id`: bigint (PK, auto-increment, NOT NULL)
  - `batch_number`: varchar (Unique, NOT NULL)
  - `species_id`: bigint (FK to `batch_species`.`id`, on_delete=PROTECT, NOT NULL)
  - `lifecycle_stage_id`: bigint (FK to `batch_lifecyclestage`.`id`, on_delete=PROTECT, NOT NULL)
  - `status`: varchar (NOT NULL) # e.g., "ACTIVE", "INACTIVE", "PLANNED", "CLOSED"
  - `batch_type`: varchar (NOT NULL) # e.g., "STANDARD", "EXPERIMENTAL"
  - `start_date`: date (NOT NULL)
  - `expected_end_date`: date (nullable)
  - `actual_end_date`: date (nullable)
  - `notes`: text (NOT NULL)
  - `created_at`: timestamptz (NOT NULL)
  - `updated_at`: timestamptz (NOT NULL)
- **`batch_batchcontainerassignment`**
  - `id`: bigint (PK, auto-increment, NOT NULL)
  - `batch_id`: bigint (FK to `batch_batch`.`id`, on_delete=CASCADE, NOT NULL)
  - `container_id`: bigint (FK to `infrastructure_container`.`id`, on_delete=PROTECT, NOT NULL)
  - `lifecycle_stage_id`: bigint (FK to `batch_lifecyclestage`.`id`, on_delete=PROTECT, NOT NULL) # Stage *within* this container
  - `population_count`: integer (NOT NULL)
  - `avg_weight_g`: numeric (nullable) # Average weight in grams per fish
  - `biomass_kg`: numeric (NOT NULL)
  - `assignment_date`: date (NOT NULL)
  - `departure_date`: date (nullable) # Date when this specific assignment ended
  - `is_active`: boolean (default: True, NOT NULL) # Whether this assignment is current/active
  - `notes`: text (NOT NULL)
  - `created_at`: timestamptz (NOT NULL)
  - `updated_at`: timestamptz (NOT NULL)
- **`batch_batchcomposition`** # Tracks components if batches are mixed
  - `id`: bigint (PK, auto-increment, NOT NULL)
  - `mixed_batch_id`: bigint (FK to `batch_batch`.`id`, related_name='components', on_delete=CASCADE, NOT NULL) # The resulting mixed batch
  - `source_batch_id`: bigint (FK to `batch_batch`.`id`, related_name='mixed_in', on_delete=CASCADE, NOT NULL) # The original batch component
  - `percentage`: numeric (NOT NULL) # Percentage this source contributes
  - `population_count`: integer (NOT NULL)
  - `biomass_kg`: numeric (NOT NULL)
  - `created_at`: timestamptz (NOT NULL)
- **`batch_batchtransfer`** # Records movements or merging/splitting of batch components
  - `id`: bigint (PK, auto-increment, NOT NULL)
  - `transfer_type`: varchar (NOT NULL) # e.g., "MOVE", "SPLIT", "MERGE", "DEATH_TRANSFER"
  - `transfer_date`: date (NOT NULL)
  - `source_batch_id`: bigint (FK to `batch_batch`.`id`, NOT NULL)
  - `source_lifecycle_stage_id`: bigint (FK to `batch_lifecyclestage`.`id`, NOT NULL)
  - `source_assignment_id`: bigint (FK to `batch_batchcontainerassignment`.`id`, nullable) # Original assignment if applicable
  - `source_count`: integer (NOT NULL) # Population count from source before transfer
  - `source_biomass_kg`: numeric (NOT NULL) # Biomass from source before transfer
  - `transferred_count`: integer (NOT NULL) # Population count actually transferred
  - `transferred_biomass_kg`: numeric (NOT NULL) # Biomass actually transferred
  - `mortality_count`: integer (NOT NULL) # Mortalities during this transfer event
  - `destination_batch_id`: bigint (FK to `batch_batch`.`id`, nullable) # Target batch if different (e.g., for MERGE)
  - `destination_lifecycle_stage_id`: bigint (FK to `batch_lifecyclestage`.`id`, nullable) # Target stage if different
  - `destination_assignment_id`: bigint (FK to `batch_batchcontainerassignment`.`id`, nullable) # Resulting new assignment if applicable
  - `is_emergency_mixing`: boolean (NOT NULL, default: False)
  - `notes`: text (NOT NULL)
  - `created_at`: timestamptz (NOT NULL)
  - `updated_at`: timestamptz (NOT NULL)
- **`batch_mortalityevent`**
  - `id`: bigint (PK, auto-increment, NOT NULL)
  - `batch_id`: bigint (FK to `batch_batch`.`id`, on_delete=CASCADE, NOT NULL) # Link to the batch experiencing mortality
  - `event_date`: date (NOT NULL)
  - `count`: integer (NOT NULL)
  - `cause`: varchar(100) (NOT NULL) # e.g., Disease, Stress, Accident
  - `description`: text (NOT NULL)
  - `created_at`: timestamptz (NOT NULL)
  - `updated_at`: timestamptz (NOT NULL)
- **`batch_growthsample`**
    - `id`: bigint (PK, auto-increment, NOT NULL)
    - `assignment_id`: bigint (FK to `batch_batchcontainerassignment`.`id`, on_delete=CASCADE, NOT NULL)
    - `sample_date`: date (NOT NULL)
    - `sample_size`: integer (NOT NULL) # Number of individuals sampled
    - `avg_weight_g`: numeric (NOT NULL)
    - `avg_length_cm`: numeric (nullable)
    - `std_deviation_weight`: numeric (nullable)
    - `std_deviation_length`: numeric (nullable)
    - `min_weight_g`: numeric (nullable)
    - `max_weight_g`: numeric (nullable)
    - `condition_factor`: numeric (nullable) # e.g., Fulton's K
    - `notes`: text (nullable)
    - `created_at`: timestamptz (NOT NULL)
    - `updated_at`: timestamptz (NOT NULL)
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

### 4.3 Feed and Inventory Management (`inventory` app)
**Purpose**: Manages feed resources, inventory, feeding events, and recommendations.

#### Tables
- **`inventory_feed`**
  - `id`: bigint (PK, auto-increment)
  - `name`: varchar(100)
  - `brand`: varchar(100)
  - `size_category`: varchar(20) (Choices: 'MICRO', 'SMALL', 'MEDIUM', 'LARGE')
  - `pellet_size_mm`: decimal(5,2) (nullable, help_text="Pellet size in millimeters")
  - `protein_percentage`: decimal(5,2) (nullable, help_text="Protein content percentage", validators: MinValueValidator(0), MaxValueValidator(100))
  - `fat_percentage`: decimal(5,2) (nullable, help_text="Fat content percentage", validators: MinValueValidator(0), MaxValueValidator(100))
  - `carbohydrate_percentage`: decimal(5,2) (nullable, help_text="Carbohydrate content percentage", validators: MinValueValidator(0), MaxValueValidator(100))
  - `description`: text (blank=True)
  - `is_active`: boolean (default=True)
  - `created_at`: timestamptz (auto_now_add=True)
  - `updated_at`: timestamptz (auto_now=True)
  - Meta: `verbose_name_plural = "Feed"`
- **`inventory_feedpurchase`**
  - `id`: bigint (PK, auto-increment)
  - `feed_id`: bigint (FK to `inventory_feed`.`id`, on_delete=PROTECT, related_name='purchases')
  - `purchase_date`: date
  - `quantity_kg`: decimal(10,2) (validators: MinValueValidator(0.01), help_text="Amount of feed purchased in kilograms")
  - `cost_per_kg`: decimal(10,2) (validators: MinValueValidator(0.01), help_text="Cost per kilogram")
  - `supplier`: varchar(100)
  - `batch_number`: varchar(100) (blank=True, help_text="Supplier's batch number")
  - `expiry_date`: date (nullable, blank=True)
  - `notes`: text (blank=True)
  - `created_at`: timestamptz (auto_now_add=True)
  - `updated_at`: timestamptz (auto_now=True)
  - Meta: `ordering = ['-purchase_date']`
- **`inventory_feedstock`**
  - `id`: bigint (PK, auto-increment)
  - `feed_id`: bigint (FK to `inventory_feed`.`id`, on_delete=PROTECT, related_name='stock_levels')
  - `feed_container_id`: bigint (FK to `infrastructure_feedcontainer`.`id`, on_delete=CASCADE, related_name='feed_stocks')
  - `current_quantity_kg`: decimal(10,2) (validators: MinValueValidator(0), help_text="Current amount of feed in stock (kg)")
  - `reorder_threshold_kg`: decimal(10,2) (validators: MinValueValidator(0), help_text="Threshold for reordering (kg)")
  - `updated_at`: timestamptz (auto_now=True)
  - `notes`: text (blank=True)
  - Meta: `unique_together = ['feed', 'feed_container']`
- **`inventory_feedingevent`**
  - `id`: bigint (PK, auto-increment)
  - `batch_id`: bigint (FK to `batch_batch`.`id`, on_delete=PROTECT, related_name='feeding_events')
  - `container_id`: bigint (FK to `infrastructure_container`.`id`, on_delete=PROTECT, related_name='feeding_events')
  - `batch_assignment_id`: bigint (FK to `batch_batchcontainerassignment`.`id`, on_delete=SET_NULL, nullable, blank=True, related_name='explicit_feeding_events', help_text="Explicit link to the assignment active at feeding time, if known.")
  - `feed_id`: bigint (FK to `inventory_feed`.`id`, on_delete=PROTECT, related_name='applied_in_feedings')
  - `feed_stock_id`: bigint (FK to `inventory_feedstock`.`id`, on_delete=SET_NULL, nullable, blank=True)
  - `recorded_by_id`: integer (FK to `users_customuser`.`id`, on_delete=PROTECT, related_name='feeding_entries', nullable, blank=True, help_text="User who recorded or performed the feeding.")
  - `feeding_date`: date
  - `feeding_time`: time
  - `amount_kg`: decimal(10,4) (validators: MinValueValidator(0.0001), help_text="Amount of feed used in kilograms")
  - `batch_biomass_kg`: decimal(10,2) (help_text="Estimated batch biomass at time of feeding (kg)")
  - `feeding_percentage`: decimal(8,6) (nullable, blank=True, help_text="Feed amount as percentage of biomass (auto-calculated)")
  - `feed_cost`: decimal(10,2) (nullable, blank=True, help_text="Calculated cost of feed used in this feeding event")
  - `method`: varchar(20) (choices available for feeding method)
  - `notes`: text
  - `created_at`: timestamptz (auto_now_add=True)
  - `updated_at`: timestamptz (auto_now=True)
  - Meta: `ordering = ['-feeding_date', '-feeding_time']`
- **`inventory_feedcontainerstock`** (FIFO Inventory Tracking)
  - `id`: bigint (PK, auto-increment)
  - `feed_container_id`: bigint (FK to `infrastructure_feedcontainer`.`id`, on_delete=CASCADE, related_name='container_stocks')
  - `feed_purchase_id`: bigint (FK to `inventory_feedpurchase`.`id`, on_delete=CASCADE, related_name='container_stocks')
  - `quantity_kg`: decimal(10,3) (validators: MinValueValidator(0), help_text="Quantity of feed from this purchase in the container (kg)")
  - `cost_per_kg`: decimal(10,2) (help_text="Cost per kg from the original purchase")
  - `purchase_date`: date (help_text="Date of the original purchase for FIFO ordering")
  - `created_at`: timestamptz (auto_now_add=True)
  - `updated_at`: timestamptz (auto_now=True)
  - Meta: `ordering = ['feed_container', 'purchase_date', 'created_at']`, `unique_together = ['feed_container', 'feed_purchase']`
- **`inventory_batchfeedingsummary`**
  - `id`: bigint (PK, auto-increment)
  - `batch_id`: bigint (FK to `batch_batch`.`id`, on_delete=CASCADE, related_name='feeding_summaries')
  - `period_start`: date
  - `period_end`: date
  - `total_feed_kg`: decimal(12,3) (validators: MinValueValidator(0), help_text="Total feed provided to the batch in this period (kg)")
  - `average_biomass_kg`: decimal(12,2) (nullable, blank=True, validators: MinValueValidator(0), help_text="Average biomass of the batch during this period (kg)")
  - `average_feeding_percentage`: decimal(5,2) (nullable, blank=True, validators: MinValueValidator(0), MaxValueValidator(100), help_text="Average daily feeding percentage of biomass")
  - `growth_kg`: decimal(10,2) (nullable, blank=True, help_text="Total growth of the batch during this period (kg)")
  - `total_feed_consumed_kg`: decimal(12,3) (nullable, blank=True, help_text="Total feed consumed by the batch during this period (kg)")
  - `total_biomass_gain_kg`: decimal(10,2) (nullable, blank=True, help_text="Total biomass gain during this period (kg)")
  - `fcr`: decimal(5,3) (nullable, blank=True, help_text="Feed Conversion Ratio (total_feed_consumed_kg / total_biomass_gain_kg) - standardized field with high precision")
  - `created_at`: timestamptz (auto_now_add=True)
  - `updated_at`: timestamptz (auto_now=True)
  - Meta: `ordering = ['batch', '-period_end']`, `verbose_name_plural = "Batch feeding summaries"`, `unique_together = ['batch', 'period_start', 'period_end']`
  - **Note**: Duplicate `feed_conversion_ratio` field was removed to maintain data integrity and use the more precise `fcr` field.

#### Relationships
- `inventory_feed` ← `inventory_feedpurchase` (PROTECT, related_name='purchases')
- `inventory_feed` ← `inventory_feedstock` (PROTECT, related_name='stock_levels')
- `infrastructure_feedcontainer` ← `inventory_feedstock` (CASCADE, related_name='feed_stocks')
- `infrastructure_feedcontainer` ← `inventory_feedcontainerstock` (CASCADE, related_name='container_stocks')
- `inventory_feedpurchase` ← `inventory_feedcontainerstock` (CASCADE, related_name='container_stocks')
- `batch_batch` ← `inventory_feedingevent` (PROTECT, related_name='feeding_events')
- `infrastructure_container` ← `inventory_feedingevent` (PROTECT, related_name='feeding_events')
- `batch_batchcontainerassignment` ← `inventory_feedingevent` (SET_NULL, related_name='explicit_feeding_events')
- `inventory_feed` ← `inventory_feedingevent` (PROTECT, related_name='applied_in_feedings')
- `users_customuser` ← `inventory_feedingevent` (PROTECT, related_name='feeding_entries')
- `inventory_feedstock` ← `inventory_feedingevent` (SET_NULL)
- `batch_batch` ← `inventory_batchfeedingsummary` (CASCADE, related_name='feeding_summaries')

### 4.4 Health Monitoring (`health` app)
**Purpose**: Tracks health observations, treatments, mortality, sampling events, and lab results.

#### Tables
- **`health_journalentry`**
  - [id](cci:2://file:///c:/Users/bf10087/Projects/AquaMind/apps/health/models.py:256:0-284:80): bigint (PK, auto-increment)
  - `batch_id`: bigint (FK to `batch_batch`.[id](cci:2://file:///c:/Users/bf10087/Projects/AquaMind/apps/health/models.py:256:0-284:80), on_delete=CASCADE, related_name='journal_entries')
  - `container_id`: bigint (FK to `infrastructure_container`.[id](cci:2://file:///c:/Users/bf10087/Projects/AquaMind/apps/health/models.py:256:0-284:80), on_delete=SET_NULL, nullable, blank=True, related_name='journal_entries')
  - `user_id`: integer (FK to `users_customuser`.[id](cci:2://file:///c:/Users/bf10087/Projects/AquaMind/apps/health/models.py:256:0-284:80), on_delete=PROTECT, related_name='journal_entries')
  - `entry_date`: timestamptz (default=timezone.now)
  - `category`: varchar(20) (Choices: 'observation', 'issue', 'action', 'diagnosis', 'treatment', 'vaccination', 'sample')
  - `severity`: varchar(10) (Choices: 'low', 'medium', 'high', default='low', nullable, blank=True)
  - `description`: text
  - `resolution_status`: boolean (default=False)
  - `resolution_notes`: text (blank=True)
  - `created_at`: timestamptz (auto_now_add=True)
  - `updated_at`: timestamptz (auto_now=True)
  - Meta: `verbose_name_plural = "Journal Entries"`, `ordering = ['-entry_date']`
- **`health_healthparameter`**
  - [id](cci:2://file:///c:/Users/bf10087/Projects/AquaMind/apps/health/models.py:256:0-284:80): bigint (PK, auto-increment)
  - `name`: varchar(100) (Unique, help_text="Name of the health parameter (e.g., Gill Health).")
  - `description_score_1`: text (help_text="Description for score 1 (Best/Excellent).")
  - `description_score_2`: text (help_text="Description for score 2 (Good).")
  - `description_score_3`: text (help_text="Description for score 3 (Fair/Moderate).")
  - `description_score_4`: text (help_text="Description for score 4 (Poor/Severe).")
  - `description_score_5`: text (help_text="Description for score 5 (Worst/Critical).", default="")
  - `is_active`: boolean (default=True, help_text="Is this parameter currently in use?")
  - `created_at`: timestamptz (auto_now_add=True)
  - `updated_at`: timestamptz (auto_now=True)
- **`health_healthsamplingevent`**
  - [id](cci:2://file:///c:/Users/bf10087/Projects/AquaMind/apps/health/models.py:256:0-284:80): bigint (PK, auto-increment)
  - `assignment_id`: bigint (FK to `batch_batchcontainerassignment`.[id](cci:2://file:///c:/Users/bf10087/Projects/AquaMind/apps/health/models.py:256:0-284:80), on_delete=CASCADE, related_name='health_sampling_events')
  - `sampling_date`: date (default=timezone.now)
  - `number_of_fish_sampled`: positive integer (help_text="Target or initially declared number of individual fish to be examined...")
  - `avg_weight_g`: decimal(10,2) (nullable, blank=True, help_text="Average weight in grams of sampled fish.")
  - `std_dev_weight_g`: decimal(10,2) (nullable, blank=True, help_text="Standard deviation of weight in grams.")
  - `min_weight_g`: decimal(10,2) (nullable, blank=True, help_text="Minimum weight in grams among sampled fish.")
  - `max_weight_g`: decimal(10,2) (nullable, blank=True, help_text="Maximum weight in grams among sampled fish.")
  - `avg_length_cm`: decimal(10,2) (nullable, blank=True, help_text="Average length in centimeters of sampled fish.")
  - `std_dev_length_cm`: decimal(10,2) (nullable, blank=True, help_text="Standard deviation of length in centimeters.")
  - `min_length_cm`: decimal(10,2) (nullable, blank=True, help_text="Minimum length in centimeters among sampled fish.")
  - `max_length_cm`: decimal(10,2) (nullable, blank=True, help_text="Maximum length in centimeters among sampled fish.")
  - `avg_k_factor`: decimal(10,4) (nullable, blank=True, help_text="Average condition factor (K-factor) of sampled fish.")
  - `calculated_sample_size`: positive integer (nullable, blank=True, help_text="Number of fish with complete measurements used in calculations.")
  - `sampled_by_id`: integer (FK to `users_customuser`.[id](cci:2://file:///c:/Users/bf10087/Projects/AquaMind/apps/health/models.py:256:0-284:80), on_delete=SET_NULL, nullable, blank=True, related_name='health_sampling_events_conducted')
  - `notes`: text (blank=True, nullable)
  - `created_at`: timestamptz (auto_now_add=True)
  - `updated_at`: timestamptz (auto_now=True)
  - Meta: `ordering = ['-sampling_date', '-created_at']`, `verbose_name = "Health Sampling Event"`
- **`health_individualfishobservation`**
  - [id](cci:2://file:///c:/Users/bf10087/Projects/AquaMind/apps/health/models.py:256:0-284:80): bigint (PK, auto-increment)
  - `sampling_event_id`: bigint (FK to `health_healthsamplingevent`.[id](cci:2://file:///c:/Users/bf10087/Projects/AquaMind/apps/health/models.py:256:0-284:80), on_delete=CASCADE, related_name='individual_fish_observations')
  - `fish_identifier`: varchar(50) (help_text="Identifier for the specific fish (e.g., tag number or sequential ID).")
  - `length_cm`: decimal(10,2) (nullable, blank=True, help_text="Length of the fish in centimeters.")
  - `weight_g`: decimal(10,2) (nullable, blank=True, help_text="Weight of the fish in grams.")
  - `created_at`: timestamptz (auto_now_add=True)
  - `updated_at`: timestamptz (auto_now=True)
  - Meta: `unique_together = ('sampling_event', 'fish_identifier')`, `ordering = ['sampling_event', 'fish_identifier']`, `verbose_name = "Individual Fish Observation", `verbose_name_plural = "Individual Fish Observations"`
- **`health_fishparameterscore`**
  - [id](cci:2://file:///c:/Users/bf10087/Projects/AquaMind/apps/health/models.py:256:0-284:80): bigint (PK, auto-increment)
  - `individual_fish_observation_id`: bigint (FK to `health_individualfishobservation`.[id](cci:2://file:///c:/Users/bf10087/Projects/AquaMind/apps/health/models.py:256:0-284:80), on_delete=CASCADE, related_name='parameter_scores')
  - `parameter_id`: bigint (FK to `health_healthparameter`.[id](cci:2://file:///c:/Users/bf10087/Projects/AquaMind/apps/health/models.py:256:0-284:80), on_delete=PROTECT, related_name='fish_scores')
  - `score`: integer (validators: MinValueValidator(1), MaxValueValidator(5), help_text="Score from 1 (best) to 5 (worst).")
  - `created_at`: timestamptz (auto_now_add=True)
  - `updated_at`: timestamptz (auto_now=True)
  - Meta: `unique_together = ('individual_fish_observation', 'parameter')`, `ordering = ['individual_fish_observation', 'parameter']`, `verbose_name = "Fish Parameter Score", `verbose_name_plural = "Fish Parameter Scores"`
- **`health_mortalityreason`**
  - [id](cci:2://file:///c:/Users/bf10087/Projects/AquaMind/apps/health/models.py:256:0-284:80): bigint (PK, auto-increment)
  - `name`: varchar(100) (Unique)
  - `description`: text (blank=True)
  - Meta: `verbose_name_plural = "Mortality Reasons"`, `ordering = ['name']`
- **`health_mortalityrecord`**
  - [id](cci:2://file:///c:/Users/bf10087/Projects/AquaMind/apps/health/models.py:256:0-284:80): bigint (PK, auto-increment)
  - `batch_id`: bigint (FK to `batch_batch`.[id](cci:2://file:///c:/Users/bf10087/Projects/AquaMind/apps/health/models.py:256:0-284:80), on_delete=CASCADE, related_name='mortality_records')
  - `container_id`: bigint (FK to `infrastructure_container`.[id](cci:2://file:///c:/Users/bf10087/Projects/AquaMind/apps/health/models.py:256:0-284:80), on_delete=CASCADE, related_name='mortality_records', nullable, blank=True)
  - `event_date`: timestamptz (auto_now_add=True)
  - `count`: positive integer
  - `reason_id`: bigint (FK to `health_mortalityreason`.[id](cci:2://file:///c:/Users/bf10087/Projects/AquaMind/apps/health/models.py:256:0-284:80), on_delete=SET_NULL, nullable, related_name='mortality_records')
  - `notes`: text (blank=True)
  - Meta: `verbose_name_plural = "Mortality Records"`, `ordering = ['-event_date']`
- **`health_licecount`**
  - [id](cci:2://file:///c:/Users/bf10087/Projects/AquaMind/apps/health/models.py:256:0-284:80): bigint (PK, auto-increment)
  - `batch_id`: bigint (FK to `batch_batch`.[id](cci:2://file:///c:/Users/bf10087/Projects/AquaMind/apps/health/models.py:256:0-284:80), on_delete=CASCADE, related_name='lice_counts')
  - `container_id`: bigint (FK to `infrastructure_container`.[id](cci:2://file:///c:/Users/bf10087/Projects/AquaMind/apps/health/models.py:256:0-284:80), on_delete=CASCADE, related_name='lice_counts', nullable, blank=True)
  - `user_id`: integer (FK to `users_customuser`.[id](cci:2://file:///c:/Users/bf10087/Projects/AquaMind/apps/health/models.py:256:0-284:80), on_delete=SET_NULL, nullable, related_name='lice_counts')
  - `count_date`: timestamptz (auto_now_add=True)
  - `adult_female_count`: positive integer (default=0)
  - `adult_male_count`: positive integer (default=0)
  - `juvenile_count`: positive integer (default=0)
  - `fish_sampled`: positive integer (default=1)
  - `notes`: text (blank=True)
  - Meta: `verbose_name_plural = "Lice Counts"`, `ordering = ['-count_date']`
- **`health_vaccinationtype`**
  - [id](cci:2://file:///c:/Users/bf10087/Projects/AquaMind/apps/health/models.py:256:0-284:80): bigint (PK, auto-increment)
  - `name`: varchar(100) (Unique)
  - `manufacturer`: varchar(100) (blank=True)
  - `dosage`: varchar(50) (blank=True)
  - `description`: text (blank=True)
  - Meta: `verbose_name_plural = "Vaccination Types"`, `ordering = ['name']`
- **`health_treatment`**
  - [id](cci:2://file:///c:/Users/bf10087/Projects/AquaMind/apps/health/models.py:256:0-284:80): bigint (PK, auto-increment)
  - `batch_id`: bigint (FK to `batch_batch`.[id](cci:2://file:///c:/Users/bf10087/Projects/AquaMind/apps/health/models.py:256:0-284:80), on_delete=CASCADE, related_name='treatments')
  - `container_id`: bigint (FK to `infrastructure_container`.[id](cci:2://file:///c:/Users/bf10087/Projects/AquaMind/apps/health/models.py:256:0-284:80), on_delete=CASCADE, related_name='treatments', nullable, blank=True)
  - `batch_assignment_id`: bigint (FK to `batch_batchcontainerassignment`.[id](cci:2://file:///c:/Users/bf10087/Projects/AquaMind/apps/health/models.py:256:0-284:80), on_delete=CASCADE, related_name='treatments', nullable, blank=True)
  - `user_id`: integer (FK to `users_customuser`.[id](cci:2://file:///c:/Users/bf10087/Projects/AquaMind/apps/health/models.py:256:0-284:80), on_delete=SET_NULL, nullable, related_name='treatments')
  - `treatment_date`: timestamptz (auto_now_add=True)
  - `treatment_type`: varchar(20) (Choices: 'medication', 'vaccination', 'delicing', 'other', default='medication')
  - `vaccination_type_id`: bigint (FK to `health_vaccinationtype`.[id](cci:2://file:///c:/Users/bf10087/Projects/AquaMind/apps/health/models.py:256:0-284:80), on_delete=SET_NULL, nullable, blank=True, related_name='treatments')
  - `description`: text
  - `dosage`: varchar(100) (blank=True)
  - `duration_days`: positive integer (default=0)
  - `withholding_period_days`: positive integer (default=0, help_text="Days before fish can be harvested...")
  - `outcome`: text (blank=True)
  - Meta: `verbose_name_plural = "Treatments"`, `ordering = ['-treatment_date']`
- **`health_sampletype`**
  - [id](cci:2://file:///c:/Users/bf10087/Projects/AquaMind/apps/health/models.py:256:0-284:80): bigint (PK, auto-increment)
  - `name`: varchar(100) (Unique)
  - `description`: text (blank=True)
  - Meta: `verbose_name_plural = "Sample Types"`
- **`health_healthlabsample`**
  - [id](cci:2://file:///c:/Users/bf10087/Projects/AquaMind/apps/health/models.py:256:0-284:80): bigint (PK, auto-increment)
  - `batch_container_assignment_id`: bigint (FK to `batch_batchcontainerassignment`.[id](cci:2://file:///c:/Users/bf10087/Projects/AquaMind/apps/health/models.py:256:0-284:80), on_delete=PROTECT, related_name='lab_samples')
  - `sample_type_id`: bigint (FK to `health_sampletype`.[id](cci:2://file:///c:/Users/bf10087/Projects/AquaMind/apps/health/models.py:256:0-284:80), on_delete=PROTECT, related_name='lab_samples')
  - `sample_date`: date (help_text="Date the sample was physically taken.")
  - `date_sent_to_lab`: date (nullable, blank=True)
  - `date_results_received`: date (nullable, blank=True)
  - `lab_reference_id`: varchar(100) (nullable, blank=True)
  - `findings_summary`: text (nullable, blank=True)
  - `quantitative_results`: jsonb (nullable, blank=True, help_text="Structured quantitative results...")
  - [attachment](cci:1://file:///c:/Users/bf10087/Projects/AquaMind/apps/health/models.py:582:4-583:53): file (upload_to='health/lab_samples/%Y/%m/', nullable, blank=True)
  - `notes`: text (nullable, blank=True)
  - `recorded_by_id`: integer (FK to `users_customuser`.[id](cci:2://file:///c:/Users/bf10087/Projects/AquaMind/apps/health/models.py:256:0-284:80), on_delete=SET_NULL, nullable, blank=True, related_name='recorded_lab_samples')
  - `created_at`: timestamptz (auto_now_add=True)
  - `updated_at`: timestamptz (auto_now=True)
  - Meta: `ordering = ['-sample_date', '-created_at']`, `verbose_name = "Health Lab Sample"`

#### Relationships
- `batch_batch` ← `health_journalentry` (CASCADE, related_name='journal_entries')
- `infrastructure_container` ← `health_journalentry` (SET_NULL, related_name='journal_entries')
- `users_customuser` ← `health_journalentry` (PROTECT, related_name='journal_entries')
- `batch_batchcontainerassignment` ← `health_healthsamplingevent` (CASCADE, related_name='health_sampling_events')
- `users_customuser` ← `health_healthsamplingevent` (SET_NULL, related_name='health_sampling_events_conducted')
- `health_healthsamplingevent` ← `health_individualfishobservation` (CASCADE, related_name='individual_fish_observations')
- `health_individualfishobservation` ← `health_fishparameterscore` (CASCADE, related_name='parameter_scores')
- `health_healthparameter` ← `health_fishparameterscore` (PROTECT, related_name='fish_scores')
- `batch_batch` ← `health_mortalityrecord` (CASCADE, related_name='mortality_records')
- `infrastructure_container` ← `health_mortalityrecord` (CASCADE, related_name='mortality_records')
- `health_mortalityreason` ← `health_mortalityrecord` (SET_NULL, related_name='mortality_records')
- `batch_batch` ← `health_licecount` (CASCADE, related_name='lice_counts')
- `infrastructure_container` ← `health_licecount` (CASCADE, related_name='lice_counts')
- `users_customuser` ← `health_licecount` (SET_NULL, related_name='lice_counts')
- `batch_batch` ← `health_treatment` (CASCADE, related_name='treatments')
- `infrastructure_container` ← `health_treatment` (CASCADE, related_name='treatments')
- `batch_batchcontainerassignment` ← `health_treatment` (CASCADE, related_name='treatments')
- `users_customuser` ← `health_treatment` (SET_NULL, related_name='treatments')
- `health_vaccinationtype` ← `health_treatment` (SET_NULL, related_name='treatments')
- `batch_batchcontainerassignment` ← `health_healthlabsample` (PROTECT, related_name='lab_samples')
- `health_sampletype` ← `health_healthlabsample` (PROTECT, related_name='lab_samples')
- `users_customuser` ← `health_healthlabsample` (SET_NULL, related_name='recorded_lab_samples')

### 4.5 Environmental Monitoring (`environmental` app)
**Purpose**: Captures time-series data for environmental conditions.

#### Tables
- **`environmental_environmentalparameter`**
  - `id`: bigint (PK, auto-increment)
  - `name`: varchar(100) (Unique) # e.g., Temperature, Dissolved Oxygen, Salinity
  - `unit`: varchar(20) # e.g., °C, mg/L, ppt
  - `description`: text (nullable)
  - `created_at`: timestamptz
  - `updated_at`: timestamptz
- **`environmental_environmentalreading`** (TimescaleDB Hypertable, partitioned by `reading_time`)
  # Primary Key for TimescaleDB hypertable is (reading_time, sensor_id)
  - `id`: bigint (auto-increment, NOT NULL) # Standard Django ID, not the TimescaleDB PK
  - `reading_time`: timestamptz (PK part 1, NOT NULL)
  - `sensor_id`: bigint (FK to `infrastructure_sensor`.`id`, PK part 2, NOT NULL)
  - `parameter_id`: bigint (FK to `environmental_environmentalparameter`.`id`, NOT NULL)
  - `value`: numeric (NOT NULL)
  - `container_id`: bigint (FK to `infrastructure_container`.`id`, NOT NULL)
  - `batch_id`: bigint (FK to `batch_batch`.`id`, nullable)
  - `recorded_by_id`: integer (FK to `auth_user`.`id`, nullable, for manual entries)
  - `is_manual`: boolean (NOT NULL)
  - `notes`: text (NOT NULL)
  - `created_at`: timestamptz (NOT NULL)
  - `updated_at`: timestamptz
- **`environmental_weatherdata`** (TimescaleDB Hypertable, partitioned by `timestamp`)
  # Primary Key for TimescaleDB hypertable is (timestamp, area_id)
  - `id`: bigint (auto-increment, NOT NULL) # Standard Django ID, not the TimescaleDB PK
  - `timestamp`: timestamptz (PK part 1, NOT NULL)
  - `area_id`: bigint (FK to `infrastructure_area`.`id`, PK part 2, on_delete=CASCADE, NOT NULL)
  - `temperature`: numeric (nullable) # Temperature in Celsius
  - `wind_speed`: numeric (nullable) # Wind speed in m/s
  - `wind_direction`: integer (nullable) # Wind direction in degrees
  - `precipitation`: numeric (nullable) # Precipitation in mm
  - `wave_height`: numeric (nullable) # Wave height in meters
  - `wave_period`: numeric (nullable) # Wave period in seconds
  - `wave_direction`: integer (nullable) # Wave direction in degrees
  - `cloud_cover`: integer (nullable) # Cloud cover in percentage
  - `created_at`: timestamptz (NOT NULL)
  - `updated_at`: timestamptz
- **`environmental_photoperioddata`**
  - `id`: bigint (PK, auto-increment, NOT NULL)
  - `area_id`: bigint (FK to `infrastructure_area`.`id`, on_delete=CASCADE, NOT NULL)
  - `date`: date (NOT NULL, Unique with `area_id`)
  - `day_length_hours`: numeric (NOT NULL)
  - `light_intensity`: numeric (nullable) # e.g., lux, PAR
  - `is_interpolated`: boolean (NOT NULL, default: False) # If data was calculated/interpolated vs directly measured
  - `created_at`: timestamptz (NOT NULL)
  - `updated_at`: timestamptz (NOT NULL)
- **`environmental_stagetransitionenvironmental`** # Records environmental conditions during a batch transfer
  - `id`: bigint (PK, auto-increment, NOT NULL)
  - `batch_transfer_id`: bigint (FK to `batch_batchtransfer`.`id`, Unique, NOT NULL)
  - `temperature`: numeric (nullable) # e.g., Celsius
  - `oxygen`: numeric (nullable) # e.g., mg/L
  - `salinity`: numeric (nullable) # e.g., ppt
  - `ph`: numeric (nullable)
  - `additional_parameters`: jsonb (nullable) # For other relevant parameters
  - `notes`: text (NOT NULL, default: '')
  - `created_at`: timestamptz (NOT NULL)
  - `updated_at`: timestamptz (NOT NULL)

#### Relationships (Model `on_delete` behavior shown)
- `infrastructure_sensor` ← `environmental_environmentalreading` (`sensor_id`, CASCADE)
- `environmental_environmentalparameter` ← `environmental_environmentalreading` (`parameter_id`, PROTECT)
- `infrastructure_container` ← `environmental_environmentalreading` (`container_id`, CASCADE)
- `batch_batch` ← `environmental_environmentalreading` (`batch_id`, SET_NULL)
- `auth_user` ← `environmental_environmentalreading` (`recorded_by_id`, SET_NULL)
- `infrastructure_area` ← `environmental_weatherdata` (`area_id`, CASCADE)
- `infrastructure_area` ← `environmental_photoperioddata` (`area_id`, CASCADE)
- `batch_batchtransfer` ← `environmental_stagetransitionenvironmental` (`batch_transfer_id`, CASCADE)

### 4.6 User Management (`auth` and `users` apps)
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

#### 4.7 Broodstock Management (broodstock app)

The Broodstock Management app’s data model supports comprehensive management of broodstock containers, fish populations, breeding operations, egg production/acquisition, environmental monitoring, and batch traceability. It reuses existing models like `infrastructure_container`, introduces normalized tables for better integrity and querying, and integrates with apps like `environmental` and `health`. The design ensures flexible traceability for internal eggs (broodstock to batch) and external eggs (supplier to batch), matching the implementation complexity of Scenario Planning. It also supports end-to-end traceability to harvest events, leveraging existing batch models and audit logging for regulatory compliance.

**Core Entities and Attributes**

- **infrastructure_container** (Reused for Broodstock Containers)  
  - `container_id` (PK): Unique identifier.  
  - `location` (CharField, max_length=100): Physical location (e.g., "Site A, Building 2, Room 5").  
  - `capacity` (IntegerField): Maximum fish capacity (e.g., 500).  
  - `containertype_id` (FK): Link to `infrastructure_containertype` (e.g., "broodstock").  
  - `status` (CharField, max_length=20, choices=[("active", "Active"), ("maintenance", "Under Maintenance"), ("quarantine", "Quarantine"), ("inactive", "Inactive")]): Container status.  
  - `created_at` (DateTimeField): Creation timestamp.  
  - `updated_at` (DateTimeField): Last update timestamp.

- **MaintenanceTask** (New Table for Container Maintenance)  
  - `task_id` (PK): Unique identifier.  
  - `container_id` (FK): Link to `infrastructure_container`.  
  - `task_type` (CharField, max_length=50, choices=[("cleaning", "Cleaning"), ("repair", "Repair"), ("inspection", "Inspection"), ("upgrade", "Equipment Upgrade")]): Type of task.  
  - `scheduled_date` (DateTimeField): Planned execution date.  
  - `completed_date` (DateTimeField, nullable): Actual completion date.  
  - `notes` (TextField, nullable): Additional details (e.g., "Replaced filter").  
  - `created_by` (FK): Link to `auth_user`.  
  - `created_at` (DateTimeField): Creation timestamp.  
  - `updated_at` (DateTimeField): Last update timestamp.

- **BroodstockFish** (New Table for Individual Fish)  
  - `fish_id` (PK): Unique identifier.  
  - `container_id` (FK): Link to `infrastructure_container` (where `containertype="broodstock"`).  
  - `traits` (JSONField, nullable, default={}): Basic traits (e.g., {"growth_rate": "high", "size": "large"}).  
  - `health_status` (CharField, max_length=20, choices=[("healthy", "Healthy"), ("monitored", "Monitored"), ("sick", "Sick"), ("deceased", "Deceased")]): Current health, synced with `health_journalentry`.  
  - `created_at` (DateTimeField): Creation timestamp.  
  - `updated_at` (DateTimeField): Last update timestamp.

- **FishMovement** (New Table for Tracking Movements)  
  - `movement_id` (PK): Unique identifier.  
  - `fish_id` (FK): Link to `BroodstockFish`.  
  - `from_container_id` (FK): Link to `infrastructure_container`.  
  - `to_container_id` (FK): Link to `infrastructure_container`.  
  - `movement_date` (DateTimeField): Date of movement.  
  - `moved_by` (FK): Link to `auth_user`.  
  - `notes` (TextField, nullable): Details (e.g., "Moved for breeding").  
  - `created_at` (DateTimeField): Creation timestamp.  
  - `updated_at` (DateTimeField): Last update timestamp.

- **BreedingPlan** (New Table for Breeding Strategies)  
  - `plan_id` (PK): Unique identifier.  
  - `name` (CharField, max_length=100): Plan name (e.g., "Winter 2023 Breeding").  
  - `start_date` (DateTimeField): Plan start date.  
  - `end_date` (DateTimeField): Plan end date.  
  - `created_at` (DateTimeField): Creation timestamp.  
  - `updated_at` (DateTimeField): Last update timestamp.

- **BreedingTraitPriority** (New Table for Trait Prioritization)  
  - `priority_id` (PK): Unique identifier.  
  - `plan_id` (FK): Link to `BreedingPlan`.  
  - `trait_name` (CharField, max_length=50, choices=[("growth_rate", "Growth Rate"), ("disease_resistance", "Disease Resistance"), ("size", "Size"), ("fertility", "Fertility")]): Trait identifier.  
  - `priority_weight` (FloatField, min_value=0, max_value=1): Weight (e.g., 0.7).  
  - `created_at` (DateTimeField): Creation timestamp.  
  - `updated_at` (DateTimeField): Last update timestamp.

- **BreedingPair** (New Table for Pair Assignments)  
  - `pair_id` (PK): Unique identifier.  
  - `plan_id` (FK): Link to `BreedingPlan`.  
  - `male_fish_id` (FK): Link to `BroodstockFish`.  
  - `female_fish_id` (FK): Link to `BroodstockFish`.  
  - `pairing_date` (DateTimeField): Date of pairing.  
  - `progeny_count` (IntegerField, nullable): Number of offspring produced.  
  - `created_at` (DateTimeField): Creation timestamp.  
  - `updated_at` (DateTimeField): Last update timestamp.

- **EggProduction** (New Table for Egg Tracking)  
  - `egg_production_id` (PK): Unique identifier.  
  - `pair_id` (FK, nullable): Link to `BreedingPair` (null for external eggs).  
  - `egg_batch_id` (CharField, max_length=50, unique): Unique egg batch identifier (e.g., "EB20231001").  
  - `egg_count` (IntegerField, min_value=0): Number of eggs (e.g., 10,000).  
  - `production_date` (DateTimeField): Date produced or acquired.  
  - `destination_station_id` (FK, nullable): Link to `infrastructure_freshwaterstation`.  
  - `source_type` (CharField, max_length=20, choices=[("internal", "Internal"), ("external", "External")]): Egg source.  
  - `created_at` (DateTimeField): Creation timestamp.  
  - `updated_at` (DateTimeField): Last update timestamp.

- **EggSupplier** (New Table for External Suppliers)  
  - `supplier_id` (PK): Unique identifier.  
  - `name` (CharField, max_length=100): Supplier name (e.g., "NorthSea Eggs").  
  - `contact_details` (TextField): Contact info (e.g., phone, email).  
  - `certifications` (TextField, nullable): Certifications (e.g., "ISO 9001").  
  - `created_at` (DateTimeField): Creation timestamp.  
  - `updated_at` (DateTimeField): Last update timestamp.

- **ExternalEggBatch** (New Table for External Eggs)  
  - `external_batch_id` (PK): Unique identifier.  
  - `egg_production_id` (FK): Link to `EggProduction` (where `source_type="external"`).  
  - `supplier_id` (FK): Link to `EggSupplier`.  
  - `batch_number` (CharField, max_length=50): Supplier’s batch ID (e.g., "S789-2023").  
  - `provenance_data` (TextField, nullable): Details (e.g., "Sourced from Farm X").  
  - `created_at` (DateTimeField): Creation timestamp.  
  - `updated_at` (DateTimeField): Last update timestamp.

- **BatchParentage** (New Table for Egg-to-Batch Links)  
  - `batch_id` (FK, PK): Link to `batch_batch`.  
  - `egg_production_id` (FK, PK): Link to `EggProduction`.  
  - `assignment_date` (DateTimeField): Date eggs assigned to batch.  
  - `created_at` (DateTimeField): Creation timestamp.  
  - `updated_at` (DateTimeField): Last update timestamp.

- **EnvironmentalReading** (Reused from `environmental` App)  
  - `reading_id` (PK): Unique identifier.  
  - `container_id` (FK): Link to `infrastructure_container`.  
  - `parameter_type` (CharField, max_length=50): Type (e.g., "temperature").  
  - `value` (FloatField): Measured value (e.g., 22.5).  
  - `timestamp` (DateTimeField): Reading time.  
  - `source` (CharField, max_length=50): Sensor or manual entry ID.  
  - `recorded_by` (FK, nullable): Link to `auth_user`.  
  - `created_at`, `updated_at` (DateTimeField): Timestamps.

- **EnvironmentalSchedule** (Reused/Extended from `environmental`)  
  - `schedule_id` (PK): Unique identifier.  
  - `container_id` (FK): Link to `infrastructure_container`.  
  - `name` (CharField, max_length=100): Schedule name (e.g., "Summer Photoperiod").  
  - `parameter_type` (CharField, max_length=50, choices=[("temperature", "Temperature"), ("photoperiod", "Photoperiod"), ("pH", "pH")]): Parameter.  
  - `start_time`, `end_time` (DateTimeField): Schedule duration.  
  - `target_value` (FloatField): Target (e.g., 12 hours light).  
  - `created_at`, `updated_at` (DateTimeField): Timestamps.

- **Scenario** (Reused from Scenario Planning)  
  - `scenario_id` (PK): Unique identifier.  
  - `name` (CharField, max_length=100): Scenario name.  
  - `description` (TextField, nullable): Scenario details.  
  - `parameters` (JSONField): Broodstock-specific params (e.g., {"egg_target": 10000, "source": "external"}).  
  - `start_date`, `end_date` (DateTimeField): Scenario timeframe.  
  - `created_by` (FK): Link to `auth_user`.  
  - `created_at`, `updated_at` (DateTimeField): Timestamps.

**Relationships**  
- **infrastructure_container** to **BroodstockFish**: One-to-many (one container holds many fish).  
- **infrastructure_container** to **MaintenanceTask**: One-to-many (one container has many tasks).  
- **infrastructure_container** to **EnvironmentalReading**: One-to-many (one container has many readings).  
- **infrastructure_container** to **EnvironmentalSchedule**: One-to-many (one container has many schedules).  
- **BreedingPlan** to **BreedingTraitPriority**: One-to-many (one plan has many priorities).  
- **BreedingPlan** to **BreedingPair**: One-to-many (one plan includes many pairs).  
- **BreedingPair** to **BroodstockFish**: Many-to-two (each pair links one male and one female).  
- **BreedingPair** to **EggProduction**: One-to-many (one pair produces multiple egg batches).  
- **EggProduction** to **BatchParentage**: One-to-many (one egg batch may link to multiple batches if split).  
- **EggProduction** to **ExternalEggBatch**: One-to-one (one external egg record per acquisition).  
- **EggSupplier** to **ExternalEggBatch**: One-to-many (one supplier provides many batches).  
- **BatchParentage** to **batch_batch**: Many-to-one (multiple egg batches may contribute to one batch).

**Constraints**  
- Unique constraint on `egg_batch_id` in `EggProduction`.  
- Foreign key constraints enforce referential integrity (e.g., `container_id`, `fish_id`, `egg_production_id`).  
- `source_type` in `EggProduction` restricted to "internal" or "external" via choices.  
- `pair_id` in `EggProduction` nullable for external eggs; non-null for internal eggs.  
- `progeny_count` in `BreedingPair` nullable until eggs are produced.  
- `destination_station_id` in `EggProduction` nullable if eggs are stored before assignment.  

**Additional Considerations**  
- **Harvest Traceability**: Leverage existing `batch_batch` and related models (e.g., `batch_batchtransfer`, `batch_mortalityevent`) to track batches to harvest. If explicit harvest events are needed, consider a `HarvestEvent` model (e.g., `harvest_id`, `batch_id`, `harvest_date`, `yield_kg`) to extend traceability to processed fish, but this can be deferred unless required by regulations.  
- **Health Integration**: Sync `BroodstockFish.health_status` with `health_journalentry` via a foreign key or API call, ensuring health events (e.g., treatments) are recorded consistently.  
- **Scalability**: Support 10,000+ fish and egg batches with indexes on `container_id`, `fish_id`, `egg_batch_id`, and `batch_id`. Use table partitioning for `EnvironmentalReading` if data volume exceeds 10M rows.  
- **Auditing**: Apply `django-auditlog` to `EggProduction`, `BatchParentage`, `BreedingPair`, `FishMovement`, and `MaintenanceTask` to ensure immutable lineage and operational records.  
- **Validation**: Enforce field constraints (e.g., `egg_count >= 0`, `priority_weight` between 0-1) via model validation. Ensure `containertype="broodstock"` for `BroodstockFish` container assignments.  
- **TimescaleDB**: Utilize TimescaleDB hypertables for `EnvironmentalReading` to optimize time-series queries, with partitioning by `timestamp`.  
- **JSON Fields**: Keep `traits` and `parameters` minimal, with structured formats (e.g., key-value pairs) and partial indexes for frequent queries.  
- **Mobile Sync**: Ensure offline data entries (e.g., movements, egg logs) include temporary IDs, resolving conflicts during sync with server-side validation.

## 5. Planned Data Model Domains (Not Yet Implemented)

### 5.1 Operational Planning
**Purpose**: Provide operational recommendations.
**Tables**: `batch_operational_plan`, `planning_recommendation`. (Details omitted).

### 5.2 Scenario Planning
**Purpose**: Simulate hypothetical scenarios.
**Tables**: `batch_scenario`, `scenario_model`. (Details omitted).

### 5.3 Analytics
**Purpose**: Support AI/ML predictions.
**Tables**: `analytics_model`, `prediction`. (Details omitted).

## 6. Data Governance

- **Audit Trails**: Standard `created_at`, `updated_at` fields exist. Consider integrating `django-auditlog` for comprehensive tracking.
- **Validation**: ORM-level validation exists. Database constraints (Foreign Keys, Uniqueness) are enforced. `on_delete` behavior specified where known/inferred.
- **Partitioning and Indexing**: TimescaleDB hypertables are partitioned. Relevant indexes exist on Foreign Keys and timestamp columns.

## 7. Appendix: Developer Notes

- **TimescaleDB Setup**: Ensure `timescaledb` extension is enabled. Use Django migrations (potentially with `RunSQL`) or manual commands (`SELECT create_hypertable(...)`) to manage hypertables.
- **Calculated Fields**: Fields like `batch_batchcontainerassignment.biomass_kg` are calculated in the application logic (e.g., model `save()` method or serializers), not stored directly unless denormalized.
- **User Profile**: Access extended user information via `user.userprofile`. Geography is linked via FK, subsidiary requires clarification (FK or CharField?).