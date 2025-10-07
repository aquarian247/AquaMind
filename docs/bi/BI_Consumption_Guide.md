# BI Consumption Guide

This guide explains how analytics teams can consume finance and harvest projections safely using the database views delivered in Issue 7. It covers the schema contract, refresh strategies, and supported delivery options so that Power BI (or any SQL-capable BI tool) can stay in sync with AquaMind’s operational data without brittle ad-hoc queries.

---

## 1. Data Assets

We expose two read-only SQL views optimised for reporting. They live in the default `public` schema and are versioned through Django migrations, meaning deployments update them automatically.

### 1.1 `vw_fact_harvest`

| Column | Type | Description |
| --- | --- | --- |
| `fact_id` | `BIGINT` | Stable surrogate key for each projected harvest lot. |
| `event_date` | `TIMESTAMP WITH TIME ZONE` | Exact timestamp of the harvest event; use as the incremental watermark. |
| `quantity_kg` | `NUMERIC(18,3)` | Live-weight quantity (kg) with three-decimal precision for finance reconciliation. |
| `unit_count` | `INTEGER` | Number of units harvested in the lot. |
| `product_grade_code` | `VARCHAR` | Canonical harvest grade (e.g. `HOG`). |
| `company` | `VARCHAR` | Friendly display name of the owning company. |
| `site_name` | `VARCHAR` | Operational site supplying the harvest. |
| `batch_id` | `INTEGER` | Reference to the operational batch for drill-through scenarios. |

Example usage:

```sql
SELECT event_date::date AS harvest_day,
       product_grade_code,
       SUM(quantity_kg) AS total_kg
FROM vw_fact_harvest
GROUP BY harvest_day, product_grade_code
ORDER BY harvest_day DESC;
```

### 1.2 `vw_intercompany_transactions`

| Column | Type | Description |
| --- | --- | --- |
| `tx_id` | `BIGINT` | Surrogate key for the intercompany transaction. |
| `posting_date` | `DATE` | Finance posting date used for accounting partitions. |
| `state` | `VARCHAR` | Transaction lifecycle (`pending`, `exported`, `posted`). |
| `from_company` | `VARCHAR` | Display name of the company issuing the charge. |
| `to_company` | `VARCHAR` | Display name of the receiving company. |
| `product_grade_code` | `VARCHAR` | Harvest grade associated with the transaction. |
| `amount` | `NUMERIC(18,2)` | Monetary amount in the transaction currency. |
| `currency` | `VARCHAR(3)` | ISO currency code (e.g. `DKK`). |

Example usage:

```sql
SELECT posting_date,
       from_company,
       to_company,
       SUM(amount) AS amount_dkk
FROM vw_intercompany_transactions
WHERE currency = 'DKK'
GROUP BY posting_date, from_company, to_company
ORDER BY posting_date DESC;
```

---

## 2. Schema Guarantees

* **Stable naming:** Columns are snake_case with human-readable dimensions so BI semantic models remain tidy. Surrogate identifiers (`fact_id`, `tx_id`) stay immutable once published.
* **Deterministic types:** Numeric values are cast explicitly (`NUMERIC(18,3)` / `NUMERIC(18,2)`) to avoid accidental precision drift between environments.
* **Performance hints:** Supporting indexes on `event_date`, `(dim_company_id, product_grade_id)`, and `posting_date` keep filter-heavy queries under 200 ms on seeded datasets.
* **No write access:** Consumers must never `INSERT`/`UPDATE` these views; DB permissions should be read-only.

---

## 3. Incremental Refresh Playbook (Power BI focus)

The recommended incremental strategy partitions by `event_date` (harvest facts) and `posting_date` (transactions), targeting a rolling 13-month window.

### 3.1 Configure Range Parameters

1. Create two Power BI parameters: `RangeStart` and `RangeEnd` of type `DateTime`. Set defaults such as:
   * `RangeStart` → `Date.AddMonths(DateTime.LocalNow(), -13)`
   * `RangeEnd` → `DateTime.LocalNow()`
2. Reference these parameters in the Power Query filters:

```m
let
    Source = PostgreSQL.Database(Server, Database),
    FactHarvest = Source{[Schema="public",Item="vw_fact_harvest"]}[Data],
    Filtered = Table.SelectRows(
        FactHarvest,
        each [event_date] >= RangeStart and [event_date] < RangeEnd
    )
in
    Filtered
```

![Power BI parameter configuration placeholder](../images/power_bi_parameter_placeholder.png)

### 3.2 Enable Incremental Refresh

1. In the model view, select the table (e.g. `FactHarvest`).
2. Choose **Incremental refresh** → enable.
3. Partition rule: *Store rows in the last* **13** *Months*, *Refresh rows in the last* **1** *Month*.
4. Set **Detect data changes** to `fact_id` for the harvest table and `tx_id` for intercompany transactions.

### 3.3 Publish and Validate

* After publishing, trigger a manual refresh once to materialise partitions.
* Use the Power BI service Refresh History to ensure partition pruning works—initial load may take longer; subsequent loads should complete quickly.
* If corporate policy requires on-prem gateways, set credentials using a db user with read-only rights to the `public` schema.

---

## 4. Delivery Options

| Option | When to Use | Notes |
| --- | --- | --- |
| **Direct PostgreSQL read** | Primary choice for internal BI teams needing freshest data | Configure read-only credentials; leverage built-in views and indexes. |
| **REST API extracts** | Lightweight extracts under 10k rows | Use finance read endpoints; expect ISO8601 timestamps and decimal strings. |
| **Nightly Parquet export (planned)** | Downstream data lake ingestion | Future enhancement—feeds from the same views to Parquet on object storage. |

---

## 5. Operational Checklist

1. **Smoke test SQL**: `SELECT COUNT(*) FROM vw_fact_harvest WHERE event_date >= CURRENT_DATE - INTERVAL '30 days';`
2. **Verify indexes**: `
SELECT indexname FROM pg_indexes
WHERE schemaname = 'public'
  AND indexname IN (
      'ix_fact_harvest_event_date',
      'ix_fact_harvest_company_grade',
      'ix_intercompany_posting_date'
  );
`
3. **Monitor growth**: Track total rows vs. partition window; adjust the 13-month horizon if finance requires longer lookbacks.
4. **Document refresh failures**: Capture the Power BI refresh ID, timestamp, and error message, then validate source rows exist in the view.

With these practices, analytics stakeholders gain a predictable contract for finance and harvest data, enabling self-serve dashboards without compromising operational workloads.
