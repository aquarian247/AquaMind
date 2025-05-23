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

### 3.3 Feed and Inventory Management (`inventory` app)
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
  - `last_updated`: timestamptz (auto_now=True)
  - `notes`: text (blank=True)
  - Meta: `unique_together = ['feed', 'feed_container']`
- **`inventory_feedingevent`**
  - `id`: bigint (PK, auto-increment)
  - `batch_id`: bigint (FK to `batch_batch`.`id`, on_delete=PROTECT, related_name='feeding_events')
  - `container_id`: bigint (FK to `infrastructure_container`.`id`, on_delete=PROTECT, related_name='feeding_events', nullable, blank=True)
  - `batch_container_assignment_id`: bigint (FK to `batch_batchcontainerassignment`.`id`, on_delete=SET_NULL, nullable, blank=True, related_name='explicit_feeding_events', help_text="Explicit link to the assignment active at feeding time, if known.")
  - `feed_id`: bigint (FK to `inventory_feed`.`id`, on_delete=PROTECT, related_name='applied_in_feedings')
  - `user_id`: integer (FK to `users_customuser`.`id`, on_delete=PROTECT, related_name='feeding_entries', help_text="User who recorded or performed the feeding.")
  - `feeding_date`: date
  - `feeding_time`: time (nullable, blank=True)
  - `feed_quantity_kg`: decimal(8,3) (validators: MinValueValidator(0), help_text="Amount of feed provided in kg")
  - `feed_cost_total`: decimal(10,2) (nullable, blank=True, help_text="Total cost of feed for this event, calculated if cost_per_kg is known.")
  - `feed_cost_per_kg`: decimal(10,2) (nullable, blank=True, help_text="Cost per kg of feed at time of feeding, can be from FeedStock or manual.")
  - `batch_biomass_kg`: decimal(10,2) (nullable, blank=True, help_text="Estimated batch biomass at time of feeding (kg)")
  - `feeding_percentage_of_biomass`: decimal(5,2) (nullable, blank=True, validators: MinValueValidator(0), MaxValueValidator(100), help_text="Feeding rate as percentage of biomass")
  - `water_temperature_c`: decimal(5,2) (nullable, blank=True, help_text="Water temperature at time of feeding (°C)")
  - `dissolved_oxygen_mg_l`: decimal(5,2) (nullable, blank=True, help_text="Dissolved oxygen at time of feeding (mg/L)")
  - `notes`: text (blank=True)
  - `is_manual_entry`: boolean (default=True, help_text="Was this entry manually created or system-generated?")
  - `source_recommendation_id`: bigint (FK to `inventory_feedrecommendation`.`id`, on_delete=SET_NULL, nullable, blank=True, help_text="Link to the feed recommendation that prompted this event, if any.")
  - `created_at`: timestamptz (auto_now_add=True)
  - `updated_at`: timestamptz (auto_now=True)
  - Meta: `ordering = ['-feeding_date', '-feeding_time']`
- **`inventory_batchfeedingsummary`**
  - `id`: bigint (PK, auto-increment)
  - `batch_id`: bigint (FK to `batch_batch`.`id`, on_delete=CASCADE, related_name='feeding_summaries')
  - `period_start`: date
  - `period_end`: date
  - `total_feed_kg`: decimal(12,3) (validators: MinValueValidator(0), help_text="Total feed provided to the batch in this period (kg)")
  - `average_biomass_kg`: decimal(12,2) (nullable, blank=True, validators: MinValueValidator(0), help_text="Average biomass of the batch during this period (kg)")
  - `average_feeding_percentage`: decimal(5,2) (nullable, blank=True, validators: MinValueValidator(0), MaxValueValidator(100), help_text="Average daily feeding percentage of biomass")
  - `feed_conversion_ratio`: decimal(8,3) (nullable, blank=True, help_text="Feed Conversion Ratio (FCR) for the period")
  - `growth_kg`: decimal(10,2) (nullable, blank=True, help_text="Total growth of the batch during this period (kg)")
  - `created_at`: timestamptz (auto_now_add=True)
  - `updated_at`: timestamptz (auto_now=True)
  - Meta: `ordering = ['batch', '-period_end']`, `verbose_name_plural = "Batch feeding summaries"`, `unique_together = ['batch', 'period_start', 'period_end']`
- **`inventory_feedrecommendation`**
  - `id`: bigint (PK, auto-increment)
  - `batch_container_assignment_id`: bigint (FK to `batch_batchcontainerassignment`.`id`, on_delete=CASCADE, related_name='feed_recommendations')
  - `feed_id`: bigint (FK to `inventory_feed`.`id`, on_delete=PROTECT, related_name='recommendations', help_text="Recommended feed type")
  - `recommended_date`: date (help_text="Date for which this recommendation applies")
  - `recommended_feed_kg`: decimal(10,3) (validators: MinValueValidator(0), help_text="Recommended feed amount in kilograms")
  - `feeding_percentage`: decimal(5,2) (validators: MinValueValidator(0), MaxValueValidator(100), help_text="Recommended feeding as percentage of biomass")
  - `feedings_per_day`: smallint (positive, default=2, help_text="Recommended number of feedings per day")
  - `water_temperature_c`: decimal(5,2) (nullable, blank=True, help_text="Water temperature at time of recommendation (°C)")
  - `dissolved_oxygen_mg_l`: decimal(5,2) (nullable, blank=True, help_text="Dissolved oxygen at time of recommendation (mg/L)")
  - `recommendation_reason`: text (help_text="Explanation of factors that influenced this recommendation")
  - `is_followed`: boolean (default=False, help_text="Whether this recommendation was followed")
  - `expected_fcr`: decimal(5,2) (nullable, blank=True, help_text="Expected FCR if recommendation is followed")
  - `created_at`: timestamptz (auto_now_add=True)
  - `updated_at`: timestamptz (auto_now=True)
  - Meta: `ordering = ['-recommended_date', '-created_at']`, `verbose_name_plural = "Feed recommendations"`, `unique_together = ['batch_container_assignment', 'recommended_date']`

