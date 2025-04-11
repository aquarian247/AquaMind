Technical Description of the AquaMind Database Schema
The AquaMind database is a relational database implemented in PostgreSQL with the TimescaleDB extension, designed to support an aquaculture management system. All tables reside in the public schema.

Overview
The schema comprises over 40 tables, organized into ten categories:

Infrastructure Management
Batch Management
Broodstock Management (new)
Growth and Species Parameters
Environmental Monitoring
Feed and Inventory Management
Health Monitoring (Medical Journal)
Scenario Planning
Operational Planning
User Management (updated)
Key Characteristics
Tables: 40+
Primary Keys: Each table uses an auto-incrementing integer column named id.
Foreign Keys: Extensive relationships ensure data integrity.
Data Types: Primarily integer, double precision, character varying, timestamp without time zone, with some json and text.
TimescaleDB: Hypertables (environmental_reading, weather_data) manage time-series data efficiently.

1. Infrastructure Management
Manages physical locations and assets.

area: Sea areas with geo-positioning (latitude, longitude, name).
freshwater_station: Freshwater stations with geo-positioning.
hall: Halls within stations.
container: Tanks or pens with type, capacity; linked to area or hall.
sensor: Sensors in containers for monitoring.
feed_containers: Feed storage units linked to areas or halls.
Key Relationships:

container → area or hall
sensor → container
feed_containers → area or hall

2. Batch Management
Tracks fish batches through their lifecycle, including support for multi-population containers and batch traceability.

batch: Core batch data (species, lifecycle stage, status, date ranges).
batch_lifecyclestage: Defines the distinct stages (Egg, Fry, Parr, Smolt, etc.).
batch_container_assignment: Assigns batch portions to containers with counts, biomass, and the specific lifecycle stage for that portion.
batch_composition: Tracks mixed-batch compositions for cases where batches get combined.
batch_transfer: Records batch movements between containers, including splits, merges, and lifecycle transitions.
batch_history: Historical batch snapshots for auditing and traceability.
batch_media: Media files linked to batches.

Key Relationships:

batch_container_assignment → batch, container: Many-to-many relationship allowing multiple batches in one container and portions of a batch across containers.
batch_composition → batch: Self-referential relationship tracking mixed-batch components and percentages.
batch_transfer → batch, batch_container_assignment: Records movements with detailed source/destination information.
batch_history → batch: Captures point-in-time snapshots of batch state.
batch_media → batch: Links media files for documentation.

3. Broodstock Management
Manages genetic traits, breeding programs, and simulations for the Broodstock Department to support selective breeding and genetic innovation.

genetic_trait:
Purpose: Catalog genetic traits of interest (e.g., disease resistance, growth rate).
Columns: id, name, description, measurement_unit
batch_genetic_profile:
Purpose: Associate genetic traits with batches, storing measured or estimated trait values.
Columns: id, batch_id, trait_id, value
breeding_program:
Purpose: Organize selective breeding initiatives with goals and timelines.
Columns: id, name, description, start_date, end_date, geneticist_id
breeding_pair:
Purpose: Record breeding pairs and their offspring within a program.
Columns: id, program_id, parent1_batch_id, parent2_batch_id, offspring_batch_id
genetic_scenario:
Purpose: Simulate breeding outcomes and assess trait trade-offs.
Columns: id, name, description, program_id, target_trait_id, environmental_factors (JSON), predicted_outcomes (JSON)
trait_tradeoff:
Purpose: Quantify relationships between traits (e.g., correlation coefficients).
Columns: id, trait1_id, trait2_id, correlation_coefficient
Key Relationships:

batch_genetic_profile → batch, genetic_trait: Links genetic traits to specific batches.
breeding_pair → breeding_program, batch: Connects pairs to programs and batches (parents and offspring).
genetic_scenario → breeding_program, genetic_trait: Ties simulations to programs and target traits.
trait_tradeoff → genetic_trait: Relates pairs of traits for trade-off analysis.
These tables integrate with existing tables like environmental_reading and growth_metric to enable comprehensive analysis of genetic, environmental, and health data, supporting the Broodstock Department’s needs.

4. Growth and Species Parameters
Manages growth metrics and species-specific parameters.

growth_metric: Batch growth data (weight, TGC, SGR).
atlantic_salmon_parameters: Parameters for Atlantic salmon growth models.
species_parameters: Generic species parameters.
Key Relationships:

growth_metric → batch, container

5. Environmental Monitoring
Handles environmental data, including time-series.

