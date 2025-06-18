# AquaMind Product Requirements Document (PRD)

## 1. Introduction

### 1.1 Purpose
AquaMind is an aquaculture management system designed to optimize operations for Bakkafrost, a leading aquaculture company operating in the Faroe Islands and Scotland. The system shall provide a unified platform to manage core operational data including infrastructure (`infrastructure_*` models), fish batches (`batch_*` models), environmental conditions (`environmental_*` models), health and inventory (`health_*`, `inventory_*` models), manage broodstock for genetic improvement, and enable data-driven decision-making across subsidiaries (Broodstock, Freshwater, Farming, Logistics). AquaMind shall ensure regulatory compliance through comprehensive audit trails, enhance operational efficiency, and support sustainability through advanced analytics, scenario planning, and future AI-driven insights.

### 1.2 Scope
This PRD defines the functional and non-functional requirements for AquaMind, covering core operations, broodstock management, operational planning, regulatory compliance, and audit trail capabilities. It outlines a phased approach to development, aligning with business goals, user needs, and the `implementation plan and progress.md`. The system shall integrate with external systems (e.g., WonderWare for sensor data, OpenWeatherMap for weather data), comply with regulatory standards in the Faroe Islands and Scotland, and accurately reflect the implemented schema defined in `docs/data model.md`.

**Note on Audit Capabilities**: The system implements comprehensive audit trails through django-simple-history for regulatory compliance, providing complete change tracking for critical models (Batch, Container, FeedStock). Advanced audit analytics functionality was removed during development to prioritize system stability and core operational features.

### 1.3 Business Drivers
- **Operational Efficiency**: Streamline batch lifecycle management (`batch_batch`, `batch_batchcontainerassignment`), resource allocation (`infrastructure_container`), and inventory tracking (`inventory_feedstock`) across subsidiaries.
- **Regulatory Compliance**: Ensure adherence to environmental, health, and financial regulations through comprehensive audit trails and change tracking in multiple jurisdictions.
- **Data Accuracy**: Maintain precise feed conversion ratio (FCR) calculations using standardized `fcr` field with decimal(5,3) precision for accurate performance tracking.
- **Genetic Improvement**: Support broodstock management and breeding programs to enhance fish quality, disease resistance, and growth rates (Planned Phase 2/3).
- **Sustainability**: Monitor environmental impact (`environmental_environmentalreading`) and optimize resource usage (`inventory_feedingevent`) to promote sustainable aquaculture practices.
- **Competitive Advantage**: Leverage data analytics and scenario planning to improve decision-making and operational outcomes.

### 1.4 Organizational Structure
AquaMind shall support Bakkafrost's organizational structure:
- **Geographies**: Faroe Islands and Scotland (Managed via `infrastructure_geography`).
- **Subsidiaries**: Broodstock, Freshwater, Farming, Logistics (Managed via `users_userprofile.subsidiary` and potentially linked models).
- **Horizontals**: Finance, Compliance (Supported via reporting and data access).
- **Roles**: Admin, Operator, Manager, Executive, Veterinarian (Managed via `users_userprofile.role` and linked `auth_group`/`auth_permission`). Permissions based on geography, subsidiary, and role.

## 2. System Overview

### 2.1 System Architecture
AquaMind shall be a full-stack web application with:
- **Backend**: Django (v4.2.11+), providing RESTful APIs via Django REST Framework for data management and business logic.
- **Frontend**: Vue.js (v3+), offering an intuitive user interface with operational dashboards and interactive views.
- **Database**: PostgreSQL with TimescaleDB extension for efficient time-series data management (`environmental_environmentalreading`, `environmental_weatherdata`).
- **Authentication**: JWT-based authentication for secure API access, integrated with `auth_user` and `users_userprofile` data.

### 2.2 Phased Approach
The development of AquaMind shall follow a phased approach as outlined in `implementation plan and progress.md`:
- **Phase 1: Core Operations (MVP - Largely Complete)**: Implement foundational features for batch management, health monitoring (Medical Journal), environmental tracking, feed/inventory, and basic dashboards.
- **Phase 2: Operational Planning and Compliance (Current/Next)**: Enhance operational efficiency with planning tools, ensure regulatory compliance, and enhance Broodstock features.
- **Phase 3: AI Enablement (Future)**: Introduce predictive analytics, scenario planning, and genomic prediction for advanced decision-making.

## 3. Functional Requirements

### 3.1 Phase 1: Core Operations (MVP)

#### 3.1.1 Infrastructure Management (`infrastructure` app)
- **Purpose**: To manage and monitor physical assets and locations critical to aquaculture operations.
- **Functionality**:
  - The system shall manage geographies (`infrastructure_geography`), areas (`infrastructure_area`), freshwater stations (`infrastructure_freshwaterstation`), halls (`infrastructure_hall`), container types (`infrastructure_containertype`), containers (`infrastructure_container`), sensors (`infrastructure_sensor`), and feed containers (`infrastructure_feedcontainer`).
  - Users shall be able to perform CRUD operations on infrastructure records via API endpoints and corresponding UI views.
  - The system shall display Areas alongside Freshwater Stations on the Infrastructure page, reflecting their relationship (`infrastructure_freshwaterstation.area_id`).
  - The system shall track sensor status (`infrastructure_sensor.status`) and container capacity (`infrastructure_container.capacity_kg`, `capacity_m3`). Containers can be linked to either a Hall or an Area via nullable ForeignKeys (`hall_id`, `area_id`).
- **Behavior**:
  - Infrastructure records shall be accessible based on user role and geography (`users_userprofile.geography_id`). Access control enforced via API permissions and querysets.
  - The UI shall provide filtering by area, hall, or station.
  - Alerts shall notify users of sensor malfunctions (`infrastructure_sensor.status != 'Active'`) or capacity issues (derived from `batch_batchcontainerassignment` data).
- **Justification**: Ensures efficient resource allocation and monitoring of physical assets across geographies.
- **User Story**: As a Farm Operator, I want to view all containers (`infrastructure_container`) within a specific freshwater station (`infrastructure_freshwaterstation`) so that I can assign batches (`batch_batch`) to appropriate locations.
  - **Acceptance Criteria**:
    - The UI displays a list of `infrastructure_container` records linked to a selected `infrastructure_freshwaterstation`.
    - Container details include `capacity_kg`, linked `infrastructure_sensor` status, and current occupancy (calculated biomass/population derived from associated `batch_batchcontainerassignment` records).
    - Users can filter containers by linked `infrastructure_area` or `infrastructure_hall`.
    - Alerts for sensor malfunctions are displayed prominently in the UI.

#### 3.1.2 Batch Management (`batch` app)
- **Purpose**: To track fish batches (`batch_batch`) through their lifecycle (`batch_lifecyclestage`), ensuring traceability and operational efficiency.
- **Functionality**:
  - The system shall track batches (`batch_batch`) through defined lifecycle stages (`batch_lifecyclestage` records: e.g., Egg, Fry, Parr, Smolt, Post-Smolt, Adult).
  - The system shall support assigning portions of batches to specific containers at specific lifecycle stages using the `batch_batchcontainerassignment` model. This model tracks `population_count`, `avg_weight_g`, and the `lifecycle_stage_id` for that specific assignment.
  - The system shall calculate derived metrics like `biomass_kg` (within `BatchContainerAssignment.save()` or serializers: `population_count * avg_weight_g / 1000`).
  - The system shall log batch transfers between containers using `batch_batchtransfer`, recording `from_container_id`, `to_container_id`, `population_count`, `transfer_type`, etc.
  - The system shall track growth via `batch_growthsample` records (linked to `batch_batchcontainerassignment`). Mortality is tracked via `batch_mortalityevent`.
  - The system shall calculate Fulton's Condition Factor (K-factor) for each growth sample using the formula \(K = 100 \times \frac{W}{L^3}\), where \(W\) is the average weight in grams (`batch_growthsample.avg_weight_g`) and \(L\) is the average length in centimeters (`batch_growthsample.avg_length_cm`) for that specific sample.
  - The K-factor shall be stored in the existing `condition_factor` field on the `batch_growthsample` model.
  - The `batch_growthsample.avg_length_cm` and `batch_growthsample.std_deviation_length` fields shall be calculated from a list of individual fish lengths provided by the user during the sampling process.
  - The system shall simulate, for testing purposes, a full lifecycle (approx. 850-900 days) with stage-appropriate container transitions, involving creation of new `BatchContainerAssignment` records upon stage changes or transfers (Ref: `simulate_full_lifecycle.py` script).
  - Batch history will be managed via audit logging tools (e.g., `django-auditlog`). Media attachments (`batch_batchmedia`) might use generic relations or a dedicated media model.
- **Behavior**:
  - Batch lifecycle stage transitions typically trigger the creation of new `BatchContainerAssignment` records or `BatchTransfer` records to reflect the change in location or status.
  - Transfers (`batch_batchtransfer`) shall require user confirmation and log the reason (`batch_batchtransfer.reason`).
  - Biomass calculations (`batch_batchcontainerassignment.biomass_kg`) shall update automatically when relevant fields (`population_count`, `avg_weight_g`) are modified.
  - The K-factor (`batch_growthsample.condition_factor`) shall be calculated automatically within the `GrowthSample` model's `save` method whenever `avg_weight_g` and calculated `avg_length_cm` are available for a sample.
