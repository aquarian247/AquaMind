# HANDOFF 2026-03-03 - Scope-21 feed/infra recovery (lineage-first)

## Why this handoff exists
- Scope-21 was previously marked complete for lifecycle + environmental data, but feed and related infra assets were under-materialized.
- Root cause: the previous feed path depended heavily on feed-store container assignment overlap and missed most lineage-relevant feed reception rows.

---

## What was implemented

### New migration tool
- Added `scripts/migration/tools/pilot_migrate_feed_inventory_lineage_scope.py`.
- Behavior:
  - starts from scoped batch keys,
  - expands populations through descendant edges,
  - selects consumed feed batches from feeding events,
  - expands upstream feed-batch lineage via feed-transfer edges,
  - hydrates feed infra + purchases + stock idempotently using `ExternalIdMap`.

### Store-location resolution strategy (for feed containers)
- Priority 1: explicit store-to-container assignment links from lineage package.
- Priority 2: inferred location from containers that consumed feed from that store (population lineage evidence).
- If neither path resolves a hall/area anchor, store is skipped and logged as unresolved.

---

## Execution log (controlled slices)

### Lineage source package
- `scripts/migration/output/fw_scope60_feed_infra_extract_descendants_20260303_131729`

### Scope-21 key source
- `scripts/migration/output/fw_scope4plus_dryrun_revised_20260303_115956/dryrun_summary.csv`

### Dry-run (full scope-21)
- Run folder: `scripts/migration/output/fw_scope21_feed_lineage_backfill_20260303_161910`
- Summary: `dryrun_summary.json`
- Stdout: `dryrun_stdout.txt`
- Result snapshot:
  - `batch_keys=21`
  - `expanded_pops=3828`
  - `feed_batches_with_upstream=137`
  - `reception_lines_scoped=5131`
  - projected writes: `purchases_created=4881`, `stock_created=4881`
  - unresolved stores: `7` (`line_rows=234`)

### Apply (5 auditable slices) + consolidation
- Run folder: `scripts/migration/output/fw_scope21_feed_lineage_apply_20260303_161953`
- Slice key files:
  - `slices/keys_slice1.csv`
  - `slices/keys_slice2.csv`
  - `slices/keys_slice3.csv`
  - `slices/keys_slice4.csv`
  - `slices/keys_slice5.csv`
- Per-slice summaries/stdout:
  - `keys_slice1.summary.json`, `keys_slice1.stdout.txt`
  - `keys_slice2.summary.json`, `keys_slice2.stdout.txt`
  - `keys_slice3.summary.json`, `keys_slice3.stdout.txt`
  - `keys_slice4.summary.json`, `keys_slice4.stdout.txt`
  - `keys_slice5.summary.json`, `keys_slice5.stdout.txt`
- Consolidation apply:
  - `final_consolidation_apply_summary.json`
  - `final_consolidation_apply_stdout.txt`
- Idempotence dry-run (post-consolidation):
  - `postcheck2_dryrun_summary.json`
  - `postcheck2_dryrun_stdout.txt`
- Idempotence + unresolved-classification dry-run:
  - `postcheck3_dryrun_summary.json`
  - `postcheck3_dryrun_stdout.txt`

---

## Verification evidence

### Key gate: idempotence
- Post-consolidation dry-run reports:
  - `purchases_created=0`, `purchases_updated=4881`
  - `stock_created=0`, `stock_updated=4881`
- This confirms repeatable replay behavior for resolved rows.

### Migr DB post-counts
From `run_summary.json` (`post_counts_migr_dev`):
- `inventory_feed=44`
- `inventory_feedpurchase=4882`
- `inventory_feedcontainerstock=4882`
- `infrastructure_feedcontainer=33`
- `ExternalIdMap(FishTalk/FeedType)=26`
- `ExternalIdMap(FishTalk/FeedStore)=33`
- `ExternalIdMap(FishTalk/FeedReceptionBatches)=4882`
- `ExternalIdMap(FishTalk/FeedContainerStock)=4882`

### Created totals attributable to this recovery run
From `run_summary.json` (`created_totals`):
- feed types created: `26`
- feed stores (containers) created: `32`
- purchases created: `4881`
- stock rows created: `4881`

