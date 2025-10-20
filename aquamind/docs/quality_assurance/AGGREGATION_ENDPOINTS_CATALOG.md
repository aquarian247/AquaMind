# Aggregation Endpoints Catalog

**Purpose:** Central reference for all aggregation, summary, metrics, trends, and analysis endpoints in AquaMind  
**Last Updated:** October 18, 2025  
**Auto-Generated:** From `api/openapi.yaml`

---

## 📚 **Quick Reference**

| App | Endpoint | Type | Description |
|-----|----------|------|-------------|
| **Batch** | `/api/v1/batch/batches/{id}/growth_analysis/` | Detail Analysis | Growth metrics over time for a batch |
| **Batch** | `/api/v1/batch/batches/{id}/performance_metrics/` | Detail Analysis | Performance metrics (mortality, FCR, etc.) |
| **Batch** | `/api/v1/batch/container-assignments/summary/` | Collection Summary | Biomass/population aggregates with filters |
| **Health** | `/api/v1/health/lice-counts/summary/` | Collection Summary | Lice count aggregates by geography/area |
| **Health** | `/api/v1/health/lice-counts/trends/` | Collection Trends | Historical lice trends (weekly/monthly) |
| **Health** | `/api/v1/health/health-sampling-events/calculate-aggregates/` | Action | Calculate health event aggregates |
| **Infrastructure** | `/api/v1/infrastructure/areas/{id}/summary/` | Detail Summary | Area-level KPIs (containers, biomass) |
| **Infrastructure** | `/api/v1/infrastructure/geographies/{id}/summary/` | Detail Summary | Geography-level KPIs |
| **Infrastructure** | `/api/v1/infrastructure/freshwater-stations/{id}/summary/` | Detail Summary | Station-level KPIs |
| **Infrastructure** | `/api/v1/infrastructure/halls/{id}/summary/` | Detail Summary | Hall-level KPIs |
| **Inventory** | `/api/v1/inventory/feed-container-stock/summary/` | Collection Summary | Feed stock aggregates |
| **Inventory** | `/api/v1/inventory/feeding-events/summary/` | Collection Summary | Feeding event aggregates |
| **Operational** | `/api/v1/operational/fcr-trends/` | Collection Trends | FCR trends (list endpoint) |
| **Operational** | `/api/v1/operational/fcr-trends/assignment-trends/` | Collection Trends | FCR trends by assignment |
| **Operational** | `/api/v1/operational/fcr-trends/batch-trends/` | Collection Trends | FCR trends by batch |
| **Operational** | `/api/v1/operational/fcr-trends/geography-trends/` | Collection Trends | FCR trends by geography |
| **Scenario** | `/api/v1/scenario/fcr-models/stage-summary/` | Action | FCR model stage summary |
| **Scenario** | `/api/v1/scenario/scenarios/{id}/sensitivity-analysis/` | Detail Analysis | Scenario sensitivity analysis |
| **Scenario** | `/api/v1/scenario/scenarios/summary-stats/` | Collection Summary | Scenario summary statistics |

---

## 📊 **Detailed Endpoint Specifications**

### **Batch App**

#### 1. Growth Analysis (Detail)
```
GET /api/v1/batch/batches/{id}/growth_analysis/
```

**Operation ID:** `api_v1_batch_batches_growth_analysis_retrieve`

**Description:** Calculate and return growth analysis metrics for a batch over time.

**Response Schema:**
```json
{
  "batch_number": "string",
  "species": "string",
  "lifecycle_stage": "string",
  "start_date": "date",
  "current_avg_weight": "number",
  "growth_metrics": [
    {
      "date": "date",
      "avg_weight_g": "number",
      "avg_length_cm": "number",
      "condition_factor": "number"
    }
  ],
  "growth_summary": {
    "total_samples": "integer",
    "avg_growth_rate": "number",
    "min_weight_g": "number",
    "max_weight_g": "number"
  }
}
```

**Use Cases:**
- Batch detail analytics page (growth trends chart)
- Executive dashboard (growth rate KPIs)
- Performance comparison across batches

**Performance:**
- ✅ Replaces ~35 paginated API calls (for 690 samples)
- ✅ Server-side aggregation
- ⚡ Cached for 30-60 seconds

---

#### 2. Performance Metrics (Detail)
```
GET /api/v1/batch/batches/{id}/performance_metrics/
```

**Operation ID:** `api_v1_batch_batches_performance_metrics_retrieve`

