# Publish integration notes and example requests for dashboard KPI consumption

## Summary
Provide actionable, copy-pasteable examples that guide the frontend migration away from client-side aggregation and onto the new / enhanced server-side summary endpoints.

## Outcome
Frontend and integration developers can plug the examples into Postman, `curl`, or `api.ts` hooks and instantly validate responses for KPI cards and trends.

## Scope
• Concrete examples for  
&nbsp;&nbsp;• **Area summary** – `GET /api/v1/infrastructure/areas/{id}/summary/`  
&nbsp;&nbsp;• **Freshwater Station summary** – `GET /api/v1/infrastructure/freshwater-stations/{id}/summary/`  
&nbsp;&nbsp;• **Hall summary** – `GET /api/v1/infrastructure/halls/{id}/summary/`  
&nbsp;&nbsp;• **Geography summary** – `GET /api/v1/infrastructure/geographies/{id}/summary/`  
&nbsp;&nbsp;• **Container-assignments summary** with filters  
&nbsp;&nbsp;• **Feeding-events summary** with start/end date range  
&nbsp;&nbsp;• **FCR trends** examples for DAILY, WEEKLY, MONTHLY intervals  
• Link back to recommendations and API-standards documents.

## Example Snippets

Area summary  
    GET /api/v1/infrastructure/areas/42/summary/
    {
      "container_count": 18,
      "ring_count": 12,
      "active_biomass_kg": 84250.5,
      "population_count": 213400,
      "avg_weight_kg": 0.395
    }

Freshwater Station summary  
    GET /api/v1/infrastructure/freshwater-stations/7/summary/
    {
      "hall_count": 6,
      "container_count": 42,
      "active_biomass_kg": 35670.8,
      "population_count": 90500,
      "avg_weight_kg": 0.394
    }

Hall summary  
    GET /api/v1/infrastructure/halls/11/summary/
    {
      "container_count": 14,
      "active_biomass_kg": 12100.2,
      "population_count": 31000,
      "avg_weight_kg": 0.39
    }

Geography summary  
    GET /api/v1/infrastructure/geographies/3/summary/
    {
      "area_count": 5,
      "station_count": 3,
      "hall_count": 11,
      "container_count": 124,
      "ring_count": 48,
      "capacity_kg": 250000.0,
      "active_biomass_kg": 132500.0
    }

Container-assignments summary with filters  
    GET /api/v1/batch/container-assignments/summary/?geography=3&container_type=RING&is_active=true
    {
      "assignment_count": 57,
      "active_biomass_kg": 48720.4,
      "population_count": 118000
    }

Feeding-events summary (range)  
    GET /api/v1/inventory/feeding-events/summary?start_date=2025-01-01&end_date=2025-01-31
    {
      "events_count": 124,
      "total_feed_kg": 3580.2
    }

FCR trends – daily buckets  
    GET /api/v1/operational/fcr-trends/?interval=DAILY&geography=3&start_date=2025-01-01&end_date=2025-01-31
    {
      "aggregation_level": "GEOGRAPHY",
      "interval": "DAILY",
      "data_points": [
        {"date": "2025-01-01", "fcr": 1.45, "confidence": 0.92},
        {"date": "2025-01-02", "fcr": 1.48, "confidence": 0.91},
        "... truncated ..."
      ]
    }

## References
* [Recommendations](server-side-aggregation-kpi-recommendations.md)  
* [API standards](../../quality_assurance/api_standards.md)  
* Existing endpoints: `/infrastructure/overview`, `/operational/fcr-trends/`

## Acceptance Criteria
1. Examples validated against current serializers & schema (drf-spectacular passes).  
2. Document linked from the recommendations doc.  
3. Reviewed and approved by at least one frontend consumer.  
4. No stale URLs or response keys; follows API-standards kebab-case conventions.  
