# Enhance container-assignments summary with geography/area/station/hall/container_type filters

## Endpoint  
GET `/api/v1/batch/container-assignments/summary/`

## Summary  
Extend the existing summary action to accept standard location filters and container type, keeping full backward-compatibility.

## Outcome  
New optional query params:  

| Param            | Type   | Notes                                              |
|------------------|--------|----------------------------------------------------|
| `geography`      | int ID | Filter by Geography of the container               |
| `area`           | int ID | Filter by Area                                     |
| `station`        | int ID | Filter by Freshwater Station                       |
| `hall`           | int ID | Filter by Hall                                     |
| `container_type` | slug   | Filter by ContainerType slug (e.g. `RING`, `TANK`) |
| `is_active`      | bool   | Defaults to `true`; include inactive when `false`  |

Response shape remains unchanged (e.g., `assignment_count`, `active_biomass_kg`, `population_count`).

## Scope  
- Update `BatchContainerAssignmentViewSet.summary` to parse and apply the new query params via related `Container` → `Hall` → `FreshwaterStation` → `Geography`.  
- Validate IDs exist; unknown filters return `400`.  
- Preserve current behaviour when no filters are supplied.  
- Document parameters and examples with `@extend_schema`.  

## References  
- `apps/batch/api/viewsets.py` → `BatchContainerAssignmentViewSet.summary`  
- Infrastructure relationships (`Container`, `Hall`, `FreshwaterStation`, `Geography`)  
- API standards: `aquamind/docs/quality_assurance/api_standards.md`  

## Implementation Steps  
1. Add helper method `apply_location_filters(queryset, request)` to build chained filters.  
2. Accept `container_type` using `slug` of `ContainerType`.  
3. Guard against conflicting or invalid IDs; return `400` with helpful detail.  
4. Update aggregation query—no change to fields, only narrowed queryset.  
5. Decorate action with updated `@extend_schema` documenting new params and examples.  
6. Maintain `@cache_page` (30–60 s) to keep performance predictable.  

## Testing  
Create `apps/batch/tests/api/test_container_assignments_summary_filters.py` covering:  
- Each filter individually (`geography`, `area`, `station`, `hall`, `container_type`, `is_active=false`).  
- Combined filters (e.g., `geography + container_type`).  
- Invalid ID / enum values → `400`.  
- Baseline with no filters (existing behaviour).  
- Active vs inactive assignments handling.  

## Acceptance Criteria  
- Filters correctly narrow aggregation; unit tests pass.  
- Response schema unchanged; OpenAPI validates with new params.  
- Backward-compatible: calls without new params behave exactly as before.  
- Endpoint respects existing authentication/permission classes.  
- drf-spectacular generates zero warnings; CI green.
