# 🐟 Backend API Gaps ― AquaMind Contract Alignment

> Repository: **aquarian247/AquaMind**  
> Related frontend issues: aquarian247/AquaMind-Frontend#\<TBD> (type-mismatch report)

---

## 1 Executive Summary
During Phase-2 of API alignment the frontend switched to the generated **ApiService** client. Type-checking exposed several **contract gaps** where the React app expects data that the backend does not deliver or endpoints that are absent from the OpenAPI spec.

Resolving these gaps will unblock strict type-checking in CI, remove brittle client-side fall-backs, and keep the contract in sync going forward.

---

## 2 Gap Matrix ‑ by Module

### 2.1 Batch

| Gap Type | Missing Item | Frontend Usage | Recommendation | Priority |
|----------|--------------|----------------|----------------|----------|
| Endpoint | `/api/v1/batch/batches/{id}/analytics/` (growth / performance) | Batch analytics cards (growth rate, FCR, mortality curves) | Provide **aggregate analytics** endpoint OR document that FE should compute from growth-samples + mortality-records | High |
| Endpoint | `/api/v1/batch/batch-container-assignments/` alias expected as `batches/{id}/container-assignments/` | Traceability view | Add nested route (`batches/{id}/container-assignments/`) for convenience, or update FE to use list+filter | Med |
| Property | `container` (nested object) on `Batch` | Batch details page shows current container | Already derivable from latest assignment → expose in serializer OR FE derives via query | Med |

### 2.2 Infrastructure

| Gap Type | Missing Item | Frontend Usage | Recommendation | Priority |
|----------|--------------|----------------|----------------|----------|
| Computed props | **Area** → `totalBiomass`, `averageWeight`, `mortalityRate`, `feedConversion` | Area KPI panels & charts | Add read-only serializer fields backed by sub-queries; heavy computation – **backend preferred** | High |
| Computed props | **Area** → `rings`, `status`, `currentStock`, `water*` env. snapshots | Area detail page | Most are aggregates; consider new `/summary/` endpoint or FE compute | Med |
| Computed props | **FreshwaterStation** → `totalBiomass`, `currentStock`, `halls`, `averageWeight`, etc. | Station overview page | Provide station summary endpoint (`/stations/{id}/summary/`) returning these props | High |
| Endpoint | `/api/v1/infrastructure/containers/overview` & `/sensors/overview` | Infra dashboards | Could be client-side aggregate; **recommend FE compute** after pagination | Low |

### 2.3 Health

| Gap Type | Missing Item | Frontend Usage | Recommendation | Priority |
|----------|--------------|----------------|----------------|----------|
| Endpoint | `/api/v1/health/summary/` (KPI tiles) | Health dashboard widgets | Add lightweight summary ViewSet method or let FE aggregate from `health-sampling-events/` | Med |
| Endpoint | `/api/v1/health/alerts/critical/` | Critical alerts list | Implement filtered list endpoint (`?severity=CRITICAL`) OR define TanStack query filter | Low |

### 2.4 Scenario Planning

| Gap Type | Missing Item | Frontend Usage | Recommendation | Priority |
|----------|--------------|----------------|----------------|----------|
| Endpoint | `/api/v1/scenario/scenarios/{id}/projections/` (list & run) | Projection chart & duplicate/run-projection buttons | Implement projections ViewSet action (`projections/`, `run-projection/`) returning paginated results | High |
| Endpoint | `/api/v1/scenario/temperature-profiles/{id}/readings/` | Temp profile dialog | If readings belong to same model, add nested route; else FE can embed readings field | Med |

### 2.5 Inventory

| Gap Type | Missing Item | Frontend Usage | Recommendation | Priority |
|----------|--------------|----------------|----------------|----------|
| Endpoint | `/api/v1/inventory/feed-container-stocks/` summary alias | Inventory dashboard | Existing `feed-container-stocks/` list exists but FE expects summary fields (capacity %, etc.). Add serializer fields | Med |
| Computed props | `FeedingEvent` lacks `feed_type_name`, `feed_brand_name` (denorm strings) | Batch Feed History table | Expose read-only string fields or JOIN client-side via feed id → **backend preferred** to keep queries light for FE | Low |

---

## 3 Recommendation Guide

Legend:  
• **Backend** – implement in DRF serializer / ViewSet for authoritative value  
• **Frontend** – compute locally via adapter after list queries  
• **Hybrid** – lightweight props client-side; heavy aggregations backend

We propose:

1. **Implement backend summaries for heavy domain KPIs** (Area, Station, Scenario projections, Batch analytics).  
2. **Expose small denormalised strings** (feed names, container names) directly to minimise client joins.  
3. **Let frontend compute trivial counts** where pagination & caching already fetch full dataset (e.g., infra overview lists).

---

## 4 Prioritisation

| Priority | Definition | Target Release |
|----------|------------|----------------|
| **High** | Blocks critical UI or business flow | Next sprint |
| **Med**  | Degrades UX but work-arounds exist | Sprint +1 |
| **Low**  | Nice-to-have / future cleanup | Backlog |

---

## 5 Next Steps

1. **Confirm Tables** – backend & product owners validate each gap / priority.  
2. **Open Sub-issues** per module with acceptance criteria & serializer specs.  
3. **Update OpenAPI** schema and regenerate TS client (CI pipeline).  
4. **Frontend** removes local fall-backs once endpoints/properties available.  
5. Close this meta-issue once all sub-issues are merged and spec tagged **v1.0-contract-strict**.

---

/cc @backend-team @product-owner @frontend-lead
