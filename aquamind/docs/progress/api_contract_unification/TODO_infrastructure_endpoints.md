# TODO – Restore Infrastructure API Endpoints
_AquaMind • API Contract Unification Progress_

---

## 1. Current Situation
* All `/api/v1/infrastructure/*` operations were **temporarily removed** from:
  * `aquamind/api/router.py` – infrastructure router import + registration removed  
  * OpenAPI schema – stripped by `prune_legacy_paths` post-processing hook
* Schemathesis suite now runs against 344 live operations (no infra noise).

## 2. Why They Were Removed
* **Double registration** of the infrastructure router produced two URL patterns for every endpoint:
  1. `router.registry.extend(infrastructure_router.registry)`
  2. `path('infrastructure/', include((infrastructure_router.urls, 'infrastructure')))`
* Django resolved only one set; drf-spectacular documented both.  
  → Result: schema advertised paths that were not reachable → **48 × 404 failures**.

## 3. Specific Technical Issue
File: `aquamind/api/router.py`

```python
# PROBLEM SECTION (before Phase 4)
router.registry.extend(infrastructure_router.registry)      # ❶
...
urlpatterns = [
    ...
    path('infrastructure/', include((infrastructure_router.urls, 'infrastructure'))),  # ❷
]
```

Both ❶ and ❷ register the same viewsets under the same prefix.  
During Phase 4 we **commented out** the import + both lines.

## 4. Steps to Properly Restore Infrastructure Endpoints
1. **Re-enable the import**  
   ```python
   from apps.infrastructure.api.routers import router as infrastructure_router
   ```
2. **Choose ONE registration style** (preferred: explicit `path()` include)
   ```python
   # Remove / comment out the registry extension ↓
   # router.registry.extend(infrastructure_router.registry)

   urlpatterns = [
       ...
       path('infrastructure/', include((infrastructure_router.urls, 'infrastructure'))),
   ]
   ```
3. **Delete the prune hook override**  
   *Remove* `aquamind.utils.openapi_utils.prune_legacy_paths` from
   `settings_ci.py -> SPECTACULAR_SETTINGS['POSTPROCESSING_HOOKS']`.
4. **Remove the function itself** or leave a TODO to delete once confirmed.
5. **Regenerate schema**  
   ```bash
   python manage.py spectacular --file api/openapi.yaml --settings=aquamind.settings_ci
   ```
6. **Validate routing locally**  
   ```bash
   python manage.py show_urls | grep infrastructure
   ```
7. **Run focused contract tests**  
   ```bash
   schemathesis run --base-url=http://127.0.0.1:8000 \
     --include-path-regex="/api/v1/infrastructure/.*" \
     --header "Authorization: Token <dev-token>" \
     api/openapi.yaml
   ```
   Expect **0 server-error / 404** failures.
8. **Full test sweep** – run entire Schemathesis suite again; error count should not increase.

## 5. How to Test the Fix (Checklist)
- [ ] Local server starts without `django.urls.exceptions.Resolver404` for infra paths  
- [ ] `GET /api/v1/infrastructure/geographies/` returns 200 with valid auth  
- [ ] Regenerated schema contains infra paths **once** (no duplicates)  
- [ ] Schemathesis infra subset passes all checks  
- [ ] Global run remains ≤ previous error count  
- [ ] GitHub CI passes

## 6. Timeline / Ownership
| Task | Owner | Target Date |
|------|-------|------------|
| Re-enable router & remove duplicate registry | _YOU_ | **Day 1** next work session |
| Remove prune hook & regenerate schema | _YOU_ | Day 1 |
| Local + CI Schemathesis validation | _YOU_ | Day 2 |
| Delete legacy hook code / docs | _YOU_ | Day 3 |
| Close Phase 4 TODO | _YOU_ | Day 3 |

> **Reminder:** Do **not** merge restoration until all contract tests pass.  
> Keep this document until infrastructure endpoints are fully operational and CI green.

---
_Last updated: {{ date }}_
