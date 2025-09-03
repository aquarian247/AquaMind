# AquaMind Feed Conversion Ratio (FCR) Enhancement PRD

## 1. Introduction

### 1.1 Purpose
This Product Requirements Document (PRD) defines enhancements to implement robust Feed Conversion Ratio (FCR) tracking and visualization in AquaMind, a Django-based aquaculture management system for Bakkafrost. FCR, calculated as `FCR = total feed consumed (kg) / total biomass gain (kg)`, is a critical KPI for operational efficiency, sustainability, and regulatory compliance (e.g., ASC, GSI standards). 

The enhancements address the need for both **actual FCR** (calculated retrospectively from logged feed events, growth samples, and mortality records) and **predicted FCR** (modeled prospectively for forecasting and scenario planning). This dual approach, inspired by industry tools like Fishtalk (which distinguishes Biological/Economical FCR in operational vs. planning modules), provides actionable insights despite sparse weighing events (typically 3-4 spot checks over 800-900 days). 

Actual FCR will include confidence levels to reflect data reliability, while predicted FCR draws from scenario models to fill gaps and enable "what-if" comparisons. Visualizations will target the Batch Management Analytics page in the Vue.js frontend, showing trends at batch, container assignment, and aggregated geography levels.

### 1.2 Scope
- **In Scope**: Minimal data model changes; server-side FCR calculations in Django; new API endpoints for trends; frontend integration for dual FCR display (actual with confidence + predicted); support for batch/container-assignment/geography aggregation levels.
- **Out of Scope**: Full AI/ML integration (Phase 3); real-time sensor-based biomass estimation; mobile app adaptations.
- **Phased Approach**: Aligns with overall PRD (Phase 1: Core ops with actual FCR; Phase 2: Planning with predicted FCR integration).
- **Dependencies**: Existing models in `batch` (e.g., GrowthSample), `inventory` (e.g., FeedingEvent), `health` (e.g., MortalityRecord), and planned `scenario` models/apps.

### 1.3 Rationale and Context
In aquaculture, FCR monitoring is essential for detecting inefficiencies (e.g., feed waste, health issues) and optimizing costs, as seen in Fishtalk's dual handling of actual (from registrations) and modeled (for projections) FCR. AquaMind's current setup (e.g., `inventory_batchfeedingsummary.fcr`) supports basic actual FCR but lacks trends, confidence handling for sparse data, and predicted integration—leading to incomplete insights.

Enhancements prioritize:
- **Operational Utility**: Focus on batch (`batch_batch`) and container assignment (`batch_batchcontainerassignment`) levels for farm operators (e.g., "How's this batch performing?"), as these are granular and actionable. Geography-level aggregation (e.g., Scotland vs. Faroe Islands via `infrastructure_geography`) supports management reporting without overwhelming ops users.
- **Data Sparsity Handling**: Actual FCR is reliable only at weighing points; interpolate/estimate between with confidence flags to avoid misleading users.
- **Predicted Integration**: Use scenario models (e.g., `FCRModel` stages) for forward-looking trends, enabling deviation alerts (e.g., actual > predicted by 5%).
- **Efficiency**: Server-side aggregation reduces frontend load (e.g., from 350MB raw data to 20kB trends, per FCR_HISTORICAL_TRENDS_INVESTIGATION.md), aligning with architecture principles (modular apps, RESTful APIs).
- **Minimal Complexity**: Changes build on existing code (e.g., FCR formula in scenario projections: `daily_feed = daily_growth * fcr * population / 1000`), avoiding bloat while enhancing usability.

This balances granularity (ops) with overview (management), preventing context rot for the coding agent by focusing on targeted changes in `inventory`, `batch`, and `operational` apps.

## 2. Functional Requirements

### 2.1 Data Model Changes
Minimal additions to support confidence and estimation in actual FCR; no major overhauls to avoid complexity.

#### Changes and Rationale
1. **inventory_batchfeedingsummary Model (inventory app)**:
   - **Add Fields**:
     - `confidence_level`: CharField (choices: 'HIGH', 'MEDIUM', 'LOW'; default='MEDIUM') – Indicates data reliability (HIGH: <30 days since last weighing; MEDIUM: 30-90 days; LOW: >90 days).
     - `estimation_method`: CharField (choices: 'MEASURED' for direct calculations, 'INTERPOLATED' for TGC-based estimates between weighings; max_length=20; null=True).
   - **Rationale**: Enhances actual FCR transparency for sparse weighings (from `batch_growthsample`). Allows flagging estimated vs. measured values, mirroring Fishtalk's adjusted FCR. No change to existing `fcr` field (DecimalField(5,3))—it's calculated as before from aggregated `total_feed_consumed_kg / total_biomass_gain_kg` over `period_start/end`. This keeps summaries lightweight for trends without denormalizing raw data.

