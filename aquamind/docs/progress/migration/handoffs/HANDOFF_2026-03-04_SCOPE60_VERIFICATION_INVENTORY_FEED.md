# Scope-60 Verification + Inventory/Feed Readout (2026-03-04)

## Verification runs executed

- Full migration verification report:
  - `scripts/migration/output/fw_scope60_verification_20260304_091704/migration_verification_report.txt`
- Full counts report (all batch numbers):
  - `scripts/migration/output/fw_scope60_verification_20260304_091704/migration_counts_report_all_batches.txt`
- Focused inventory/infrastructure/feed verification dataset:
  - `scripts/migration/output/fw_scope60_verification_20260304_091704/inventory_infra_feed_verification.json`
- Feed stock edge-case rows:
  - `scripts/migration/output/fw_scope60_verification_20260304_091704/feed_stock_non_positive_rows.json`
- Feed purchase/stock cardinality + map uniqueness:
  - `scripts/migration/output/fw_scope60_verification_20260304_091704/feed_purchase_stock_cardinality.json`

## Core verification outcome

- `migration_verification_report.py` returns **1 required-table failure**:
  - `health_licecount = 0`
- Cross-check against source scope populations shows:
  - `public_lice_samples.csv` rows matching scope populations: **0**
  - Scope populations with lice samples: **0**
- Interpretation:
  - This is a script-level "required table" policy mismatch for this FW-focused scope, not a demonstrated migration loss.

## Inventory infrastructure (current DB state)

- `infrastructure_feedcontainer`: **41**
- Feed container location integrity:
  - hall-linked: **41**
  - area-linked: **0**
  - rows with neither hall nor area: **0**
- Feed container types:
  - `SILO`: **26**
  - `OTHER`: **15**
- Top stations by feed-container count:
  - `S24 Strond`: 24
  - `S16 Glyvradalur`: 6
  - `FW22 Applecross`: 3
  - `S21 Vidareidi`: 2

## Feed purchase data

- `inventory_feedpurchase`: **5755**
- Total purchased quantity: **39,278,176.06 kg**
- Purchase date range: **2009-04-07 .. 2026-01-22**
- Unique suppliers: **5**
- Top suppliers by quantity:
  - `Havsbrun`: 25,595,251 kg (2301 rows)
  - `Biomar`: 10,780,340.06 kg (3143 rows)
  - `Ewos FRESHWATER`: 2,300,585 kg (243 rows)

## Feed stock data

- `inventory_feedcontainerstock`: **5755**
- Total stock quantity field sum: **39,278,176.06 kg**
- Entry date range: **2009-04-07T10:10:00Z .. 2026-01-22T00:01:00Z**
- Distinct containers with stock: **41**
- Distinct purchases represented in stock: **5755**

### Purchase/stock integrity

- Purchase->stock cardinality histogram:
  - `1`: **5755**
- Purchases with zero stock rows: **0**
- Purchases with multiple stock rows: **0**
- Stock rows missing purchase FK: **0**
- Stock rows missing container FK: **0**

## Feed migration map integrity

- External map counts:
  - `FeedStore`: 41
  - `FeedType`: 52
  - `FeedReceptionBatches`: 5755
  - `FeedContainerStock`: 5755
  - `OrgUnit_FW`: 10
  - `Feeding`: 101570
- Duplicate `source_identifier` checks (feed scope models): **0 duplicates**

## Feed/infra scope execution status cross-check

From `scripts/migration/output/fw_scope60_feed_lineage_apply_20260303_163806/run_summary.json`:

- `stores_unresolved`: **0**
- `stores_unresolved_primary`: **0**
- `stores_unresolved_upstream_only`: **0**
- `external_map_orgunit_fw`: **10**
- Delta from baseline in feed/infra run:
  - feed containers: `+8`
  - feed purchases: `+873`
  - feed stock rows: `+873`
  - feed types: `+26`

## Noted caveats (non-blocking for migration completeness)

- Capacity comparison (`sum(stock.quantity_kg)` vs `feed_container.capacity_kg`) flags many over-capacity containers.
  - This reflects semantic mismatch for this migration representation (stock rows mirror reception quantities; not decremented operational "current level" ledger).
- Two stock rows have `quantity_kg = 0`:
  - Both map to source identifiers with sentinel-like line metadata and 2012 timestamp.
  - See `feed_stock_non_positive_rows.json`.

