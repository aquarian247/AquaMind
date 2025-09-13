# Server-side Aggregation for KPI Cards (v1) — Recommendations & Specs

Audience: **Backend engineers**  
Scope: Replace high-impact client-side aggregations for KPI card-like GUI components with server-side endpoints under `/api/v1/`. Provide concise strategy, prioritized endpoints, and example payloads as inspiration. Address any gaps in the existing FCR trends feature.

---

## Executive Summary

• Adopt small, purpose-built aggregation endpoints to power KPI cards for geographies, areas, stations, and halls.  
• Reuse patterns already present in the codebase (e.g., `/infrastructure/overview`, `container-assignments/summary`, `feeding-events/summary`) to keep it simple and consistent.  
• Prioritize endpoints that eliminate expensive client-side joins (containers × assignments) used by the dashboard and area/station KPI hooks.  
• FCR trends are largely in place; a few improvements will make the feature complete and clearer for consumers.

📋 **[Implementation Playbook](../development/aggregation_playbook.md)**: Follow this guide for standardized aggregation endpoint development.

---

## Current State (What Exists Today)

* **Infrastructure overview endpoint** – totals for containers, capacity, active biomass, and today’s feeding events [6].  
* **Batch container assignments summary** – aggregates active biomass and count [7].  
* **Inventory feeding summary endpoints** – model/viewset for summaries and a `feeding-events/summary` action for quick counts [8][9].  
* **Operational FCR trends endpoint & service** – daily/weekly/monthly intervals, batch/assignment/geography scopes, predicted + actual merge [10][11].  
* **Frontend** performs client-side aggregation for KPI cards (area/station) and various dashboard metrics, causing over-fetching and extra compute in the browser [2][3][5].  
* **ADR** allows client-side aggregation only when backend endpoints are missing; prefer server-side aggregation as endpoints become available [1].

---

## Gaps Driving KPI Server Endpoints

* **Area KPI**: total biomass, average weight, container count, population count computed client-side via multiple list endpoints [2].  
* **Station KPI**: same pattern as area; joins halls → containers → active assignments [3].  
* **Geography-level rollups**: counts of areas, stations, halls, rings, containers; total capacity & active biomass (partly covered by overview) — not available per-entity.  
* **Dashboard KPIs**: mixed sources & client aggregation; can be simplified by reusing new KPI endpoints and existing summaries [5][6][8].

---

## Recommendations (Concise Strategy)

1. Provide small, cached summary endpoints per infrastructure entity following existing naming patterns (kebab-case, explicit basenames, DRF viewsets + `@action` where applicable).  
2. Keep response shapes minimal: counts and sums only (e.g., `container_count`, `ring_count`, `active_biomass_kg`, `population_count`, `avg_weight_kg`). Compute `avg_weight` as `biomass / population`.  
3. Reuse existing models for aggregation: `Container`, `BatchContainerAssignment`, `FeedingEvent`. Use DB-level aggregates (`Sum`/`Count`) and short cache windows (30–60 s).  
4. Keep under `/api/v1/`. Apply standard auth and geography-based filters as needed.  
5. Use `drf-spectacular` for explicit schemas and clear OpenAPI documentation for each endpoint.

---

## Proposed Endpoints (Inspiration Specs)

_All endpoints under `/api/v1/`; payloads are inspirational, not prescriptive._

### 1) Area KPI Summary

* **GET** `/infrastructure/areas/{id}/summary/`  
* Replaces `useAreaKpi` client aggregation [2].  
* Query params: `is_active=true|false` (default `true`)  
* Response:
```json
{
  "container_count": 18,
  "ring_count": 12,
  "active_biomass_kg": 84250.5,
  "population_count": 213400,
  "avg_weight_kg": 0.395
}
```
* Implementation notes  
  • `container_count`: `Container.objects.filter(area_id=id).count()`  
  • `ring_count`: filter by container_type category/name containing “Ring”/“Pen” [5]  
  • Biomass & population: sum over active `BatchContainerAssignment` for containers in area [7]  
  • Cache 30–60 s; document schema via `extend_schema`.

### 2) Freshwater Station KPI Summary

