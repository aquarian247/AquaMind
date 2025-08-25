# 📈 Investigate & Implement Historical FCR Trend Calculations

Repository: **aquarian247/AquaMind**  
Labels: `enhancement`, `analytics`, `inventory`, `phase-next`

---

## 1 Problem Statement

**Feed Conversion Ratio (FCR)** is the primary efficiency KPI in aquaculture:  

```
FCR = (total feed used) / (biomass gain)
```

Management, finance and nutrition teams rely on **multi-month historical FCR trends** to:

* Detect feed wastage & optimise feeding strategies  
* Correlate environmental factors with production cost  
* Produce mandatory sustainability reports (ASC, GSI)

At the moment the frontend attempts to derive FCR trends client-side, pulling thousands of `FeedingEvent`, `GrowthSample` and `MortalityRecord` rows, causing:

* Large payloads and slow dashboards on high-latency links
* Complex, error-prone calculations replicated in JS
* Inconsistent results across clients

We need a **single, authoritative, server-side implementation** that delivers aggregated FCR series ready for visualisation.

---

## 2 Design Considerations

| Topic | Server-Side Aggregation | Client-Side Aggregation |
|-------|------------------------|-------------------------|
| **Data volume** | Delivers *N* points (e.g. weekly) – small | Transfers all raw events – large |
| **Consistency** | One canonical formula, tested in Python | Risk of divergent JS logic |
| **CPU / I/O cost** | Executes once on DB, can cache | Repeated in every browser session |
| **Security** | Sensitive cost data stays in VLAN | Exposes granular cost data to DMZ |
| **Extensibility** | Easy to add filters (species, geography) | Hard to slice in browser without more data |

Given the heavy data volume (see §3) and need for uniform business logic, **server-side aggregation is preferred**.

---

## 3 Data Volume Analysis

| Table | Avg rows / month | Payload / row | Monthly size |
|-------|------------------|---------------|--------------|
| FeedingEvent | ~120 k | 180 B | **22 MB** |
| GrowthSample | ~15 k | 140 B | 2 MB |
| MortalityRecord | ~30 k | 160 B | 5 MB |

For a one-year trend, naive client download ≈ **350 MB**.  
Aggregating in SQL and returning 52 weekly data points ≈ **20 kB**.

---

## 4 Performance Implications

* Use **TimescaleDB continuous aggregates** or materialised views to compute FCR weekly/monthly.
* Index on `feeding_date`, `batch_id` and `species_id` to accelerate filters.
* Cache layer: 15-min TTL in Redis keyed by `(geography, species, period, aggregation_level)`.
* Expect  < 200 ms response for typical queries.

---

## 5 Proposed API Design

```
GET /api/v1/inventory/fcr-trends/
```

| Query Param | Type | Default | Description |
|-------------|------|---------|-------------|
| `start_date` | ISO date | 1 year ago | Lower bound for trend |
| `end_date`   | ISO date | today | Upper bound |
| `interval`   | enum(`DAILY`,`WEEKLY`,`MONTHLY`) | `WEEKLY` | Bucket size |
| `species`    | int[] | — | Filter by species |
| `geography`  | int[] | — | Filter by geography/area |

### Response (example)

```json
{
  "interval": "WEEKLY",
  "unit": "ratio",
  "series": [
    { "period_start": "2025-01-01", "period_end": "2025-01-07", "fcr": 1.27 },
    { "period_start": "2025-01-08", "period_end": "2025-01-14", "fcr": 1.32 }
  ]
}
```

*Paginated?* – No, bounded series size  
*Auth* – Same JWT; permission filters applied server-side

---

## 6 Success Criteria

* [ ] **Accuracy**: Values match independent Excel model ≤ ±0.02 FCR points  
* [ ] **Performance**: p95 latency ≤ 250 ms for 1-year weekly query  
* [ ] **Scalability**: Handles 10 parallel queries (load tests) without DB lock  
* [ ] **OpenAPI Spec**: Endpoint documented & CI passes contract tests  
* [ ] **Unit Tests**: Cover edge cases (zero growth, missing feed data) ≥ 90 % branch  
* [ ] **Frontend Integration**: React dashboard consumes new endpoint – removes bulk FeedingEvent download

---

## 7 Next Steps

1. **Data model review** – confirm Feed/FIFO cost tracking alignment  
2. Prototype SQL aggregate (CTE or continuous aggregate)  
3. Create serializer + viewset + router entry (`fcr-trends`)  
4. Write unit + integration tests (fixture factories exist)  
5. Update `openapi.yaml` → triggers client regen pipeline  
6. Coordinate with frontend team to switch dashboard to new endpoint  
7. Load/perf test & tune indexes/materialised view refresh policy

/cc @inventory-team @db-performance @frontend-lead
