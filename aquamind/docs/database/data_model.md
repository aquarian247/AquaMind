# AquaMind Data Model

## 1. Introduction

This document defines the data model for AquaMind, an aquaculture management system. It integrates the database schema details obtained from direct inspection (`inspect_db_schema.py`) and Django model introspection. It aims to provide an accurate representation of the *implemented* schema while also outlining *planned* features. The database uses PostgreSQL with the TimescaleDB extension.

**Note on Naming**: This document uses the actual database table names following the Django convention (`appname_modelname`).

## 2. Database Overview

- **Database**: PostgreSQL with TimescaleDB extension.
- **Schema**: All tables reside in the `public` schema.
- **Time-Series Data**: `environmental_environmentalreading` and `environmental_weatherdata` are TimescaleDB hypertables partitioned by their respective timestamp columns (`reading_time`, `timestamp`). Automatic compression enabled after 7 days with segmentation by container_id/parameter_id and area_id respectively.
- **Audit Trails**: Comprehensive change tracking implemented via django-simple-history for critical models across all major business domains, providing regulatory compliance and operational transparency.
- **Implementation Status**:
  - **Implemented Apps/Domains**: `infrastructure`, `batch`, `inventory`, `health`, `environmental`, `users` (including `auth`), `finance`, `broodstock`, `scenario`, `harvest`.
  - **Planned Apps/Domains**: Operational Planning, Advanced Analytics.
  - **Removed Components**: Advanced audit analytics functionality (Core app) was removed to prioritize system stability and core operational features.

## 3. Audit Trail Implementation

### 3.1 Django Simple History Integration
AquaMind implements comprehensive audit trails using django-simple-history to track changes to critical models for regulatory compliance and operational transparency. The system provides complete Create/Update/Delete (CUD) logging across all major business domains.

#### Tracked Models by App

**Batch App (8 models)**
- **`batch_batch`**: Complete change history for batch lifecycle management
- **`batch_batchcontainerassignment`**: Container assignment changes and biomass updates
- **`batch_growthsample`**: Growth sampling and weight measurements
- **`batch_mortalityevent`**: Mortality tracking and cause documentation
- **`batch_batchtransfer`**: Batch transfers between containers
- **`batch_species`**: Species definition changes
- **`batch_lifecyclestage`**: Lifecycle stage modifications
- **`batch_batchcomposition`**: Batch composition tracking

**Broodstock App (10 models with HistoricalRecords(), 10 historical tables currently active)**
- **`broodstock_batchparentage`**: Egg-to-batch lineage tracking ✓
- **`broodstock_breedingpair`**: Breeding pair assignments and outcomes ✓
- **`broodstock_breedingplan`**: Breeding strategy definitions ✓
- **`broodstock_breedingtraitpriority`**: Trait prioritization for breeding plans ✓
- **`broodstock_broodstockfish`**: Individual broodstock fish records ✓
- **`broodstock_eggproduction`**: Internal/external egg production records ✓
- **`broodstock_eggsupplier`**: External egg supplier information ✓
- **`broodstock_externaleggbatch`**: External egg acquisition details ✓
- **`broodstock_fishmovement`**: Individual fish movements between containers ✓
- **`broodstock_maintenancetask`**: Container maintenance task tracking ✓

**Health App (12 models with HistoricalRecords(), 10 historical tables currently active)**
- **`health_fishparameterscore`**: Health parameter scores for individual fish observations
- **`health_healthlabsample`**: Laboratory sample tracking and results ✓
- **`health_healthparameter`**: Health assessment parameters ✓
- **`health_healthsamplingevent`**: Detailed health sampling sessions ✓
- **`health_individualfishobservation`**: Individual fish health observations ✓
- **`health_journalentry`**: Health observation and treatment entries ✓
- **`health_licecount`**: Lice population monitoring ✓
- **`health_mortalityreason`**: Mortality cause categorization
- **`health_mortalityrecord`**: Health-related mortality documentation ✓
- **`health_sampletype`**: Sample type definitions for lab testing
- **`health_treatment`**: Medical treatment administration ✓
- **`health_vaccinationtype`**: Vaccination type definitions

**Infrastructure App (8 models)**
- **`infrastructure_container`**: Container modifications and status changes
- **`infrastructure_containertype`**: Container type definitions
- **`infrastructure_sensor`**: Sensor configuration and calibration
- **`infrastructure_feedcontainer`**: Feed container management
- **`infrastructure_geography`**: Geographic location definitions
- **`infrastructure_area`**: Operational area configurations
- **`infrastructure_freshwaterstation`**: Freshwater station management
- **`infrastructure_hall`**: Facility hall definitions

**Inventory App (7 models)**
- **`inventory_feed`**: Feed type and specification changes
- **`inventory_feedpurchase`**: Feed procurement and supplier tracking
- **`inventory_feedstock`**: Feed stock level monitoring
- **`inventory_feedingevent`**: Feeding event documentation
- **`inventory_containerfeedingsummary`**: Container-level feeding summaries
- **`inventory_batchfeedingsummary`**: Batch-level feeding and FCR analysis
- **`inventory_feedcontainerstock`**: FIFO inventory tracking

**Operational App (0 models)**
- No operational models currently tracked

**Scenario App (9 models)**
- **`scenario_scenario`**: Scenario planning configurations
- **`scenario_scenariomodelchange`**: Mid-scenario model adjustments
- **`scenario_scenarioprojection`**: Daily projection calculations
- **`scenario_temperatureprofile`**: Temperature profile definitions
- **`scenario_temperaturereading`**: Temperature data points
- **`scenario_tgcmodel`**: Thermal Growth Coefficient models
- **`scenario_fcrmodel`**: Feed Conversion Ratio models
- **`scenario_fcrmodelstage`**: Stage-specific FCR values
- **`scenario_mortalitymodel`**: Mortality rate models

**Environmental App (0 models)**
- Environmental readings use TimescaleDB hypertables but are excluded from audit trails

**Harvest App (3 models)**
- **`harvest_harvestevent`**: Harvest event tracking and documentation
- **`harvest_harvestlot`**: Individual harvest lot management
- **`harvest_harvestwaste`**: Harvest waste tracking

**Users App (2 models)**
- **`auth_user`**: User account changes
- **`users_userprofile`**: User profile modifications

#### Historical Tables (57 Total - All currently active)
All historical tables follow the naming convention `{app}_historical{model}` and include:
- Complete field-level change tracking
- User attribution (`history_user_id`)
- Timestamp tracking (`history_date`)
- Change type indication (`history_type`: +, ~, -)
- Optional change reason (`history_change_reason`)

**API Endpoints**: Each tracked model provides dedicated history endpoints:
- `GET /api/v1/{app}/history/{model}/` - List model history
- `GET /api/v1/{app}/history/{model}/{id}/` - Retrieve specific historical record

#### Features
- **Automatic Tracking**: All CUD operations automatically recorded
- **User Attribution**: Changes linked to authenticated user
- **Timestamp Precision**: Microsecond-level change tracking
- **Admin Integration**: Historical records viewable through Django admin
- **API Access**: RESTful history endpoints with filtering and pagination
- **OpenAPI Documentation**: Complete schema generation with zero Spectacular warnings
- **Frontend Integration**: Generated TypeScript clients with clean method names

#### Benefits
- **Regulatory Compliance**: Complete audit trail for Faroese and Scottish regulations
- **Operational Transparency**: Full visibility into all system changes
- **Data Recovery**: Historical state reconstruction capabilities
- **Change Analysis**: Pattern recognition and trend analysis
- **Debugging Support**: Complete operational history for troubleshooting
- **Contract-First Development**: Clean OpenAPI schema enables optimal frontend integration

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

#### Historical Tables (Audit Trail)
All infrastructure models implement django-simple-history for comprehensive change tracking and regulatory compliance. Each model creates a corresponding historical table following the naming convention `{app}_historical{model}`.