- **Justification**: Provides complete visibility into batch lifecycles and container assignments, enabling precise management, accurate biomass tracking, and traceability. Allows for granular health assessment through the K-factor calculated at the time of sampling for specific container assignments.
- **User Story**: As a Farm Operator, I want to track the specific lifecycle stage (`batch_lifecyclestage`) of the fish within each container assignment (`batch_batchcontainerassignment`) for a given batch (`batch_batch`).
  - **Acceptance Criteria**:
    - The UI displays the active `batch_batchcontainerassignment` records for a selected `batch_batch`.
    - Each assignment detail view shows the linked `infrastructure_container`, `population_count`, `avg_weight_g`, calculated `biomass_kg`, and the specific `batch_lifecyclestage` for that assignment.
    - Transfers (`batch_batchtransfer`) between containers are logged with timestamps, reasons, and user details.
    - Growth patterns (`batch_growthsample` data) are visualized in a chart showing stage transitions over time.
- **User Story**: As a Manager, I want to view batch history (via audit logs) so that I can trace its movements and significant changes.
  - **Acceptance Criteria**:
    - The UI provides a batch history view (e.g., audit log entries filtered for the `batch_batch` instance) with timestamps, description of changes (e.g., stage change, transfer, population update), and user details.
    - Media attachments are accessible if implemented.
    - Users can filter history by date range or event type.
- **User Story**: As a Farm Operator, I want to view the K-factor for a batch so that I can assess its overall condition and growth.
  - **Acceptance Criteria**:
    - The UI displays the K-factor for a selected batch alongside other metrics (e.g., `biomass_kg`).
    - The K-factor is updated whenever `avg_weight_g`, `avg_length_cm`, or `std_deviation_length` changes.
    - An alert is generated if the K-factor falls below a configurable threshold (e.g., K < 0.8).

#### 3.1.3 Feed and Inventory Management (`inventory` app)
- **Purpose**: To comprehensively manage feed resources, optimize feeding practices, ensure accurate cost tracking, and support data-driven feeding decisions for optimal batch growth and operational efficiency.
- **Functionality**:
  - **Feed Type Management**:
    - The system shall manage comprehensive feed specifications via `inventory_feed`, including nutritional composition (protein, fat, carbohydrate, ash, moisture percentages), pellet size, brand information, and lifecycle stage suitability.
    - Feed types shall be categorized by size category, brand, and active status for efficient selection and filtering.
    - The system shall support feed recommendations based on batch lifecycle stage, size, and nutritional requirements.

  - **Feed Procurement and Purchase Management**:
    - The system shall track feed purchases via `inventory_feedpurchase`, capturing supplier information, batch numbers, quantities, costs per kilogram, purchase dates, and expiry dates for comprehensive procurement tracking.
    - Purchase records shall include quality certifications, delivery details, and storage requirements to ensure feed quality and traceability.
    - The system shall support purchase planning based on consumption forecasts, stock levels, and batch feeding schedules.

  - **FIFO Inventory Tracking and Cost Management**:
    - The system shall implement First-In-First-Out (FIFO) inventory methodology via `inventory_feedcontainerstock`, tracking individual feed batches within containers by purchase date and entry date to ensure oldest feed is consumed first.
    - Each container stock entry shall link to specific feed purchases (`inventory_feedpurchase`) maintaining cost per kilogram, batch numbers, and expiry dates for precise cost tracking and quality control.
    - The system shall provide FIFO-specific operations including:
      - Adding feed batches to containers while maintaining chronological order
      - Retrieving container stock in FIFO order (oldest first)
      - Automatic cost calculation during feed consumption using oldest available batches
    - Feed cost calculations shall be automatically applied to feeding events (`inventory_feedingevent.feed_cost`) using FIFO methodology, ensuring accurate cost attribution without manual intervention.

  - **Feed Stock Management and Monitoring**:
    - The system shall maintain real-time stock levels via `inventory_feedstock` linked to `infrastructure_feedcontainer`, tracking current quantities, reorder thresholds, and last updated timestamps.
    - Stock levels shall be automatically updated based on feed additions (purchases) and consumption (feeding events), maintaining accuracy across all containers.
    - The system shall generate low-stock alerts when quantities fall below configurable thresholds (percentage of container capacity or absolute values), enabling proactive procurement planning.
    - Historical stock level trends shall be available for analysis, supporting consumption pattern identification and inventory optimization.

  - **Feeding Event Management and Optimization**:
    - The system shall log detailed feeding events via `inventory_feedingevent`, capturing batch assignments, feed types, quantities, feeding methods (manual, automatic, broadcast), batch biomass at feeding time, and calculated feeding percentages.
    - Feeding events shall be validated for compatibility with batch lifecycle stages, ensuring appropriate feed types and quantities are used for each growth phase.
    - The system shall calculate feeding percentages automatically based on feed amount and batch biomass, supporting feeding optimization and growth monitoring.
    - Feeding schedules and recommendations shall be generated based on batch needs, environmental conditions, and feed availability.

  - **Feed Conversion Ratio (FCR) Calculation and Analysis**:
    - The system shall calculate Feed Conversion Ratios at the batch level via enhanced `inventory_batchfeedingsummary` records using the standardized `fcr` field with decimal(5,3) precision for accurate performance tracking.
    - FCR calculations shall support both standard batches (single batch in container) and mixed batches (multiple batches sharing containers), providing accurate performance metrics regardless of container configuration.
    - The system shall generate feeding summaries automatically or on-demand, aggregating feeding events, calculating total consumption, biomass changes, and FCR for performance analysis.
    - FCR trends and comparisons shall be available across batches, time periods, and feed types, supporting feeding strategy optimization and performance benchmarking.
    - **Data Accuracy**: The system maintains data integrity by using a single, precise FCR field, eliminating duplicate field issues and ensuring consistent calculations across all feeding summaries.

  - **Feed Quality and Compliance Tracking**:
    - The system shall track feed quality parameters including expiry dates, storage conditions, and quality certifications linked to purchase batches.
    - Alerts shall be generated for approaching expiry dates, ensuring feed quality and reducing waste through timely consumption.
    - The system shall support compliance reporting for feed usage, costs, and quality metrics required by regulatory bodies.

  - **Inventory Analytics and Reporting**:
    - The system shall provide comprehensive inventory analytics including consumption patterns, cost trends, FCR performance, and stock optimization recommendations.
    - Reports shall be generated for feed usage by batch, container, time period, and feed type, supporting operational analysis and cost management.
    - The system shall support export capabilities for inventory data, feeding summaries, and cost reports in multiple formats (PDF, CSV, Excel).

- **Behavior**:
  - FIFO inventory operations shall maintain strict chronological order, automatically consuming oldest feed batches first and calculating costs based on original purchase prices.
  - Feed cost calculations shall occur automatically during feeding event creation, eliminating manual cost entry and ensuring accuracy.
  - Low-stock alerts shall trigger based on configurable thresholds, considering both absolute quantities and consumption rates for proactive inventory management.
  - Feeding events shall be validated in real-time for batch compatibility, feed availability, and quantity constraints.
  - FCR calculations shall update automatically when feeding events or batch weight measurements are recorded, providing current performance metrics.
  - Stock levels shall be updated immediately upon feed additions or consumption, maintaining real-time accuracy across all containers.

- **Justification**: Comprehensive feed management optimizes operational efficiency, reduces costs through accurate tracking and FIFO methodology, ensures feed quality and compliance, supports data-driven feeding decisions through FCR analysis, and provides complete traceability from purchase to consumption for regulatory compliance and cost control.

- **User Story (Feed Type Management)**: As a Feed Manager, I want to manage feed specifications and recommendations so that I can ensure optimal nutrition for different batch stages.
  - **Acceptance Criteria**:
    - The UI allows creating and editing feed types with complete nutritional profiles, pellet sizes, and stage suitability.
    - Feed recommendations are provided based on batch lifecycle stage and size requirements.
    - Feed types can be filtered by brand, size category, and active status for efficient selection.
    - Nutritional composition is displayed clearly for feeding decision support.

- **User Story (FIFO Inventory Tracking)**: As a Logistics Manager, I want to track feed inventory using FIFO methodology so that I can ensure oldest feed is used first and maintain accurate cost tracking.
  - **Acceptance Criteria**:
    - The system displays container stock in FIFO order (oldest batches first) with purchase dates and costs.
    - Adding feed to containers maintains chronological order and links to original purchase records.
    - Feeding events automatically calculate costs using FIFO methodology without manual intervention.
    - Container stock summaries show total quantities, values, and batch composition for each container.

- **User Story (Feed Cost Management)**: As a Farm Manager, I want automatic feed cost calculation during feeding events so that I can track actual feeding costs without manual calculations.
  - **Acceptance Criteria**:
    - Creating feeding events automatically calculates and stores feed costs based on FIFO consumption.
    - Cost calculations consider mixed feed batches with different purchase prices in the same container.
    - Feeding event details show cost breakdown by feed batch consumed.
    - Cost reports aggregate feeding costs by batch, time period, and feed type for analysis.

- **User Story (FCR Analysis)**: As a Production Manager, I want to monitor Feed Conversion Ratios for my batches so that I can optimize feeding strategies and assess batch performance.
  - **Acceptance Criteria**:
    - The system calculates FCR automatically for specified time periods, considering total feed consumed and biomass gain.
    - FCR calculations support both single and mixed batch scenarios in shared containers.
    - FCR trends are visualized over time with comparisons across batches and feed types.
    - Feeding summaries can be generated on-demand or automatically for performance reporting.