**Description:** Calculate and return performance metrics for a batch.

**Response Schema:**
```json
{
  "batch_number": "string",
  "days_active": "integer",
  "current_metrics": {
    "population_count": "integer",
    "biomass_kg": "number",
    "avg_weight_g": "number"
  },
  "mortality_metrics": {
    "total_count": "integer",
    "total_biomass_kg": "number",
    "mortality_rate": "number",
    "by_cause": [
      {
        "cause": "string",
        "count": "integer",
        "percentage": "number"
      }
    ]
  },
  "container_metrics": [
    {
      "container_name": "string",
      "population": "integer",
      "biomass_kg": "number",
      "density_kg_m3": "number"
    }
  ]
}
```

**Use Cases:**
- Batch analytics page (performance overview)
- Executive dashboard (mortality KPIs)
- Health monitoring alerts

**Performance:**
- ✅ Replaces ~286 API calls (for 5720 mortality events)
- ✅ Pre-aggregated mortality stats
- ⚡ Cached for 30-60 seconds

---

#### 3. Container Assignments Summary (Collection)
```
GET /api/v1/batch/container-assignments/summary/
```

**Operation ID:** `batch-container-assignments-summary`

**Query Parameters:**
- `geography` (integer) - Filter by geography ID
- `area` (integer) - Filter by area ID
- `station` (integer) - Filter by station ID
- `hall` (integer) - Filter by hall ID
- `container_type` (string) - Filter by container type
- `is_active` (boolean) - Filter by active status (default: true)

**Response Schema:**
```json
{
  "active_biomass_kg": "number",
  "count": "integer"
}
```

**Use Cases:**
- Executive dashboard (biomass/population by geography)
- Infrastructure overview (capacity utilization)
- Geography comparison cards

**Performance:**
- ✅ Single query with filters
- ✅ DB-level aggregation (Sum, Count)
- ⚡ Cached for 30-60 seconds

---

### **Health App**

#### 4. Lice Counts Summary (Collection)
```
GET /api/v1/health/lice-counts/summary/
```

**Operation ID:** `api_v1_health_lice_counts_summary_retrieve`

**Query Parameters:**
- `geography` (integer) - Filter by geography ID
- `area` (integer) - Filter by area ID
- `start_date` (date) - Start of date range
- `end_date` (date) - End of date range

**Response Schema:**
```json
{
  "average_per_fish": "number",
  "total_counts": "integer",
  "fish_sampled": "integer",
  "by_development_stage": {
    "mature": "number",
    "movable": "number",
    "chalimus": "number",
    "adult": "number"
  }
}
```

**Use Cases:**
- Executive dashboard (lice alert levels)
- Health monitoring dashboard
- Compliance reporting

**Performance:**
- ✅ Aggregates across all lice count records
- ✅ Filters by geography/area/date range
- ⚡ Cached for 30-60 seconds

---

#### 5. Lice Counts Trends (Collection)
```
GET /api/v1/health/lice-counts/trends/
```

**Operation ID:** `api_v1_health_lice_counts_trends_retrieve`

**Query Parameters:**
- `geography` (integer) - Filter by geography ID
- `area` (integer) - Filter by area ID
- `start_date` (date) - Start of date range
- `end_date` (date) - End of date range
- `interval` (enum) - Time interval: `weekly` or `monthly`

**Response Schema:**
```json
{
  "trends": [
    {
      "period": "string",
      "average_per_fish": "number",
      "total_counts": "integer",
      "fish_sampled": "integer"
    }
  ]
}
```

**Use Cases:**
- Executive dashboard (lice trend charts)
- Health analytics (historical patterns)
- Predictive modeling

**Performance:**
- ✅ Time-series aggregation
- ✅ Flexible intervals (weekly/monthly)
- ⚡ Cached for 30-60 seconds

---

### **Infrastructure App**

#### 6. Area Summary (Detail)
```
GET /api/v1/infrastructure/areas/{id}/summary/
```

**Operation ID:** `area-summary`

**Response Schema:**
```json
{
  "container_count": "integer",
  "active_biomass_kg": "number",
  "population_count": "integer",
  "avg_weight_kg": "number"
}
```

**Use Cases:**
- Infrastructure overview page (area cards)
- Capacity planning dashboards

---

#### 7. Geography Summary (Detail)
```
GET /api/v1/infrastructure/geographies/{id}/summary/
```

**Operation ID:** `api_v1_infrastructure_geographies_summary_retrieve`