- **`infrastructure_historicalgeography`**
  - Mirrors `infrastructure_geography` plus history tracking fields
  - `history_id`: integer (PK, auto-increment)
  - `history_date`: timestamptz (timestamp of change)
  - `history_change_reason`: varchar (optional reason for change, nullable)
  - `history_type`: varchar (+, ~, - for create/update/delete)
  - `history_user_id`: integer (FK to user who made change, nullable)

- **`infrastructure_historicalarea`**
  - Mirrors `infrastructure_area` plus history tracking fields
  - Same history fields as above

- **`infrastructure_historicalfreshwaterstation`**
  - Mirrors `infrastructure_freshwaterstation` plus history tracking fields
  - Same history fields as above

- **`infrastructure_historicalhall`**
  - Mirrors `infrastructure_hall` plus history tracking fields
  - Same history fields as above

- **`infrastructure_historicalcontainertype`**
  - Mirrors `infrastructure_containertype` plus history tracking fields
  - Same history fields as above

- **`infrastructure_historicalcontainer`**
  - Mirrors `infrastructure_container` plus history tracking fields
  - Same history fields as above

- **`infrastructure_historicalsensor`**
  - Mirrors `infrastructure_sensor` plus history tracking fields
  - Same history fields as above

- **`infrastructure_historicalfeedcontainer`**
  - Mirrors `infrastructure_feedcontainer` plus history tracking fields
  - Same history fields as above

#### Relationships (Inferred `on_delete` where script failed)
- `infrastructure_geography` ← `infrastructure_area` (PROTECT)
- `infrastructure_geography` ← `infrastructure_freshwaterstation` (PROTECT)
- `infrastructure_freshwaterstation` ← `infrastructure_hall` (CASCADE)
- `infrastructure_hall` ← `infrastructure_container` (CASCADE)
- `infrastructure_area` ← `infrastructure_container` (CASCADE)
- `infrastructure_containertype` ← `infrastructure_container` (PROTECT)
- `infrastructure_container` ← `infrastructure_sensor` (CASCADE)
- `infrastructure_hall` ← `infrastructure_feedcontainer` (CASCADE)
- `infrastructure_area` ← `infrastructure_feedcontainer` (CASCADE)
- `infrastructure_container` ← `broodstock_maintenancetask` (CASCADE, related_name='maintenance_tasks')
- `infrastructure_container` ← `broodstock_broodstockfish` (PROTECT, related_name='broodstock_fish')
- `infrastructure_container` ← `broodstock_fishmovement` (PROTECT, from_container, related_name='fish_movements_from')
- `infrastructure_container` ← `broodstock_fishmovement` (PROTECT, to_container, related_name='fish_movements_to')
- `infrastructure_freshwaterstation` ← `broodstock_eggproduction` (SET_NULL, related_name='egg_productions')

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
  - `last_weighing_date`: date (nullable) # Date of most recent growth sample for FCR confidence calculation
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

#### Historical Tables (Audit Trail)
All batch models with `history = HistoricalRecords()` create corresponding historical tables following the django-simple-history naming convention `{app}_historical{model}`. These tables track complete change history for regulatory compliance and operational transparency.

- **`batch_historicalbatch`**
  - All fields from `batch_batch` plus history tracking fields
  - `history_id`: integer (PK, auto-increment)
  - `history_date`: timestamptz (timestamp of change)
  - `history_change_reason`: varchar (optional reason for change)
  - `history_type`: varchar (+, ~, - for create/update/delete)
  - `history_user_id`: integer (FK to user who made change)
- **`batch_historicalbatchcontainerassignment`**
  - All fields from `batch_batchcontainerassignment` plus history tracking fields
  - Same history fields as above
- **`batch_historicalbatchtransfer`**
  - All fields from `batch_batchtransfer` plus history tracking fields
  - Same history fields as above
- **`batch_historicalgrowthsample`**
  - All fields from `batch_growthsample` plus history tracking fields
  - Same history fields as above
- **`batch_historicalmortalityevent`**
  - All fields from `batch_mortalityevent` plus history tracking fields
  - Same history fields as above
- **`batch_historicalbatchcomposition`** (Note: Table creation pending - model has `history = HistoricalRecords()` but migration may not have run)

#### Relationships (Inferred `on_delete` where script failed)
- `batch_species` ← `batch_batch` (PROTECT)
- `batch_lifecyclestage` ← `batch_batch` (PROTECT, for `lifecycle_stage_id`)
- `batch_batch` ← `batch_batchcontainerassignment` (CASCADE)
- `infrastructure_container` ← `batch_batchcontainerassignment` (PROTECT)
- `batch_lifecyclestage` ← `batch_batchcontainerassignment` (PROTECT)
- `batch_batch` ← `batch_batchcomposition` (CASCADE, both FKs)
- `batch_batch` ← `batch_batchtransfer` (PROTECT, source_batch and destination_batch FKs)
- `batch_batchcontainerassignment` ← `batch_batchtransfer` (PROTECT, source_assignment and destination_assignment FKs)
- `batch_lifecyclestage` ← `batch_batchtransfer` (PROTECT, source_lifecycle_stage and destination_lifecycle_stage FKs)
- `batch_batch` ← `batch_mortalityevent` (PROTECT)
- `batch_batchcontainerassignment` ← `batch_growthsample` (CASCADE)
- `batch_batch` ← `broodstock_batchparentage` (CASCADE, related_name='parentage')

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
- **`inventory_containerfeedingsummary`** (New Table - Container-Level FCR)
  - `id`: bigint (PK, auto-increment)
  - `batch_id`: bigint (FK to `batch_batch`.`id`, on_delete=CASCADE, related_name='container_feeding_summaries')
  - `container_assignment_id`: bigint (FK to `batch_batchcontainerassignment`.`id`, on_delete=CASCADE, related_name='feeding_summaries')
  - `period_start`: date
  - `period_end`: date
  - `total_feed_kg`: decimal(10,3) (validators: MinValueValidator(0), help_text="Total feed provided to this container in this period (kg)")
  - `starting_biomass_kg`: decimal(10,2) (nullable, blank=True, help_text="Starting biomass for this container at period start")
  - `ending_biomass_kg`: decimal(10,2) (nullable, blank=True, help_text="Ending biomass for this container at period end")
  - `growth_kg`: decimal(8,2) (nullable, blank=True, help_text="Biomass growth for this container during the period")
  - `fcr`: decimal(5,3) (nullable, blank=True, help_text="Feed Conversion Ratio for this container")
  - `confidence_level`: varchar(20) (nullable, blank=True, choices=['VERY_HIGH', 'HIGH', 'MEDIUM', 'LOW'], help_text="Confidence level for this container's FCR")
  - `estimation_method`: varchar(20) (nullable, blank=True, choices=['MEASURED', 'INTERPOLATED', 'MIXED'], help_text="Method used for FCR estimation")
  - `data_points`: integer (default=0, help_text="Number of data points used in calculation")
  - `created_at`: timestamptz (auto_now_add=True)
  - `updated_at`: timestamptz (auto_now=True)
  - Meta: `unique_together = ['container_assignment', 'period_start', 'period_end']`, `ordering = ['container_assignment', '-period_end']`
  - **Note**: Container-level FCR calculations that feed into batch-level aggregations
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
  - `weighted_avg_fcr`: decimal(5,3) (nullable, blank=True, help_text="Weighted average FCR across all containers in the batch")
  - `total_starting_biomass_kg`: decimal(12,2) (nullable, blank=True, help_text="Total starting biomass for all containers in batch")
  - `total_ending_biomass_kg`: decimal(12,2) (nullable, blank=True, help_text="Total ending biomass for all containers in batch")
  - `container_count`: integer (default=0, help_text="Number of active containers in the batch during this period")
  - `overall_confidence_level`: varchar(20) (nullable, blank=True, choices=['VERY_HIGH', 'HIGH', 'MEDIUM', 'LOW'], help_text="Overall confidence level for FCR calculation")
  - `estimation_method`: varchar(20) (nullable, blank=True, choices=['MEASURED', 'INTERPOLATED', 'MIXED'], help_text="Method used for FCR estimation")
  - `fcr`: decimal(5,3) (nullable, blank=True, help_text="Feed Conversion Ratio (total_feed_consumed_kg / total_biomass_gain_kg) - legacy field")
  - `created_at`: timestamptz (auto_now_add=True)
  - `updated_at`: timestamptz (auto_now=True)
  - Meta: `ordering = ['batch', '-period_end']`, `verbose_name_plural = "Batch feeding summaries"`, `unique_together = ['batch', 'period_start', 'period_end']`
  - **Note**: Updated to support container-first FCR calculations with weighted averages and confidence levels.

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
- `batch_batch` ← `inventory_containerfeedingsummary` (CASCADE, related_name='container_feeding_summaries')
- `batch_batchcontainerassignment` ← `inventory_containerfeedingsummary` (CASCADE, related_name='feeding_summaries')