* **GET** `/infrastructure/freshwater-stations/{id}/summary/`  
* Replaces `useStationKpi` client aggregation [3].  
* Query params: `is_active=true|false`  
* Response:
```json
{
  "hall_count": 6,
  "container_count": 42,
  "active_biomass_kg": 35670.8,
  "population_count": 90500,
  "avg_weight_kg": 0.394
}
```
* Implementation notes  
  • `hall_count`: `Hall.objects.filter(freshwater_station_id=id).count()`  
  • Biomass & population: assignments in containers under those halls [7].

### 3) Hall KPI Summary

* **GET** `/infrastructure/halls/{id}/summary/`  
* Response:
```json
{
  "container_count": 14,
  "active_biomass_kg": 12100.2,
  "population_count": 31000,
  "avg_weight_kg": 0.39
}
```

### 4) Geography KPI Summary

* **GET** `/infrastructure/geographies/{id}/summary/`  
* Response:
```json
{
  "area_count": 5,
  "station_count": 3,
  "hall_count": 11,
  "container_count": 124,
  "ring_count": 48,
  "capacity_kg": 250000.0,
  "active_biomass_kg": 132500.0
}
```
* Implementation notes: blend counts plus capacity (`Container.max_biomass_kg`) & active biomass (see overview) [6].

### 5) Generic Container/Assignment Summary (Optional)

* **GET** `/infrastructure/containers/summary/?area={id}&station={id}&hall={id}&geography={id}`  
* Returns counts & biomass; useful fallback when bespoke endpoints aren’t available.

### 6) Batch Assignment Summary (Enhance Existing)

* **GET** `/batch/container-assignments/summary/?is_active=true&geography={id}&area={id}&station={id}&container_type={slug}`  
* Extend current summary with standard location filters [7].

### 7) Feeding Events Summary (Enhance Existing)

* **GET** `/inventory/feeding-events/summary/?date=today|YYYY-MM-DD&batch={id}&container={id}&start_date=YYYY-MM-DD&end_date=YYYY-MM-DD`  
* Add `start_date`/`end_date` range alternative [8].  
* Response unchanged: `events_count`, `total_feed_kg`.

---

## Prioritization (Do First → Next)

1. Area summary (replaces `useAreaKpi`) [2]  
2. Station summary (replaces `useStationKpi`) [3]  
3. Geography summary (feeds top-level dashboard cards) [6]  
4. Hall summary (infra drill-down)  
5. Enhance `container-assignments/summary` with filters  
6. Extend `feeding-events/summary` to support date ranges

---

## Integration Notes (Frontend Migration)

* **useAreaKpi** → call `GET /infrastructure/areas/{id}/summary/`; remove container/assignment joins [2].  
* **useStationKpi** → call `GET /infrastructure/freshwater-stations/{id}/summary/` [3].  
* **Dashboard KPI cards** → reuse `/infrastructure/overview` [6], geography summary, and `/inventory/feeding-events/summary` [8]; keep client-only values (e.g., nextFeedingHours) until backend design exists.  
* **api.ts**: switch to server summaries where available; retain graceful fallbacks [5].

---

## FCR Trends — Completion Checklist

1. **Weighted averaging** – replace simple average with weighting by `total_feed_kg` or `biomass_gain_kg` in `aggregate_container_fcr_to_batch` [12].  
2. **Explicit schema** – ensure serializer/docs specify units (ratio), meaning of `data_points`, and semantics of `confidence`/`estimation_method` [10][11].  
3. **Geography defaulting** – document default aggregation behavior and always return explicit `aggregation_level` [10][11].  
4. **Series bucketization** – confirm bucket edges match interval semantics (DAILY, WEEKLY Mon–Sun, MONTHLY calendar) and are documented [10][11].  
5. **Scenario metadata** – keep `scenarios_used`; optionally surface model/version metadata [11].  
6. **Confidence alignment** – ensure weighing-date logic via `GrowthSampleService` feeds into summaries [11][12].

---

## Testing & Quality

* Add API tests mirroring existing patterns (see tests for container-assignments summary) to validate metrics, filters, and caching [7].  
* Update OpenAPI via drf-spectacular (`extend_schema`) for each new summary endpoint [6][10].  
* Keep cache windows short (30–60 s) to avoid stale dashboards.

---

## Integration Notes & Examples (Issue #53)

