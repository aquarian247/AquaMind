# HANDOFF 2026-03-03 - Scope-60 feed/infra lineage execution (FW-first)

## Why this handoff exists
- After scope-21 feed recovery, we executed the same lineage-first feed/infra contract for the full 60-key FW scope.
- Initial full dry-run exposed one primary FW blocker store (`Gjógv`) due missing container anchor mappings.
- We hardened the feed lineage migrator with an auditable OrgUnit fallback anchor path and completed full-scope execution.

---

## Code changes applied

- `scripts/migration/tools/pilot_migrate_feed_inventory_lineage_scope.py`
  - Added unresolved impact split:
    - `stores_unresolved_primary*`
    - `stores_unresolved_upstream_only*`
  - Added OrgUnit fallback anchoring for feed stores:
    - fallback path: `FeedStore.OrgUnitID -> OrgUnit_FW -> FreshwaterStation -> Hall`
    - creates missing station/hall anchors when needed (non-dry-run)
    - emits counters:
      - `orgunit_station_created`
      - `orgunit_station_updated`
      - `orgunit_hall_created`
      - `orgunit_hall_reused`
  - Added `--org-units-csv` argument (default: `scripts/migration/data/extract/org_units.csv`).

- `aquamind/docs/progress/migration/DATA_MAPPING_DOCUMENT.md`
  - bumped to `v5.8`
  - documented OrgUnit fallback anchoring + unresolved class reporting contract.

---

## Execution artifacts

### Run folder
- `scripts/migration/output/fw_scope60_feed_lineage_apply_20260303_163806`

### Pre-run baseline
- `baseline_counts_migr_dev.json`

### Dry-runs
- Initial dry-run before OrgUnit fallback hardening:
  - `full_dryrun_summary.json`
  - `full_dryrun_stdout.txt`
  - showed unresolved stores with primary impact.
- Post-hardening dry-run:
  - `full_dryrun_orgunit_fallback_summary.json`
  - `full_dryrun_orgunit_fallback_stdout.txt`
  - `stores_unresolved=0`.

### Controlled apply slices (6x10 keys)
- Slice inputs:
  - `slices/keys_slice1.csv` ... `slices/keys_slice6.csv`
- Slice outputs:
  - `keys_slice1.summary.json` ... `keys_slice6.summary.json`
  - `keys_slice1.stdout.txt` ... `keys_slice6.stdout.txt`

### Consolidation + idempotence
- `final_consolidation_apply_summary.json`
- `final_consolidation_apply_stdout.txt`
- `postcheck_dryrun_summary.json`
- `postcheck_dryrun_stdout.txt`

### Consolidated machine summary
- `run_summary.json`

---

## Gate results

### Full-scope completion gate (feed/infra domain)
- Full scope keys: `60`
- Expanded populations: `11,929`
- Scoped reception lines: `5,787`
- Final unresolved stores: `0`
- Final skipped lines: `32` (data-quality line skips; no unresolved-anchor skips)

### Idempotence gate
- Post-apply dry-run:
  - `purchases_created=0`, `purchases_updated=5755`
  - `stock_created=0`, `stock_updated=5755`
- Result: deterministic/idempotent replay confirmed.

### DB delta gate (`migr_dev`)
From `run_summary.json`:
- `inventory_feed`: `+26`
- `inventory_feedpurchase`: `+873`
- `inventory_feedcontainerstock`: `+873`
- `infrastructure_feedcontainer`: `+8`
- `ExternalIdMap FeedType`: `+26`
- `ExternalIdMap FeedStore`: `+8`
- `ExternalIdMap FeedReceptionBatches`: `+873`
- `ExternalIdMap FeedContainerStock`: `+873`
- `ExternalIdMap OrgUnit_FW`: `+10`

---

## Interpretation
- Scope-60 feed/infra lineage migration now runs to completion under FW-first boundaries without unresolved store anchors.
- The prior assumption that unresolved stores were sea-only does not hold for full-60 (primary FW store impact existed pre-fallback); fallback anchoring was required to reach closure.

---

## Recommended next workstream (after this handoff)
1. Resolve scope-60 core replay keyspace gap before non-feed residual domains:
   - probe artifact: `scope60_core_dryrun_probe.txt`
   - current split:
     - resolvable with existing `pilot_migrate_input_batch.py`: `51`
       - `scope60_core_resolvable_keys.csv`
       - `scope60_core_resolvable_dryrun.txt` (`Failures: 0`)
     - unresolved in current stitched keyspace: `9`
       - `scope60_core_unresolved_keys.csv`
       - `scope60_core_unresolved_key_resolution_candidates.json`
2. Run full scope-60 residual domains beyond feed/infra in controlled slices:
   - feeding parity catch-up
   - environmental residuals
   - health residuals
3. Run freeze-grade verification gates across all residual domains.
4. Only after full-domain gates pass, decide whether to run a clean-room replay as final reproducibility proof.