#### Historical Tables (Audit Trail)
All inventory models with `history = HistoricalRecords()` create corresponding historical tables following the django-simple-history naming convention `{app}_historical{model}`. These tables track complete change history for regulatory compliance and operational transparency.

**Currently Active Historical Tables (7 total):**
- **`inventory_historicalfeed`**
  - All fields from `inventory_feed` plus history tracking fields
  - `history_id`: integer (PK, auto-increment)
  - `history_date`: timestamptz (timestamp of change)
  - `history_change_reason`: varchar (optional reason for change, nullable)
  - `history_type`: varchar (+, ~, - for create/update/delete)
  - `history_user_id`: integer (FK to user who made change, nullable)
- **`inventory_historicalfeedpurchase`**
  - All fields from `inventory_feedpurchase` plus history tracking fields
  - Same history fields as above
- **`inventory_historicalfeedstock`**
  - All fields from `inventory_feedstock` plus history tracking fields
  - Same history fields as above
- **`inventory_historicalfeedingevent`**
  - All fields from `inventory_feedingevent` plus history tracking fields
  - Same history fields as above
- **`inventory_historicalfeedcontainerstock`**
  - All fields from `inventory_feedcontainerstock` plus history tracking fields
  - Same history fields as above
- **`inventory_historicalcontainerfeedingsummary`**
  - All fields from `inventory_containerfeedingsummary` plus history tracking fields
  - Same history fields as above
- **`inventory_historicalbatchfeedingsummary`**
  - All fields from `inventory_batchfeedingsummary` plus history tracking fields
  - Same history fields as above

### 4.4 Health Monitoring (`health` app)
**Purpose**: Tracks health observations, treatments, mortality, sampling events, and lab results.

#### Tables
- **`health_sampletype`**
  - `id`: bigint (PK, auto-increment)
  - `name`: varchar(100) (Unique)
  - `description`: text (blank=True)
- **`health_mortalityreason`**
  - `id`: bigint (PK, auto-increment)
  - `name`: varchar(100) (Unique)
  - `description`: text (blank=True)
- **`health_journalentry`**
  - id: bigint (PK, auto-increment)
  - `batch_id`: bigint (FK to `batch_batch`.id, on_delete=CASCADE, related_name='journal_entries')
  - `container_id`: bigint (FK to `infrastructure_container`.id, on_delete=SET_NULL, nullable, blank=True, related_name='journal_entries')
  - `user_id`: integer (FK to `users_customuser`.id, on_delete=PROTECT, related_name='journal_entries')
  - `entry_date`: timestamptz (default=timezone.now)
  - `category`: varchar(20) (Choices: 'observation', 'issue', 'action', 'diagnosis', 'treatment', 'vaccination', 'sample')
  - `severity`: varchar(10) (Choices: 'low', 'medium', 'high', default='low', nullable, blank=True)
  - `description`: text
  - `resolution_status`: boolean (default=False)
  - `resolution_notes`: text (NOT NULL)
  - `created_at`: timestamptz (auto_now_add=True)
  - `updated_at`: timestamptz (auto_now=True)
  - Meta: `verbose_name_plural = "Journal Entries"`, `ordering = ['-entry_date']`
- **`health_healthparameter`**
  - id: bigint (PK, auto-increment)
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
  - id: bigint (PK, auto-increment)
  - `assignment_id`: bigint (FK to `batch_batchcontainerassignment`.id, on_delete=CASCADE, related_name='health_sampling_events')
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
  - `sampled_by_id`: integer (FK to `users_customuser`.id, on_delete=SET_NULL, nullable, blank=True, related_name='health_sampling_events_conducted')
  - `notes`: text (blank=True, nullable)
  - `created_at`: timestamptz (auto_now_add=True)
  - `updated_at`: timestamptz (auto_now=True)
  - Meta: `ordering = ['-sampling_date', '-created_at']`, `verbose_name = "Health Sampling Event"`
- **`health_individualfishobservation`**
  - id: bigint (PK, auto-increment)
  - `sampling_event_id`: bigint (FK to `health_healthsamplingevent`.id, on_delete=CASCADE, related_name='individual_fish_observations')
  - `fish_identifier`: varchar(50) (help_text="Identifier for the specific fish (e.g., tag number or sequential ID).")
  - `length_cm`: decimal(10,2) (nullable, blank=True, help_text="Length of the fish in centimeters.")
  - `weight_g`: decimal(10,2) (nullable, blank=True, help_text="Weight of the fish in grams.")
  - `created_at`: timestamptz (auto_now_add=True)
  - `updated_at`: timestamptz (auto_now=True)
  - Meta: `unique_together = ('sampling_event', 'fish_identifier')`, `ordering = ['sampling_event', 'fish_identifier']`, `verbose_name = "Individual Fish Observation", `verbose_name_plural = "Individual Fish Observations"`
- **`health_fishparameterscore`**
  - id: bigint (PK, auto-increment)
  - `individual_fish_observation_id`: bigint (FK to `health_individualfishobservation`.id, on_delete=CASCADE, related_name='parameter_scores')
  - `parameter_id`: bigint (FK to `health_healthparameter`.id, on_delete=PROTECT, related_name='fish_scores')
  - `score`: smallint (validators: MinValueValidator(1), MaxValueValidator(5), help_text="Score from 1 (best) to 5 (worst).")
  - `created_at`: timestamptz (auto_now_add=True)
  - `updated_at`: timestamptz (auto_now=True)
  - Meta: `unique_together = ('individual_fish_observation', 'parameter')`, `ordering = ['individual_fish_observation', 'parameter']`, `verbose_name = "Fish Parameter Score", `verbose_name_plural = "Fish Parameter Scores"`
- **`health_mortalityreason`**
  - id: bigint (PK, auto-increment)
  - `name`: varchar(100) (Unique)
  - `description`: text (blank=True)
  - Meta: `verbose_name_plural = "Mortality Reasons"`, `ordering = ['name']`
- **`health_mortalityrecord`**
  - id: bigint (PK, auto-increment)
  - `batch_id`: bigint (FK to `batch_batch`.id, on_delete=CASCADE, related_name='mortality_records')
  - `container_id`: bigint (FK to `infrastructure_container`.id, on_delete=CASCADE, related_name='mortality_records', nullable, blank=True)
  - `event_date`: timestamptz
  - `count`: positive integer
  - `reason_id`: bigint (FK to `health_mortalityreason`.id, on_delete=SET_NULL, nullable, related_name='mortality_records')
  - `notes`: text (NOT NULL)
  - Meta: `verbose_name_plural = "Mortality Records"`, `ordering = ['-event_date']`