- **User Story (Stock Management)**: As a Logistics Manager, I want to monitor feed stock levels and receive alerts so that I can plan purchases and prevent stockouts.
  - **Acceptance Criteria**:
    - The UI displays current stock levels per container with visual indicators for low stock conditions.
    - Alerts are generated when stock falls below configurable thresholds, considering consumption rates.
    - Historical stock trends are available for consumption pattern analysis and procurement planning.
    - Stock updates occur automatically based on feed additions and consumption events.

#### 3.1.4 Health Monitoring (Medical Journal - `health` app)
- **Purpose**: To monitor and document the health of fish batches, ensuring timely interventions through detailed observations, general health logging, and quantified health/growth metrics.
- **Functionality**:
  - **General Health Journaling**:
    - The system shall track general health events via `health_journalentry` records, linked to specific batch assignments (`health_journalentry.assignment_id`). Entry types (`entry_type` field) include Observation, Diagnosis, Treatment, Vaccination.
    - Specific event details are stored in linked models: `health_licecount`, `health_mortalityrecord` (linked to `health_mortalityreason`), `health_treatment`, `health_vaccinationrecord` (all typically linked back to a `health_journalentry`).
    - Veterinarians and authorized personnel (`users_userprofile.role`) shall be able to log `health_journalentry` records with rich text notes, and optionally attach pictures and videos (via a separate Media model or generic relations).
    - For `health_journalentry` of type 'Observation', users can record scores for predefined `health_healthparameter`s using the `health_healthobservation` model, linking the journal entry to a parameter with a score (e.g., 1-5 scale).

  - **Detailed Health Sampling & Growth Metrics**:
    - The system shall support creation of `health_healthsamplingevent` records, each representing a specific, detailed sampling session for a `batch_batchcontainerassignment`.
    - Each `HealthSamplingEvent` can have multiple associated `health_individualfishobservation` records, capturing data for each fish sampled (e.g., weight, length, visual abnormalities, and specific parameter scores).
    - For each `IndividualFishObservation`, users can record scores for predefined `health_healthparameter`s (e.g., Gill Condition, Skin Condition) using the `health_fishparameterscore` model, linking the individual fish's observation to a parameter with a score (1-5 scale).
    - Based on the collection of `IndividualFishObservation` data within a `HealthSamplingEvent`, the system shall automatically calculate and store the following aggregate growth metrics on the `HealthSamplingEvent` itself:
      - `avg_weight_g`, `std_dev_weight_g`, `min_weight_g`, `max_weight_g`
      - `avg_length_cm`, `std_dev_length_cm`, `min_length_cm`, `max_length_cm`
      - `avg_k_factor` (Condition Factor)
      - `uniformity_percentage` (based on Coefficient of Variation of weight)
      - `calculated_sample_size` (number of fish used for K-factor and other specific calculations, based on data completeness).

  - **Biological Laboratory Sampling**:
    - The system shall support recording of biological laboratory samples via the `health_healthlabsample` model.
    - Each `health_healthlabsample` record links to a `batch_batchcontainerassignment` and a `health_sampletype`.
    - Key information tracked includes:
      - `sample_date`: Date sample was physically taken.
      - `date_sent_to_lab`: Date sample sent to the lab.
      - `date_results_received`: Date lab results were received.
      - `lab_reference_id`: External ID from the lab for tracking.
      - `findings_summary`: Qualitative summary of results.
      - `quantitative_results`: Structured JSON for detailed quantitative data (e.g., pathogen loads, cell counts).
      - `attachment`: Ability to upload the lab report (e.g., PDF).
      - `notes`: Additional comments by the veterinarian or staff.
      - `recorded_by`: User who recorded the lab sample results.
    - This allows for comprehensive tracking of diagnostic tests and external lab analyses, supplementing the on-site health monitoring.

  - **Common Health Parameters** (applicable to both `HealthObservation` and `FishParameterScore` contexts):
    - Gill Condition: Evaluates gill health.
    - Eye Condition: Evaluates eye clarity and damage.
    - Wounds: Measures skin lesions and severity.
    - Fin Condition: Assesses fin erosion or damage.
    - Body Condition: Evaluates overall physical shape and deformities.
    - Swimming Behavior: Monitors activity levels and movement patterns.
    - Appetite: Assesses feeding response.
    - Mucous Membrane Condition: Evaluates mucus layer on skin.
    - Color/Pigmentation: Monitors abnormal color changes.

  - The system shall provide health trend analysis (e.g., mortality rates aggregated from `health_mortalityrecord`, lice prevalence from `health_licecount`, average health scores from `health_healthobservation` and `health_fishparameterscore`, and trends in calculated growth metrics from `HealthSamplingEvent`).
  - The system shall support predefined categories via `health_mortalityreason`, `health_vaccinationtype`, `health_sampletype`.
- **Behavior**:
  - Users can create, view, update, and delete `health_journalentry` records and their associated details (lice counts, mortality, treatments) via dedicated API endpoints.
  - Users can create, view, update, and delete `HealthSamplingEvent` records and their associated `IndividualFishObservation` and `FishParameterScore` data via dedicated API endpoints.
  - Calculation of aggregate metrics on `HealthSamplingEvent` occurs automatically upon saving or via a dedicated API action.
  - Health data (both journal entries and sampling events) shall be filterable by batch, container, date range, and specific health parameters or metric thresholds.
  - Pictures and videos attached to journal entries shall be uploaded with a maximum file size of 50MB enforced.
  - Entries are linked to the user who created them (e.g., `health_journalentry.created_by_id`, `HealthSamplingEvent.created_by_id`).

- **User Story (General Health Logging)**: As a Veterinarian, I want to log a health observation in the `health_journalentry` with pictures, videos, and quantified health scores (using `health_healthobservation`) for multiple parameters, so that I can document general conditions for a specific batch assignment.
  - **Acceptance Criteria**:
    - The UI allows creating a `health_journalentry` linked to a `batch_batchcontainerassignment`.
    - Users can attach text, pictures, and videos.
    - UI provides dropdowns/inputs to score general health parameters for the batch (via `health_healthobservation`).

- **User Story (Detailed Sampling & Growth Metrics)**: As a Veterinarian or Farm Manager, I want to record detailed observations for individual fish during a health check via a `HealthSamplingEvent`, including their weight and length, and see automatically calculated growth metrics like average weight, average length, K-factor, and uniformity for the sampled group, so I can accurately assess the batch's condition and growth performance.
  - **Acceptance Criteria**:
    - I can create a `HealthSamplingEvent` for a specific batch in a container.
    - For this event, I can add multiple `IndividualFishObservation` records, inputting weight (g) and length (cm) for each fish, and optionally score specific parameters per fish using `health_fishparameterscore`.
    - Upon saving the event or triggering a calculation, the system displays the `avg_weight_g`, `std_dev_weight_g`, `avg_length_cm`, `std_dev_length_cm`, `avg_k_factor`, and `uniformity_percentage` for the `HealthSamplingEvent`.
    - The `calculated_sample_size` correctly reflects how many fish had sufficient data for these calculations.
    - These calculated metrics are available via the API when retrieving a `HealthSamplingEvent`.

- **User Story (Lab Sampling)**: As a Veterinarian or Farm Manager, I want to record lab samples (`health_healthlabsample`) for a batch, including the date sent to the lab and the lab's findings, so that I can track diagnostic results and integrate them into the batch's health record.
  - **Acceptance Criteria**:
    - I can create a `health_healthlabsample` record for a specific batch assignment.
    - I can input the sample date, date sent to the lab, and date results were received.
    - I can upload the lab report (e.g., PDF) and add notes.
    - The system links the lab sample to the batch assignment and displays it in the batch's health record.

- **User Story (Trend Analysis)**: As a Manager, I want to view health trends for a batch, including mortality rates, average lice counts, average general health scores, and growth metric trends (K-factor, average weight from `HealthSamplingEvent`), so that I can identify potential issues and track performance.
  - **Acceptance Criteria**:
    - The UI displays trends in chart format for the selected metrics.
    - Users can filter trends by batch, container, or date range.
    - Alerts can be configured for trends exceeding defined thresholds.

#### 3.1.5 Environmental Monitoring (`environmental` app)
- **Purpose**: To monitor environmental conditions in real-time using TimescaleDB hypertables, ensuring optimal conditions for fish batches.
- **Functionality**:
  - The system shall capture time-series data in `environmental_environmentalreading` (linked to `infrastructure_sensor` and `environmental_environmentalparameter`) and `environmental_weatherdata` (linked to `infrastructure_area`). These are TimescaleDB hypertables partitioned by `reading_time` and `timestamp` respectively, created via `create_hypertable`.
  - The system shall integrate with WonderWare (or similar external sensor system) to populate `environmental_environmentalreading`.
  - The system shall integrate with OpenWeatherMap (or similar external weather service) to populate `environmental_weatherdata`.
  - The system shall manage photoperiod data via `environmental_photoperioddata` (linked to `infrastructure_area`).
  - The system shall display environmental readings and weather conditions on dashboards.
  - The system shall alert users to environmental anomalies (e.g., `value` in `environmental_environmentalreading` outside safe range defined per `environmental_environmentalparameter`, potentially stored in parameter model or configuration).
