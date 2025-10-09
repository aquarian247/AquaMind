# Issue 7 — BI Delivery: Views, Indexing & Incremental Refresh Guide  

_Parent plan_: `docs/progress/harvest_and_finance_app/IMPLEMENTATION_PLAN.md`  

---

## 1 Summary  
Surface Finance data to Power BI (or other analytics tools) through **stable database views** and supporting indexes, then document an incremental-refresh approach and schema guarantees.

---

## 2 Read First (Context Pack)  

| Doc / Code | Purpose |
|------------|---------|
| `docs/architecture.md` | overall layers & data-flow |
| `docs/design/finance_harvest_design_spec.md` → Power BI section | canonical star schema & refresh goals |
| `apps/finance/models.py` | dims, `FactHarvest`, `IntercompanyTransaction` fields |

Always open these at session start to prevent context rot.

---

## 3 Scope  

### 3.1 SQL Views  
Create a Django **RunSQL** migration (or raw SQL file wired into migrations) that defines:

1. **`vw_fact_harvest`**  
   ```sql
   CREATE OR REPLACE VIEW vw_fact_harvest AS
   SELECT
       fh.fact_id,
       fh.event_date,
       fh.quantity_kg,
       fh.unit_count,
       pg.code          AS product_grade_code,
       dc.display_name  AS company,
       ds.site_name,
       fh.dim_batch_id  AS batch_id
   FROM finance_factharvest            fh
   JOIN harvest_productgrade           pg ON pg.id  = fh.product_grade_id
   JOIN finance_dimcompany             dc ON dc.id  = fh.dim_company_id
   JOIN finance_dimsite                ds ON ds.id  = fh.dim_site_id;
   ```

2. **`vw_intercompany_transactions`**  
   ```sql
   CREATE OR REPLACE VIEW vw_intercompany_transactions AS
   SELECT
       tx.tx_id,
       tx.posting_date,
       tx.state,
       dc_from.display_name AS from_company,
       dc_to.display_name   AS to_company,
       pg.code              AS product_grade_code,
       tx.amount,
       tx.currency
   FROM finance_intercompanytransaction        tx
   JOIN finance_intercompanypolicy             pol ON pol.id = tx.policy_id
   JOIN finance_dimcompany         dc_from ON dc_from.id = pol.from_company_id
   JOIN finance_dimcompany         dc_to   ON dc_to.id   = pol.to_company_id
   JOIN harvest_productgrade       pg      ON pg.id      = pol.product_grade_id;
   ```

### 3.2 Indexes  
Add in the same migration (or separate) indexes on fact tables for common filters:  
```sql
CREATE INDEX IF NOT EXISTS ix_factharvest_event_date
        ON finance_factharvest(event_date);

CREATE INDEX IF NOT EXISTS ix_factharvest_company_grade
        ON finance_factharvest(dim_company_id, product_grade_id);

CREATE INDEX IF NOT EXISTS ix_intercompany_posting_date
        ON finance_intercompanytransaction(posting_date);
```

### 3.3 BI Consumption Guide  
New doc: `docs/bi/BI_Consumption_Guide.md`  
Must include:  
- Stable column list & data types for each view  
- Naming conventions (snake_case vs camel etc.)  
- Recommended incremental refresh:  
  - Partition by `event_date` (monthly)  
  - Minimum <code>WHERE event_date &gt; EOMONTH(TODAY(),-13)</code> for incremental loads  
  - Watermark field = `event_date`; detect new rows by `fact_id`  
- Delivery options:  
  1. Direct Postgres read (preferred)  
  2. REST pull via Finance read APIs (small extracts)  
  3. Nightly parquet export (optional)

---

## 4 Deliverables  
- Django migration file creating both views & indexes.  
- `docs/bi/BI_Consumption_Guide.md` with ≥ 1 example Power BI parameter screenshot (image placeholder ok).  

---

## 5 Acceptance Criteria  
- [ ] Running migration produces `vw_fact_harvest` & `vw_intercompany_transactions` visible in `psql \dv`.  
- [ ] `SELECT * FROM vw_fact_harvest LIMIT 5;` returns expected columns & types.  
- [ ] Guide documents incremental refresh rules and delivery options.  
- [ ] Index existence verified via `\di`.  
- [ ] Query on seeded data (≤ 10 k rows) completes in < 200 ms (local).  

---

## 6 Implementation Guidance  
1. **Explicit casts** – cast numeric → `DECIMAL(18,3)` where necessary to stabilise types.  
2. **Keep views narrow** – only analytics-ready columns; avoid leaking surrogate FK IDs except `batch_id`.  
3. **Materialised views?** – consider only if analytics query volume proves heavy; gate behind Postgres ≥ 14 & cron `REFRESH MATERIALIZED VIEW CONCURRENTLY`.  
4. **Migration pattern** – use `RunSQL(sql, reverse_sql)` to ensure rollback drops views/indexes.  
5. **Testing** – in tests, call `connection.cursor().execute('EXPLAIN SELECT …')` to assert index usage.  

---

## 7 Out of Scope  
- Building actual Power BI reports / .pbix files.  
- Data warehouse ETL outside Postgres.  
- Performance testing at production scale (handled after volume benchmark).

---

## 8 PR Checklist  
- [ ] Migration added & applied locally.  
- [ ] Guide committed at `docs/bi/BI_Consumption_Guide.md`.  
- [ ] Master plan checkbox ticked & issue linked.  
- [ ] PR description: purpose, how to validate views, risk/rollback plan.  