- **`health_licecount`**
  - id: bigint (PK, auto-increment)
  - `batch_id`: bigint (FK to `batch_batch`.id, on_delete=CASCADE, related_name='lice_counts')
  - `container_id`: bigint (FK to `infrastructure_container`.id, on_delete=CASCADE, related_name='lice_counts', nullable, blank=True)
  - `user_id`: integer (FK to `users_customuser`.id, on_delete=SET_NULL, nullable, related_name='lice_counts')
  - `count_date`: timestamptz (auto_now_add=True)
  - `adult_female_count`: positive integer (default=0)
  - `adult_male_count`: positive integer (default=0)
  - `juvenile_count`: positive integer (default=0)
  - `fish_sampled`: positive integer (default=1)
  - `notes`: text (NOT NULL)
  - Meta: `verbose_name_plural = "Lice Counts"`, `ordering = ['-count_date']`
- **`health_vaccinationtype`**
  - id: bigint (PK, auto-increment)
  - `name`: varchar(100) (Unique)
  - `manufacturer`: varchar(100) (blank=True)
  - `dosage`: varchar(50) (blank=True)
  - `description`: text (blank=True)
  - Meta: `verbose_name_plural = "Vaccination Types"`, `ordering = ['name']`
- **`health_treatment`**
  - id: bigint (PK, auto-increment)
  - `batch_id`: bigint (FK to `batch_batch`.id, on_delete=CASCADE, related_name='treatments')
  - `container_id`: bigint (FK to `infrastructure_container`.id, on_delete=CASCADE, related_name='treatments', nullable, blank=True)
  - `batch_assignment_id`: bigint (FK to `batch_batchcontainerassignment`.id, on_delete=CASCADE, related_name='treatments', nullable, blank=True)
  - `user_id`: integer (FK to `users_customuser`.id, on_delete=SET_NULL, nullable, related_name='treatments')
  - `treatment_date`: timestamptz (auto_now_add=True)
  - `treatment_type`: varchar(20) (Choices: 'medication', 'vaccination', 'delicing', 'other', default='medication')
  - `vaccination_type_id`: bigint (FK to `health_vaccinationtype`.id, on_delete=SET_NULL, nullable, blank=True, related_name='treatments')
  - `description`: text
  - `dosage`: varchar(100) (blank=True)
  - `duration_days`: positive integer (default=0)
  - `withholding_period_days`: positive integer (default=0, help_text="Days before fish can be harvested...")
  - `outcome`: text (blank=True)
  - Meta: `verbose_name_plural = "Treatments"`, `ordering = ['-treatment_date']`
- **`health_sampletype`**
  - id: bigint (PK, auto-increment)
  - `name`: varchar(100) (Unique)
  - `description`: text (blank=True)
  - Meta: `verbose_name_plural = "Sample Types"`
- **`health_healthlabsample`**
  - id: bigint (PK, auto-increment)
  - `batch_container_assignment_id`: bigint (FK to `batch_batchcontainerassignment`.id, on_delete=PROTECT, related_name='lab_samples')
  - `sample_type_id`: bigint (FK to `health_sampletype`.id, on_delete=PROTECT, related_name='lab_samples')
  - `sample_date`: date (help_text="Date the sample was physically taken.")
  - `date_sent_to_lab`: date (nullable, blank=True)
  - `date_results_received`: date (nullable, blank=True)
  - `lab_reference_id`: varchar(100) (nullable, blank=True)
  - `findings_summary`: text (nullable, blank=True)
  - `quantitative_results`: jsonb (nullable, blank=True, help_text="Structured quantitative results...")
  - attachment: file (upload_to='health/lab_samples/%Y/%m/', nullable, blank=True)
  - `notes`: text (nullable, blank=True)
  - `recorded_by_id`: integer (FK to `users_customuser`.id, on_delete=SET_NULL, nullable, blank=True, related_name='recorded_lab_samples')
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
- `health_mortalityreason` ← `health_mortalityrecord` (PROTECT, related_name='mortality_records')
- `batch_batch` ← `health_mortalityrecord` (CASCADE, related_name='mortality_records')
- `infrastructure_container` ← `health_mortalityrecord` (CASCADE, related_name='mortality_records')
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

#### Historical Tables (Audit Trail)
All health models with `history = HistoricalRecords()` create corresponding historical tables following the django-simple-history naming convention `{app}_historical{model}`. These tables track complete change history for regulatory compliance and operational transparency.

**Currently Active Historical Tables (All 10):**
- **`health_historicalfishparameterscore`**
  - All fields from `health_fishparameterscore` plus history tracking fields
  - `history_id`: integer (PK, auto-increment)
  - `history_date`: timestamptz (timestamp of change)
  - `history_change_reason`: varchar (optional reason for change, nullable)
  - `history_type`: varchar (+, ~, - for create/update/delete)
  - `history_user_id`: integer (FK to user who made change, nullable)
- **`health_historicalhealthlabsample`**
  - All fields from `health_healthlabsample` plus history tracking fields
  - Same history fields as above
- **`health_historicalhealthparameter`**
  - All fields from `health_healthparameter` plus history tracking fields
  - Same history fields as above
- **`health_historicalhealthsamplingevent`**
  - All fields from `health_healthsamplingevent` plus history tracking fields
  - Same history fields as above
- **`health_historicalindividualfishobservation`**
  - All fields from `health_individualfishobservation` plus history tracking fields
  - Same history fields as above
- **`health_historicaljournalentry`**
  - All fields from `health_journalentry` plus history tracking fields
  - Same history fields as above
- **`health_historicallicecount`**
  - All fields from `health_licecount` plus history tracking fields
  - Same history fields as above
- **`health_historicalmortalityrecord`**
  - All fields from `health_mortalityrecord` plus history tracking fields
  - Same history fields as above
- **`health_historicaltreatment`**
  - All fields from `health_treatment` plus history tracking fields
  - Same history fields as above

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

### 4.6 Finance Management (`finance` app)
**Purpose**: To track financial transactions, harvest events, and intercompany policies for regulatory compliance and operational reporting.

#### Tables
- **`finance_dimcompany`**
  - `company_id`: bigint (PK, auto-increment)
  - `geography_id`: bigint (FK to `infrastructure_geography`, on_delete=PROTECT, related_name='finance_companies')
  - `subsidiary`: varchar(3) (choices from Subsidiary enum)
  - `display_name`: varchar(100)
  - `currency`: varchar(3) (nullable)
  - `nav_company_code`: varchar(50) (nullable)
- **`finance_dimsite`**
  - `site_id`: bigint (PK, auto-increment)
  - `source_model`: varchar(16) (choices: 'STATION', 'AREA')
  - `source_pk`: integer (positive integer)
  - `company_id`: bigint (FK to `finance_dimcompany`, on_delete=PROTECT, related_name='sites')
  - `site_name`: varchar(100)
- **`finance_factharvest`**
  - `fact_id`: bigint (PK, auto-increment)
  - `event_date`: timestamptz
  - `quantity_kg`: numeric(12,3)
  - `unit_count`: integer
  - `dim_batch_id`: integer
  - `dim_company_id`: bigint (FK to `finance_dimcompany`, on_delete=PROTECT)
  - `dim_site_id`: bigint (FK to `finance_dimsite`, on_delete=PROTECT)
  - `event_id`: bigint (FK to `harvest_harvestevent`, on_delete=PROTECT)
  - `lot_id`: bigint (FK to `harvest_harvestlot`, on_delete=PROTECT, unique=True)
  - `product_grade_id`: bigint (FK to `harvest_productgrade`, on_delete=PROTECT)
  - `created_at`: timestamptz
  - `updated_at`: timestamptz
- **`finance_intercompanypolicy`**
  - `policy_id`: bigint (PK, auto-increment)
  - `method`: varchar(20)
  - `markup_percent`: numeric(6,3) (nullable)
  - `from_company_id`: bigint (FK to `finance_dimcompany`, on_delete=PROTECT)
  - `to_company_id`: bigint (FK to `finance_dimcompany`, on_delete=PROTECT)
  - `product_grade_id`: bigint (FK to `harvest_productgrade`, on_delete=PROTECT)
  - `created_at`: timestamptz
  - `updated_at`: timestamptz
