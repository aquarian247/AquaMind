# Implement Geography KPI Summary endpoint (counts, capacity, biomass)

## Endpoint  
`GET /api/v1/infrastructure/geographies/{id}/summary/`

## Summary  
Add a detail action on `GeographyViewSet` that returns geography-level roll-ups for infrastructure inventory and biomass, eliminating multiple client-side joins.

## Outcome  
The endpoint returns the following fields:

| Field               | Type | Description                                                                                   |
|---------------------|------|-----------------------------------------------------------------------------------------------|
| `area_count`        | int  | Number of Areas in the geography                                                              |
| `station_count`     | int  | Number of Freshwater Stations in the geography                                               |
| `hall_count`        | int  | Number of Halls in the geography                                                              |
| `container_count`   | int  | Number of Containers in the geography                                                         |
| `ring_count`        | int  | Containers whose `container_type` category/name contains “ring” or “pen”                      |
| `capacity_kg`       | dec  | Sum of `Container.max_biomass_kg`                                                             |
| `active_biomass_kg` | dec  | Sum of `BatchContainerAssignment.active_biomass_kg` for **active** assignments in geography   |

## Scope  
- Add `@action(detail=True, methods=["get"])` named `summary` to **GeographyViewSet**.  
- Use ORM aggregates (`Count`, `Sum`) to compute metrics:  
  • Traverse child FK relationships (`Area`, `FreshwaterStation`, `Hall`, `Container`).  
  • `ring_count` filters `Container.container_type__category__icontains` **ring** OR **pen**.  
  • `capacity_kg` is the sum of `max_biomass_kg` on containers.  
  • `active_biomass_kg` sums active `BatchContainerAssignment.biomass_kg`.  
- Decorate action with `@method_decorator(cache_page(60))` for a 60 s cache window.  
- Document request/response with `@extend_schema` and an explicit `GeographySummarySerializer`.  

## References  
- Recommendations: `aquamind/docs/progress/aggregation/server-side-aggregation-kpi-recommendations.md`  
- Existing aggregate patterns:  
  • `apps/infrastructure/api/viewsets/overview.py`  
  • `apps/batch/api/viewsets.py` → `BatchContainerAssignmentViewSet.summary`  
- API standards: `aquamind/docs/quality_assurance/api_standards.md`

## Implementation Steps  
1. In `GeographyViewSet`, add:  
   ```python
   @method_decorator(cache_page(60), name="summary")
   @action(detail=True, methods=["get"], url_path="summary")
   @extend_schema(
       responses=GeographySummarySerializer,
       description="Return KPI roll-up for a single Geography."
   )
   def summary(self, request, pk=None):
       ...
   ```  
2. Query related objects efficiently using `prefetch_related` to avoid N+1 queries.  
3. Aggregate counts and sums as described in *Scope*.  
4. Compute `ring_count` with `filter(container_type__category__icontains="ring") | filter(container_type__category__icontains="pen")`.  
5. Build `GeographySummarySerializer` with the seven fields, example values, and units in help texts.  
6. Register kebab-case basename in router; regenerate OpenAPI schema.  

## Testing  
Create `apps/infrastructure/tests/api/test_geography_summary.py` covering:  
- Empty geography (all zeros).  
- Geography with mixed container types → validate `ring_count`.  
- Inactive assignments excluded from `active_biomass_kg`.  
- Geography with containers missing `max_biomass_kg` (capacity treated as 0).  
- Division-by-zero safe; cache neutrality (second call within 60 s faster).  

## Acceptance Criteria  
- All metrics correct and match ground-truth fixture queries.  
- Unit tests pass; OpenAPI schema validates without warnings.  
- Endpoint respects existing permission classes and kebab-case router conventions under `/api/v1/`.  
- Response time < 200 ms with warm cache.
