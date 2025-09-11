# Finance & Harvest Design Specification

## Executive Summary
This document designs two key capabilities for AquaMind:  
1. **Harvest Domain** – closes the operational harvest gap by modelling lots, grades, yields, waste and full traceability.  
2. **Thin, read-only Finance App** – surfaces dimensional facts derived from operational events for Power BI analytics and Microsoft NAV export, including intercompany transactions.

Guiding principles  
• Single operational source of truth → derived finance facts  
• Contract-first, kebab-case APIs with established API contract testing  
• Immutable event log, idempotent projections, full audit via simple-history

Key outcomes  
• Robust Harvest models & endpoints (lots, waste, grades, traceability) [7]  
• Dimensional star schema powering BI and ERP exports [3][4][5]  
• Intercompany pricing & journal export framework

---

## Scope & Audience
Scope: Harvest operations, Finance aggregation/exports, Intercompany pricing.  
Audience: Engineering teams, BI/Finance stakeholders, API integrators.

## Terminology & Grain
*Event* – atomic operational action (HarvestEvent, FeedEvent…).  
*Lot* – graded quantity produced by a harvest event.  
*Fact grain* – Lot × EventDate × Company × Site × ProductGrade × Batch.

---

# 1  Harvest Domain

### 1.1 Objectives
• Record harvests with lot/grade detail and link to batch/container at time of event.  
• Support partial & multi-day harvests, waste/by-products, document attachments.  
• Trigger intercompany transactions when destination subsidiary differs.

### 1.2 Entity Overview
Mermaid ERD (for reference):