- **`finance_intercompanytransaction`**
  - `tx_id`: bigint (PK, auto-increment)
  - `posting_date`: date
  - `amount`: numeric(14,2) (nullable)
  - `currency`: varchar(3) (nullable)
  - `state`: varchar(20)
  - `event_id`: bigint (FK to `harvest_harvestevent`, on_delete=PROTECT)
  - `policy_id`: bigint (FK to `finance_intercompanypolicy`, on_delete=PROTECT)
  - `created_at`: timestamptz
  - `updated_at`: timestamptz
- **`finance_navexportbatch`**
  - `batch_id`: bigint (PK, auto-increment)
  - `date_from`: date
  - `date_to`: date
  - `posting_date`: date
  - `currency`: varchar(3) (nullable)
  - `state`: varchar(20)
  - `company_id`: bigint (FK to `finance_dimcompany`, on_delete=PROTECT)
  - `created_at`: timestamptz
  - `updated_at`: timestamptz
- **`finance_navexportline`**
  - `line_id`: bigint (PK, auto-increment)
  - `document_no`: varchar(32)
  - `account_no`: varchar(50)
  - `balancing_account_no`: varchar(50)
  - `amount`: numeric(14,2)
  - `description`: varchar(255)
  - `batch_id_int`: integer
  - `batch_id`: bigint (FK to `finance_navexportbatch`, on_delete=CASCADE)
  - `dim_company_id`: bigint (FK to `finance_dimcompany`, on_delete=PROTECT)
  - `dim_site_id`: bigint (FK to `finance_dimsite`, on_delete=PROTECT)
  - `product_grade_id`: bigint (FK to `harvest_productgrade`, on_delete=PROTECT)
  - `transaction_id`: bigint (FK to `finance_intercompanytransaction`, on_delete=PROTECT)
  - `created_at`: timestamptz
  - `updated_at`: timestamptz

#### Historical Tables (Audit Trail)
**5 of 7 finance models** are tracked with django-simple-history for regulatory compliance and operational transparency. Historical tables follow the naming convention `{app}_historical{model}` and include standard audit fields.

**Tracked Models (5 total):**
- **`finance_factharvest`** → `finance_historicalfactharvest`
- **`finance_intercompanypolicy`** → `finance_historicalintercompanypolicy`
- **`finance_intercompanytransaction`** → `finance_historicalintercompanytransaction`
- **`finance_navexportbatch`** → `finance_historicalnavexportbatch`
- **`finance_navexportline`** → `finance_historicalnavexportline`

**Non-tracked Models (2 total):**
- `finance_dimcompany` (dimension table, changes infrequent)
- `finance_dimsite` (dimension table, changes infrequent)

**Historical Table Structure** (all historical tables):
- `history_id`: integer (PK, auto-increment)
- `history_date`: timestamptz (timestamp of change)
- `history_change_reason`: varchar (optional reason for change, nullable)
- `history_type`: varchar (+, ~, - for create/update/delete)
- `history_user_id`: integer (FK to `auth_user`, nullable)
- *Plus all fields from the original model*

#### BI Views
- **`vw_fact_harvest`** (Business Intelligence View)
  - **Purpose**: Combines harvest facts with product grades, companies, and sites for reporting and analytics
  - **Columns**:
    - `fact_id`: bigint (references `finance_factharvest.fact_id`)
    - `event_date`: timestamptz (harvest event timestamp)
    - `quantity_kg`: numeric (harvest quantity in kilograms)
    - `unit_count`: integer (number of individual units harvested)
    - `product_grade_code`: varchar (product grade code from harvest system)
    - `company`: varchar (company display name)
    - `site_name`: varchar (operational site name)
    - `batch_id`: integer (batch identifier for traceability)
- **`vw_intercompany_transactions`** (Business Intelligence View)
  - **Purpose**: Provides intercompany transaction details with company and product information for financial reporting
  - **Columns**:
    - `tx_id`: bigint (references `finance_intercompanytransaction.tx_id`)
    - `posting_date`: date (accounting posting date)
    - `state`: varchar (transaction state: 'pending', 'exported', 'posted')
    - `from_company`: varchar (source company display name)
    - `to_company`: varchar (destination company display name)
    - `product_grade_code`: varchar (product grade code)
    - `amount`: numeric (transaction amount)
    - `currency`: varchar (currency code, 3 characters)

#### Relationships
**Dimension Tables:**
- `infrastructure_geography` ← `finance_dimcompany` (PROTECT, related_name='finance_companies')
- `finance_dimcompany` ← `finance_dimsite` (PROTECT, related_name='sites')

**Fact Tables:**
- `finance_dimcompany` ← `finance_factharvest` (PROTECT, related_name='fact_harvests')
- `finance_dimsite` ← `finance_factharvest` (PROTECT, related_name='fact_harvests')
- `harvest_harvestevent` ← `finance_factharvest` (PROTECT, related_name='finance_facts')
- `harvest_harvestlot` ← `finance_factharvest` (PROTECT, related_name='finance_fact', unique=True)
- `harvest_productgrade` ← `finance_factharvest` (PROTECT, related_name='finance_facts')

**Intercompany Policies:**
- `finance_dimcompany` ← `finance_intercompanypolicy` (PROTECT, from_company, related_name='policies_outbound')
- `finance_dimcompany` ← `finance_intercompanypolicy` (PROTECT, to_company, related_name='policies_inbound')
- `harvest_productgrade` ← `finance_intercompanypolicy` (PROTECT, related_name='intercompany_policies')

**Intercompany Transactions:**
- `harvest_harvestevent` ← `finance_intercompanytransaction` (PROTECT, related_name='intercompany_transactions')
- `finance_intercompanypolicy` ← `finance_intercompanytransaction` (PROTECT, related_name='transactions')

**NAV Export System:**
- `finance_dimcompany` ← `finance_navexportbatch` (PROTECT, related_name='nav_export_batches')
- `finance_navexportbatch` ← `finance_navexportline` (CASCADE, related_name='lines')
- `finance_dimcompany` ← `finance_navexportline` (PROTECT, related_name='nav_export_lines')
- `finance_dimsite` ← `finance_navexportline` (PROTECT, related_name='nav_export_lines')
- `harvest_productgrade` ← `finance_navexportline` (PROTECT, related_name='nav_export_lines')
- `finance_intercompanytransaction` ← `finance_navexportline` (PROTECT, related_name='nav_export_lines')

**Historical Table Relationships:**
- `auth_user` ← `finance_historicalfactharvest` (SET_NULL, history_user_id)
- `auth_user` ← `finance_historicalintercompanypolicy` (SET_NULL, history_user_id)
- `auth_user` ← `finance_historicalintercompanytransaction` (SET_NULL, history_user_id)
- `auth_user` ← `finance_historicalnavexportbatch` (SET_NULL, history_user_id)
- `auth_user` ← `finance_historicalnavexportline` (SET_NULL, history_user_id)

### 4.7 User Management (`auth` and `users` apps)
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
- `auth_user` ← `broodstock_maintenancetask` (SET_NULL, created_by, related_name='created_maintenance_tasks')
- `auth_user` ← `broodstock_breedingplan` (SET_NULL, created_by, related_name='breeding_plans')
- `auth_user` ← `broodstock_fishmovement` (SET_NULL, moved_by, related_name='fish_movements')
- `auth_user` ← `health_journalentry` (PROTECT, user, related_name='journal_entries')
- `auth_user` ← `health_healthsamplingevent` (SET_NULL, sampled_by, related_name='health_sampling_events_conducted')
- `auth_user` ← `health_licecount` (SET_NULL, user, related_name='lice_counts')
- `auth_user` ← `health_treatment` (SET_NULL, user, related_name='treatments')
- `auth_user` ← `health_healthlabsample` (SET_NULL, recorded_by, related_name='recorded_lab_samples')
- `auth_user` ← `inventory_feedingevent` (PROTECT, recorded_by, related_name='feeding_entries')
- `auth_user` ← `environmental_environmentalreading` (SET_NULL, recorded_by)
- `auth_user` ← `scenario_scenario` (PROTECT, created_by)