This section provides actionable, copy-pasteable examples for integrating the new server-side summary endpoints into frontend applications. All examples use the real API endpoints and include authentication headers for immediate testing.

### Authentication Setup

All endpoints require JWT authentication. Include the access token in the Authorization header:

```bash
# Replace YOUR_JWT_TOKEN with actual token from /api/token/
AUTH_HEADER="Authorization: Bearer YOUR_JWT_TOKEN"
```

### Base URL
```bash
BASE_URL="http://localhost:8000/api/v1"
```

---

### 1. Area KPI Summary

**Endpoint:** `GET /api/v1/infrastructure/areas/{id}/summary/`

**Replaces:** `useAreaKpi` client-side aggregation

**Response Schema:**
```json
{
  "container_count": 18,
  "ring_count": 12,
  "active_biomass_kg": 84250.5,
  "population_count": 213400,
  "avg_weight_kg": 0.395
}
```

**cURL Example:**
```bash
# Get area summary for area ID 5
curl -X GET "http://localhost:8000/api/v1/infrastructure/areas/5/summary/" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json"
```

**Postman Example:**
```
Method: GET
URL: http://localhost:8000/api/v1/infrastructure/areas/5/summary/
Headers:
  Authorization: Bearer YOUR_JWT_TOKEN
  Content-Type: application/json
```

**JavaScript/React Example:**
```typescript
// In api.ts or custom hook
const fetchAreaSummary = async (areaId: number) => {
  const response = await fetch(`/api/v1/infrastructure/areas/${areaId}/summary/`, {
    headers: {
      'Authorization': `Bearer ${getStoredToken()}`,
      'Content-Type': 'application/json'
    }
  });

  if (!response.ok) {
    throw new Error('Failed to fetch area summary');
  }

  return response.json();
};

// Usage in component
const areaData = await fetchAreaSummary(5);
console.log(`Area has ${areaData.container_count} containers with ${areaData.active_biomass_kg}kg biomass`);
```

---

### 2. Freshwater Station KPI Summary

**Endpoint:** `GET /api/v1/infrastructure/freshwater-stations/{id}/summary/`

**Replaces:** `useStationKpi` client-side aggregation

**Response Schema:**
```json
{
  "hall_count": 6,
  "container_count": 42,
  "active_biomass_kg": 35670.8,
  "population_count": 90500,
  "avg_weight_kg": 0.394
}
```

**cURL Example:**
```bash
# Get freshwater station summary for station ID 7
curl -X GET "http://localhost:8000/api/v1/infrastructure/freshwater-stations/7/summary/" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json"
```

**Postman Example:**
```
Method: GET
URL: http://localhost:8000/api/v1/infrastructure/freshwater-stations/7/summary/
Headers:
  Authorization: Bearer YOUR_JWT_TOKEN
  Content-Type: application/json
```

---

### 3. Hall KPI Summary

**Endpoint:** `GET /api/v1/infrastructure/halls/{id}/summary/`

**Response Schema:**
```json
{
  "container_count": 14,
  "active_biomass_kg": 12100.2,
  "population_count": 31000,
  "avg_weight_kg": 0.39
}
```

**cURL Example:**
```bash
# Get hall summary for hall ID 11
curl -X GET "http://localhost:8000/api/v1/infrastructure/halls/11/summary/" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json"
```

---

### 4. Geography KPI Summary

**Endpoint:** `GET /api/v1/infrastructure/geographies/{id}/summary/`

**Response Schema:**
```json
{
  "area_count": 5,
  "station_count": 3,
  "hall_count": 11,
  "container_count": 124,
  "ring_count": 48,
  "capacity_kg": 250000.0,
  "active_biomass_kg": 132500.0
}
```

**cURL Example:**
```bash
# Get geography summary for geography ID 3
curl -X GET "http://localhost:8000/api/v1/infrastructure/geographies/3/summary/" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json"
```

**Postman Example:**
```
Method: GET
URL: http://localhost:8000/api/v1/infrastructure/geographies/3/summary/
Headers:
  Authorization: Bearer YOUR_JWT_TOKEN
  Content-Type: application/json
```

---

### 5. Container Assignments Summary with Filters

**Endpoint:** `GET /api/v1/batch/container-assignments/summary/`

