# AquaMind Product Requirements Document (PRD)

## 1. Introduction

### 1.1 Purpose
AquaMind is an aquaculture management system designed to optimize operations for Bakkafrost, a leading aquaculture company operating in the Faroe Islands and Scotland. The system shall provide a unified platform to manage core operational data including infrastructure (`infrastructure_*` models), fish batches (`batch_*` models), environmental conditions (`environmental_*` models), health and inventory (`health_*`, `inventory_*` models), manage broodstock for genetic improvement, and enable data-driven decision-making across subsidiaries (Broodstock, Freshwater, Farming, Logistics). AquaMind shall ensure regulatory compliance, enhance operational efficiency, and support sustainability through advanced analytics, scenario planning, and AI-driven insights.

### 1.2 Scope
This PRD defines the functional and non-functional requirements for AquaMind, covering core operations, broodstock management, operational planning, regulatory compliance, and future AI-driven capabilities. It outlines a phased approach to development, aligning with business goals, user needs, and the `implementation plan and progress.md`. The system shall integrate with external systems (e.g., WonderWare for sensor data, OpenWeatherMap for weather data), comply with regulatory standards in the Faroe Islands and Scotland, and accurately reflect the implemented schema defined in `docs/data model.md`.

### 1.3 Business Drivers
- **Operational Efficiency**: Streamline batch lifecycle management (`batch_batch`, `batch_batchcontainerassignment`), resource allocation (`infrastructure_container`), and inventory tracking (`inventory_feedstock`) across subsidiaries.
- **Regulatory Compliance**: Ensure adherence to environmental, health, and financial regulations in multiple jurisdictions.
- **Genetic Improvement**: Support broodstock management and breeding programs to enhance fish quality, disease resistance, and growth rates (Planned Phase 2/3).
- **Sustainability**: Monitor environmental impact (`environmental_environmentalreading`) and optimize resource usage (`inventory_feedingevent`) to promote sustainable aquaculture practices.
- **Competitive Advantage**: Leverage AI and predictive analytics to improve decision-making and operational outcomes (Planned Phase 3).

### 1.4 Organizational Structure
AquaMind shall support Bakkafrost’s organizational structure:
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
  - The system shall calculate Fulton’s Condition Factor (K-factor) for each growth sample using the formula \(K = 100 \times \frac{W}{L^3}\), where \(W\) is the average weight in grams (`batch_growthsample.avg_weight_g`) and \(L\) is the average length in centimeters (`batch_growthsample.avg_length_cm`) for that specific sample.
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
- **Purpose**: To manage feed resources (`inventory_feed`) and ensure optimal feeding practices for batches.
- **Functionality**:
  - The system shall manage feed types (`inventory_feed`), purchases (`inventory_feedpurchase`), stock levels (`inventory_feedstock` linked to `infrastructure_feedcontainer`), and feeding events (`inventory_feedingevent`).
  - The system shall generate feed recommendations using `inventory_feedrecommendation` based on batch lifecycle stage (`batch_batchcontainerassignment.lifecycle_stage_id`), fish weight (`batch_batchcontainerassignment.avg_weight_g`), and environmental conditions (`environmental_environmentalreading` data).
  - The system shall track feed stock levels (`inventory_feedstock.quantity_kg`) and alert users to low inventory.
  - The system shall log feeding events (`inventory_feedingevent`) linked to specific batch assignments (`inventory_feedingevent.assignment_id`).
  - Feed type suitability for stages is managed via the `inventory_feed_suitable_for_stages` ManyToMany relationship table.
- **Behavior**:
  - Feed recommendations (`inventory_feedrecommendation`) shall update dynamically based on changes in the linked batch assignment or relevant environmental data.
  - Low-stock alerts shall trigger when `inventory_feedstock.quantity_kg` falls below a configurable threshold (e.g., percentage of `infrastructure_feedcontainer.capacity_kg`).
  - Feeding events shall be validated to ensure compatibility with the batch's current stage (via `assignment.lifecycle_stage_id`) and suitable feed types (`inventory_feed_suitable_for_stages`).
- **Justification**: Optimizes feed usage, reduces waste, and supports healthy batch growth.
- **User Story**: As a Farm Operator, I want to receive feed recommendations (`inventory_feedrecommendation`) for a specific batch container assignment (`batch_batchcontainerassignment`) so that I can ensure optimal growth.
  - **Acceptance Criteria**:
    - The UI displays relevant `inventory_feedrecommendation` records linked to the assignment, with details (`recommended_feed_id`, `recommended_quantity_kg`, `reasoning`).
    - Recommendations are demonstrably based on the assignment's `lifecycle_stage_id`, `avg_weight_g`, and relevant environmental data.
    - Users can log an `inventory_feedingevent` directly from the recommendation.
    - Recommendations are updated based on configured frequency (e.g., daily) or significant data changes.