#### Historical Tables (Audit Trail)
All user models with `history = HistoricalRecords()` create corresponding historical tables following the django-simple-history naming convention `{app}_historical{model}`. These tables track complete change history for regulatory compliance and operational transparency.

**Currently Active Historical Tables (2 total):**
- **`auth_historicaluser`**
  - All fields from `auth_user` plus history tracking fields
  - `history_id`: integer (PK, auto-increment)
  - `history_date`: timestamptz (timestamp of change)
  - `history_change_reason`: varchar (optional reason for change, nullable)
  - `history_type`: varchar (+, ~, - for create/update/delete)
  - `history_user_id`: integer (FK to user who made change, nullable)
- **`users_historicaluserprofile`**
  - All fields from `users_userprofile` plus history tracking fields
  - Same history fields as above

#### 4.8 Broodstock Management (broodstock app - IMPLEMENTED)

The Broodstock Management app provides comprehensive tracking of broodstock fish populations, breeding operations, egg production (both internal and external), and complete traceability from broodstock to harvest batches. It integrates with infrastructure, batch, environmental, and health apps for end-to-end aquaculture lifecycle management.

**Core Entities and Attributes**

- **`broodstock_maintenancetask`**
  - `id`: bigint (PK, auto-increment)
  - `container_id`: bigint (FK to `infrastructure_container`, on_delete=CASCADE, related_name='maintenance_tasks')
  - `task_type`: varchar(50) (choices: 'cleaning', 'repair', 'inspection', 'upgrade')
  - `scheduled_date`: timestamptz
  - `completed_date`: timestamptz (nullable)
  - `notes`: text (blank=True)
  - `created_by_id`: integer (FK to `auth_user`, on_delete=SET_NULL, nullable)
  - `created_at`: timestamptz
  - `updated_at`: timestamptz

- **`broodstock_broodstockfish`**
  - `id`: bigint (PK, auto-increment)
  - `container_id`: bigint (FK to `infrastructure_container`, on_delete=PROTECT, related_name='broodstock_fish')
  - `traits`: jsonb (default={}, blank=True)
  - `health_status`: varchar(20) (choices: 'healthy', 'monitored', 'sick', 'deceased', default='healthy')
  - `created_at`: timestamptz
  - `updated_at`: timestamptz

- **`broodstock_fishmovement`**
  - `id`: bigint (PK, auto-increment)
  - `fish_id`: bigint (FK to `broodstock_broodstockfish`, on_delete=CASCADE, related_name='movements')
  - `from_container_id`: bigint (FK to `infrastructure_container`, on_delete=PROTECT, related_name='fish_movements_from')
  - `to_container_id`: bigint (FK to `infrastructure_container`, on_delete=PROTECT, related_name='fish_movements_to')
  - `movement_date`: timestamptz (db_index=True, default=timezone.now)
  - `moved_by_id`: integer (FK to `auth_user`, on_delete=SET_NULL, nullable)
  - `notes`: text (blank=True)
  - `created_at`: timestamptz
  - `updated_at`: timestamptz

- **`broodstock_breedingplan`**
  - `id`: bigint (PK, auto-increment)
  - `name`: varchar(100)
  - `start_date`: timestamptz
  - `end_date`: timestamptz
  - `objectives`: text (blank=True)
  - `geneticist_notes`: text (blank=True)
  - `breeder_instructions`: text (blank=True)
  - `created_by_id`: integer (FK to `auth_user`, on_delete=SET_NULL, nullable)
  - `created_at`: timestamptz
  - `updated_at`: timestamptz

- **`broodstock_breedingtraitpriority`**
  - `id`: bigint (PK, auto-increment)
  - `plan_id`: bigint (FK to `broodstock_breedingplan`, on_delete=CASCADE, related_name='trait_priorities')
  - `trait_name`: varchar(50) (choices: 'growth_rate', 'disease_resistance', 'size', 'fertility')
  - `priority_weight`: numeric (validators: MinValueValidator(0), MaxValueValidator(1))
  - `created_at`: timestamptz
  - `updated_at`: timestamptz

- **`broodstock_breedingpair`**
  - `id`: bigint (PK, auto-increment)
  - `plan_id`: bigint (FK to `broodstock_breedingplan`, on_delete=CASCADE, related_name='breeding_pairs')
  - `male_fish_id`: bigint (FK to `broodstock_broodstockfish`, on_delete=PROTECT, related_name='breeding_pairs_as_male')
  - `female_fish_id`: bigint (FK to `broodstock_broodstockfish`, on_delete=PROTECT, related_name='breeding_pairs_as_female')
  - `pairing_date`: timestamptz (default=timezone.now)
  - `progeny_count`: integer (nullable)
  - `created_at`: timestamptz
  - `updated_at`: timestamptz

- **`broodstock_eggproduction`**
  - `id`: bigint (PK, auto-increment)
  - `pair_id`: bigint (FK to `broodstock_breedingpair`, on_delete=PROTECT, nullable, related_name='egg_productions')
  - `egg_batch_id`: varchar(50) (unique=True)
  - `egg_count`: integer (validators: MinValueValidator(0))
  - `production_date`: timestamptz (default=timezone.now)
  - `destination_station_id`: bigint (FK to `infrastructure_freshwaterstation`, on_delete=SET_NULL, nullable)
  - `source_type`: varchar(20) (choices: 'internal', 'external')
  - `created_at`: timestamptz
  - `updated_at`: timestamptz

- **`broodstock_eggsupplier`**
  - `id`: bigint (PK, auto-increment)
  - `name`: varchar(100) (unique=True)
  - `contact_details`: text
  - `certifications`: text (blank=True)
  - `created_at`: timestamptz
  - `updated_at`: timestamptz

- **`broodstock_externaleggbatch`**
  - `id`: bigint (PK, auto-increment)
  - `egg_production_id`: bigint (OneToOne to `broodstock_eggproduction`, on_delete=CASCADE, related_name='external_batch')
  - `supplier_id`: bigint (FK to `broodstock_eggsupplier`, on_delete=PROTECT, related_name='egg_batches')
  - `batch_number`: varchar(50)
  - `provenance_data`: text (blank=True)
  - `created_at`: timestamptz
  - `updated_at`: timestamptz

- **`broodstock_batchparentage`**
  - `batch_id`: bigint (FK to `batch_batch`, on_delete=CASCADE, related_name='parentage')
  - `egg_production_id`: bigint (FK to `broodstock_eggproduction`, on_delete=PROTECT, related_name='batch_assignments')
  - `assignment_date`: timestamptz (default=timezone.now)
  - `created_at`: timestamptz
  - `updated_at`: timestamptz
  - Meta: unique_together = ['batch', 'egg_production']

**Historical Tables (Audit Trail)**
All broodstock models with `history = HistoricalRecords()` create corresponding historical tables following the django-simple-history naming convention `{app}_historical{model}`. These tables track complete change history for regulatory compliance and operational transparency.

**Currently Active Historical Tables (All 10):**
- **`broodstock_historicalbatchparentage`**
- **`broodstock_historicalbreedingpair`**
- **`broodstock_historicalbreedingplan`**
- **`broodstock_historicalbreedingtraitpriority`**
- **`broodstock_historicalbroodstockfish`**
- **`broodstock_historicaleggproduction`**
- **`broodstock_historicaleggsupplier`**
- **`broodstock_historicalexternaleggbatch`**
- **`broodstock_historicalfishmovement`**
- **`broodstock_historicalmaintenancetask`**

**Additional Considerations**
- **Regulatory Compliance**: Complete audit trail from broodstock selection through harvest for Faroese and Scottish salmon regulations
- **Health Integration**: `BroodstockFish.health_status` integrates with `health_journalentry` for comprehensive health tracking
- **Scalability**: Supports 10,000+ broodstock fish with efficient indexing on container and fish relationships
- **Validation**: Strict validation ensures internal eggs have breeding pairs, external eggs do not
- **Traceability**: End-to-end traceability from individual broodstock fish through egg production to harvest batches

