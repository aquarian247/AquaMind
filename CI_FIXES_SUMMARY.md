# CI Pipeline Fixes – API Contract Unification  
*(feature/api-contract-unification branch)*  

This document records every change applied to unblock the two CI pipelines (backend + frontend) and allow the API-contract unification work to merge.

---

## 1. Backend CI (`django-tests.yml`)

| Issue | Symptom | Fix | Files |
|-------|---------|-----|-------|
| Schemathesis contract tests returned **401 Unauthorized** for every endpoint | 392 endpoint failures | 1. Added an on-the-fly **CI test user** inside the workflow<br>2. Generated a token via `manage.py shell`<br>3. Masked & passed it to Schemathesis with `--header "Authorization: Token $TOKEN"` | `.github/workflows/django-tests.yml` |
| OpenAPI generation errors blocked spec | drf-spectacular produced 3 blocking errors | • Created `AuthTokenSerializer` & `AuthTokenResponseSerializer` under `apps/users/api/serializers.py`<br>• Updated `CustomObtainAuthToken` to inherit from `GenericAPIView`, set `serializer_class`, and added `@extend_schema` metadata<br>• Annotated `dev_auth` with `@extend_schema` response<br>• Added `serializer_class = CSVUploadSerializer` to `DataEntryViewSet` (`apps/scenario/api/viewsets.py`) | `apps/users/api/serializers.py`<br>`apps/users/api/views.py`<br>`apps/scenario/api/viewsets.py` |
| Excess schema warnings (calculated fields defaulting to string) | Noise in spec & generated TS client | Added `@extend_schema_field(...)` decorators & type hints to representative calculated fields (e.g., `BatchSerializer` getters). Not a gate, but keeps warnings low. | Multiple serializer files (started with `apps/batch/api/serializers/batch.py`) |
| Convenience spec regeneration | Manual steps error-prone | Added cross-platform script `scripts/regenerate_api.(sh|ps1)` to generate & validate spec and optionally regenerate the frontend client. | `scripts/regenerate_api.sh`, `scripts/regenerate_api.ps1` |

**Result:**  
* OpenAPI 3.1 schema now validates with **0 errors** in CI.  
* Schemathesis contract job passes – all functional checks green.

---

## 2. Frontend CI (`AquaMind-Frontend`)

| Issue | Symptom | Fix | File |
|-------|---------|-----|------|
| TypeScript compile failure | 8 syntax errors in `client/src/pages/inventory.tsx` (lines 649-694 & 1692-1694) | • Removed orphaned/duplicated JSX after the component’s closing brace.<br>• Realigned `<Card>` blocks inside the main return.<br>• Ensured all braces & parentheses balance. | `client/src/pages/inventory.tsx` |

**Result:**  
* `npm run type-check` succeeds, Vite build passes.

---

## 3. Combined Outcome

| Pipeline | Status Before | Status After |
|----------|---------------|--------------|
| Backend (GitHub Action `test`) | ❌ OpenAPI errors, Schemathesis 401 failures | ✅ All tests, spec generation & contract checks pass |
| Frontend (GitHub Action `frontend-ci`) | ❌ TypeScript compile errors | ✅ Build & type-check succeed |

Green pipelines confirm that the API contract unification work is complete and safe to merge into **develop / main**.

---

### Next Steps / Maintenance

1. Keep the CI token creation snippet; rotate user/password if security policies change.  
2. When adding new function-based auth endpoints, remember to declare request/response serializers or `@extend_schema` decorators.  
3. Use `scripts/regenerate_api.sh --validate --frontend` when modifying backend serializers to immediately catch schema regressions.  

---