**Enhanced with location-based filtering**

**Response Schema:**
```json
{
  "active_biomass_kg": 48720.4,
  "count": 57
}
```

**cURL Examples:**

```bash
# Default summary (all active assignments)
curl -X GET "http://localhost:8000/api/v1/batch/container-assignments/summary/" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"

# Filtered by geography
curl -X GET "http://localhost:8000/api/v1/batch/container-assignments/summary/?geography=3" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"

# Filtered by area
curl -X GET "http://localhost:8000/api/v1/batch/container-assignments/summary/?area=5" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"

# Filtered by station
curl -X GET "http://localhost:8000/api/v1/batch/container-assignments/summary/?station=7" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"

# Filtered by hall
curl -X GET "http://localhost:8000/api/v1/batch/container-assignments/summary/?hall=11" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"

# Filtered by container type
curl -X GET "http://localhost:8000/api/v1/batch/container-assignments/summary/?container_type=PEN" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"

# Combined filters (geography + container type)
curl -X GET "http://localhost:8000/api/v1/batch/container-assignments/summary/?geography=3&container_type=RING" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"

# Include inactive assignments
curl -X GET "http://localhost:8000/api/v1/batch/container-assignments/summary/?is_active=false" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

**JavaScript/React Example:**
```typescript
// In api.ts - flexible filtering function
const fetchContainerAssignmentsSummary = async (filters: {
  geography?: number;
  area?: number;
  station?: number;
  hall?: number;
  container_type?: string;
  is_active?: boolean;
} = {}) => {
  const params = new URLSearchParams();

  // Add filters to query params
  Object.entries(filters).forEach(([key, value]) => {
    if (value !== undefined) {
      params.append(key, String(value));
    }
  });

  const response = await fetch(`/api/v1/batch/container-assignments/summary/?${params}`, {
    headers: {
      'Authorization': `Bearer ${getStoredToken()}`,
      'Content-Type': 'application/json'
    }
  });

  if (!response.ok) {
    throw new Error('Failed to fetch container assignments summary');
  }

  return response.json();
};

// Usage examples
const allActive = await fetchContainerAssignmentsSummary();
const byGeography = await fetchContainerAssignmentsSummary({ geography: 3 });
const ringsOnly = await fetchContainerAssignmentsSummary({ container_type: 'RING' });
const combined = await fetchContainerAssignmentsSummary({
  geography: 3,
  container_type: 'PEN',
  is_active: true
});
```

---

### 6. Feeding Events Summary with Date Ranges

**Endpoint:** `GET /api/v1/inventory/feeding-events/summary/`

**Enhanced with date range support**

**Response Schema:**
```json
{
  "events_count": 124,
  "total_feed_kg": 3580.2
}
```

**cURL Examples:**

```bash
# Default (today's feeding events)
curl -X GET "http://localhost:8000/api/v1/inventory/feeding-events/summary/" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"

# Specific date
curl -X GET "http://localhost:8000/api/v1/inventory/feeding-events/summary/?date=2025-01-15" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"

# Date range (January 2025)
curl -X GET "http://localhost:8000/api/v1/inventory/feeding-events/summary/?start_date=2025-01-01&end_date=2025-01-31" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"

# Date range with batch filter
curl -X GET "http://localhost:8000/api/v1/inventory/feeding-events/summary/?start_date=2025-01-01&end_date=2025-01-31&batch=42" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"

# Date range with container filter
curl -X GET "http://localhost:8000/api/v1/inventory/feeding-events/summary/?start_date=2025-01-01&end_date=2025-01-31&container=15" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

**JavaScript/React Example:**
```typescript
// In api.ts - flexible feeding events summary
const fetchFeedingEventsSummary = async (filters: {
  date?: string;
  start_date?: string;
  end_date?: string;
  batch?: number;
  container?: number;
} = {}) => {
  const params = new URLSearchParams();

  Object.entries(filters).forEach(([key, value]) => {
    if (value !== undefined) {
      params.append(key, String(value));
    }
  });

  const response = await fetch(`/api/v1/inventory/feeding-events/summary/?${params}`, {
    headers: {
      'Authorization': `Bearer ${getStoredToken()}`,
      'Content-Type': 'application/json'
    }
  });

  if (!response.ok) {
    throw new Error('Failed to fetch feeding events summary');
  }

  return response.json();
};

// Usage examples
const today = await fetchFeedingEventsSummary();
const specificDate = await fetchFeedingEventsSummary({ date: '2025-01-15' });
const monthRange = await fetchFeedingEventsSummary({
  start_date: '2025-01-01',
  end_date: '2025-01-31'
});
const batchMonth = await fetchFeedingEventsSummary({
  start_date: '2025-01-01',
  end_date: '2025-01-31',
  batch: 42
});
```