#### 4.9 Harvest Management (harvest app - IMPLEMENTED)

The Harvest Management app's data model supports comprehensive tracking of harvest operations, from batch harvesting through processing and waste management. It provides regulatory compliance through complete traceability from batch to final product, with detailed weight tracking and quality grading.

**Core Entities and Attributes**

- **`harvest_harvestevent`** (Harvest Event Tracking)
  - `id`: bigint (PK, auto-increment)
  - `event_date`: timestamptz (db_index=True)
  - `assignment_id`: bigint (FK to `batch_batchcontainerassignment`, on_delete=PROTECT)
  - `batch_id`: bigint (FK to `batch_batch`, on_delete=PROTECT)
  - `dest_geography_id`: bigint (FK to `infrastructure_geography`, on_delete=PROTECT, nullable)
  - `dest_subsidiary`: varchar(3) (choices from Subsidiary enum, nullable)
  - `document_ref`: varchar(100)
  - `created_at`: timestamptz (auto_now_add=True)
  - `updated_at`: timestamptz (auto_now=True)

- **`harvest_harvestlot`** (Individual Lot Management)
  - `id`: bigint (PK, auto-increment)
  - `event_id`: bigint (FK to `harvest_harvestevent`, on_delete=CASCADE)
  - `product_grade_id`: bigint (FK to `harvest_productgrade`, on_delete=PROTECT)
  - `live_weight_kg`: numeric(12,3) (validators: MinValueValidator(0))
  - `gutted_weight_kg`: numeric(12,3) (nullable, validators: MinValueValidator(0))
  - `fillet_weight_kg`: numeric(12,3) (nullable, validators: MinValueValidator(0))
  - `unit_count`: integer (positive integer)
  - `created_at`: timestamptz (auto_now_add=True)
  - `updated_at`: timestamptz (auto_now=True)

- **`harvest_harvestwaste`** (Waste Tracking)
  - `id`: bigint (PK, auto-increment)
  - `event_id`: bigint (FK to `harvest_harvestevent`, on_delete=CASCADE)
  - `category`: varchar(50)
  - `weight_kg`: numeric(12,3) (validators: MinValueValidator(0))
  - `created_at`: timestamptz (auto_now_add=True)
  - `updated_at`: timestamptz (auto_now=True)

- **`harvest_productgrade`** (Product Grading)
  - `id`: bigint (PK, auto-increment)
  - `code`: varchar(50) (Unique)
  - `name`: varchar(100)
  - `description`: text
  - `created_at`: timestamptz (auto_now_add=True)
  - `updated_at`: timestamptz (auto_now=True)

**Relationships**
**Internal Harvest App Relationships:**
- `harvest_harvestevent` ← `harvest_harvestlot` (CASCADE, related_name='lots')
- `harvest_harvestevent` ← `harvest_harvestwaste` (CASCADE, related_name='waste_entries')
- `harvest_productgrade` ← `harvest_harvestlot` (PROTECT, related_name='lots')

**Cross-App Relationships:**
- `batch_batch` ← `harvest_harvestevent` (PROTECT, related_name='harvest_events')
- `batch_batchcontainerassignment` ← `harvest_harvestevent` (PROTECT, related_name='harvest_events')
- `infrastructure_geography` ← `harvest_harvestevent` (PROTECT, related_name='destination_harvest_events')

**Finance App Integration:**
- `harvest_harvestevent` ← `finance_factharvest` (PROTECT, related_name='finance_facts')
- `harvest_harvestlot` ← `finance_factharvest` (PROTECT, related_name='finance_fact', unique=True)
- `harvest_productgrade` ← `finance_factharvest` (PROTECT, related_name='finance_facts')
- `harvest_harvestevent` ← `finance_intercompanytransaction` (PROTECT, related_name='intercompany_transactions')
- `harvest_productgrade` ← `finance_intercompanypolicy` (PROTECT, related_name='intercompany_policies')
- `harvest_productgrade` ← `finance_navexportline` (PROTECT, related_name='nav_export_lines')

**Historical Table Relationships:**
- `auth_user` ← `harvest_historicalharvestevent` (SET_NULL, history_user_id)
- `auth_user` ← `harvest_historicalharvestlot` (SET_NULL, history_user_id)
- `auth_user` ← `harvest_historicalharvestwaste` (SET_NULL, history_user_id)
- `auth_user` ← `harvest_historicalproductgrade` (SET_NULL, history_user_id)

**Constraints**
- Unique constraints on harvest event document references
- Weight validations (gutted ≤ live, fillet ≤ gutted)
- Foreign key constraints ensure batch traceability

**Additional Considerations**
- **Regulatory Compliance**: Complete audit trail from egg to plate for Faroese and Scottish salmon regulations
- **Yield Analytics**: Automatic calculation of processing yields and recovery rates
- **Quality Control**: Product grading by code ensures consistent quality standards
- **Economic Tracking**: Integration with finance app for harvest profitability analysis
- **Scalability**: Support for high-volume harvest operations with efficient indexing on event_date
- **Traceability**: End-to-end traceability from batch through harvest lots to finance facts

#### 4.10 Scenario Planning (scenario app - IMPLEMENTED)

The Scenario Planning app’s data model enables aquaculture managers to create, manage, and analyze hypothetical scenarios for salmon farming operations, projecting key metrics like fish growth, population, biomass, and feed consumption. It reuses existing models like `batch_lifecyclestage`, introduces normalized tables for integrity and querying, and integrates with apps like `batch` for real-time data initialization. The design ensures scalability for large projection datasets, supports audit logging for traceability, and matches the implementation complexity of Broodstock Management.

**Core Entities and Attributes**

- **TemperatureProfile** (New Table for Temperature Profiles)  
  - `profile_id` (PK): Unique identifier.  
  - `name` (CharField, max_length=255): Descriptive name (e.g., "Faroe Islands Winter").  
  - `created_at` (DateTimeField): Creation timestamp.  
  - `updated_at` (DateTimeField): Last update timestamp.

- **TemperatureReading** (New Table for Temperature Data)  
  - `reading_id` (PK): Unique identifier.  
  - `profile_id` (FK): Link to `TemperatureProfile`.  
  - `reading_date` (DateField): Date of the reading.  
  - `temperature` (FloatField): Value in degrees Celsius (e.g., 12.5).  
  - `created_at` (DateTimeField): Creation timestamp.  
  - `updated_at` (DateTimeField): Last update timestamp.

- **TGCModel** (New Table for TGC Models)  
  - `model_id` (PK): Unique identifier.  
  - `name` (CharField, max_length=255): Model name (e.g., "Scotland April TGC").  
  - `location` (CharField, max_length=255): Location (e.g., "Scotland Site 1").  
  - `release_period` (CharField, max_length=255): Release timing (e.g., "April").  
  - `tgc_value` (FloatField): TGC coefficient (e.g., 0.025).  
  - `exponent_n` (FloatField): Temperature exponent (e.g., 0.33).  
  - `exponent_m` (FloatField): Weight exponent (e.g., 0.66).  
  - `profile_id` (FK): Link to `TemperatureProfile`.  
  - `created_at` (DateTimeField): Creation timestamp.  
  - `updated_at` (DateTimeField): Last update timestamp.

- **FCRModel** (New Table for FCR Models)  
  - `model_id` (PK): Unique identifier.  
  - `name` (CharField, max_length=255): Model name (e.g., "Standard FCR").  
  - `created_at` (DateTimeField): Creation timestamp.  
  - `updated_at` (DateTimeField): Last update timestamp.