2. **batch_batchcontainerassignment Model (batch app)**:
   - **Add Field**:
     - `last_weighing_date`: DateField (null=True) – Tracks the most recent `batch_growthsample.date` for this assignment.
   - **Rationale**: Enables per-assignment confidence calculation (e.g., time since last weighing), as batches can split/move across containers. Supports operational granularity without querying all samples each time.

3. **No Changes to Other Models**:
   - Existing links suffice: FCR pulls from `inventory_feedingevent` (feed), `batch_growthsample` (biomass gain), `health_mortalityrecord` (adjustments for losses).
   - Predicted FCR uses existing `scenario` models (e.g., `FCRModelStage.fcr_value`) without alteration—integrate via queries.

#### Implementation Notes
- Use Django signals or model `save()` overrides to auto-update `last_weighing_date` on `GrowthSample` creation.
- Calculations remain in services (e.g., `inventory/services.py`) for modularity, per code_organization_guidelines.md.

### 2.2 Django App Changes
Changes span apps for modularity, following architecture.md (e.g., inventory for feed/FCR, batch for growth, operational for planning/trends).

#### Inventory App (Primary for Actual FCR)
- **Add/Modify**:
  - Services: New `calculate_fcr_summary` function to compute actual FCR, confidence, and method (triggered on FeedingEvent/GrowthSample saves or cron jobs).
  - Models: As above (feedingsummary enhancements).
  - API: Extend ViewSets/Serializers for FCR fields.
- **Rationale**: Inventory owns feed tracking and summaries; centralizes actual FCR logic here to avoid duplication.

#### Batch App (For Growth and Assignment Integration)
- **Add/Modify**:
  - Models: As above (assignment field).
  - Services: Helper to fetch recent growth samples for FCR calcs.
- **Rationale**: Batch handles biomass/growth data; minimal changes ensure assignment-level granularity for ops.

#### Operational App (For Trends and Predicted Integration)
- **Add/Modify**:
  - Services: `generate_fcr_trends` to aggregate actual/predicted series (e.g., query inventory summaries + scenario projections).
  - API: New endpoint `/api/v1/operational/fcr-trends/` (per API_standards.md: kebab-case, plural, unique basename='fcr-trends').
    - Params: `batch_id` (optional for batch-level), `assignment_id` (optional for container-level), `geography_id` (optional for aggregate), `interval` (DAILY/WEEKLY/MONTHLY), `start_date`, `end_date`.
    - Response: JSON series with `period_start`, `actual_fcr`, `confidence`, `predicted_fcr`, `deviation`.
  - **Rationale**: Operational app manages planning/dashboards; ideal for trends and scenario integration. Aggregates to geography for management without ops overload.

#### No Changes to Other Apps
- Core/Users/Environmental/Health/Infrastructure: Provide inputs (e.g., mortality adjustments) but no direct FCR logic.

### 2.3 API and Frontend Integration
- **API Design**: Follow api_standards.md (kebab-case URLs, explicit basenames). Use DRF routers in each app's `api/routers.py`.
- **Frontend (Vue.js)**: On Batch Management Analytics page, display line chart/table with actual (dots with confidence colors) + predicted (dotted line); filters for levels.
- **Interaction Logic**: Compare actual vs. predicted (e.g., deviation %); use predicted for future periods or low-confidence gaps. From scenario code: Predicted derives from `fcr_value * daily_growth`; actual overrides when available.

### 2.4 User Stories and Acceptance Criteria
- **As a Farm Operator**: View batch/assignment FCR trends to monitor performance.
  - AC: Chart shows actual/predicted; confidence flags; <3s load.
- **As a Manager**: View geography FCR for reports.
  - AC: Aggregated trends; exportable.
- **Edge Cases**: Zero growth (FCR=inf, handle as null); no weighings (low confidence, rely on predicted).

## 3. Non-Functional Requirements
- **Performance**: <250ms for trends (use TimescaleDB aggregates, Redis cache per FCR_HISTORICAL_TRENDS_INVESTIGATION.md).
- **Security**: RBAC via users app; audit changes.
- **Scalability**: Handle 10k+ summaries; index on dates/IDs.
- **Testing**: 90% coverage; contract tests per api_standards.md.

## 4. Success Metrics
- Adoption: 80% ops users view FCR weekly.
- Accuracy: Matches Fishtalk-like calcs (±0.02).
- Efficiency: Reduces frontend data load by 99%.

## 5. Next Steps
1. Update data_model.md with changes.
2. Prototype in inventory/operational apps.
3. Test integration with scenario projections.
4. Frontend hookup to new API.