---

### 7. FCR Trends with Different Intervals

**Endpoint:** `GET /api/v1/operational/fcr-trends/`

**Response Schema:**
```json
{
  "interval": "DAILY",
  "unit": "ratio",
  "aggregation_level": "geography",
  "model_version": "v1.0",
  "series": [
    {
      "period_start": "2025-01-01",
      "period_end": "2025-01-01",
      "actual_fcr": 1.45,
      "confidence": "HIGH",
      "data_points": 12,
      "predicted_fcr": 1.48,
      "scenarios_used": 3,
      "deviation": -2.03,
      "container_name": null,
      "assignment_id": null,
      "container_count": 45,
      "total_containers": 48
    }
  ]
}
```

**cURL Examples:**

```bash
# Default FCR trends (geography level, daily intervals, last year)
curl -X GET "http://localhost:8000/api/v1/operational/fcr-trends/" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"

# Daily intervals (most granular)
curl -X GET "http://localhost:8000/api/v1/operational/fcr-trends/?interval=DAILY&start_date=2025-01-01&end_date=2025-01-31" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"

# Weekly intervals (Monday-Sunday buckets)
curl -X GET "http://localhost:8000/api/v1/operational/fcr-trends/?interval=WEEKLY&start_date=2025-01-01&end_date=2025-01-31" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"

# Monthly intervals (calendar months)
curl -X GET "http://localhost:8000/api/v1/operational/fcr-trends/?interval=MONTHLY&start_date=2025-01-01&end_date=2025-12-31" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"

# Batch-level aggregation
curl -X GET "http://localhost:8000/api/v1/operational/fcr-trends/?batch_id=42&interval=WEEKLY" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"

# Container assignment-level aggregation
curl -X GET "http://localhost:8000/api/v1/operational/fcr-trends/?assignment_id=15&interval=DAILY" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"

# Geography-specific aggregation
curl -X GET "http://localhost:8000/api/v1/operational/fcr-trends/?geography_id=3&interval=MONTHLY" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"

# Without predicted values
curl -X GET "http://localhost:8000/api/v1/operational/fcr-trends/?include_predicted=false" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

**JavaScript/React Example:**
```typescript
// In api.ts - FCR trends with flexible parameters
const fetchFCRTrends = async (params: {
  start_date?: string;
  end_date?: string;
  interval?: 'DAILY' | 'WEEKLY' | 'MONTHLY';
  batch_id?: number;
  assignment_id?: number;
  geography_id?: number;
  include_predicted?: boolean;
} = {}) => {
  const queryParams = new URLSearchParams();

  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined) {
      queryParams.append(key, String(value));
    }
  });

  const response = await fetch(`/api/v1/operational/fcr-trends/?${queryParams}`, {
    headers: {
      'Authorization': `Bearer ${getStoredToken()}`,
      'Content-Type': 'application/json'
    }
  });

  if (!response.ok) {
    throw new Error('Failed to fetch FCR trends');
  }

  return response.json();
};