- **Behavior**:
  - Environmental data ingestion shall occur at configured intervals (e.g., sensor polling rate, API call frequency).
  - Alerts shall be triggered when readings exceed predefined thresholds associated with `environmental_environmentalparameter`.
  - Historical data shall be queryable efficiently for analysis and visualization in time-series charts, leveraging TimescaleDB functions.
- **Justification**: Ensures optimal growing conditions, reduces risks, and supports sustainability goals.
- **User Story**: As a Farm Operator, I want to view real-time environmental conditions (`environmental_environmentalreading`) in a specific container (`infrastructure_container`) so that I can ensure optimal conditions.
  - **Acceptance Criteria**:
    - The UI displays the latest readings (e.g., Temperature, Dissolved Oxygen) for active sensors (`infrastructure_sensor`) linked to the selected container.
    - Historical data is available in an interactive time-series chart (zoom/pan).
    - Weather conditions (`environmental_weatherdata`) for the container's `infrastructure_area` are displayed contextually.
    - Alerts for readings outside defined safe ranges are clearly displayed in the UI.
- **User Story**: As a Manager, I want to analyze environmental trends (`environmental_environmentalreading` aggregates) so that I can identify long-term patterns.
  - **Acceptance Criteria**:
    - The UI provides a trend analysis view with selectable time ranges and aggregation options (e.g., hourly average, daily max).
    - Trends are visualized for multiple parameters (`environmental_environmentalparameter`).
    - Users can compare trends across different containers or areas.
    - Exportable reports of raw or aggregated environmental data are available in CSV format.

#### 3.1.6 User Management (`auth`, `users` apps)
- **Purpose**: To manage user access and ensure data security across organizational dimensions using Django's built-in auth and a custom profile.
- **Functionality**:
  - The system shall manage user accounts via `auth_user` extended by a one-to-one link to `users_userprofile`.
  - Access control is based on role (`users_userprofile.role`), geography (`users_userprofile.geography_id` FK to `infrastructure_geography`), and subsidiary (`users_userprofile.subsidiary`). Permissions assigned via standard Django `auth_group` and `auth_permission`.
  - Supported roles shall include Admin, Operator, Manager, Executive, and Veterinarian, mapped to appropriate permission groups.
  - The system shall use JWT authentication (e.g., via `djangorestframework-simplejwt`) for secure API access.
  - The system shall log user actions for audit purposes (e.g., via `django-auditlog` configured to track relevant models).
- **Behavior**:
  - Users shall only see data relevant to their role, geography, and subsidiary, enforced consistently at the API level (e.g., overriding `get_queryset` in Views/ViewSets).
  - Admins (`is_staff` or specific role group) shall have access to manage users and permissions via the Django admin interface or custom UI views.
  - JWT tokens shall expire after a configured duration (e.g., 24 hours), requiring refresh or re-authentication.
- **Justification**: Ensures data security and operational autonomy while supporting organizational structure.
- **User Story**: As an Admin, I want to assign roles (via `auth_group`), geography, and subsidiary to a user (`users_userprofile`) so that they can access only relevant data.
  - **Acceptance Criteria**:
    - The admin interface allows admins to create/edit `auth_user` and linked `users_userprofile` records, assigning them to appropriate `auth_group`s and setting geography/subsidiary.
    - API endpoints consistently enforce permissions based on the user's profile and group memberships.
    - User actions (CRUD operations on key models, logins) are logged with timestamps and details in the audit log.
    - Attempts to access restricted data result in appropriate HTTP error responses (e.g., 403 Forbidden).
- **User Story**: As a Manager, I want to access data for my subsidiary only so that I can focus on my operations.
  - **Acceptance Criteria**:
    - The UI components (lists, dashboards) automatically display data filtered by the logged-in user's `users_userprofile.subsidiary`.
    - API requests are filtered server-side based on the authenticated user's profile.
    - Attempts to manually access other subsidiaries' data via API are denied.
    - Dashboards are pre-filtered or offer filters constrained by the user's profile.

#### 3.1.7 Operational Dashboards
- **Purpose**: To provide real-time insights into operations, enabling informed decision-making.
- **Functionality**:
  - The system shall provide dashboards displaying summaries of active batches (`batch_batch`), environmental conditions (`environmental_environmentalreading` summaries), weather data (`environmental_weatherdata`), and key performance indicators.
  - Dashboards shall include metrics like growth rate (derived from `batch_growthsample`), total biomass_kg (aggregated from `batch_batchcontainerassignment`), and health status indicators (derived from recent `health_journalentry` data).
  - Dashboards shall be role-specific and automatically filtered by geography and subsidiary based on the logged-in user's `users_userprofile`.
  - The system shall support exporting dashboard views or underlying data (e.g., charts as images, tables as CSV/PDF).
- **Behavior**:
  - Dashboards shall load efficiently (target < 3-5 seconds) by optimizing database queries (using `select_related`, `prefetch_related`, TimescaleDB functions) and frontend rendering.
  - Metrics shall update based on a defined refresh interval or triggered by significant events.
  - Filters relevant to the user's context shall apply efficiently.
- **Justification**: Enhances situational awareness and supports proactive management.
- **User Story**: As a Manager, I want to view a dashboard of active batches (`batch_batch`) within my geography (`users_userprofile.geography_id`) so that I can monitor their status.
  - **Acceptance Criteria**:
    - The dashboard displays active batches filtered by geography, showing key metrics (e.g., current stage distribution from `batch_batchcontainerassignment`, total `biomass_kg`, average growth rate).
    - Environmental condition summaries (e.g., avg/min/max temp) and current weather for relevant areas are visualized.
    - Filters allow users to further refine view by subsidiary if applicable within their permissions.
    - Users can export the current dashboard view as a PDF or image.

#### 3.1.8 Broodstock Management (broodstock app)

**Purpose**  
The Broodstock Management module in AquaMind is a core component of the salmon farming lifecycle, enabling broodstock managers and farm operators to oversee broodstock populations, manage breeding operations, track egg production and acquisition, and ensure comprehensive traceability. It supports both internally produced eggs from broodstock and externally sourced eggs from third-party suppliers, providing flexible lineage tracking critical for quality control, operational planning, and regulatory compliance. Designed with the same usability and implementability as Scenario Planning, this feature focuses on practical, essential capabilities without advanced predictive analytics, ensuring broodstock management aligns with AquaMind's goal of optimizing salmon farming processes.

**Functionality**  
This section details the comprehensive capabilities of the Broodstock Management module, structured into key functional areas:

- **Broodstock Container Management**  
  - **Description:** Manage containers housing broodstock fish using the existing `infrastructure_container` model, designated with a `containertype` of "broodstock" selected from `infrastructure_containertype`.  
  - **Specifications:**  
    - Maintain a detailed inventory of broodstock containers, capturing unique IDs, physical locations (e.g., site, building, room), capacities (fish or biomass limits), and statuses (e.g., "active", "under maintenance", "quarantine").  
    - Schedule and log maintenance tasks such as cleaning, repairs, or equipment checks via the `MaintenanceTask` model, with fields for task type, scheduled and completed dates, and notes.  
    - Integrate real-time environmental monitoring (e.g., temperature, dissolved oxygen, photoperiod) through the `environmental` app, linking to `infrastructure_container` via `container_id`.  
    - Provide a dashboard displaying container statuses, upcoming maintenance tasks, and environmental alerts, with filters for location and type.  
    - Support mobile access for viewing container details and logging maintenance tasks on-site.  
  - **Data Requirements:** Container ID, location (site, building, room), capacity (numeric), status (enum), maintenance task details (type, dates, notes), environmental sensor data (parameter, value, timestamp).

- **Fish Population Tracking**  
  - **Description:** Track individual broodstock fish and population aggregates within containers using `BroodstockFish` and `FishMovement` models, ensuring accurate counts and lineage data.  
  - **Specifications:**  
    - Record individual fish details including unique IDs, current container assignments, basic traits (e.g., growth rate, size), and health statuses (via integration with the `health` app).  
    - Log fish movements between containers using `FishMovement`, capturing source and destination containers, movement dates, and responsible users, with automatic population updates.  
    - Maintain population summaries per container, showing total fish counts, average health status, and movement history.  
    - Link fish to breeding events for internal egg traceability, ensuring parentage data is preserved.  
    - Enable mobile entry of fish movements and health observations, with offline sync capability.  
  - **Data Requirements:** Fish ID, container ID (FK), traits (JSON), health status (enum), movement history (from/to container IDs, date, user), population aggregates (count, status).

- **Breeding Operations**  
  - **Description:** Facilitate breeding planning and execution, prioritizing traits and assigning pairs to optimize egg production, tracked via `BreedingPlan`, `BreedingTraitPriority`, and `BreedingPair`.  
  - **Specifications:**  
    - Define breeding plans with start/end dates and objectives (e.g., egg yield, trait enhancement) using `BreedingPlan`.  
    - Set trait priorities (e.g., growth rate, disease resistance) with weights in `BreedingTraitPriority`, guiding pair selection.  
    - Assign breeding pairs manually or via basic trait-matching suggestions in `BreedingPair`, linking male and female `BroodstockFish` IDs with pairing dates and expected progeny counts.  
    - Log breeding events with timestamps and user details, integrating with egg production records.  
    - Provide a breeding dashboard showing active plans, pair statuses, and trait priority summaries.  
  - **Data Requirements:** Plan ID, name, dates, trait priorities (name, weight), pair details (male/female fish IDs, date, progeny count), event logs (timestamp, user).

