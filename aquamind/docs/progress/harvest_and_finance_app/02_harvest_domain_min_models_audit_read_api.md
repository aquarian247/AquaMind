# Issue 2 — Harvest Domain: Minimal Models, Audit & Read API

## 1 Summary  
Introduce the **Harvest** module so AquaMind can record harvest activities without yet touching inter-company finance logic.  
Models are history-enabled; endpoints are **read-only**. Fields `dest_geography` & `dest_subsidiary` are included now so later projections can detect inter-company moves.

---

## 2 Read First (Context Pack)  
Always open these before coding or reviewing:

| Doc / Code | Purpose |
|------------|---------|
| `docs/design/finance_harvest_design_spec.md` → Harvest section | canonical domain design |
| `docs/quality_assurance/api_standards.md` | kebab-case, basename rules |
| `docs/architecture.md` | high-level component diagram |
| Infra models: `apps/infrastructure/models/{geography.py, area.py, station.py, hall.py, container.py}` | source of geography & container context |
| Batch models: `apps/batch/models/{batch.py, assignment.py, transfer.py}` | linkage for batch & assignments |

---

## 3 Scope  

### 3.1 New App `apps/harvest`  
| Model | Key Fields | Notes |
|-------|-----------|-------|
| **HarvestEvent** | `event_date`, `batch` FK, `assignment` FK, `dest_geography` FK, `dest_subsidiary` (enum), `document_ref`, timestamps | add `HistoricalRecords()` |
| **ProductGrade** | `code`, `name` | seed with agreed grade list later |
| **HarvestLot** | `event` FK, `product_grade` FK, `live_weight_kg`, `gutted_weight_kg?`, `fillet_weight_kg?`, `unit_count` | `HistoricalRecords()` |
| **HarvestWaste** | `event` FK, `category`, `weight_kg` | `HistoricalRecords()` |

### 3.2 Admin & Migrations  
* Register all models with search/filter on key fields.  
* Ensure history tables are generated via `django-simple-history`.

### 3.3 Read-Only API  
| Method | Route | Filters |
|--------|-------|---------|
| GET | `/api/v1/operational/harvest-events/` | `batch`, `date_from`, `date_to`, `document_ref` |
| GET | `/api/v1/operational/harvest-lots/` | `event`, `grade` |

Implement Serializers, ViewSets, routers in **kebab-case** with **explicit basenames**.

---

## 4 Deliverables  
- `apps/harvest/` package with models, serializers, viewsets, urls, admin.  
- Auto-generated migrations (including history tables).  
- Router include in main API router.  
- Updated OpenAPI file passes validation.  

---

## 5 Acceptance Criteria  
- [ ] `python manage.py migrate` applies & rolls back cleanly.  
- [ ] History tables exist for all harvest models.  
- [ ] Endpoints list & filter correctly; **no POST/PUT/PATCH/DELETE** allowed.  
- [ ] OpenAPI regenerates without conflicts; Schemathesis contract tests pass.  
- [ ] Routers comply with standards (kebab-case path, explicit basename).  

---

## 6 Implementation Guidance  
1. **History** – add `HistoricalRecords()` to each model; import `simple_history` in `settings.INSTALLED_APPS` if not already.  
2. **Natural Key for Future Writes** – model validation may enforce uniqueness of `(document_ref, event_date)`.  
3. **Enums** – reuse `users.models.Subsidiary` TextChoices for `dest_subsidiary`.  
4. **Filtering** – leverage DRF filters & `django-filters` for date range.  
5. **Router Check** – after registering ViewSets, open `apps/*/api/routers.py` to ensure no basename omissions remain from earlier clean-up.  
6. **Tests** – add basic list/filter tests & history table creation test.  

---

## 7 Out of Scope  
- Write/create/update endpoints (will arrive in a later phase).  
- Inter-company projection or pricing logic.  
- NAV export, BI views.  

---

## 8 Links / Traceability  
- Parent plan: `docs/progress/harvest_and_finance_app/IMPLEMENTATION_PLAN.md`  
- Decision record: `docs/adr/ADR_000X_lightweight_intercompany_finance_dims.md`  

Check off this issue in the master plan when **all acceptance criteria** are met.
