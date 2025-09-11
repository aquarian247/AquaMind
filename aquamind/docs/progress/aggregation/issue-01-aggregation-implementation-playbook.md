# Establish Aggregation Implementation Playbook (patterns, tests, docs)

## Summary  
Create a shared “playbook” that standardizes how we build aggregation endpoints for KPI cards—covering patterns, caching, schema, and tests—to minimize context-rot across engineering sessions.

## Outcome  
A concise document and copy-pasteable code snippets that every subsequent aggregation task follows. CI validation steps are codified and reusable.

## Scope  
• Add a short doc section (or sibling markdown) containing:  
  – Required imports, `@action` vs `APIView` selection, example `extend_schema`, and `cache_page` usage.  
  – A minimal test template using `reverse()` and kebab-case basenames.  
  – Command(s) for OpenAPI validation (`drf-spectacular --validate`).  
• **No business logic** or endpoint implementation belongs in this task.

## References  
- `aquamind/docs/progress/aggregation/server-side-aggregation-kpi-recommendations.md`  
- `aquamind/docs/quality_assurance/api_standards.md`  
- Example aggregates:  
  • `apps/infrastructure/api/viewsets/overview.py`  
  • `apps/batch/api/viewsets.py` → `BatchContainerAssignmentViewSet.summary`  
  • `apps/inventory/api/viewsets/feeding.py` → `FeedingEventViewSet.summary`

## Approach  
1. Create or update `aquamind/docs/development/aggregation_playbook.md`.  
2. Add code snippet: a DRF `@action` with `@extend_schema` and `@method_decorator(cache_page(60))`.  
3. Add pytest template illustrating:  
   ```python
   url = reverse("area-summary", args=[area.id])
   response = client.get(url)
   assert response.status_code == 200
   ```  
4. Document the command to regenerate & validate OpenAPI:  
   ```bash
   ./manage.py spectacular --file openapi.yaml && spectral lint openapi.yaml
   ```  
5. Link the new playbook from the recommendations document.

## Acceptance Criteria  
- Playbook published and linked in recommendations.  
- Includes: pattern snippet, test template, OpenAPI validation command.  
- Readable in ≤5 min; adopted by at least one follow-up issue PR.  
- CI passes; no drf-spectacular warnings introduced.
