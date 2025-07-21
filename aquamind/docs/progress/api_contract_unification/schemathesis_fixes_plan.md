# Schemathesis Fixes & Hardening Plan  
*Location*: `aquamind/docs/progress/api_contract_unification/schemathesis_fixes_plan.md`  
*Owner*: API Unification Tiger Team  
*Status*: **In&nbsp;Progress** &nbsp;|&nbsp; _Last updated: 2025-07-21_  
_Note_: Generic **401 / 403 / 404 / 500** response injection has been implemented & schema regenerated.  
This should eliminate ~180 “undocumented status code” failures in the next CI run.

---

## 1. Executive Summary

Latest CI run (`feature/api-contract-unification`) shows **104 / 392 Schemathesis checks passing**  
* → **288 failures** spread across 5 major categories (undocumented 404s, unhandled 4xx/5xx, invalid data, auth drift, CI artefact gaps).*  

Goal: raise contract-test pass-rate to **≥ 95 %** while keeping fixes **sustainable and maintainable**.

---

## 2. Root Cause Analysis

| Category | Symptoms | Likely Root Cause |
|----------|----------|-------------------|
| **Undocumented status codes** | “Undocumented HTTP status code 404” | OpenAPI schema missing 404/401/403 responses for detail routes & auth endpoints |
| **Resource existence errors (404)** | PUT/PATCH/DELETE to `/resource/0/` fails | Schemathesis generates non-existent IDs; backend returns 404 (valid) but schema disallows it |
| **Validation / Integrity errors (400/500)** | `IntegrityError NOT NULL … description` | Missing required fields in generated payloads; serializers do not handle nulls gracefully |
| **Auth inconsistency** | “401 unauthorized” on endpoints declared secured | Token OK, but viewset lacks `authentication_classes` / permission mismatch |
| **CI noise & artefact loss** | 29 000+ log lines, truncated output | CLI verbosity + artefact limits; missing `--junit-xml` for GitHub annotations |

---

## 3. Action Plan (check off as completed)

### 3.1 Status-Code Documentation
- [x] ✅ Add generic `404` response to all `{id}` detail operations (`AutoSchema` hook)  
- [x] ✅ Inject `401` / `403` for secured endpoints (`ensure_global_security` already present; extend `add_validation_error_responses`)  
- [x] ✅ Regenerate `api/openapi.yaml`; diff & commit

### 3.2 Resource Existence Validation
- [ ] ☐ Create *test data factory* (`scripts/testing/factory.py`) that seeds at least one valid record per model before Schemathesis run  
- [ ] ☐ Add `pre_run.sh` in CI to call factory via management command (`python manage.py seed_schemathesis_data`)  
- [ ] ☐ Configure Schemathesis `--pre-run` hook if available (or wrapper script)

### 3.3 Data Generation Improvements
- [ ] ☐ Add `x-example` or `examples` in schema for complex POST payloads (`EnvironmentalReading`, `Scenario`)  
- [ ] ☐ Tighten schema constraints (e.g., non-nullable `description` on `EnvironmentalParameter`) so fuzzing respects required fields  
- [ ] ☐ Review `clamp_integer_schema_bounds` ‑ confirm bounds cover PostgreSQL+SQLite

### 3.4 Authentication Consistency
- [ ] ☐ Audit **all** viewsets: enforce  
  ```python
  authentication_classes = [TokenAuthentication, JWTAuthentication]
  permission_classes     = [IsAuthenticated]
  ```  
- [ ] ☐ Add anonymous whitelist for `/api/v1/auth/token/`, `/api/v1/auth/dev-auth/` (schema `security: [{}]`)  
- [ ] ☐ Remove temporary `AuthHeaderDebugMiddleware` after confirmation

### 3.5 CI / CD Enhancements
- [ ] ☐ Split contract-test job: `prepare-data` → `schemathesis-run` (matrix ready)  
- [ ] ☐ Store full Schemathesis output as artefact **and** JUnit XML for PR annotations  
- [ ] ☐ Increase `--hypothesis-max-examples` to `25` once flake rate stabilises  
- [ ] ☐ Fail fast on schema diff between `generate-spec` step & committed file

---

## 4. Technical Implementation Details

### 4.1 Status Code Hook (`openapi_utils.py`)
```python
def add_standard_responses(endpoints: Any) -> Any:
    for path, path_item in endpoints["paths"].items():
        for method, op in path_item.items():
            # Skip non-HTTP keys
            if method not in {"get", "post", "put", "patch", "delete"}:
                continue
            responses = op.setdefault("responses", {})
            # 404 for any path containing '{id}' or '{pk}'
            if "{id}" in path or "{pk}" in path:
                responses.setdefault("404", {"description": "Not Found"})
            # 401 / 403 for secured ops
            if op.get("security", []):       # empty list means anonymous
                responses.setdefault("401", {"description": "Unauthorized"})
                responses.setdefault("403", {"description": "Forbidden"})
    return endpoints
```
Add hook path to `SPECTACULAR_SETTINGS["POSTPROCESSING_HOOKS"]`.

### 4.2 Seed Data Management Command
```python
# apps/core/management/commands/seed_schemathesis_data.py
class Command(BaseCommand):
    help = "Populate minimal valid objects for contract tests"

    def handle(self, *args, **opts):
        from apps.environmental.models import EnvironmentalParameter
        EnvironmentalParameter.objects.get_or_create(
            name="Temperature", defaults={"unit": "°C", "description": "Water temperature"}
        )
        # Repeat for other critical models …
        self.stdout.write(self.style.SUCCESS("Seeded base data"))
```

### 4.3 Example Payloads
```yaml
components:
  schemas:
    EnvironmentalReading:
      type: object
      required: [parameter_id, value, recorded_at]
      example:
        parameter_id: 1
        value: 12.6
        recorded_at: "2025-07-01T12:00:00Z"
```

### 4.4 CI Workflow Snippet
```yaml
- name: Seed data
  run: python manage.py seed_schemathesis_data --settings=aquamind.settings_ci

- name: Schemathesis run
  run: |
    schemathesis run \
      --report junit.xml \
      --junit-xml schemathesis-junit.xml \
      ...
```

---

## 5. Testing & Validation

1. **Local loop**
   ```bash
   python manage.py migrate --settings=aquamind.settings_ci
   python manage.py seed_schemathesis_data --settings=aquamind.settings_ci
   TOKEN=$(python manage.py get_ci_token --settings=aquamind.settings_ci)
   schemathesis run --base-url=http://127.0.0.1:8000 \
     --header "Authorization: Token $TOKEN" api/openapi.yaml
   ```
2. **CI pipeline**
   * Ensure `schemathesis-output.txt` & `schemathesis-junit.xml` artefacts uploaded
3. **Manual spot-checks**
   * Try `curl -H "Authorization: Token $TOKEN" http://…/parameters/1/`

---

## 6. Success Criteria & Metrics

| Metric | Target | Notes |
|--------|--------|-------|
| Schemathesis pass-rate | **≥ 95 %** (≤ 20 failures) | Stretch: 100 % |
| Undocumented status code occurrences | 0 | Verified via log grep |
| CI duration impact | +≤ 20 % | Keep under 12 min total |
| OpenAPI diff noise | None | Schema deterministic & committed |
| PR annotation clarity | JUnit XML produced | GitHub UI shows failing cases |

---

### 🎯 Completion Definition of Done

- [ ] All checkboxes in §3 ticked  
- [ ] CI badge green on `feature/api-contract-unification`  
- [ ] Front-end client regenerates with no type errors  
- [ ] Document updated with final metrics & moved to **Completed** folder  

