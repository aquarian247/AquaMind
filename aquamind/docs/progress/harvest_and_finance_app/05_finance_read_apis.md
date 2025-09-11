# Issue 5 — Finance Read APIs: Facts & Inter-Company Transactions

_Master plan ref_: `docs/progress/harvest_and_finance_app/IMPLEMENTATION_PLAN.md`  

---

## 1 Summary  
Expose **read-only** REST endpoints for  
* `fact_harvest` (quantities & dimensional keys)  
* `IntercompanyTransaction` (pricing state machine)  

Endpoints must support robust **filtering**, **pagination**, **ordering**, and **role-based access control (RBAC)**.  
They will power BI pulls and NAV export dashboards; schema stability is critical.

---

## 2 Read First (Context Pack)  

| Doc / Code | Purpose |
|------------|---------|
| `docs/quality_assurance/api_standards.md` | URL / basename rules, testing requirements |
| `docs/design/finance_harvest_design_spec.md` – Finance API section | canonical response shapes & sample queries |
| `apps/*/api/routers.py` | verify kebab-case + explicit basenames |
| `apps/finance/models.py` | `FactHarvest`, `IntercompanyTransaction`, dimension FK names |

Always open these before coding or reviewing to avoid context rot.

---

## 3 Scope  

### 3.1 Endpoints  

| Method | Path | Query Params |
|--------|------|--------------|
| GET | `/api/v1/finance/facts/harvests/` | `company`, `site`, `batch`, `grade`, `date_from`, `date_to`, `ordering` |
| GET | `/api/v1/finance/intercompany/transactions/` | `state`, `company`, `date_from`, `date_to`, `ordering` |

### 3.2 Components  
* **Serializers** – flat, stable field sets (no nested dim objects).  
* **ViewSets** – `ReadOnlyModelViewSet`; DRF filter backend + `django-filters`.  
* **Pagination** – default page size 100; client override via `page_size`.  
* **Ordering** – default `-event_date`; allow param `?ordering=event_date`.  
* **Permissions** – `IsAuthenticated & HasFinanceRole` (FINANCE, ADMIN, etc.).

---

## 4 Deliverables  
- `apps/finance/api/serializers.py` with `FactHarvestSerializer`, `IntercompanyTxSerializer`.  
- `apps/finance/api/viewsets.py` defining two `ReadOnlyModelViewSet` classes.  
- `apps/finance/api/routers.py` registering:  
  - `router.register(r'facts/harvests', FactHarvestViewSet, basename='finance-fact-harvests')`  
  - `router.register(r'intercompany/transactions', IntercompanyTxViewSet, basename='finance-intercompany-transactions')`  
- Tests (`tests/api/test_finance_read_apis.py`) covering:  
  - Filtering combinations (AND logic).  
  - Pagination & ordering.  
  - 403 for non-FINANCE roles; 405 for write attempts.  
- Updated OpenAPI (`api/openapi.yaml`) and passing Schemathesis contract run.

---

## 5 Acceptance Criteria  

- [ ] Endpoint URLs follow kebab-case; basenames explicit; no duplicate routes.  
- [ ] Filters apply cumulatively (logical **AND**).  
- [ ] Pagination works; `page`, `page_size` query params honoured.  
- [ ] Ordering by `event_date` (asc/desc) or other allowed fields.  
- [ ] All write verbs (POST/PUT/PATCH/DELETE) return **405**.  
- [ ] Unauthorized user receives **403**; user with `UserProfile.role in {FINANCE, ADMIN}` succeeds.  
- [ ] Contract tests (Schemathesis) pass; OpenAPI schema validates.

---

## 6 Implementation Guidance  

1. **Query Optimisation**  
   ```python
   queryset = FactHarvest.objects.select_related(
       'product_grade', 'dim_company', 'dim_site'
   ).order_by('-event_date')
   ```
   Use `only()` if large text columns exist.

2. **Filter Backends**  
   - `DjangoFilterBackend` for equality filters.  
   - `DateFromToRangeFilter` for `event_date`.  
   - `OrderingFilter` for `ordering` param.

3. **Serializer Shape**  
   Return IDs plus user-friendly names:  
   ```json
   {
     "event_date": "2025-05-04",
     "quantity_kg": 1234.5,
     "company": {"id": 3, "display_name": "Farming-FO"},
     "site": {"id": 12, "site_name": "FO Area 1"},
     "product_grade": {"id": 1, "code": "HOG"},
     "batch": 987
   }
   ```

4. **Permissions**  
   Simple custom class example:  
   ```python
   class IsFinance(ReadOnly):  # pseudo
       return request.user.profile.role in {'FINANCE', 'ADMIN'}
   ```

5. **Testing Tips**  
   - Create fixture user with role `FINANCE`.  
   - Use `reverse()` + query params to assert filter intersections.  
   - Schemathesis: ensure examples in serializer `Meta.examples`.

---

## 7 Out of Scope  
- NAV export endpoints (handled in Issue 6).  
- Write / update of finance facts or IC transactions.  
- FX or pricing mutation.

---

## 8 PR Checklist  

- [ ] Serializers, ViewSets, routers added.  
- [ ] Unit & contract tests green.  
- [ ] OpenAPI regenerated & committed.  
- [ ] Docs updated (design spec + master plan checkbox).  
- [ ] PR description: what changed, how to test, risk/rollback.  

Mark this issue **complete** in the master plan when all acceptance criteria are met.