**Response Schema:**
```json
{
  "id": "integer",
  "name": "string",
  "total_stations": "integer",
  "total_areas": "integer",
  "total_containers": "integer",
  "total_biomass_kg": "number"
}
```

**Use Cases:**
- Executive dashboard (geography-level KPIs)
- Geography comparison views

---

#### 8. Freshwater Station Summary (Detail)
```
GET /api/v1/infrastructure/freshwater-stations/{id}/summary/
```

**Operation ID:** `api_v1_infrastructure_freshwater_stations_summary_retrieve`

**Response Schema:**
```json
{
  "id": "integer",
  "name": "string",
  "hall_count": "integer",
  "tank_count": "integer",
  "active_biomass_kg": "number",
  "capacity_utilization_percent": "number"
}
```

**Use Cases:**
- Station detail pages
- Capacity planning

---

#### 9. Hall Summary (Detail)
```
GET /api/v1/infrastructure/halls/{id}/summary/
```

**Operation ID:** `hall-summary`

**Response Schema:**
```json
{
  "tank_count": "integer",
  "active_biomass_kg": "number",
  "population_count": "integer",
  "avg_weight_kg": "number"
}
```

**Use Cases:**
- Hall detail pages
- Freshwater station management

---

### **Inventory App**

#### 10. Feed Container Stock Summary (Collection)
```
GET /api/v1/inventory/feed-container-stock/summary/
```

**Operation ID:** `api_v1_inventory_feed_container_stock_summary_retrieve`

**Query Parameters:**
- `geography` (integer) - Filter by geography
- `feed_type` (string) - Filter by feed type

**Response Schema:**
```json
{
  "total_stock_kg": "number",
  "container_count": "integer",
  "by_feed_type": [
    {
      "feed_type": "string",
      "total_kg": "number",
      "container_count": "integer"
    }
  ]
}
```

**Use Cases:**
- Inventory dashboard
- Feed ordering alerts

---

#### 11. Feeding Events Summary (Collection)
```
GET /api/v1/inventory/feeding-events/summary/
```

**Operation ID:** `feeding-events-summary`

**Query Parameters:**
- `batch` (integer) - Filter by batch
- `start_date` (date) - Start of date range
- `end_date` (date) - End of date range

**Response Schema:**
```json
{
  "total_feed_kg": "number",
  "total_cost": "number",
  "event_count": "integer",
  "avg_feed_per_event_kg": "number"
}
```

**Use Cases:**
- Batch feed history view
- Cost analysis dashboards

---

### **Operational App**

#### 12. FCR Trends (Collection)
```
GET /api/v1/operational/fcr-trends/
```

**Operation ID:** `api_v1_operational_fcr_trends_list`

**Query Parameters:**
- Various filters for FCR calculations

**Use Cases:**
- Performance analytics
- Batch comparison

---

#### 13. FCR Trends - Assignment Level
```
GET /api/v1/operational/fcr-trends/assignment-trends/
```

**Operation ID:** `api_v1_operational_fcr_trends_assignment_trends_retrieve`

**Query Parameters:**
- `assignment_id` (integer)
- `start_date`, `end_date` (dates)

**Use Cases:**
- Container assignment performance tracking

---

#### 14. FCR Trends - Batch Level
```
GET /api/v1/operational/fcr-trends/batch-trends/
```

**Operation ID:** `api_v1_operational_fcr_trends_batch_trends_retrieve`

**Query Parameters:**
- `batch_id` (integer)
- `start_date`, `end_date` (dates)

**Use Cases:**
- Batch analytics (current implementation in History tab)

---

#### 15. FCR Trends - Geography Level
```
GET /api/v1/operational/fcr-trends/geography-trends/
```

**Operation ID:** `api_v1_operational_fcr_trends_geography_trends_retrieve`

**Query Parameters:**
- `geography_id` (integer)
- `start_date`, `end_date` (dates)

**Use Cases:**
- Executive dashboard (FCR by geography)

---

### **Scenario App**

#### 16. FCR Models Stage Summary
```
GET /api/v1/scenario/fcr-models/stage-summary/
```

**Operation ID:** `api_v1_scenario_fcr_models_stage_summary_retrieve`

**Use Cases:**
- Scenario planning (FCR modeling)

---

#### 17. Scenario Sensitivity Analysis (Detail)
```
POST /api/v1/scenario/scenarios/{id}/sensitivity-analysis/
```

**Operation ID:** `api_v1_scenario_scenarios_sensitivity_analysis_create`

