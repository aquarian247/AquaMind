# Issue 6 — NAV Export Skeleton: Pending Intercompany → Journal File

_Master plan reference_: `docs/progress/harvest_and_finance_app/IMPLEMENTATION_PLAN.md`  
_Prev. phases_: IC projection & Finance read APIs complete.

---

## 1 Summary  
Build the first slice of NAV integration: batch pending **IntercompanyTransaction** rows into a _journal file_ (CSV ‑ default, JSON optional) and expose download.  
Goal is **export-ready payload**, not live posting to NAV.

---

## 2 Read First (Context Pack)  

| Doc / Code | Why you must read |
|------------|------------------|
| `docs/design/finance_harvest_design_spec.md` – NAV export section | canonical format & business rules |
| `docs/quality_assurance/api_standards.md` | URL / basename / testing standards |
| `apps/finance/models.py` (`IntercompanyTransaction`, `DimCompany`, `DimSite`, `ProductGrade`) | source data |

Open these at the start of every session to avoid context rot.

---

## 3 Scope  

### 3.1 Models (`apps/finance`)

| Model | Key Fields | Notes |
|-------|------------|-------|
| **NavExportBatch** | `batch_id` PK, `created_at`, `company` FK → `DimCompany`, `posting_date`, `currency`, `state` (`draft` \| `exported`) | one batch ⇔ one company |
| **NavExportLine** | `line_id` PK, `batch` FK, `document_no`, `account_no`, `balancing_account_no`, `amount`, `description`, `dim_company_id`, `dim_site_id`, `product_grade_id`, `batch_id_int` | immutable, audit via `HistoricalRecords()` |

Unique constraint: `(batch, document_no)`.

### 3.2 Service  

`finance.services.export.create_export_batch(company_id, date_from, date_to)`  
Steps  
1. Fetch **pending** `IntercompanyTransaction` rows for `company_id`, date range.  
2. Create `NavExportBatch` in `draft` state.  
3. Map each IC txn → one `NavExportLine` (placeholder account numbers OK).  
4. Mark those transactions `exported` (state change).  
5. Persist batch; return batch id.

`finance.services.export.generate_csv(batch_id)`  
- Serialises header row + detail rows exactly as spec.  
- Uses Python `csv` module with UTF-8 encoding, `decimal_point` “.”.

### 3.3 Endpoints  

| Method | Path | Behaviour |
|--------|------|-----------|
| POST | `/api/v1/finance/nav-exports/` | body: `{company, date_from, date_to}` → creates export batch, returns metadata |
| GET | `/api/v1/finance/nav-exports/{id}/download` | streams CSV (`Content-Type: text/csv`) |

Routes registered via `router.register(..., basename='finance-nav-exports')`.

---

## 4 Deliverables  
- Models, migrations, admin registrations.  
- Export service (create batch + CSV generator).  
- ViewSet / endpoints + serializers.  
- Sample CSV format in code docstring & design spec.  
- Unit + integration tests.  
- OpenAPI diff committed; API regression suite stays green.

---

## 5 Acceptance Criteria  

- [ ] POST returns `201` with batch metadata; body validates input.  
- [ ] Batch creation sets linked IC transactions to `exported`.  
- [ ] GET download returns a well-formed CSV with header + at least one detail line.  
- [ ] Re-calling POST with identical filter set returns **400** unless `force=true` param supplied (idempotency guard).  
- [ ] OpenAPI schema validates & API regression suite green.  
- [ ] Roles: only FINANCE / ADMIN may create or download exports (403 otherwise).

---

## 6 Implementation Guidance  

1. **Account mapping placeholders**  
   Use config dict in `settings.NAV_ACCOUNT_MAP`; comment _TODO – finance to supply codes_.  
2. **Document no.**  
   Use IC transaction pk padded: `IC{tx_id}` until NAV numbering rules provided.  
3. **CSV structure**  
   ```
   export_id,created_at,company,posting_date,currency
   IC00001,2025-09-30,Farming-FO,2025-09-30,EUR
   document_no,account_no,balancing_account_no,amount,description,dim_company,dim_site,dim_product_grade,batch_id
   IC123,4000,3000,12500.00,Intercompany HOG,Farming-FO,FO Area 1,HOG,987
   ```  
4. **Streaming download** – use `StreamingHttpResponse` to avoid large memory usage.  
5. **Idempotency** – uniqueness on `(company, date_from, date_to)` inside batch meta; return existing batch if already exported _unless_ `force=true`.  
6. **Testing** – fixtures with two companies; assert state transitions & CSV contents.

---

## 7 Out of Scope  

- Direct NAV API push or SFTP upload.  
- FX conversion / multi-currency journals.  
- Reversal or reposting logic.

---

## 8 PR Checklist  

- [ ] Models & migrations added.  
- [ ] Service functions & tests.  
- [ ] ViewSet with POST/GET; routers updated.  
- [ ] OpenAPI regenerated & committed.  
- [ ] Docs: design spec NAV section updated, master plan checkbox ticked.  
- [ ] PR description includes rollback plan & CSV sample.

Tick this issue in the master implementation plan when **all acceptance criteria** pass.  