// Usage examples
const defaultTrends = await fetchFCRTrends();
const dailyTrends = await fetchFCRTrends({
  interval: 'DAILY',
  start_date: '2025-01-01',
  end_date: '2025-01-31'
});
const batchWeekly = await fetchFCRTrends({
  batch_id: 42,
  interval: 'WEEKLY',
  start_date: '2025-01-01',
  end_date: '2025-03-31'
});
const geographyMonthly = await fetchFCRTrends({
  geography_id: 3,
  interval: 'MONTHLY',
  start_date: '2025-01-01',
  end_date: '2025-12-31'
});
```

---

### Frontend Migration Guide

#### Migration Strategy

1. **Identify client-side aggregations** that can be replaced
2. **Test new endpoints** with Postman/cURL first
3. **Update hooks and API calls** incrementally
4. **Maintain fallbacks** during transition
5. **Remove client-side aggregation logic** after verification

#### Common Migration Patterns

**Before (Client-side aggregation):**
```typescript
// useAreaKpi.ts - OLD approach
const useAreaKpi = (areaId: number) => {
  const { data: containers } = useContainers({ areaId });
  const { data: assignments } = useAssignments({ areaId });

  // Complex client-side joins and calculations
  const biomass = assignments?.reduce((sum, a) => sum + a.biomass_kg, 0) || 0;
  const population = assignments?.reduce((sum, a) => sum + a.population_count, 0) || 0;
  const avgWeight = population > 0 ? biomass / population : 0;

  return {
    containerCount: containers?.length || 0,
    biomass,
    population,
    avgWeight
  };
};
```

**After (Server-side aggregation):**
```typescript
// useAreaKpi.ts - NEW approach
const useAreaKpi = (areaId: number) => {
  const { data: summary } = useQuery({
    queryKey: ['area-summary', areaId],
    queryFn: () => api.get(`/infrastructure/areas/${areaId}/summary/`)
  });

  return {
    containerCount: summary?.container_count || 0,
    biomass: summary?.active_biomass_kg || 0,
    population: summary?.population_count || 0,
    avgWeight: summary?.avg_weight_kg || 0
  };
};
```

#### Hook Replacement Mapping

| Old Hook | New Endpoint | Migration Priority |
|----------|-------------|-------------------|
| `useAreaKpi` | `/infrastructure/areas/{id}/summary/` | High |
| `useStationKpi` | `/infrastructure/freshwater-stations/{id}/summary/` | High |
| Dashboard KPI cards | Multiple summary endpoints | Medium |
| `useBatchFcr` | `/operational/fcr-trends/` | Medium |

#### Error Handling

```typescript
// Robust error handling for summary endpoints
const fetchSummaryWithFallback = async (endpoint: string) => {
  try {
    const response = await api.get(endpoint);
    return response.data;
  } catch (error) {
    console.warn(`Server-side summary failed for ${endpoint}, falling back to client aggregation`);
    // Implement fallback logic here
    return null;
  }
};
```

#### Performance Benefits

- **Reduced network requests**: Single endpoint vs multiple list endpoints
- **Faster response times**: Server-side aggregation vs client-side processing
- **Lower bandwidth**: Summary data vs full object lists
- **Better caching**: 30-60s cache windows on summary endpoints

#### Testing Strategy

1. **Unit tests**: Verify endpoint responses match expected schemas
2. **Integration tests**: Compare old vs new hook outputs
3. **Performance tests**: Measure response times and data transfer
4. **Fallback tests**: Ensure graceful degradation when server unavailable

---

## Sources

[1] AquaMind-Frontend/docs/architecture.md — ADR: API Aggregation Strategy (hybrid approach)  
[2] AquaMind-Frontend/client/src/hooks/aggregations/useAreaKpi.ts — client-side area KPI aggregation  
[3] AquaMind-Frontend/client/src/hooks/aggregations/useStationKpi.ts — client-side station KPI aggregation  
[4] AquaMind-Frontend/client/src/hooks/aggregations/useBatchFcr.ts — client-side batch FCR aggregation  
[5] AquaMind-Frontend/client/src/lib/api.ts — dashboard and infrastructure aggregations  
[6] AquaMind/apps/infrastructure/api/viewsets/overview.py — infrastructure overview aggregation endpoint  
[7] AquaMind/apps/batch/api/viewsets.py — `BatchContainerAssignmentViewSet.summary` aggregation  
[8] AquaMind/apps/inventory/api/viewsets/feeding.py — `FeedingEventViewSet.summary` aggregation  
[9] AquaMind/apps/inventory/api/viewsets/summary.py — batch feeding summary viewset  
[10] AquaMind/apps/operational/api/viewsets/fcr_trends.py — FCRTrendsViewSet  
[11] AquaMind/apps/operational/services/fcr_trends_service.py — FCR trends service logic  
[12] AquaMind/apps/inventory/services/fcr_service.py — batch/container FCR calculation and aggregation
