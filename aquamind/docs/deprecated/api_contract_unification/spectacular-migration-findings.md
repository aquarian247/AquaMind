# Spectacular Migration – Key Findings & Action Plan
_AquaMind / docs / progress_

## 1  |  Discovery

| Aspect | Current State |
|--------|---------------|
| Schema generator configured in `settings.py` | `DEFAULT_SCHEMA_CLASS = "drf_spectacular.openapi.AutoSchema"` |
| Packages installed | **drf-spectacular** **and** **drf-yasg** |
| Decorators found in view code | `@swagger_auto_schema` and other `drf_yasg` utilities |

**Key Finding:**  
Although `drf-spectacular` is already configured as the project-wide OpenAPI engine, many ViewSets still rely on `drf_yasg` decorators.  
Those decorators override Spectacular’s automatic introspection and mask query-parameter detection.

---

## 2  |  Why drf-spectacular Is Preferable

* **Automatic parameter detection**  
  ‑ Detects `filter_backends`, `filterset_fields`, `search_fields`, `ordering_fields`, pagination and authentication schemes without manual hints.

* **OpenAPI 3.1 ready**  
  ‑ Generates spec compliant with the latest standard; simplifies downstream tooling and client generation.

* **Cleaner code**  
  ‑ Eliminates hundreds of verbose `@swagger_auto_schema` blocks—maintainers write docstrings only where extra context is required (`@extend_schema`).

* **Better defaults & hooks**  
  ‑ Global `SECURITY`, convenient post-processing hooks, reusable components, etc.

---

## 3  |  Evidence: Auto-Detected Query Parameters

After generating a fresh schema with:

```bash
python manage.py spectacular --file openapi_test.yaml
```

Spectacular produced, for example, for `/api/v1/batch/batches/`:

```yaml
parameters:
  - in: query
    name: batch_number        # from filterset_fields
    schema: { type: string }
  - in: query
    name: batch_type          # enum detected from model choices
  - in: query
    name: lifecycle_stage
    schema: { type: integer }
  - name: ordering            # from OrderingFilter
  - name: page                # from pagination
  - name: search              # from SearchFilter
  - in: query
    name: species
    schema: { type: integer }
```

None of these parameters were declared manually—Spectacular inferred them.

Similar automatic detection is visible on:

* `/api/v1/batch/container-assignments/`
* `/api/v1/infrastructure/containers/`
* Every endpoint using `django-filter` or search/order backends

---

## 4  |  Migration Path

1. **Remove drf-yasg decorators**
   * Delete all `@swagger_auto_schema(...)` lines.
   * Strip `from drf_yasg...` imports.
2. **Add minimal `@extend_schema` only where behaviour deviates from defaults**  
   * Custom actions, non-standard request bodies, examples, etc.
3. **Run `spectacular --validate`**  
   * Ensures the spec remains error-free.
4. **Update docs & CI**
   * Replace swagger/redoc endpoints under `drf_yasg` with Spectacular’s `/api/schema/swagger-ui/` and `/api/schema/redoc/`.
5. **Clean dependencies**
   * Remove `drf-yasg` from `requirements.txt` once migration is complete.
6. **Regression test**
   * Execute contract tests (`schemathesis`) and unit tests to confirm unchanged behaviour.

---

## 5  |  Benefits on Completion

* **Reduced maintenance debt**  
  ‑ Hundreds of lines of repetitive decorator code deleted; fewer merge conflicts.
* **Consistent, up-to-date documentation**  
  ‑ New query params appear automatically when filters/search fields are added.
* **Modern tooling compatibility**  
  ‑ OpenAPI 3.1 facilitates better code-gen (e.g., Autorest, openapi-generator), validation, and mocking.
* **Cleaner review process**  
  ‑ Reviewers focus on business logic, not documentation boiler-plate.
* **Faster onboarding**  
  ‑ Developers only need to learn Spectacular’s small surface area (`extend_schema`, `extend_schema_field`).

---

### Status

* **Documentation updated:** `quality_assurance/api_documentation_standards.md` now references drf-spectacular.
* **Code untouched:** All prior Git changes were rolled back; migration work will proceed in a dedicated branch.

> _Next milestone_: Remove first batch of yasg decorators from `apps/infrastructure/api/viewsets/*` and regenerate the schema to verify zero manual parameters are required.