- **User Story**: As a Logistics Manager, I want to track feed stock levels (`inventory_feedstock`) so that I can plan purchases (`inventory_feedpurchase`).
  - **Acceptance Criteria**:
    - The UI displays current `inventory_feedstock.quantity_kg` per `infrastructure_feedcontainer` with visual indicators for low stock.
    - Alerts are sent when stock falls below a defined threshold.
    - Logging `inventory_feedpurchase` records correctly updates associated `inventory_feedstock` levels (likely via signals or scheduled tasks).
    - Historical stock levels are available in a time-series chart.

#### 3.1.4 Health Monitoring (Medical Journal - `health` app)
- **Purpose**: To monitor and document the health of fish batches, ensuring timely interventions through detailed observations and quantified health metrics.
- **Functionality**:
  - The system shall track health events via `health_journalentry` records, linked to specific batch assignments (`health_journalentry.assignment_id`). Entry types (`entry_type` field) include Observation, Diagnosis, Treatment, Vaccination.
  - Specific event details are stored in linked models: `health_licecount`, `health_mortalityrecord` (linked to `health_mortalityreason`), `health_treatment`, potentially `health_vaccinationrecord` (all linked back to `health_journalentry`).
  - Veterinarians (`users_userprofile.role == 'Veterinarian'`) shall be able to log journal entries (`health_journalentry`) with pictures and videos attached (via a separate Media model with generic relations) and quantify health parameters on a 1-to-5 scale (1 being best, 5 being worst) using the defined `health_healthparameter` and `health_healthobservation` models.
  - Quantifiable health parameters shall include:
    - Gill Health: Assesses gill condition (e.g., mucus, lesions).
    - Eye Condition: Evaluates eye clarity and damage.
    - Wounds: Measures skin lesions and severity.
    - Fin Condition: Assesses fin erosion or damage.
    - Body Condition: Evaluates overall physical shape and deformities.
    - Swimming Behavior: Monitors activity levels and movement patterns.
    - Appetite: Assesses feeding response.
    - Mucous Membrane Condition: Evaluates mucus layer on skin.
    - Color/Pigmentation: Monitors abnormal color changes.
  - Health scores for these parameters shall be stored using the `health_healthobservation` model, linking a `health_journalentry` to a `health_healthparameter` with a score (1-5).
  - The system shall provide health trend analysis (e.g., mortality rates aggregated from `health_mortalityrecord`, lice prevalence from `health_licecount`, average health scores over time).
  - The system shall support predefined categories via `health_mortalityreason`, `health_vaccinationtype`, `health_sampletype`.
- **Behavior**:
  - Health records (`health_journalentry` and related tables) shall be timestamped (`created_at`, `updated_at`) and treated as immutable once finalized.
  - Pictures and videos shall be uploaded with a maximum file size of 50MB enforced.
  - Trends, including average health scores for each parameter, shall be visualized on a dashboard with filtering by batch (`batch_batch`), container (`infrastructure_container`), or time range.
  - Entries are linked to the user who created them via `health_journalentry.created_by_id` (FK to `auth_user`).
- **Justification**: Enables proactive health management through standardized, quantifiable assessments, supports regulatory compliance, and improves batch outcomes.
- **User Story**: As a Veterinarian, I want to log a health observation (`health_journalentry`) with pictures, videos, and quantified health scores so that I can document conditions for a specific batch assignment (`batch_batchcontainerassignment`).
  - **Acceptance Criteria**:
    - The UI allows users with appropriate permissions to create a `health_journalentry` linked to a `batch_batchcontainerassignment`.
    - Users can attach text, pictures, and videos.
    - Uploaded media is linked to the journal entry and viewable in the UI.
    - File uploads are validated for size (≤50MB) and allowed formats.
    - The UI provides dropdowns to score health parameters (e.g., gill health, eye condition) on a 1-to-5 scale.
    - Health scores are saved correctly using the `health_healthobservation` model.
    - The entry is automatically linked to the logged-in user (`created_by_id`).
- **User Story**: As a Manager, I want to view health trends for a batch (`batch_batch`) so that I can identify potential issues.
  - **Acceptance Criteria**:
    - The UI displays trends (e.g., mortality rate aggregated from `health_mortalityrecord`, avg lice counts from `health_licecount`, average health scores for each parameter) in a chart format.
    - Users can filter trends by batch, container, or date range.
    - Alerts are generated for trends exceeding configurable thresholds (e.g., weekly mortality rate > 5%, avg gill health score > 3).
    - Detailed health records (`health_journalentry`), including media and health scores, are accessible directly from the trend view.

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
    - The UI components (lists, dashboards) automatically display data filtered by the logged-in user’s `users_userprofile.subsidiary`.
    - API requests are filtered server-side based on the authenticated user's profile.
    - Attempts to manually access other subsidiaries’ data via API are denied.
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