environmental_reading: Time-series sensor/manual data (hypertable).
photoperiod_data: Day length data by area.
weather_data: Weather conditions by area (hypertable).
stage_transition_environmental: Environmental conditions during stage transitions.
Key Relationships:

environmental_reading → container, batch, sensor
photoperiod_data → area
weather_data → area
stage_transition_environmental → batch_distribution

6. Feed and Inventory Management
Manages feed types, stock, and feeding events.

feed: Feed types (brand, composition).
feed_purchase: Feed purchase records.
feed_stock: Current stock in feed containers.
feeding_event: Individual feeding events (amount, FCR).
batch_feeding_summary: Feeding summaries per batch.
Key Relationships:

feed_purchase → feed
feed_stock → feed, feed_containers
feeding_event → batch, container, feed
batch_feeding_summary → batch

7. Health Monitoring (Medical Journal)

***Note:** This feature is planned. The tables listed below (except `mortality_record`/`batch_mortalityevent`) are not yet implemented in the current database schema (as of 2025-04-11).*

Records health observations and treatments.
journal_entry: Health observations (appearance, behavior).
lice_count: Sea lice counts.
mortality_record: Mortality events with reasons.
mortality_reason: Mortality reason categories.
treatment: Applied treatments (type, outcome).
vaccination_type: Vaccination types.
sample_type: Sample types.
Key Relationships:

journal_entry → batch, container, user
lice_count → batch, container, user
mortality_record → batch, container, mortality_reason
treatment → batch, container, user

8. Scenario Planning

***Note:** This feature is planned. The tables listed below are not yet implemented in the current database schema (as of 2025-04-11).*

Supports hypothetical scenario creation and comparison.
batch_scenario: Scenario definitions (name, growth model).
batch_scenario_container: Container assignments for scenarios.
batch_scenario_growth: Growth targets (TGC, SGR).
batch_scenario_feeding: Feeding plans.
batch_scenario_environmental: Environmental targets.
scenario_comparison: Comparisons between scenarios (id, name, scenarios as JSON).
Key Relationships:

batch_scenario_container → batch_scenario, container
batch_scenario_growth → batch_scenario
batch_scenario_feeding → batch_scenario, feed
batch_scenario_environmental → batch_scenario
scenario_comparison → batch_scenario (via JSON or many-to-many)

9. Operational Planning

***Note:** This feature is planned. The tables listed below are not yet implemented in the current database schema (as of 2025-04-11).*

Facilitates real-time planning and recommendations.
infrastructure_state: Container state (capacity, health, density).
planning_recommendation: Operational recommendations (type, priority, details as JSON).
recommendation_action: Actions on recommendations (action taken, user).
Key Relationships:

infrastructure_state → container
planning_recommendation → batch, container (from/to)
recommendation_action → planning_recommendation, user

10. User Management
Manages user accounts and access control, leveraging Django's built-in authentication and permission systems while extending them to fully support AquaMind's complex organizational structure.

user:
Extended Django User Model with additional fields:
geography: Links to the user's region (e.g., Faroe Islands, Scotland).
subsidiary: Ties to the user's company (e.g., Farming, Logistics).
role: Defines the user's role (e.g., manager, veterinarian).
geography:
Purpose: Define regions of operation.
Columns: id, name (e.g., "Faroe Islands", "Scotland")
subsidiary:
Purpose: Define companies within regions.
Columns: id, name, geography_id
Access Control:

Authentication: Handled by Django's User model and built-in views for login, logout, and password management.
Permissions: Model-level access via Django groups (e.g., "Finance Group") and permissions (e.g., can_view_batch), assigned based on role.
Row-Level Security: Implemented with custom QuerySets or django-guardian to restrict access to specific data instances (e.g., batches or programs) based on geography, subsidiary, or user-specific assignments.
Audit Logging: Uses django-auditlog or Django signals to track changes, ensuring accountability (e.g., who updated a batch record).
Key Relationships:

user → geography, subsidiary: Ties users to their organizational context.
Referenced across tables for auditing (e.g., recorded_by in feeding_event, journal_entry, or breeding_program).
This enhanced structure supports role-based, geography-based, and subsidiary-based access control, ensuring data security and operational integrity across AquaMind’s multi-dimensional organizational hierarchy.

Notes for Developers
All tables are in the public schema.
Hypertables leverage TimescaleDB for efficient time-series data management.
Map tables to Django models with appropriate relationships (e.g., ForeignKey, ManyToManyField).
Optimize for large datasets, particularly in Scenario Planning, Environmental Monitoring, and now Broodstock Management.