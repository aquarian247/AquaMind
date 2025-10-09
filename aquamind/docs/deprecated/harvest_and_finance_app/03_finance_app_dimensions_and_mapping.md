# Issue 3 — Finance App: Dimensions & Mapping From Operations

## 1 Summary  
Introduce **apps/finance** – a read-only domain that defines the legal / BI entities required for inter-company reporting without touching operational schemas.  
Core deliverable: `DimCompany` and `DimSite` tables plus an idempotent sync command that seeds / refreshes rows from existing infrastructure data and `users.models.Subsidiary` enums.

---

## 2 Read First (Context Pack)  

| Doc / Code | Why read? |
|------------|-----------|
| `docs/design/finance_harvest_design_spec.md` – Finance dims section | canonical target model |
| `docs/architecture.md` | component & data-flow overview |
| `docs/quality_assurance/api_standards.md` | naming & router rules (use later) |
| `apps/infrastructure/models/geography.py` | geography FK source |
| `apps/infrastructure/models/area.py` / `station.py` | site sources & geography linkage |
| `apps/users/models.py` (`Subsidiary` TextChoices) | subsidiary enumeration |

---

## 3 Scope  

### 3.1 App Skeleton  
```
apps/
└─ finance/
   ├─ __init__.py
   ├─ models.py
   ├─ admin.py
   ├─ management/
   │   └─ commands/
   │       └─ finance_sync_dimensions.py
   └─ migrations/0001_initial.py  (auto-generated)
```

### 3.2 Models  
| Model | Key Fields | Notes |
|-------|------------|-------|
| **DimCompany** | `company_id` (PK), `geography` FK, `subsidiary` (enum), `display_name`, `currency` _nullable_, `nav_company_code` _nullable_ | unique `(geography, subsidiary)` constraint |
| **DimSite** | `site_id` (PK), `source_model` (`"station"` \| `"area"`), `source_pk` (int), `company` FK, `site_name` | unique `(source_model, source_pk)` |

### 3.3 Management Command  
`python manage.py finance_sync_dimensions`  
Tasks:  
1. Collect all `Geography` rows.  
2. For each geography × subsidiary actually present in infra or user profiles, _upsert_ a `DimCompany` row.  
3. Scan `FreshwaterStation` + `Area`; create / update matching `DimSite`, linking to correct `DimCompany`.  
4. Surplus `DimSite` rows not found on refresh remain untouched (soft-delete optional, not required).

### 3.4 Admin  
Register `DimCompany` and `DimSite` with list / search filters on geography, subsidiary, site_name.

---

## 4 Deliverables  
- Finance app package with models & migrations.  
- Admin registrations.  
- Fully-documented management command.  
- Unit tests for sync idempotency & mapping correctness.

---

## 5 Acceptance Criteria  
- [ ] `manage.py migrate` creates both tables; rollback clean.  
- [ ] Running `finance_sync_dimensions` twice produces identical row counts (upsert semantics).  
- [ ] Every `DimSite` row resolves to a valid `DimCompany`.  
- [ ] At least one `DimCompany` row per geography present in DB.  
- [ ] Nullable fields (`currency`, `nav_company_code`) accepted; no non-null constraint failures.  
- [ ] Tests cover: first-run insert, second-run no-duplication, mapping integrity.

---

## 6 Implementation Guidance  
1. **Display Name**  
   ```python
   display_name = f"{subsidiary}-{geography.name}"
   ```  
2. **Subsidiary Derivation**  
   - `FreshwaterStation` ⇒ `Subsidiary.FRESHWATER`  
   - `Area`           ⇒ `Subsidiary.FARMING`  
   - Extend later if Broodstock/Logistics infra models emerge.  
3. **Upsert Pattern** – use `update_or_create()` inside atomic transaction.  
4. **No Operational FKs** – do **not** add FKs from infra or batch models back to Finance dims. All joins occur in read-only queries/projections.  
5. **Testing** – create fixtures with two geographies & a few stations/areas; assert row counts & relations.  
6. **Future Fields** – leave TODO comment to add `legal_entity_code` or `vat_no` if required.

---

## 7 Out of Scope  
- Fact tables (`fact_harvest`, etc.)  
- Inter-company pricing policies.  
- API endpoints (handled in later issues).  
- NAV export logic.

---

## 8 Links / Traceability  
- Master plan: `docs/progress/harvest_and_finance_app/IMPLEMENTATION_PLAN.md`  
- Decision record: `docs/adr/ADR_000X_lightweight_intercompany_finance_dims.md`  

Tick this phase in the master plan once **all acceptance criteria** are satisfied.