### Recovery summary artifact
- `scripts/migration/output/fw_scope21_feed_lineage_apply_20260303_161953/run_summary.json`

---

## Residual gap (explicit)

`7` feed stores remain unresolved for location anchoring (`234` scoped reception rows skipped):
- `0EC171B0-6A1B-4C31-A67C-78372C499E51` (`BRS3 Geocrab`)
- `1DD9DEC6-D3ED-4C22-9541-2B64FF6A1707` (`KLM`)
- `1F9699B0-A9A4-4794-9F82-75D56B6D459E` (`Bingja`)
- `5C1DFEB7-05FA-4E22-9461-B33214B94F1B` (`Kishorn`)
- `62A717AF-E337-440F-80A1-1D1E8A834950` (`Plattar í L 1,5mm`)
- `64C8C5A1-AADA-4D46-8BC6-6F34E64AD895` (`Bulkur Biomar`)
- `853EEF0C-5B32-4183-9E7E-A7610754D158` (`Couldoran`)

Detailed unresolved analysis:
- `scripts/migration/output/fw_scope21_feed_lineage_apply_20260303_161953/unresolved_store_analysis.json`
- `scripts/migration/output/fw_scope21_feed_lineage_apply_20260303_161953/unresolved_store_upstream_connectivity.json`
- `scripts/migration/output/fw_scope21_feed_lineage_apply_20260303_161953/unresolved_store_transfer_resolution.json`

### Scope-boundary interpretation
- For all unresolved stores, unresolved feed batches are `upstream-only` in this scope:
  - `primary_consumed_unresolved_batches=0`.
- Script-side unresolved classification confirms:
  - `primary_line_rows=0`
  - `upstream_only_line_rows=234`
- These stores do not appear as direct consumption stores for scope-21 expanded FW populations; they appear only via upstream feed-batch lineage.
- Practical implication:
  - current FW cohort feed consumption coverage is intact,
  - unresolved stores are supply-chain lineage nodes and can be deferred under a FW-first policy (sea/mixed-network infra out-of-scope), while kept explicitly logged.

---

## Recommendation
- Scope-21 is **materially recovered** for feed/infra versus the previous state and now has deterministic lineage-scoped purchase/stock coverage.
- Scope-21 is **not yet absolute-complete** for feed/infra until the 7 unresolved stores are location-mapped (or an approved fallback policy is ratified).

---

## Exact next-step commands

1) Re-run unresolved analysis (if needed):
```bash
python3 scripts/migration/tools/pilot_migrate_feed_inventory_lineage_scope.py \
  --lineage-extract-dir scripts/migration/output/fw_scope60_feed_infra_extract_descendants_20260303_131729 \
  --scope-batch-keys-file scripts/migration/output/fw_scope4plus_dryrun_revised_20260303_115956/dryrun_summary.csv \
  --cutoff-end-date 2026-01-22 \
  --dry-run \
  --summary-json scripts/migration/output/fw_scope21_feed_lineage_apply_20260303_161953/postcheck2_dryrun_summary.json
```

2) If store-location anchors are provided/resolved, apply just that delta:
```bash
python3 scripts/migration/tools/pilot_migrate_feed_inventory_lineage_scope.py \
  --lineage-extract-dir scripts/migration/output/fw_scope60_feed_infra_extract_descendants_20260303_131729 \
  --scope-batch-keys-file scripts/migration/output/fw_scope4plus_dryrun_revised_20260303_115956/dryrun_summary.csv \
  --cutoff-end-date 2026-01-22 \
  --summary-json scripts/migration/output/fw_scope21_feed_lineage_apply_20260303_161953/final_delta_apply_summary.json
```

3) Verify post-apply idempotence:
```bash
python3 scripts/migration/tools/pilot_migrate_feed_inventory_lineage_scope.py \
  --lineage-extract-dir scripts/migration/output/fw_scope60_feed_infra_extract_descendants_20260303_131729 \
  --scope-batch-keys-file scripts/migration/output/fw_scope4plus_dryrun_revised_20260303_115956/dryrun_summary.csv \
  --cutoff-end-date 2026-01-22 \
  --dry-run \
  --summary-json scripts/migration/output/fw_scope21_feed_lineage_apply_20260303_161953/post_delta_idempotence_summary.json
```
