# FCR Trends — clarify schema (units, data_points, confidence) and default behavior

## Endpoint / Scope  
Existing: `/api/v1/operational/fcr-trends/` (ViewSet + Serializer)

---

## Summary  
Clarify and document schema semantics for FCR trends responses and enforce explicit defaults.

---

## Outcome  
- Serializer / docs specify:  
  • units (FCR ratio)  
  • meaning of `data_points` array  
  • semantics of `confidence` and `estimation_method`  
- Response always includes explicit `aggregation_level` and interval semantics (DAILY, WEEKLY Mon–Sun, MONTHLY calendar).

---

## Scope  
- Update serializer docstrings and drf-spectacular `extend_schema` to include field descriptions and concrete examples.  
- Ensure defaults are explicit:  
  • default `aggregation_level` (e.g., `GEOGRAPHY`)  
  • default `interval` (e.g., `DAILY`)  
  • documented behavior when filters are omitted.  
- Optionally expose `scenarios_used` and model / version metadata for transparency.

---

## References  
- `apps/operational/api/viewsets/fcr_trends.py`  
- `apps/operational/services/fcr_trends_service.py`  
- Recommendations doc — FCR checklist (`aquamind/docs/progress/aggregation/server-side-aggregation-kpi-recommendations.md`)

---

## Implementation Steps  
1. Add / expand `extend_schema` on the ViewSet’s list / retrieve actions with response examples covering each interval and aggregation level.  
2. Update the serializer:  
   - Ensure `aggregation_level`, `interval`, `units`, and `confidence` are explicit, documented fields.  
   - Include optional `scenarios_used` and `model_version` metadata if available from service layer.  
3. Document interval bucket boundaries (e.g., WEEKLY aggregates are **Monday–Sunday inclusive**) in the field description.  
4. Regenerate OpenAPI; resolve any drf-spectacular warnings.

---

## Testing  
Add `apps/operational/tests/api/test_fcr_trends_schema.py` covering:  
- Default response when no filters supplied (contains explicit fields).  
- Presence and correctness of `units`, `aggregation_level`, `interval`, `confidence`.  
- OpenAPI generation passes with zero warnings.

---

## Acceptance Criteria  
- Serializer & docs clearly define all fields, units, and default behaviors.  
- Endpoint returns explicit `aggregation_level` & `interval` regardless of request filters.  
- Tests pass; OpenAPI generation succeeds without warnings.  
- Optional metadata (`scenarios_used`, `model_version`) present when service provides it.
