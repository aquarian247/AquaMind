# AquaMind Product Requirements Document (PRD)

## 1. Introduction
AquaMind is an aquaculture management system designed to streamline fish farming operations across the full lifecycle of fish batches. It provides a scalable, unified platform to manage batches, monitor environmental conditions, optimize daily operations, simulate long-term scenarios, ensure regulatory compliance, and enhance resource efficiency. The system supports a holding company with operations in two geographies—Faroe Islands (HQ) and Scotland—and includes subsidiary companies: Broodstock, Freshwater (including Hatcheries), Farming (grow-out stages), and Logistics. Each subsidiary operates with its own financials, requiring robust access controls to maintain data security and operational integrity.

This PRD outlines the requirements for a secure, user-friendly system, serving as a clear guide for development. It assumes a fresh start while leveraging the existing, effective database structure.

## 2. Product Purpose
AquaMind aims to:
- Track fish batches from egg to adult with manual stage transitions.
- Retrieve and analyze environmental data, including sensor readings from WonderWare, weather data from external sources (e.g., OpenWeatherMap), and daylight data via astronomical formulas based on latitude and date.
- Optimize daily operations with actionable recommendations.
- Simulate hypothetical scenarios for long-term strategy.
- Ensure compliance with regulations in the Faroe Islands and Scotland.
- Provide insights through growth modeling and inventory tracking.

The system serves executive management, country management, subsidiary companies (Broodstock, Freshwater, Farming, Logistics), and horizontals (QA, Finance, Veterinarians), aligning with their unique operational and oversight needs.

## 3. Key Features and Functionality

### 3.1 Infrastructure Management
**Purpose**: Provide the foundational structure for managing physical assets and locations, enabling all other features like batch management, scenario planning, and operational optimization.

**Functionality**:
- Create and maintain freshwater stations, broodstock stations, and sea areas, each with geo-positioning (latitude/longitude) to collect daylight (via astronomical formulas) and weather data (via external APIs, e.g., OpenWeatherMap).
- Define container types (e.g., tanks, pens) and assign them to stations or areas.
- Manage Logistics assets (e.g., ships) and track their operations, such as transporting fish (e.g., "Ship A moved PostSmolt from Station B to Area C on [date]") or performing treatments (e.g., "Ship D deliced Pens X, Y, Z on [date]"), with associated costs logged.

**Behavior**:
- Geo-positioning enables automatic environmental data retrieval and calculations.
- Logistics operations are recorded with timestamps, asset details, and costs for financial tracking and inter-company billing.

**Justification**:
- *Freshwater/Farming*: Ensures accurate station and container setup for batch assignments.
- *Logistics*: Tracks ship-based services and costs, supporting operational efficiency.
- *Country Management*: Provides oversight of infrastructure across geographies.

### 3.2 Batch Management
**Purpose**: Track and manage fish batches across their lifecycle for operational accuracy and financial reporting.

**Functionality**:
- Create, update, and delete fish batches.
- Assign batches to containers (e.g., tanks, pens) and record manual stage transitions.
- Track stages: Egg, Fry, Parr, Smolt, PostSmolt, Adult.
- Log health metrics (e.g., mortality, disease) and treatments.

**Behavior**:
- Stage transitions are manual, recorded post-action with details like fish counts and treatments.
- Display batch history and status in a tabular format.

**Justification**:
- *Freshwater (including Hatcheries)*: Ensures accurate logging of frequent stage transitions.
- *Farming*: Tracks grow-out stages and health metrics.
- *Logistics*: Supports recording transitions with ship services.
- *Finance*: Provides data for inter-company transactions.

### 3.3 Environmental Monitoring
**Purpose**: Monitor water quality, weather, and daylight to maintain fish health and compliance.

**Functionality**:
- Retrieve sensor readings (e.g., temperature, pH, oxygen) via WonderWare.
- Fetch weather data from external APIs (e.g., OpenWeatherMap) and calculate daylight using astronomical formulas based on latitude and date.
- Store and analyze data for real-time and historical insights.
- Offer dashboards with visualizations (e.g., graphs, trends).

**Behavior**:
- Trigger alerts for critical thresholds (e.g., low oxygen, extreme weather).
- Enable historical data retrieval for compliance and analysis.

**Justification**:
- *Veterinarians*: Ensures fish health with timely alerts.
- *QA*: Provides data for compliance reporting.
- *Country Management*: Offers site-specific visibility.

### 3.4 Operational Planning
**Purpose**: Optimize daily batch management and resource use with data-driven recommendations.

**Functionality**:
- Monitor tank density, health status, and resource availability.
- Generate ranked recommendations (e.g., redistribute fish, transition batches).

**Behavior**:
- Present actionable suggestions to managers, updated with new data.

**Justification**:
- *Freshwater*: Critical for managing frequent stage transitions and complex logistics in hatcheries and stations.
- *Farming*: Prevents overcrowding and improves health outcomes.
- *Country Management*: Aligns resource use with site goals.
- *Executive Management*: Boosts profitability by optimizing tank usage.

### 3.5 Scenario Planning
**Purpose**: Simulate long-term strategies to forecast outcomes and refine production plans.

**Functionality**:
- Create scenarios by adjusting variables (e.g., feed, temperature).
- Simulate growth using models like TGC, SGR, and EGI.
- Compare scenarios with visual outputs (e.g., growth curves).

**Behavior**:
- Store large datasets for simulations and allow side-by-side comparisons.

**Justification**:
- *QA*: Projects future biomass and environmental impacts for permit applications and assessments (e.g., area capacity estimates).
- *Executive Management*: Enables data-driven long-term decisions.
- *Broodstock/Freshwater/Farming*: Tests tailored strategies.
- *Finance*: Supports cost forecasting.