#### Relationships
- `inventory_feed` ← `inventory_feedpurchase` (PROTECT, related_name='purchases')
- `inventory_feed` ← `inventory_feedstock` (PROTECT, related_name='stock_levels')
- `infrastructure_feedcontainer` ← `inventory_feedstock` (CASCADE, related_name='feed_stocks')
- `batch_batch` ← `inventory_feedingevent` (PROTECT, related_name='feeding_events')
- `infrastructure_container` ← `inventory_feedingevent` (PROTECT, related_name='feeding_events')
- `batch_batchcontainerassignment` ← `inventory_feedingevent` (SET_NULL, related_name='explicit_feeding_events')
- `inventory_feed` ← `inventory_feedingevent` (PROTECT, related_name='applied_in_feedings')
- `users_customuser` ← `inventory_feedingevent` (PROTECT, related_name='feeding_entries')
- `inventory_feedrecommendation` ← `inventory_feedingevent` (SET_NULL, related_name='feed_events_based_on_this') (Note: Model has `source_recommendation` on `FeedingEvent`)
- `batch_batch` ← `inventory_batchfeedingsummary` (CASCADE, related_name='feeding_summaries')
- `batch_batchcontainerassignment` ← `inventory_feedrecommendation` (CASCADE, related_name='feed_recommendations')
- `inventory_feed` ← `inventory_feedrecommendation` (PROTECT, related_name='recommendations')

### 3.4 Health Monitoring (`health` app)
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
  - `avg_weight_g`: decimal(7,2) (nullable, blank=True, help_text="Calculated average weight...")
  - `avg_length_cm`: decimal(5,2) (nullable, blank=True, help_text="Calculated average length...")
  - `std_dev_weight_g`: decimal(7,2) (nullable, blank=True, help_text="Calculated standard deviation of weight...")
  - `std_dev_length_cm`: decimal(5,2) (nullable, blank=True, help_text="Calculated standard deviation of length...")
  - `min_weight_g`: decimal(7,2) (nullable, blank=True, help_text="Minimum weight recorded...")
  - `max_weight_g`: decimal(7,2) (nullable, blank=True, help_text="Maximum weight recorded...")
  - `min_length_cm`: decimal(5,2) (nullable, blank=True, help_text="Minimum length recorded...")
  - `max_length_cm`: decimal(5,2) (nullable, blank=True, help_text="Maximum length recorded...")
  - `avg_k_factor`: decimal(5,2) (nullable, blank=True, help_text="Calculated average K-factor...")
  - `calculated_sample_size`: positive integer (nullable, blank=True, help_text="Actual number of fish with weight measurements...")
  - `sampled_by_id`: integer (FK to `users_customuser`.[id](cci:2://file:///c:/Users/bf10087/Projects/AquaMind/apps/health/models.py:256:0-284:80), on_delete=SET_NULL, nullable, blank=True, related_name='health_sampling_events_conducted')
  - `notes`: text (blank=True, nullable)
  - `created_at`: timestamptz (auto_now_add=True)
  - `updated_at`: timestamptz (auto_now=True)
  - Meta: `ordering = ['-sampling_date', '-created_at']`, `verbose_name = "Health Sampling Event"`
- **`health_individualfishobservation`**
  - [id](cci:2://file:///c:/Users/bf10087/Projects/AquaMind/apps/health/models.py:256:0-284:80): bigint (PK, auto-increment)
  - `sampling_event_id`: bigint (FK to `health_healthsamplingevent`.[id](cci:2://file:///c:/Users/bf10087/Projects/AquaMind/apps/health/models.py:256:0-284:80), on_delete=CASCADE, related_name='individual_fish_observations')
  - `fish_identifier`: positive integer (help_text="Sequential identifier for the fish within this sampling event...")
  - `length_cm`: decimal(5,2) (nullable, blank=True)
  - `weight_g`: decimal(7,2) (nullable, blank=True)
  - `created_at`: timestamptz (auto_now_add=True)
  - `updated_at`: timestamptz (auto_now=True)
  - Meta: `unique_together = ('sampling_event', 'fish_identifier')`, `ordering = ['sampling_event', 'fish_identifier']`
- **`health_fishparameterscore`**
  - [id](cci:2://file:///c:/Users/bf10087/Projects/AquaMind/apps/health/models.py:256:0-284:80): bigint (PK, auto-increment)
  - `individual_fish_observation_id`: bigint (FK to `health_individualfishobservation`.[id](cci:2://file:///c:/Users/bf10087/Projects/AquaMind/apps/health/models.py:256:0-284:80), on_delete=CASCADE, related_name='parameter_scores')
  - `parameter_id`: bigint (FK to `health_healthparameter`.[id](cci:2://file:///c:/Users/bf10087/Projects/AquaMind/apps/health/models.py:256:0-284:80), on_delete=PROTECT, related_name='fish_scores')
  - `score`: integer (validators: MinValueValidator(1), MaxValueValidator(5), help_text="Score from 1 (Best) to 5 (Worst)...")
  - `created_at`: timestamptz (auto_now_add=True)
  - `updated_at`: timestamptz (auto_now=True)
  - Meta: `unique_together = ('individual_fish_observation', 'parameter')`, `ordering = ['individual_fish_observation', 'parameter']`
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