#### 3.1.8 Broodstock Management (Initial Foundation)
- **Purpose**: To manage broodstock populations for genetic improvement and breeding optimization (Note: Full features are planned for Phase 2/3).
- **Functionality (Phase 1 - Basic Tracking)**:
  - The system shall track broodstock populations using the existing `batch_batch` model, possibly identified by a specific `batch_species` or naming convention.
  - Basic tracking of lineage might be handled through notes fields or careful batch naming conventions initially.
  - Environmental condition tracking utilizes existing `environmental` app features applied to containers housing broodstock batches.
  - *(Advanced features like `genetic_trait`, `batch_genetic_profile`, `breeding_program`, `breeding_pair`, and SNP integration are planned for later phases and require new model implementation).*
- **Behavior (Phase 1)**:
  - Broodstock batches are managed using the standard batch workflow regarding container assignment (`batch_batchcontainerassignment`) and basic health/environmental monitoring.
- **Justification**: Establishes foundational tracking within the existing framework before dedicated broodstock models are built.
- **User Story**: As a Broodstock Operator, I want to assign a batch designated as broodstock (`batch_batch`) to a specific container (`infrastructure_container`) and monitor its environmental conditions (`environmental_environmentalreading`).
  - **Acceptance Criteria**:
    - Users can create/assign batches clearly identified as broodstock (e.g., via species link or name).
    - Standard environmental monitoring is available for containers housing these broodstock batches.
    - Standard health events (`health_journalentry`) can be logged against assignments for these broodstock batches.

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
    - Recommendations include rationale (e.g., “Container at 90% capacity”).
    - Users can accept, reject, or modify the recommendation.
    - Accepted transfers are logged and executed with user confirmation.
- **User Story**: As a Manager, I want to view a planning dashboard so that I can identify operational bottlenecks.
  - **Acceptance Criteria**:
    - The dashboard displays resource usage (e.g., container occupancy, staff allocation).
    - Predictive insights highlight potential issues (e.g., “Container X at risk of overcrowding”).
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
    - Alerts are generated for violations (e.g., “Temperature exceeded safe limit”).
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
- **Purpose**: To enable predictive modeling for operational and strategic planning.
- **Functionality**:
  - The system shall allow users to create hypothetical scenarios for batch growth, resource usage, and environmental impact.
  - The system shall use growth modeling to predict outcomes (e.g., time to harvest, biomass) under different conditions.
  - The system shall provide risk analysis (e.g., disease outbreaks, environmental anomalies).
  - The system shall support scenario comparison with side-by-side visualizations.
  - Scenarios shall include parameters like temperature, feed type, and stocking density.
- **Behavior**:
  - Predictions shall be based on historical data and growth models.
  - Risks shall be quantified with probability scores (e.g., “30% chance of disease outbreak”).
  - Scenarios shall be saved and shareable with other users.
- **Justification**: Supports proactive planning, mitigates risks, and optimizes outcomes.
- **User Story**: As a Manager, I want to simulate batch growth under different conditions so that I can plan for contingencies.
  - **Acceptance Criteria**:
    - The UI allows users to create scenarios with adjustable parameters.
    - The system predicts outcomes (e.g., growth rate, harvest date) and displays results.
    - Risks (e.g., disease likelihood) are highlighted with mitigation suggestions.
    - Users can compare multiple scenarios in a single view.

#### 3.3.2 Predictive Health Management
- **Purpose**: To proactively manage batch health using AI-driven insights.
- **Functionality**:
  - The system shall predict health risks (e.g., disease outbreaks, lice infestations) using environmental data, health records, and batch history.
  - The system shall recommend preventive actions (e.g., treatments, environmental adjustments).
  - The system shall provide confidence scores for predictions (e.g., “80% confidence in lice risk”).
  - The system shall log prediction accuracy for continuous improvement.
- **Behavior**:
  - Predictions shall be updated daily or on-demand.
  - Recommendations shall include actionable steps with expected outcomes.
  - Alerts shall be sent via the UI and email for high-risk predictions.
- **Justification**: Reduces health risks, improves batch survival rates, and supports regulatory compliance.
- **User Story**: As a Farm Operator, I want to receive alerts for potential health risks so that I can take preventive action.
  - **Acceptance Criteria**:
    - Alerts are generated for predicted risks (e.g., “High lice risk detected”).
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