- **Egg Production and Acquisition**  
  - **Description:** Manage egg production from internal broodstock and acquisition from external suppliers, ensuring traceability with `EggProduction`, `EggSupplier`, and `ExternalEggBatch`.  
  - **Specifications:**  
    - Record internal egg production events linked to `BreedingPair`, generating unique `egg_batch_id`s in `EggProduction`, with egg counts, production dates, and destination stations.  
    - Log external egg batches via `ExternalEggBatch`, capturing supplier details from `EggSupplier` (e.g., name, certifications), batch numbers, and provenance data (e.g., source farm, transport conditions).  
    - Assign eggs (internal or external) to freshwater batches via `BatchParentage`, linking `egg_batch_id` to `batch_batch`.  
    - Support mobile logging of egg production and acquisition, with validation for egg counts and supplier data.  
    - Display egg batch summaries, distinguishing internal vs. external sources, with links to lineage details.  
  - **Data Requirements:** Egg batch ID, pair ID (nullable), egg count, production/acquisition date, supplier ID, batch number, provenance data, batch ID (FK).

- **Environmental Monitoring and Control**  
  - **Description:** Monitor and adjust broodstock container conditions using the `environmental` app, ensuring optimal health and productivity.  
  - **Specifications:**  
    - Capture real-time environmental data (e.g., temperature, pH, photoperiod) via `environmental_environmentalreading`, linked to `infrastructure_container`.  
    - Define and apply environmental schedules (e.g., light cycles) per container using `environmental_photoperioddata`, with start/end times and parameter targets.  
    - Generate alerts for parameter deviations (e.g., temperature > 25°C), viewable on dashboards and mobile devices.  
    - Log manual or automated adjustments (e.g., heater activation) with timestamps and user/system details.  
    - Provide historical environmental trends per container for analysis.  
  - **Data Requirements:** Container ID, parameter type, reading value, timestamp, schedule details (start/end, target), alert logs (condition, timestamp), adjustment logs.

- **Operational Planning with Scenarios**  
  - **Description:** Leverage Scenario Planning tools to plan broodstock operations, integrating internal and external egg sourcing strategies.  
  - **Specifications:**  
    - Create broodstock scenarios in the `scenario` model, specifying parameters like breeding schedules, egg production targets, or external sourcing ratios.  
    - Compare scenarios based on outcomes (e.g., egg yield, cost, resource use), reusing Scenario Planning's comparison logic.  
    - Link scenarios to specific containers or egg batches for execution tracking.  
    - Coordinate with freshwater stations for egg handoffs, ensuring batch creation aligns with scenario plans.  
    - Support mobile scenario review and basic edits (e.g., adjusting timelines).  
  - **Data Requirements:** Scenario ID, name, parameters (JSON), outcomes (yield, cost), linked containers/egg batches, station handoff details.

- **Traceability and Lineage Management**  
  - **Description:** Ensure end-to-end traceability from broodstock to batch for internal eggs and from supplier to batch for external eggs, with audit trails.  
  - **Specifications:**  
    - Link internal egg batches (`EggProduction`) to breeding pairs and progeny batches (`BatchParentage`), preserving parent fish IDs and breeding dates.  
    - Record external egg batches (`ExternalEggBatch`) with supplier provenance, linking to `batch_batch` without broodstock data.  
    - Generate lineage reports showing batch origins (e.g., "Batch B123 from Pair P456" or "Batch B124 from Supplier S789").  
    - Maintain immutable audit trails for breeding, egg production/acquisition, and batch creation using `django-auditlog`.  
    - Provide mobile access to lineage queries and report exports.  
  - **Data Requirements:** Egg batch ID, pair ID (nullable), batch ID, parentage/supplier details, audit logs (event, timestamp, user).

- **Mobile Access**  
  - **Description:** Enable on-site management via mobile apps, supporting real-time data entry and monitoring.  
  - **Specifications:**  
    - View container statuses, environmental readings, fish details, and lineage data (internal/external) on mobile devices.  
    - Log maintenance tasks, fish movements, breeding events, egg production/acquisition, and environmental adjustments offline, syncing when online.  
    - Receive and acknowledge environmental alerts remotely, with push notifications.  
    - Ensure offline mode preserves data integrity and audit trails.  
  - **Data Requirements:** User actions (task logs, movements), data entries (fish, eggs), alert responses (timestamp, user), sync logs.

- **Reporting**  
  - **Description:** Deliver detailed reports for operational insights and traceability, with export options.  
  - **Specifications:**  
    - Generate reports on container usage, fish populations, breeding outcomes, egg production (internal/external), and batch lineage.  
    - Offer prebuilt templates (e.g., "Broodstock-to-Batch Traceability", "External Egg Sourcing Summary").  
    - Support PDF/CSV exports for sharing with stakeholders or regulators.  
    - Display trends (e.g., egg output by month, internal vs. external sourcing ratios) with basic visualizations.  
    - Allow report generation from mobile devices, with export queued for sync.  
  - **Data Requirements:** Report type, parameters (e.g., date range), generated data (counts, lineage), export logs (format, timestamp).

**Behavior**  
- *Container Management:* Status updates occur in real time based on sensor inputs or manual entries; maintenance tasks trigger notifications when due, updating container status upon completion.  
- *Fish Tracking:* Population counts adjust instantly with `FishMovement` entries; health status changes (via `health` app) reflect in summaries; lineage links remain immutable for internal eggs.  
- *Breeding Operations:* Pair assignments in `BreedingPair` lock fish availability, triggering `EggProduction` records upon egg collection, with automatic batch linkage.  
- *Egg Acquisition:* External egg entries in `ExternalEggBatch` bypass breeding data, directly creating batches via `BatchParentage`.  
- *Environmental Monitoring:* Parameter deviations trigger immediate alerts; schedules apply consistently, with logs capturing all changes.  
- *Traceability:* Lineage queries return complete origins (internal: broodstock pair; external: supplier), with audit trails ensuring data integrity.  
- *Scenarios:* Plans integrate broodstock and egg sourcing options, updating dynamically with operational data.  
- *Mobile:* Offline entries sync seamlessly, preserving timestamps and user attribution for traceability.

**Justification**  
Broodstock management underpins salmon farming success, directly impacting egg quality and production efficiency. This module provides robust tools for container management, fish tracking, breeding, and egg sourcing, with flexible traceability addressing both internal and external workflows. Integration with Scenario Planning enhances strategic decision-making, while mobile access and detailed reporting ensure operational agility and compliance, aligning with AquaMind's mission to streamline salmon farming without unnecessary complexity.

**User Stories and Acceptance Criteria**

- *User Story 1: Managing Broodstock Containers*  
  **As a Broodstock Manager, I want to monitor and maintain broodstock containers to ensure optimal conditions for fish health and breeding.**  
  - **Acceptance Criteria:**  
    - View a list of containers filtered by location/status, showing ID, capacity, and real-time environmental data.  
    - Schedule a maintenance task (e.g., "clean tank") with a due date and receive a notification when due.  
    - Log task completion on mobile, updating container status to "active".  
    - Dashboard highlights overdue tasks and environmental alerts (e.g., "Temperature > 25°C").

- *User Story 2: Tracking Fish Populations*  
  **As a Farm Operator, I want to track fish movements and health to maintain accurate population data and support breeding decisions.**  
  - **Acceptance Criteria:**  
    - Enter a fish movement (e.g., Fish F123 from Container C1 to C2) on mobile, updating population counts instantly.  
    - View a container's fish list with IDs, traits, and health statuses from the `health` app.  
    - Search a fish by ID and see its movement history and current location.  
    - Summary shows total fish, average health, and recent movements per container.

- *User Story 3: Planning and Executing Breeding*  
  **As a Broodstock Manager, I want to plan breeding operations and assign pairs based on trait priorities to optimize egg production.**  
  - **Acceptance Criteria:**  
    - Create a breeding plan with start/end dates and trait priorities (e.g., "growth rate: 0.7").  
    - Assign a male and female fish as a pair, manually or via trait suggestions, locking their availability.  
    - Log a breeding event with 10,000 eggs produced, generating an `egg_batch_id` linked to the pair.  
    - Dashboard shows active plans, pair statuses, and expected egg yields.

- *User Story 4: Managing Egg Sources*  
  **As an Aquaculture Manager, I want to record internal egg production and external egg purchases to track all batch origins.**  
  - **Acceptance Criteria:**  
    - Record an internal egg batch (e.g., 10,000 eggs from Pair P456) with production date and destination station.  
    - Log an external egg batch (e.g., 15,000 eggs from Supplier S789) with supplier details and certifications.  
    - Assign eggs to a batch (e.g., B123), linking via `BatchParentage` with immutable records.  
    - View egg batch summaries distinguishing internal vs. external sources.

- *User Story 5: Ensuring Traceability*  
  **As a Quality Control Officer, I want to trace a batch to its broodstock or supplier to verify its provenance for audits.**  
  - **Acceptance Criteria:**  
    - Select Batch B123 and view its origin (e.g., "Pair P456, bred 2023-10-01" or "Supplier S789, acquired 2023-10-02").  
    - Generate a lineage report showing parent fish IDs (internal) or supplier provenance (external).  
    - Audit trail lists all events (e.g., breeding, acquisition, batch creation) with timestamps/users.  
    - Export the report as PDF from mobile or desktop.