- **FCRModelStage** (New Table for FCR per Stage)  
  - `model_id` (FK, PK): Link to `FCRModel`.  
  - `stage_id` (FK, PK): Link to `batch_lifecyclestage`.  
  - `fcr_value` (FloatField, min_value=0): FCR for the stage (e.g., 1.2).  
  - `duration_days` (IntegerField, min_value=1): Stage duration in days (e.g., 90).  
  - `created_at` (DateTimeField): Creation timestamp.  
  - `updated_at` (DateTimeField): Last update timestamp.

- **MortalityModel** (New Table for Mortality Models)  
  - `model_id` (PK): Unique identifier.  
  - `name` (CharField, max_length=255): Model name (e.g., "Low Mortality").  
  - `frequency` (CharField, max_length=10, choices=[("daily", "Daily"), ("weekly", "Weekly")]): Rate application frequency.  
  - `rate` (FloatField, min_value=0, max_value=100): Mortality rate percentage (e.g., 0.1).  
  - `created_at` (DateTimeField): Creation timestamp.  
  - `updated_at` (DateTimeField): Last update timestamp.

- **Scenario** (New Table for Scenario Configurations)  
  - `scenario_id` (PK): Unique identifier.  
  - `name` (CharField, max_length=255): Scenario name (e.g., "Scotland April Sim").  
  - `start_date` (DateField): Simulation start date.  
  - `duration_days` (IntegerField, min_value=1): Total simulation days (e.g., 900).  
  - `initial_count` (IntegerField, min_value=1): Initial fish count (e.g., 10000).  
  - `genotype` (CharField, max_length=255): Fish genotype (e.g., "SalmoBreed").  
  - `supplier` (CharField, max_length=255): Fish supplier (e.g., "AquaGen").  
  - `initial_weight` (FloatField, nullable, min_value=0): Initial weight in grams (e.g., 50).  
  - `tgc_model_id` (FK): Link to `TGCModel`.  
  - `fcr_model_id` (FK): Link to `FCRModel`.  
  - `mortality_model_id` (FK): Link to `MortalityModel`.  
  - `batch_id` (FK, nullable): Link to `batch_batch` for real-data initialization.  
  - `created_by` (FK): Link to `auth_user`.  
  - `created_at` (DateTimeField): Creation timestamp.  
  - `updated_at` (DateTimeField): Last update timestamp.

- **ScenarioModelChange** (New Table for Model Changes)  
  - `change_id` (PK): Unique identifier.  
  - `scenario_id` (FK): Link to `Scenario`.  
  - `change_day` (IntegerField, min_value=0): Day of change (e.g., 180).  
  - `new_tgc_model_id` (FK, nullable): Link to new `TGCModel`.  
  - `new_fcr_model_id` (FK, nullable): Link to new `FCRModel`.  
  - `new_mortality_model_id` (FK, nullable): Link to new `MortalityModel`.  
  - `created_at` (DateTimeField): Creation timestamp.  
  - `updated_at` (DateTimeField): Last update timestamp.

- **ScenarioProjection** (New Table for Daily Projections)  
  - `projection_id` (PK): Unique identifier.  
  - `scenario_id` (FK): Link to `Scenario`.  
  - `projection_date` (DateField): Projection date.  
  - `day_number` (IntegerField, min_value=0): Day offset from start (e.g., 45).  
  - `average_weight` (FloatField, min_value=0): Fish weight in grams (e.g., 250.5).  
  - `population` (FloatField, min_value=0): Fish count (e.g., 9950.3).  
  - `biomass` (FloatField, min_value=0): Biomass in kilograms (e.g., 2491.2).  
  - `daily_feed` (FloatField, min_value=0): Daily feed in kilograms (e.g., 30.5).  
  - `cumulative_feed` (FloatField, min_value=0): Total feed in kilograms (e.g., 1200.7).  
  - `temperature` (FloatField): Temperature in Celsius (e.g., 12.8).  
  - `current_stage_id` (FK): Link to `batch_lifecyclestage`.  
  - `created_at` (DateTimeField): Creation timestamp.  
  - `updated_at` (DateTimeField): Last update timestamp.

- **batch_lifecyclestage** (Reused for Lifecycle Stages)  
  - `stage_id` (PK): Unique identifier.  
  - `name` (CharField, max_length=100): Stage name (e.g., "Smolt").  
  - `description` (TextField, nullable): Stage details.  
  - `created_at` (DateTimeField): Creation timestamp.  
  - `updated_at` (DateTimeField): Last update timestamp.

**Relationships**  
- **TemperatureProfile** to **TemperatureReading**: One-to-many (one profile has many readings).  
- **TemperatureProfile** to **TGCModel**: One-to-many (one profile used by many models).  
- **TGCModel** to **Scenario**: One-to-many (one model used in many scenarios).  
- **FCRModel** to **FCRModelStage**: One-to-many (one model defines many stages).  
- **FCRModel** to **Scenario**: One-to-many (one model used in many scenarios).  
- **MortalityModel** to **Scenario**: One-to-many (one model used in many scenarios).  
- **Scenario** to **ScenarioModelChange**: One-to-many (one scenario has many changes).  
- **Scenario** to **ScenarioProjection**: One-to-many (one scenario generates many projections).  
- **batch_lifecyclestage** to **FCRModelStage**: One-to-many (one stage used in many FCR models).  
- **batch_lifecyclestage** to **ScenarioProjection**: One-to-many (one stage applies to many projection days).  
- **batch_batch** to **Scenario**: One-to-many (one batch initializes many scenarios).

**Constraints**  
- Unique constraint on `name` in `TemperatureProfile`, `TGCModel`, `FCRModel`, and `MortalityModel`.  
- Foreign key constraints enforce referential integrity (e.g., `profile_id`, `model_id`, `scenario_id`).  
- `frequency` in `MortalityModel` restricted to "daily" or "weekly" via choices.  
- `rate` in `MortalityModel` between 0 and 100.  
- `change_day` in `ScenarioModelChange` nullable or between 0 and `Scenario.duration_days - 1`.  
- `initial_count` and `duration_days` in `Scenario` must be positive.  

**Additional Considerations**  
- **Scalability**: Handle large datasets in `ScenarioProjection` (e.g., 900+ rows per scenario) with indexes on `scenario_id` and `projection_date`. Use TimescaleDB hypertables for `ScenarioProjection`, partitioned by `projection_date`, if data exceeds 1M rows.  
- **Auditing**: Apply `django-auditlog` to `Scenario`, `ScenarioModelChange`, `TGCModel`, `FCRModel`, and `MortalityModel` for traceability and compliance.  
- **Validation**: Enforce constraints via model validation (e.g., `fcr_value > 0`, `initial_weight >= 0` or null, `rate` between 0-100).  
- **Integration**: Link `batch_id` in `Scenario` to `batch_batch` for real-time data; optionally sync `TemperatureReading` with `environmental_reading`.  
- **TimescaleDB**: Optimize `ScenarioProjection` with hypertables for time-series efficiency.  
- **JSON Fields**: Avoid JSON fields to maintain normalization; all data is structured.  
- **Mobile Sync**: Support offline scenario creation with temporary IDs, resolving conflicts during server sync.

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

## 8. TimescaleDB Hypertables (Implemented)

**Purpose**: Efficient time-series data management for environmental monitoring and weather data.

**Implemented TimescaleDB Hypertables**:
- **`environmental_environmentalreading`**: Environmental sensor readings
  - **Partitioning**: By `reading_time` (timestamp with time zone)
  - **Compression**: Enabled after 7 days, segmented by `container_id, parameter_id`
  - **Chunks**: 123 active chunks with data automatically migrated
- **`environmental_weatherdata`**: Weather station data
  - **Partitioning**: By `timestamp` (timestamp with time zone)
  - **Compression**: Enabled after 7 days, segmented by `area_id`
  - **Chunks**: 0 chunks (empty table ready for data)

**Benefits**:
- Sub-second query performance for environmental data queries
- Automatic data compression (70-90% reduction) for historical readings
- Efficient storage of high-frequency sensor data
- Built-in time-bucket aggregation functions
- Automatic chunk management and retention policies