erDiagram  
  COMPANY ||--o{ SITE : has  
  SITE ||--o{ CONTAINER : has  
  SPECIES ||--o{ BATCH : has  
  BATCH ||--o{ BATCH_ASSIGNMENT : at  
  BATCH_ASSIGNMENT ||--o{ HARVEST_EVENT : produces  
  HARVEST_EVENT ||--o{ HARVEST_LOT : splits  
  PRODUCT_GRADE ||--o{ HARVEST_LOT : classifies  
  HARVEST_EVENT ||--o{ HARVEST_WASTE : yields  
  HARVEST_EVENT }o--|| COMPANY : source_company  
  HARVEST_EVENT }o--|| COMPANY : dest_company  

### 1.3 Proposed Django Models (illustrative)
```python
class HarvestEvent(models.Model):
    event_id = models.BigAutoField(primary_key=True)
    event_date = models.DateTimeField(db_index=True)
    source_company = models.ForeignKey("users.Company", on_delete=models.PROTECT)
    source_site = models.ForeignKey("infrastructure.Site", on_delete=models.PROTECT)
    batch = models.ForeignKey("batch.Batch", on_delete=models.PROTECT)
    assignment = models.ForeignKey("batch.BatchContainerAssignment", on_delete=models.PROTECT)
    dest_company = models.ForeignKey("users.Company", on_delete=models.PROTECT,
                                     related_name="harvest_dest_company", null=True, blank=True)
    dest_site = models.ForeignKey("infrastructure.Site", on_delete=models.PROTECT,
                                  null=True, blank=True)
    document_ref = models.CharField(max_length=100, blank=True)  # weigh-out sheet id
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class ProductGrade(models.Model):
    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=100)

class HarvestLot(models.Model):
    lot_id = models.BigAutoField(primary_key=True)
    event = models.ForeignKey(HarvestEvent, on_delete=models.CASCADE, related_name="lots")
    product_grade = models.ForeignKey(ProductGrade, on_delete=models.PROTECT)
    live_weight_kg = models.DecimalField(max_digits=12, decimal_places=3)
    gutted_weight_kg = models.DecimalField(max_digits=12, decimal_places=3, null=True, blank=True)
    fillet_weight_kg = models.DecimalField(max_digits=12, decimal_places=3, null=True, blank=True)
    unit_count = models.IntegerField()

class HarvestWaste(models.Model):
    event = models.ForeignKey(HarvestEvent, on_delete=models.CASCADE, related_name="waste_items")
    category = models.CharField(max_length=50)  # bloodwater, trimmings…
    weight_kg = models.DecimalField(max_digits=12, decimal_places=3)
```
Audit: enable `HistoricalRecords()` on each model.

### 1.4 Business Rules
1. A batch may generate many `HarvestEvent`s; each event may have many lots.  
2. Yield validation: Σ(gutted_weight) ≤ Σ(live_weight) per event (± tolerance).  
3. Intercompany trigger: `dest_company != source_company` → create `IntercompanyTransaction`.  
4. Idempotency: natural key = (`document_ref`, `event_date`, `source_site`).

### 1.5 Harvest API (kebab-case, plural, explicit basename)
• `POST   /api/v1/operational/harvest-events/`  
• `GET    /api/v1/operational/harvest-events/{id}/`  
• `GET    /api/v1/operational/harvest-events/?batch=&date_from=&date_to=`  
• `GET    /api/v1/operational/harvest-lots/?event=&grade=`  

---

# 2  Finance App (read-only)

### 2.1 Objectives
• Provide stable dimensional facts for BI and ERP without duplicating operational data.  
• Support Power BI star schema & NAV journal export.

### 2.2 Dimensions
| Table | Key fields |
|-------|------------|
| dim_company | company_id, name, currency |
| dim_geography | geography_id, name |
| dim_site | site_id, company_id, name |
| dim_species | species_id, name |
| dim_product_grade | grade_id, code, name |
| dim_batch | batch_id, species_id, start_date |
| dim_operation | op_type_id, code (harvest, feed…) |

### 2.3 Fact Tables (initial)
`fact_harvest`, `fact_feed_consumed`, `fact_mortality`, `fact_transfer`  
Columns: quantity_kg, unit_count, value_amount (nullable), event_date plus dimension FKs.

### 2.4 Intercompany Pricing & Transactions
```python
class IntercompanyPolicy(models.Model):
    from_company = models.ForeignKey("users.Company", on_delete=models.PROTECT, related_name="ic_from")
    to_company   = models.ForeignKey("users.Company", on_delete=models.PROTECT, related_name="ic_to")
    product_grade = models.ForeignKey("harvest.ProductGrade", on_delete=models.PROTECT)
    method = models.CharField(max_length=20)  # market, cost_plus, standard
    markup_percent = models.DecimalField(max_digits=6, decimal_places=3, null=True, blank=True)

class IntercompanyTransaction(models.Model):
    tx_id = models.BigAutoField(primary_key=True)
    event = models.ForeignKey("harvest.HarvestEvent", on_delete=models.PROTECT)
    policy = models.ForeignKey(IntercompanyPolicy, on_delete=models.PROTECT)
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    currency = models.CharField(max_length=3)
    posting_date = models.DateField(db_index=True)
    state = models.CharField(max_length=20, default="pending")  # pending/exported/posted
```

### 2.5 Event Sourcing & Projections
• Capture operational events as immutable rows or via history tables.  
• Projection service builds facts idempotently, watermark on `(event_date, event_id)`.  
• Supports full rebuilds for policy change backfill.

### 2.6 Finance API
• `GET  /api/v1/finance/facts/harvests/?company=&site=&date_from=&date_to=`  
• `GET  /api/v1/finance/intercompany/transactions/?state=pending`  
• `POST /api/v1/finance/nav-exports/` – create export batch & mark tx exported  
• `GET  /api/v1/finance/nav-exports/{id}/download`

Facts endpoints are read-only; export endpoints guarded by permissions.

---

# 3  Power BI Integration

### 3.1 Schema & Incremental Refresh
• Publish star schema (dims + facts) in read replica / dedicated DB.  
• Partition facts monthly on `event_date`.  
• Provide surrogate keys + natural keys for lineage.

### 3.2 Sample Measures
```
Yield %              = DIVIDE(SUM(fact_harvest.gutted_weight_kg), SUM(fact_harvest.live_weight_kg))
Harvested kg / site  = SUM(fact_harvest.quantity_kg)
Intercompany margin  = SUM(IntercompanyTransaction.amount) - SUM(fact_harvest.value_amount)
```

### 3.3 Delivery Options
REST queries or direct DB read (preferred). Optional parquet extracts to object storage.

---

# 4  NAV Export Specification

### 4.1 Journal File Format
Header row: `export_id, created_at, company, posting_date, currency`  
Detail rows: `document_no, account_no, balancing_account_no, amount, description, dim_company, dim_site, dim_product_grade, batch_id`

CSV (UTF-8, decimal point) or JSON alternative. Dates ISO-8601.

### 4.2 Mapping Rules
| Source | NAV field |
|--------|-----------|
| IntercompanyTransaction.amount | amount |
| ProductGrade → mapping | item/dim |
| Site/Geography | dimension |

Mirrored lines posted for both companies as required.

### 4.3 Transport
Secure bucket / file-share. Filename: `NAV_IC_{company}_{YYYYMMDD}_{export_id}.csv`.

---

# 5  Integrity, Security & Audit
• FK chains ensure traceability batch → harvest → finance facts.  
• Row-level access (geography/subsidiary) leverages existing RBAC [4].  
• `django-simple-history` on new models.  
• Schemathesis contract tests, explicit basenames, kebab-case [5].

---

# 6  Non-Functional Requirements
• Scale: ≥ 1 million fact rows; partition on `event_date`; selective indexes.  
• Idempotency: natural keys + unique constraints.  
• Observability: projection & export metrics; audit retention per policy.

---

# 7  Phased Roadmap
1. **Phase 1** – Harvest domain (models, endpoints, audit), publish `fact_harvest` quantities [7].  
2. **Phase 2** – Finance dims & facts, read APIs, BI incremental refresh [3][4].  
3. **Phase 3** – Intercompany policies, transactions, NAV export.  
4. **Phase 4** – Cost valuation (feed, treatment, overhead) & margin analytics.

---

# 8  Open Decisions
1. Intercompany pricing default method & markup?  
2. Grade taxonomy standardisation & NAV mapping?  
3. NAV integration transport preference?  
4. FX source for multi-currency?  
5. Fillet weights captured in Phase 1 or later?

---

# 9  References
[1] PRD – aquamind/docs/prd.md  
[2] Data Model – aquamind/docs/database/data_model.md  
[3] Personas – aquamind/docs/personas.md  
[4] Architecture – aquamind/docs/architecture.md  
[5] API Standards – aquamind/docs/quality_assurance/api_standards.md  
[6] API Structure Analysis – aquamind/docs/progress/api_consolidation/AquaMind Django REST API Structure Analysis Report.md  
[7] Fit/Gap Analysis – aquamind/docs/fit_gap_analysis.md  