**Additional Considerations**  
- *Scalability:* Support thousands of containers, fish, and egg batches with optimized queries and indexing on `container_id`, `fish_id`, and `egg_batch_id`.  
- *Usability:* Design intuitive interfaces, clearly separating internal and external egg workflows, with tooltips for new users.  
- *Integration:* Reuse `environmental` for monitoring, `health` for fish status, and Scenario Planning for operational strategies.  
- *Reliability:* Ensure mobile sync preserves data integrity; sensor failures trigger fallback manual entry with logs.  
- *Traceability:* Guarantee immutable lineage links and audit trails, meeting regulatory standards for both egg sources.

### 3.2 Phase 2: Operational Planning and Compliance

#### 3.2.1 Operational Planning
- **Purpose**: To optimize resource allocation and operational workflows through data-driven insights.
- **Functionality**:
  - The system shall provide real-time infrastructure monitoring, tracking container status, sensor health, and asset utilization.
  - The system shall include a recommendation engine for:
    - Batch transfers based on lifecycle stage, container capacity, and environmental conditions.
    - Feed optimization based on batch needs and inventory levels.
    - Resource allocation (e.g., staff scheduling, equipment usage).
  - The system shall generate actionable insights for operational planning, such as:
    - Predicting container overcrowding and recommending transfers.
    - Identifying underutilized assets and suggesting reallocation.
    - Optimizing feed schedules to minimize waste.
  - The system shall allow users to accept, reject, or modify recommendations, logging the decision.
  - The system shall provide a planning dashboard with visualizations of resource usage and operational bottlenecks.
- **Behavior**:
  - Recommendations shall be updated daily or on-demand based on new data.
  - Planning dashboards shall display real-time metrics with predictive insights.
  - User decisions on recommendations shall be logged with timestamps and rationale.
- **Justification**: Enhances operational efficiency, reduces costs, and improves resource utilization.
- **User Story**: As a Farm Operator, I want to receive recommendations for batch transfers so that I can optimize container usage.
  - **Acceptance Criteria**:
    - The system suggests transfers based on lifecycle stage, container capacity, and environmental data.
    - Recommendations include rationale (e.g., "Container at 90% capacity").
    - Users can accept, reject, or modify the recommendation.
    - Accepted transfers are logged and executed with user confirmation.
- **User Story**: As a Manager, I want to view a planning dashboard so that I can identify operational bottlenecks.
  - **Acceptance Criteria**:
    - The dashboard displays resource usage (e.g., container occupancy, staff allocation).
    - Predictive insights highlight potential issues (e.g., "Container X at risk of overcrowding").
    - Visualizations include charts for utilization trends over time.
    - Users can drill down into specific assets or batches for details.

#### 3.2.2 Regulatory Compliance and Reporting
- **Purpose**: To ensure compliance with environmental, health, and financial regulations in the Faroe Islands and Scotland.
- **Functionality**:
  - The system shall generate reports for regulatory compliance, including:
    - Environmental impact reports (e.g., water quality, waste metrics).
    - Health compliance reports (e.g., treatment usage, vaccination records).
    - Financial compliance reports (e.g., feed costs, operational expenses).
  - The system shall track compliance metrics, such as:
    - Environmental readings within acceptable thresholds.
    - Treatment usage within regulatory limits.
    - Mortality rates and causes for reporting.
  - The system shall provide audit trails for all user actions, health events, and environmental data changes.
  - The system shall support configurable reporting templates for different regulatory bodies.
  - Reports shall be exportable in PDF and CSV formats.
- **Behavior**:
  - Compliance metrics shall be monitored in real-time with alerts for violations.
  - Reports shall include timestamps, user details, and data sources for traceability.
  - Audit trails shall be immutable and accessible to compliance officers.
- **Justification**: Ensures adherence to regulations, avoids penalties, and maintains operational integrity.
- **User Story**: As a Compliance Officer, I want to generate an environmental impact report so that I can submit it to authorities.
  - **Acceptance Criteria**:
    - The UI allows users to select a report type (e.g., environmental impact).
    - The report includes metrics (e.g., water quality, waste levels) with timestamps.
    - The report is exportable in PDF and CSV formats.
    - Audit trails for environmental data changes are included in the report.
- **User Story**: As a Compliance Officer, I want to receive alerts for regulatory violations so that I can take corrective action.
  - **Acceptance Criteria**:
    - Alerts are generated for violations (e.g., "Temperature exceeded safe limit").
    - Alerts include details (e.g., container, timestamp, reading value).
    - Users can view a history of violations and actions taken.
    - Corrective actions (e.g., adjust environmental controls) are logged.

#### 3.2.3 Enhanced Broodstock Management
- **Purpose**: To advance genetic improvement through detailed broodstock analysis and breeding simulations.
- **Functionality**:
  - The system shall integrate with external genetic analysis tools to import SNP panel data and breeding values.
  - The system shall support broodstock scenario planning, simulating breeding outcomes based on genetic traits and environmental conditions.
  - The system shall track advanced broodstock metrics, such as:
    - Breeding values for traits like disease resistance and growth rate.
    - Inbreeding coefficients to ensure genetic diversity.
    - Offspring performance linked to broodstock parents.
  - The system shall recommend breeding pairs based on genetic data and desired traits.
  - The system shall log breeding program outcomes for future analysis.
- **Behavior**:
  - Scenarios shall allow users to adjust parameters (e.g., environmental conditions, trait priorities).
  - Recommendations shall include predicted outcomes (e.g., offspring traits).
  - Breeding outcomes shall be compared against predictions for validation.
- **Justification**: Enhances genetic improvement, supports long-term sustainability, and improves fish quality.
- **User Story**: As a Broodstock Manager, I want to simulate breeding outcomes so that I can plan the next generation.
  - **Acceptance Criteria**:
    - The UI allows users to create scenarios with broodstock pairs and environmental parameters.
    - The system simulates outcomes (e.g., offspring traits, growth rates) and displays results.
    - Results are saved for future reference and comparison.
    - Users can adjust parameters and re-run simulations.
- **User Story**: As a Broodstock Manager, I want to receive breeding pair recommendations so that I can optimize genetic outcomes.
  - **Acceptance Criteria**:
    - The system suggests pairs based on genetic data (e.g., SNP panels, breeding values).
    - Recommendations include predicted outcomes (e.g., disease resistance score).
    - Users can accept or reject recommendations, logging the decision.
    - Inbreeding risks are highlighted with mitigation suggestions.

### 3.3 Phase 3: AI Enablement

#### 3.3.1 Scenario Planning and Simulation

**Purpose**  
The Scenario Planning and Simulation feature in AquaMind enables aquaculture managers, production planners, and farm operators to create, manage, and analyze hypothetical scenarios for salmon farming operations. By leveraging configurable biological models—namely the Thermal Growth Coefficient (TGC) model, Feed Conversion Ratio (FCR) model, and mortality model—this feature projects key metrics such as fish growth (average weight), population (number of fish), biomass, feed consumption, and optimal harvest times. This functionality supports data-driven decision-making for critical operations including stocking, feeding schedules, resource allocation, and harvest planning, aligning with AquaMind's goal of optimizing operational efficiency, sustainability, and profitability in salmon farming.

**Functionality**  
The Scenario Planning and Simulation feature comprises several interconnected components designed to provide flexibility and precision in planning:

- **Model Management**  
  - *TGC Models:*  
    - **Description:** Thermal Growth Coefficient (TGC) models calculate daily growth increments based on temperature and time, critical for projecting salmon weight gain across lifecycle stages.  
    - **Specifications:**  
      - Supports creation of multiple TGC models tailored to specific locations and release periods (e.g., "Faroe Islands, January Release," "Scotland Location X, April Release").  
      - Accommodates up to one temperature change per day, though typically updated weekly based on historical or projected environmental data.  
      - Variations account for regional differences:  
        - **Faroe Islands:** Stable sea temperatures due to the Gulf Stream, resulting in simpler, less variable TGC models.  
        - **Scotland:** Diverse locations with fluctuating temperatures, requiring distinct models per site and release timing (e.g., summer vs. winter transfers to sea).  
      - Users can define new TGC models or select from a library, specifying temperature profiles and growth coefficients.  
    - **Data Requirements:** Each model requires a location identifier, release period, and a temperature profile (daily or weekly values).  
  - *FCR Models:*  
    - **Description:** Feed Conversion Ratio (FCR) models estimate feed efficiency by defining the ratio of feed consumed to weight gained per lifecycle stage.  
    - **Specifications:**  
      - FCR values are assigned to each salmon lifecycle stage, for example:  
        - **Egg/Alevin:** No FCR (feeding from yolk sac).  
        - **Fry:** FCR 1.0 (90-100 days in freshwater).  
        - **Parr:** FCR 1.1 (90-100 days in freshwater).  
        - **Smolt:** FCR 1.0 (90-100 days in freshwater).  
        - **Post-Smolt:** FCR 1.1 (transition to sea).  
        - **Adult:** FCR 1.2 (~400 days in open sea rings).  
      - Users can customize FCR values per stage or use predefined defaults.  
    - **Data Requirements:** Stage-specific FCR values and stage duration in days.  
  - *Mortality Models:*  
    - **Description:** Mortality models estimate population decline over time using percentage-based rates.  
    - **Specifications:**  
      - Supports daily or weekly mortality rates (e.g., 0.1% per day or 0.7% per week).  
      - Rates can remain constant or vary by lifecycle stage or environmental conditions.  
      - Users can define custom rates or select from historical averages.  
    - **Data Requirements:** Mortality rate (percentage), frequency (daily/weekly), and optional stage-specific adjustments.  