### 3.6 Regulatory Compliance
**Purpose**: Ensure adherence to industry standards in the Faroe Islands and Scotland.

**Functionality**:
- Generate compliance reports (e.g., water quality logs).
- Track regulatory deadlines and requirements.

**Behavior**:
- Alert users to risks or deadlines and export reports.

**Justification**:
- *QA*: Maintains licenses with current operational data.
- *Country Management*: Ensures regional compliance.
- *Executive Management*: Mitigates risks.

### 3.7 Inventory Management
**Purpose**: Optimize feed and resource planning for cost efficiency.

**Functionality**:
- Track feed types, quantities, and usage.
- Predict needs based on growth and plans.

**Behavior**:
- Suggest reorder points and align feed schedules.

**Justification**:
- *Farming/Logistics*: Ensures resource availability.
- *Finance*: Reduces overstocking or shortages.
- *Executive Management*: Oversees resource costs.

### 3.8 Growth Modeling
**Purpose**: Predict fish growth to inform operational and strategic decisions.

**Functionality**:
- Calculate metrics:
  - *TGC*: Growth efficiency based on temperature.
  - *SGR*: Daily growth rate.
  - *FCR*: Feed efficiency.
- Use real-time and historical data for accuracy.

**Behavior**:
- Display metrics on dashboards and integrate into planning tools.
- Update dynamically with new inputs from WonderWare or manual entries.

**Justification**:
- *Freshwater*: Optimizes station infrastructure and transition planning.
- *Veterinarians*: Monitors growth for health interventions.
- *Farming*: Optimizes lifecycle timing.
- *Executive Management*: Informs production planning.

### 3.9 Medical Journal
**Purpose**: Provide a comprehensive health monitoring system for veterinarians to track fish health, treatments, and regulatory compliance across batches.

**Functionality**:
- *Journal Entries*: Record observations, issues, and actions, with:
  - Categorization (e.g., observation, issue, action).
  - Severity levels (e.g., low, medium, high).
  - Resolution status tracking.
  - Links to specific batches or containers.
- *Vaccination Management*: Track:
  - Vaccination types (e.g., manufacturer, dosage).
  - Administration records (e.g., date, dosage, user, notes).
  - Compliance with vaccination schedules.
- *Treatment Tracking*: Log:
  - Treatment types and applications (e.g., date, dosage, duration).
  - Withholding periods and end dates for food safety.
- *Parasite Management*: Monitor sea lice with:
  - Counts by life stage (e.g., adult female/male, juvenile).
  - Average parasites per fish.
  - Pre- and post-treatment counts to assess effectiveness.
- *Sampling System*: Record water quality and fish health samples, linked to batches or containers.

**Behavior**:
- Maintain a chronological health history for each batch, enabling early issue detection and treatment efficacy analysis.
- Ensure compliance with withholding periods and vaccination requirements through alerts and reports.

**Justification**:
- *Veterinarians*: Supports detailed health records, proactive interventions, and regulatory adherence.
- *QA*: Provides auditable data for compliance reporting.
- *Finance*: Tracks treatment costs impacting production.

## 4. Security, Authentication, and Access Control
**Purpose**: Secure data and features based on the organizational structure and user roles.

**Functionality**:
- Implement Role-Based Access Control (RBAC) to restrict access by:
  - *Geography*: Faroe Islands (HQ) and Scotland.
  - *Subsidiary Companies*: Broodstock, Freshwater, Farming, Logistics.
  - *Horizontals*: QA, Finance, Veterinarians.
- Support secure user authentication (e.g., multi-factor authentication).
- Maintain audit logs for key actions (e.g., stage transitions, report generation).

**Behavior**:
- Limit data access to authorized users (e.g., Broodstock sees only genetic data, Finance sees cross-company financials).
- Prevent subsidiaries from viewing each other’s data unless explicitly permitted (e.g., Logistics services sold to Farming).

**Justification**:
- *Subsidiary Companies*: Protects financial and operational data for independent profitability (e.g., Broodstock selling to Freshwater).
- *Country Management*: Ensures oversight within their geography without compromising other regions.
- *Executive Management*: Provides full visibility while maintaining security across the holding company.

## 5. Scalability Considerations
AquaMind must handle:
- Large volumes of environmental readings (gigabytes of time-series data).
- Extensive scenario simulations, potentially scaling with farm size.
- Real-time data integration from WonderWare and external APIs across multiple sites.

The system should prioritize efficient data storage, processing, and retrieval to support growth without performance degradation. *Tech Hint*: Use TimescaleDB for time-series data management.

## 6. Organizational Structure and Access
The system reflects:
- *Geographies*: Faroe Islands (HQ) and Scotland.
- *Subsidiary Companies*:
  - *Broodstock*: Manages genetic data and sells to Freshwater.
  - *Freshwater*: Manages early lifecycle stages and sells to Farming.
  - *Farming*: Oversees hatchery and grow-out stages.
  - *Logistics*: Provides ship-based services (e.g., delicing, net cleaning, transport).
- *Horizontals*: QA (compliance), Finance (financials), Veterinarians (health).

Role Based Access Control (RBAC) ensures each entity accesses only relevant data, supporting independent financials and operational autonomy.

## 7. Next Steps
This PRD is a foundation. Future steps include:
- Refining features with subsidiary and horizontal feedback.
- Defining UI/UX requirements (e.g., role-specific dashboards).
- Pairing with a tech stack proposal document.

Development should start with a project skeleton and documentation to align teams on this vision.