# API Contract Fixes Plan  
_AquaMind – Backend_  
**Created:** 2025-07-21 **Maintainer:** `@Backend-Droid`  

---

## 1 · Executive Summary  
Recent Schemathesis runs revealed multiple contract mismatches between the documented OpenAPI specification (`api/openapi.yaml`) and actual runtime behaviour:

* Endpoints that rely on **query-string parameters** (`batch_id`, `container_id`, …) do **not document** those parameters.  
* Such endpoints legitimately return **400 Bad Request** on validation errors, but **400 is missing** from their documented response codes.  
* One endpoint (`POST /api/v1/batch/growth-samples/`) is throwing a **500 TypeError** – an implementation bug.  
* Hooks now load correctly; remaining failures are true contract or logic errors.

Failing to align docs & behaviour blocks CI and downstream consumers (frontend code-gen, external integrators). This plan details the chronological tasks required to restore contract integrity.

---

## 2 · Task Breakdown (checkboxes)  

### A Schema Fixes (Documentation-only)  
- [x] A1 Add missing **query parameters** to each affected endpoint in `api/openapi.yaml`.  
- [x] A2 Add **`400` response** object (with generic error schema) where validation errors are possible.  
- [ ] A3 Regenerate schema via `python manage.py spectacular --file api/openapi.yaml --settings=aquamind.settings_ci` and commit.

### B Implementation Fixes  
- [ ] B1 `POST /api/v1/batch/growth-samples/` – reproduce & patch TypeError, add regression unit test.  
- [ ] B2 Ensure parameter validation returns `400` (not `500`) everywhere.  
- [ ] B3 Ensure viewsets use `ValidatedPageNumberPagination` so invalid `page` queries give `400`.

### C Patterns Sweep  
- [ ] C1 Search for DRF endpoints ending in **`/by_batch/`**, **`/by_container/`**, **`/fifo_order/`**, etc. Verify that required IDs are documented & validated.  
- [ ] C2 Glob-search for `required.*parameter` strings in error messages to catch similar undocumented params.  
- [ ] C3 Check all non-CRUD “action” routes (`@action`) for missing parameter documentation & 400 codes.

### D Testing & CI  
- [ ] D1 Run local **Schemathesis** (`--max-examples=3`) with hooks; ensure zero failures.  
- [ ] D2 Run full **pytest** suite – all pass.  
- [ ] D3 Push branch; GitHub Actions must pass **contract step**.  
- [ ] D4 Frontend: regenerate TypeScript client once contract is green.

---

## 3 · Affected Endpoints (initial set)  

| Endpoint | Required Query Param(s) | Missing in Schema | Response Code Issues |
|----------|-------------------------|-------------------|----------------------|
| GET `/api/v1/inventory/feeding-events/by_batch/` | `batch_id` | Parameter & 400 | Undocumented 400 |
| GET `/api/v1/inventory/batch-feeding-summaries/by_batch/` | `batch_id` | Parameter & 400 | Undocumented 400 |
| GET `/api/v1/inventory/feed-container-stock/fifo_order/` | `container_id` | Parameter & 400 | Undocumented 400 |
| GET `/api/v1/broodstock/fish/by_container/` | `container_id` | Parameter & 400 | Undocumented 400 |
| GET `/api/v1/scenario/scenarios/summary_stats/` | `batch_id` (optional?) | Response schema | Missing field `biological_constraints_info` |
| POST `/api/v1/batch/growth-samples/` | body JSON | N/A | 500 (TypeError) |

_✱ Additional endpoints may appear during pattern sweep._

---

## 4 · Examples of Fixes Needed  

### 4.1 OpenAPI (YAML)  

```yaml
/api/v1/inventory/feeding-events/by_batch/:
  get:
    parameters:
      - in: query
        name: batch_id
        required: true
        schema:
          type: integer
          minimum: 1
    responses:
      "400":
        description: Bad request (validation error)
        content:
          application/json:
            schema:
              $ref: "#/components/schemas/ErrorDetail"
```

### 4.2 DRF View Validation (simplified)  

```python
batch_id = self.request.query_params.get("batch_id")
if batch_id is None:
    return Response({"error": "batch_id parameter is required"}, status=400)
```

### 4.3 Error Schema Component  

```yaml
components:
  schemas:
    ErrorDetail:
      type: object
      properties:
        error:
          type: string
      required: ["error"]
```

---

## 5 · Testing Approach  

1. **Unit tests** for each amended view verifying 400 behaviour when parameter missing.  
2. **Schemathesis**  
   * `SCHEMATHESIS_HOOKS=aquamind.utils.schemathesis_hooks`  
   * `--checks all --max-examples=5` locally.  
3. **CI Pipeline** runs full Schemathesis against updated schema, must pass.  
4. Manual **cURL reproduction** for one sample of each endpoint to double-check docs match reality.  

---

## 6 · Success Criteria  

* ✔ OpenAPI schema includes every required query/body parameter and accurate response codes (200 + 400 + auth codes + 500).  
* ✔ `schemathesis run` (CI) completes **with zero failures and zero warnings** for undocumented status codes or missing fields.  
* ✔ No 500s in CI after TypeError fix.  
* ✔ All automated unit & integration tests pass.  
* ✔ Frontend code-gen regenerates without manual overrides for these endpoints.  

---

### Revision History  

| Date | Author | Notes |
|------|--------|-------|
| 2025-07-21 | Backend-Droid | Initial plan drafted |
| 2025-07-21 | Backend-Droid | ✅ Completed tasks A1 & A2 – query params & 400 responses added to schema |