- **Multi-Method Data Entry System**  
  - **Description:** To manage large datasets (up to 900+ daily values for temperature, mortality, and FCR), the system provides multiple intuitive data entry methods that minimize manual input while offering maximum flexibility.  
  - **Specifications:**  
    - *CSV Upload for Bulk Data:*  
      - Users can upload CSV files containing daily values with drag-and-drop or browse functionality.  
      - Downloadable CSV templates ensure correct formatting (e.g., columns: Date, Value).  
      - Upload validation with preview modal for data confirmation before import.  
      - Bulk processing reduces 900+ manual entries to a single upload operation.  
    - *Date Range-Based Input:*  
      - Users specify values for custom date ranges instead of daily entries.  
      - Form interface with Start Date, End Date, and Value fields.  
      - "Add Range" functionality allows stacking multiple periods (e.g., Jan 1–Mar 31: 10°C; Apr 1–Jun 30: 12°C).  
      - "Copy to Next Range" option for quick value adjustments.  
    - *Predefined Profiles and Templates:*  
      - Library of common profiles (e.g., "Northern Europe Summer Temperature," "Standard Salmon Mortality").  
      - Template selection dropdown with customization options.  
      - System templates for standard scenarios and user-created custom templates.  
      - Template versioning and sharing across users/geographies.  
    - *Visual Data Editor:*  
      - Interactive line charts for graphical data adjustment.  
      - Click-and-drag functionality to modify individual points or draw trends.  
      - Zoom and pan controls for precise editing across long timelines.  
      - Real-time chart updates with immediate visual feedback.  
    - *Formula-Based Input:*  
      - Pattern generation using mathematical formulas (e.g., linear increase, step changes).  
      - Dropdown selection of preset patterns (Constant, Linear Increase, Seasonal Variation).  
      - Parameter input fields based on selected pattern (Start Value, End Value, Duration).  
      - Automatic data generation eliminating repetitive manual entry.  
    - *Real-Time Feedback and Preview:*  
      - Live preview charts/tables updating as users modify data.  
      - Summary statistics display (average temperature, total mortality).  
      - Data validation with immediate error highlighting.  
      - Export preview functionality before final model creation.  

- **Scenario Creation**  
  - **Description:** Users create scenarios by combining TGC, FCR, and mortality models with initial conditions to simulate salmon farming outcomes.  
  - **Specifications:**  
    - *Inputs:*  
      - Selection of TGC, FCR, and mortality models from the model library.  
      - Initial conditions: start date, duration (in days), initial fish count, genotype and supplier (can come from own Broodstock or external supplier).
      - NB! At the outset it is not necessary to define start weight
      - Optional linkage to existing batches via `batch_batch` for real-data initialization.  
    - *Types:*  
      - **Hypothetical Scenarios:** Based on user-defined initial conditions.  
      - **Batch-Based Scenarios:** Initialized with current data from an existing batch.  
    - *Features:*  
      - Ability to duplicate scenarios for comparative analysis.  
      - Option to adjust parameters mid-simulation (e.g., change FCR model at a specific date).  

