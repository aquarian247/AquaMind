# OpenAPI Generation – Issues To Fix  
*File: `aquamind/docs/progress/openapi_issues_to_fix.md`*  
_Last updated: 2025-07-03_

During the Section&nbsp;4 testing phase the backend OpenAPI build produced **24 errors (3 unique sources)** and **72 warnings (36 unique fields)**.  
The errors block endpoints from appearing in the spec; the warnings degrade schema quality but do **not** fail CI.

---

## 1  Blocking Errors (must-fix)

| # | File & Line | Problem | Impact | Suggested Fix |
|---|-------------|---------|--------|---------------|
| **E-1** | `apps/users/api/views.py` – class `CustomObtainAuthToken` (line&nbsp;14) | APIView has **no `serializer_class`** so drf-spectacular cannot infer request / response schema. | `/api/auth/token/` missing from spec | ```python\nclass AuthTokenSerializer(serializers.Serializer):\n    username = serializers.CharField()\n    password = serializers.CharField(write_only=True)\n\nclass CustomObtainAuthToken(GenericAPIView):\n    permission_classes = [AllowAny]\n    serializer_class = AuthTokenSerializer\n    def post(self, request, *args, **kwargs):\n        ...\n``` |
| **E-2** | `apps/users/api/views.py` – function `dev_auth` (line&nbsp;46) | Decorated function view without serializer; treated as plain `APIView`. | `/api/auth/dev/` missing (dev only) | Either convert to `GenericAPIView` + serializer _or_ add:<br>```python\n@extend_schema(responses=AuthTokenSerializer)\n``` |
| **E-3** | `apps/scenario/api/viewsets.py` – class `DataEntryViewSet` (≈ line 750) | ViewSet lacks `serializer_class` attribute. | All `/api/v1/scenario/data-entry/*` paths absent | Declare proper serializer:<br>```python\nclass DataEntryViewSet(viewsets.ModelViewSet):\n    queryset = DataEntry.objects.all()\n    serializer_class = DataEntrySerializer\n``` |

> After fixing, regenerate the spec locally and ensure errors count = **0**.

---

## 2  Schema Quality Warnings (type-hints)

36 serializer `@property` / `get_…` methods lack explicit field type.  
drf-spectacular defaults them to **string**, causing incorrect models in the TS client.

Typical examples:

| File | Methods |
|------|---------|
| `apps/batch/api/serializers/batch.py` | `get_calculated_biomass_kg`, `get_current_lifecycle_stage`, etc. |
| `apps/health/api/serializers/lab_sample.py` | `get_batch_number`, `get_container_name`, … |
| `apps/scenario/api/serializers.py` | `get_stage_coverage`, `get_temperature_summary`, … |
| `apps/inventory/api/serializers/container_stock.py` | `get_total_value` |

### Recommended Fix Pattern

```python
from drf_spectacular.utils import extend_schema_field

@extend_schema_field(serializers.FloatField())
def get_calculated_biomass_kg(self, obj) -> float:   # add return type too
    return obj.calculated_biomass_kg
```

Apply `extend_schema_field` (or add real model field & annotate return type).  
Aim to reduce warning count to near-zero; cosmetic warnings may remain.

---

## 3  Checklist for Resolution

- [ ] Add `AuthTokenSerializer` & wire into `CustomObtainAuthToken`
- [ ] Annotate `dev_auth` with explicit response schema or rewrite
- [ ] Define `serializer_class` for `DataEntryViewSet`
- [ ] Pass `python manage.py spectacular --file api/openapi.yaml --validate` with **0 errors**
- [ ] For each warning, choose: add `@extend_schema_field`, type-hint, or accept as string
- [ ] Regenerate TS client (`npm run generate:api`) and run `npm run type-check`
- [ ] Commit fixes with label **spec-sync** (will trigger auto-regen workflow)

---

## 4  CI Expectations

| Test | CI Job | Success Gate |
|------|--------|--------------|
| OpenAPI generation | `django-tests` | Errors = 0 |
| Contract tests (Schemathesis) | `django-tests` | 0 failed checks |
| TS client build | `frontend-ci` | `npm run build` passes |

Once these issues are resolved the API contract unification will be fully stable.  