**Use Cases:**
- Scenario planning (what-if analysis)

---

#### 18. Scenario Summary Stats (Collection)
```
GET /api/v1/scenario/scenarios/summary-stats/
```

**Operation ID:** `api_v1_scenario_scenarios_summary_stats_retrieve`

**Use Cases:**
- Scenario comparison dashboards

---

## 🎯 **Endpoint Discovery Methods**

### **Method 1: OpenAPI Spec (Recommended)**

✅ **Best for:** Discovering ALL endpoints with their exact schemas

```bash
# Search for aggregation endpoints
grep -i "/summary/\|/aggregate/\|/metrics/\|/trends/\|/analysis/" api/openapi.yaml

# Get operation IDs
grep -i "operationId.*summary\|operationId.*aggregate" api/openapi.yaml
```

**Advantages:**
- ✅ Single source of truth
- ✅ Includes request/response schemas
- ✅ Shows all query parameters
- ✅ Up-to-date with current deployment

**Disadvantages:**
- ❌ No semantic grouping by use case
- ❌ Requires understanding YAML structure

---

### **Method 2: This Catalog (Recommended for Quick Lookup)**

✅ **Best for:** Quick reference during feature development

**Advantages:**
- ✅ Organized by app and use case
- ✅ Includes example responses
- ✅ Performance notes and caching info
- ✅ Cross-references to frontend usage

**Disadvantages:**
- ⚠️ Needs manual updates when endpoints change
- ⚠️ Can become stale if not maintained

---

### **Method 3: Backend Code Search**

✅ **Best for:** Understanding implementation details

```bash
# Find ViewSet actions
grep -r "@action.*summary\|@action.*aggregate" apps/*/api/viewsets/

# Find APIView classes
grep -r "class.*Summary.*APIView\|class.*Aggregate.*View" apps/*/api/
```

**Advantages:**
- ✅ Shows implementation details
- ✅ Reveals caching strategies
- ✅ Shows DB query patterns

**Disadvantages:**
- ❌ Harder to get complete list
- ❌ Requires backend codebase access

---

## 💡 **Recommendation**

**Use a hybrid approach:**

1. **For Discovery:** Search OpenAPI spec (`api/openapi.yaml`)
2. **For Quick Reference:** Use this catalog
3. **For Implementation:** Check backend code + aggregation playbook

**Maintain this catalog by:**
- 🔄 Auto-regenerating from OpenAPI spec monthly
- 📝 Adding use case examples as features are built
- ✅ Updating performance notes based on real usage

---

## 🚀 **Missing Aggregations (Opportunities)**

Based on current frontend needs:

### **1. Geography-Level Growth Metrics** (High Priority)
```
GET /api/v1/batch/batches/geography-summary/
  ?geography={id}
  &start_date={date}
  &end_date={date}
```

**Needed for:** Executive Dashboard (TGC, SGR, Growth Rate KPIs)

**Would aggregate:** `growth_analysis` data across all batches in geography

---

### **2. Geography-Level Performance Summary** (High Priority)
```
GET /api/v1/batch/batches/geography-performance/
  ?geography={id}
```

**Needed for:** Executive Dashboard (Mortality, FCR by geography)

**Would aggregate:** `performance_metrics` data across all batches in geography

---

### **3. Financial Summary by Geography** (Medium Priority)
```
GET /api/v1/finance/summary/
  ?geography={id}
  &start_date={date}
  &end_date={date}
```

**Needed for:** Executive Dashboard Financial Tab

**Would aggregate:** Revenue, costs, margins by geography

---

## 📚 **Related Documentation**

- [Aggregation Implementation Playbook](./aggregation_playbook.md) - How to build new endpoints
- [Server-Side Aggregation Recommendations](../progress/aggregation/server-side-aggregation-kpi-recommendations.md)
- [API Standards](../quality_assurance/api_standards.md)
- [Aggregation Implementation Plan](../progress/aggregation/aggregation-implementation-plan.md)

---

## 🔄 **Maintenance**

**Update this catalog when:**
- ✅ New aggregation endpoints are added
- ✅ Endpoint schemas change significantly
- ✅ Performance characteristics change
- ✅ New use cases are discovered

**Review Schedule:** Monthly or after major feature releases

**Owner:** Backend team (with frontend input for use cases)

---

**Last Verified:** October 18, 2025  
**OpenAPI Spec Version:** Current production (`api/openapi.yaml`)