- **Configurable Biological Parameters**  
  - **Description:** The system provides flexible, admin-configurable biological parameters to accommodate different operational strategies and research findings.  
  - **Architecture:**  
    ```mermaid
    graph TD
        A[Biological Constraints System] --> B[BiologicalConstraints]
        B --> C[StageConstraint]
        
        B --> D["Bakkafrost Standard<br/>300g+ smolt target"]
        B --> E["Conservative<br/>Traditional limits"]
        
        C --> F[Weight Ranges]
        C --> G[Temperature Ranges]
        C --> H[Freshwater Limits]
        
        I[TGC Model] --> J[TGCModelStage]
        K[FCR Model] --> L[FCRModelStage]
        L --> M[FCRModelStageOverride]
        N[Mortality Model] --> O[MortalityModelStage]
        
        P[Scenario] --> B
        P --> I
        P --> K
        P --> N
        
        style D fill:#90EE90
        style E fill:#FFE4B5
        style P fill:#87CEEB
    ```
  - **Specifications:**  
    - *Biological Constraint Sets:*  
      - Named sets of biological rules (e.g., "Bakkafrost Standard", "Conservative", "Experimental").  
      - Stage-specific weight ranges, temperature ranges, and freshwater limits.  
      - Permission-based management (only scenario admin users can modify).  
    - *Stage-Specific Overrides:*  
      - TGC values and exponents can vary by lifecycle stage.  
      - FCR values can have weight-based variations within stages.  
      - Mortality rates can be customized per stage.  
    - *Flexibility:*  
      - No hardcoded limits - all parameters database-configurable.  
      - Support for company-specific targets (e.g., Bakkafrost's 300g+ smolt).  
      - Easy adjustment based on latest research findings.  

- **Projection Calculations**  
  - **Description:** The system calculates projections based on the selected models and initial conditions.  
  - **Specifications:**  
    - *Growth Projection:*  
      - Daily weight increase calculated using the TGC model:  
        `Daily Growth = TGC * (Temperature)^n * (Current Weight)^m`  
        (where `n` and `m` are model-specific exponents, typically provided in the TGC model definition).  
      - Stage-specific TGC values applied when configured.  
      - Aggregated to weekly/monthly averages for display.  
    - *Population Projection:*  
      - Daily or weekly population decrease:  
        `New Population = Current Population * (1 - Mortality Rate)`  
        Applied per time step based on model frequency.  
      - Stage-specific mortality rates used when available.  
    - *Biomass Projection:*  
      - `Biomass (kg) = Population * Average Weight / 1000`.  
    - *Feed Consumption:*  
      - `Daily Feed (kg) = Daily Growth * FCR * Population / 1000`.  
      - Stage and weight-specific FCR values applied.  
      - Accumulated over the scenario duration.  
    - *Harvest Timing:*  
      - Identifies dates when average weight reaches user-defined target weights (e.g., 4.5 kg).  
      - Considers biomass constraints and harvest plant capacities (if linked to operational data).  

- **Visualization and Analysis**  
  - **Description:** Provides intuitive displays and tools to interpret scenario outcomes.  
  - **Specifications:**  
    - *Charts:*  
      - Line graphs for average weight, population, biomass, and feed consumption over time.  
      - Configurable time scales (daily, weekly, monthly).  
    - *Comparison:*  
      - Side-by-side visualization of multiple scenarios (e.g., standard vs. increased feeding).  
      - Highlight differences in harvest timing and biomass.  
    - *Export:*  
      - Data exportable in CSV format (columns: Date, Weight, Population, Biomass, Feed).  
      - Chart snapshots in PNG/PDF.  

**Behavior**  
- *Model Application:*  
  - TGC models apply daily growth increments using the specified temperature profile, defaulting to the last known value if no update is provided.  
  - Mortality rates adjust population continuously, with daily or weekly recalculation based on model settings.  
  - FCR models transition automatically as fish progress through lifecycle stages, determined by days since scenario start. They rely on the registered growth (TGC) and mortality of the day in order to calculate the feed usage for the same day
- *Dynamic Updates:*  
  - Projections recalculate instantly upon changes to models, initial conditions, or mid-scenario parameter adjustments.  
  - Users receive warnings if data inconsistencies arise (e.g., negative population).  
- *Integration:*  
  - Links to `batch_batch` and `infrastructure_container` for real-time data initialization.  
  - Optionally incorporates environmental data (e.g., temperature from `environmental_environmentalreading`) if available; otherwise, uses user-input projections.  

**Justification**  
Scenario planning is a cornerstone of salmon farming management, enabling proactive optimization of harvest schedules, feed usage, and resource allocation. By integrating configurable TGC, FCR, and mortality models, AquaMind provides precise, location-specific projections that reflect real-world variability (e.g., stable Faroe Islands vs. fluctuating Scotland conditions). This feature reduces operational risks, enhances feed efficiency, and ensures compliance with biomass limits, directly supporting AquaMind's objectives of operational excellence and sustainable aquaculture.

**User Stories and Acceptance Criteria**

- *User Story 1: Creating a Location-Specific Growth Scenario*  
  **As a Production Planner at Bakkafrost, I want to simulate the growth of a smolt batch released in April at a Scotland site, so I can determine the optimal harvest time and feed requirements.**  
  - **Acceptance Criteria:**  
    - The user can select a TGC model for "Scotland Location X, April Release" with weekly temperature updates.  
    - The user assigns an FCR model with stage-specific values (Smolt: 1.0, Post-Smolt: 1.1, Adult: 1.2).  
    - The user sets a weekly mortality rate of 0.5%.  
    - The user inputs: start date (e.g., April 1, 2024), initial count (100,000 fish), initial weight (50g), duration (600 days).  
    - The system generates projections for:  
      - Average weight reaching 4.5 kg around day 550.  
      - Population decreasing to ~92,000 fish by harvest.  
      - Biomass peaking at ~414 tons.  
      - Total feed consumption of ~450 tons.  
    - A chart displays weight and biomass trends, with a harvest date marker at 4.5 kg.  

- *User Story 2: Comparing Feeding Strategies*  
  **As a Farm Manager, I want to compare two scenarios for a Faroe Islands batch—one with standard feeding and one with a higher FCR—to assess impacts on growth and harvest timing.**  
  - **Acceptance Criteria:**  
    - The user creates Scenario A with a TGC model for "Faroe Islands, January Release," FCR (Adult: 1.2), and 0.3% weekly mortality.  
    - The user duplicates it as Scenario B, adjusting Adult FCR to 1.3.  
    - Both scenarios start with 50,000 fish at 100g on January 1, 2024, for 500 days.  
    - The system displays side-by-side charts showing:  
      - Scenario A: Harvest at 4.5 kg on day 480, feed use ~200 tons.  
      - Scenario B: Harvest at 4.5 kg on day 490, feed use ~215 tons.  
    - The user exports both datasets in CSV for stakeholder review.  

- *User Story 3: Batch-Based Planning*  
  **As an Aquaculture Manager, I want to project the future state of an existing batch using its current data, so I can plan resource needs accurately.**  
  - **Acceptance Criteria:**  
    - The user selects an existing batch from `batch_batch` (e.g., 75,000 fish, 1.5 kg average weight, Smolt stage).  
    - The user applies a TGC model for the batch's location, the default FCR model, and a 0.2% daily mortality rate.  
    - The system projects from the current date forward 300 days, showing:  
      - Transition to Post-Smolt and Adult stages with corresponding FCR shifts.  
      - Biomass reaching 300 tons by day 250.  
    - The projection aligns with real-time batch data at the starting point.  

**Additional Considerations**  
- *Scalability:* The system must handle hundreds of scenarios and models without performance degradation, caching frequent calculations and supporting bulk data operations.  
- *Usability:* Multi-method data entry system reduces complexity from 900+ manual inputs to manageable operations through CSV uploads, templates, and automated pattern generation. Model selection features guided wizards with validation and preview capabilities.  
- *Data Entry Efficiency:* Template library and formula-based generation enable rapid model creation, while visual editors provide intuitive adjustment capabilities for fine-tuning.  
- *User Experience:* Real-time feedback, preview functionality, and multiple input methods accommodate different user preferences and skill levels.  
- *Extensibility:* Modular data entry framework allows future integration of additional models (e.g., oxygen levels) and input methods.  
- *Validation:* Comprehensive input validation across all entry methods ensures realistic values, with immediate feedback and error prevention.

#### 3.3.2 Predictive Health Management
- **Purpose**: To proactively manage batch health using AI-driven insights.
- **Functionality**:
  - The system shall predict health risks (e.g., disease outbreaks, lice infestations) using environmental data, health records, and batch history.
  - The system shall recommend preventive actions (e.g., treatments, environmental adjustments).
  - The system shall provide confidence scores for predictions (e.g., "80% confidence in lice risk").
  - The system shall log prediction accuracy for continuous improvement.
- **Behavior**:
  - Predictions shall be updated daily or on-demand.
  - Recommendations shall include actionable steps with expected outcomes.
  - Alerts shall be sent via the UI and email for high-risk predictions.
- **Justification**: Reduces health risks, improves batch survival rates, and supports regulatory compliance.
- **User Story**: As a Farm Operator, I want to receive alerts for potential health risks so that I can take preventive action.
  - **Acceptance Criteria**:
    - Alerts are generated for predicted risks (e.g., "High lice risk detected").
    - Alerts include confidence scores and recommended actions.
    - Users can view the data (e.g., environmental trends) that triggered the alert.
    - Actions taken in response to alerts are logged.

#### 3.3.3 Genomic Prediction
- **Purpose**: To optimize breeding outcomes using AI-driven genetic analysis.
- **Functionality**:
  - The system shall predict genetic outcomes for broodstock offspring using SNP panel data and breeding values.
  - The system shall recommend breeding pairs to optimize desired traits (e.g., disease resistance, growth rate).
  - The system shall provide visualizations of predicted genetic outcomes (e.g., trait distribution).
  - The system shall integrate with external genetic tools for data import and validation.
- **Behavior**:
  - Predictions shall include confidence intervals for accuracy.
  - Recommendations shall prioritize user-defined traits (e.g., disease resistance over growth rate).
  - Visualizations shall allow users to compare predicted vs. actual outcomes.
- **Justification**: Enhances genetic improvement, reduces trial-and-error in breeding, and improves fish quality.
- **User Story**: As a Broodstock Manager, I want to receive breeding pair recommendations so that I can improve genetic outcomes.
  - **Acceptance Criteria**:
    - The system suggests pairs based on genetic data and user-defined priorities.
    - Recommendations include predicted outcomes (e.g., offspring trait scores).
    - Visualizations show trait distribution for predicted offspring.
    - Users can accept or reject recommendations, logging the decision.

## 4. Non-Functional Requirements

### 4.1 Performance
- Handle target batch/container load with specified real-time data frequency (e.g., 10k batches, ~1 reading/min/container). Database queries optimized for large datasets.
- API response times: Target < 500ms (95th percentile) for common read operations.
- Dashboard load times: Target < 3-5 seconds, utilizing efficient aggregation and frontend rendering.

### 4.2 Scalability
- Architecture supports adding geographies/subsidiaries (consider impact on filtering/querying).
- TimescaleDB efficiently handles growing time-series data volume. Ensure proper indexing and hypertable management. Database connection pooling configured appropriately.

### 4.3 Security
- Row-level security consistently enforced via permissions/querysets in APIs.
- JWT authentication secure implementation with appropriate token lifetimes and refresh mechanisms.
- Comprehensive audit trails via `django-auditlog` covering critical models and user actions.
- Data encryption at rest/transit for sensitive information (PII, potentially health/genetic data).
- Adherence to Django security best practices (CSRF, XSS, SQL Injection prevention).

### 4.4 Usability
- Intuitive UI/UX tailored to user roles.
- Multi-language support framework (English first).
- In-app help/tooltips for complex workflows.

### 4.5 Integration
- Robust and fault-tolerant integration with WonderWare (Sensor data). Error handling and monitoring.
- Robust integration with OpenWeatherMap (Weather data). Error handling and monitoring.
- Planned integration with genetic analysis tools (Phase 2/3).
- Well-documented RESTful APIs using OpenAPI/Swagger schema generation.

## 5. Success Metrics

*(Metrics remain largely the same as the revised PRD, but should be tracked against the specific functionalities)*
- **Phase 1 (MVP)**: High user adoption/success rate for core tasks (batch tracking, health logging); Dashboard performance met; Feed recommendation adoption rate; Initial broodstock tracking functional.
- **Phase 2**: High acceptance rate for planning recommendations; Error-free compliance report generation; Measurable improvement in broodstock scenario planning outcomes; Reduction in resource waste.
- **Phase 3**: Measurable reduction in disease outbreaks via predictive health; Scenario planning accuracy targets met; Measurable improvement in offspring traits via genomic prediction.

## 6. Assumptions and Constraints

- **Assumptions**:
  - Users have basic training on aquaculture operations and system usage.
  - External systems (e.g., WonderWare, OpenWeatherMap) provide reliable data.
  - Historical data is available for AI model training in Phase 3.
- **Constraints**:
  - Initial development focuses on Faroe Islands and Scotland, with other geographies added later.
  - AI features depend on the availability of sufficient historical data for training models.

## 7. Glossary
*(Glossary remains largely the same but ensure terms map directly to model/concept names used)*
- **Area**: `infrastructure_area`
- **Batch**: `batch_batch`
- **BatchContainerAssignment**: `batch_batchcontainerassignment` - Links a Batch to a Container for a specific LifecycleStage, tracking population/weight.
- **Broodstock**: Fish used for breeding (managed initially via `batch_batch`, later with specific models).
- **Container**: `infrastructure_container`
- **Environmental Reading**: `environmental_environmentalreading`
- **Feed Recommendation**: `inventory_feedrecommendation`
- **Freshwater Station**: `infrastructure_freshwaterstation`
- **Genetic Trait**: (Planned Model) `genetic_trait`
- **Hall**: `infrastructure_hall`
- **Health Event / Journal Entry**: `health_journalentry` and related detailed records (`health_licecount`, `health_mortalityrecord`, etc.).
- **Infrastructure**: Models within the `infrastructure` app.
- **JWT Authentication**: JSON Web Token-based authentication.
- **Lifecycle Stage**: `batch_lifecyclestage`
- **Mortality Record**: `health_mortalityrecord` (linked to `health_journalentry`) / `batch_mortalityevent` (direct link to assignment - check consistency)
- **Operational Planning**: (Planned Feature)
- **Photoperiod Data**: `environmental_photoperioddata`
- **Regulatory Compliance**: (Feature Area)
- **Scenario Planning**: (Planned Feature)
- **Sensor**: `infrastructure_sensor`
- **SNP Panel**: (Planned Data Input for Broodstock)
- **Subsidiary**: Field in `users_userprofile`, potentially future model.
- **TimescaleDB**: PostgreSQL extension used for `environmental_environmentalreading`, `environmental_weatherdata`.
- **UserProfile**: `users_userprofile` (linked one-to-one with `auth_user`).