# Issue 4 — Finance Projection: `fact_harvest` & Inter-Company Detection  

**Parent plan:** `docs/progress/harvest_and_finance_app/IMPLEMENTATION_PLAN.md`  
**Decision ref:** `docs/adr/ADR_000X_lightweight_intercompany_finance_dims.md`

---

## 1 Summary  
Build an **idempotent** projection that:

1. Materialises `fact_harvest` rows from `HarvestLot` records.  
2. Detects inter-company movements by comparing derived source/destination company keys.  
3. Creates **pending** `IntercompanyTransaction` rows when an `IntercompanyPolicy` permits pricing.

---

## 2 Read First (Context Pack)  

| Doc / Code | Why |
|------------|-----|
| `docs/design/finance_harvest_design_spec.md` (Projections & IC section) | canonical logic & grain |
| `apps/harvest/*` (created in Issue 2) | event & lot schema |
| `apps/finance/*` (created in Issue 3) | `DimCompany`, `DimSite` lookup utilities |

> Always open these files at the start of the agent session to avoid context rot.

---

## 3 Scope  

### 3.1 Models (apps/finance)

| Model | Key Fields | Notes |
|-------|------------|-------|
| **FactHarvest** | `fact_id` PK, `event` FK, `lot` FK, `event_date`, `quantity_kg`, `unit_count`, `product_grade` FK, `dim_company` FK, `dim_site` FK, `dim_batch_id` (int) | immutable; no updates |
| **IntercompanyPolicy** | `policy_id` PK, `from_company` FK, `to_company` FK, `product_grade` FK, `method` (`market` \| `cost_plus` \| `standard`), `markup_percent` _nullable_ | one row per pair/grade |
| **IntercompanyTransaction** | `tx_id` PK, `event` FK, `policy` FK, `amount` _nullable_, `currency` _nullable_, `posting_date`, `state` (`pending` \| `exported` \| `posted`) | created by projection |

All models use `HistoricalRecords()` for audit; add sensible indexes on `event_date`, `dim_company_id`, `product_grade_id`.

### 3.2 Projection Service & CLI

```
python manage.py finance_project --from=YYYY-MM-DD --to=YYYY-MM-DD
```

Responsibilities  
1. **Load water-mark** (latest processed `(event_date, event_id)`); default = `--from`.  
2. **Iterate HarvestEvents in range**, prefetch lots & related infra.  
3. **Derive keys**  
   - `source_company_key` = geography + subsidiary from assignment.container → hall/station **or** area.  
   - `dest_company_key`   = (dest_geography, dest_subsidiary) on event (nullable).  
   - Resolve to `DimCompany` & `DimSite` via helper in `finance.utils.mapping`.  
4. **Insert FactHarvest** rows: one per **lot** (grain = lot).  
5. **Inter-company**: If keys differ **and** matching `IntercompanyPolicy` exists → create `IntercompanyTransaction` in `pending` state.  
6. **Idempotency**: use natural key (`lot_id`) + unique constraint to avoid duplicates; on conflict, skip.  
7. **Logging**: summary counts (events, lots, facts, IC txns).  

---

## 4 Deliverables  

- Django models & migrations.  
- `apps/finance/management/commands/finance_project.py` CLI.  
- Unit tests: idempotent re-run, correct company mapping, IC detection.  
- Updated OpenAPI (no new endpoints yet, but models registered with admin).  

---

## 5 Acceptance Criteria  

- [ ] Re-running projection produces **no duplicate** `FactHarvest` or `IntercompanyTransaction` rows.  
- [ ] Each fact links back to original `HarvestLot` and resolves valid dimension FKs.  
- [ ] IC transaction created **only** when `source_company_key ≠ dest_company_key` **and** policy row exists.  
- [ ] Projection CLI prints counts & duration; exits 0.  
- [ ] Tests cover: first run, second run (idempotent), IC positive & negative cases.  

---

## 6 Implementation Guidance  

- **Nullable value fields** – `amount`, `currency` remain `NULL` until pricing logic arrives.  
- **Indexes** –  
  ```sql
  CREATE INDEX ix_fact_harvest_event_date         ON finance_factharvest(event_date);
  CREATE INDEX ix_fact_harvest_dim_company_grade  ON finance_factharvest(dim_company_id, product_grade_id);
  ```  
- **Mapping helper** – centralise logic in `finance.utils.mapping.get_company_site(batch_assignment_or_event)` to avoid duplication.  
- **Observability** – use Django `logging` with structured JSON (`logger.info({"event":"projection_complete", ...})`).  
- **Transactions** – wrap projection batch in `atomic()` to maintain consistency.  

---

## 7 Out of Scope  

- NAV export (Issue 6).  
- Complex pricing calculation or FX conversion.  
- API endpoints for facts/IC transactions (Issue 5).  

---

## 8 Checklist for PR  

- [ ] Models & migrations added.  
- [ ] CLI command & docs in `README.md`.  
- [ ] Tests green (`pytest` / `manage.py test`).  
- [ ] OpenAPI regenerated & committed.  
- [ ] Master plan checkbox updated & issue linked.  
- [ ] Risk & rollback section in PR description.  

_Tick this phase in the master plan when **all acceptance criteria** are met._
