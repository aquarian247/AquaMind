# Migration Handover Document - 2026-01-26

## 🎯 Goal: Full lifecycle migration for Vár 2024 (FW + Sea) with correct counts

**Objective:** Migrate one full lifecycle batch (Vár 2024 sea batch stitched to FW origins), validate KPIs and lifecycle stage totals, and fix mortality migration performance.

---

## ✅ Completed This Session

1. **Full lifecycle stitching pipeline added**
   - New script: `scripts/migration/tools/input_full_lifecycle_stitching.py`
   - Uses: `ext_inputs.csv` + `ext_populations.csv` + `population_links.csv` + `grouped_organisation.csv`
   - Strategy:
     - Sea batch key: `Vár 2024|1|2024`
     - Source yearclass derived from population names = **2022**
     - Selected FW batches (current):  
       - `AX_LHS 22 Q4|1|2022` (Smolt)
       - `Mai 2022|1|2022` (Smolt)
       - `Stofnfiskur Aug 22|3|2022` (Egg&Alevin/Fry)
       - `Stofnfiskur aug22|5|2022` (Egg&Alevin/Fry)
   - Stage coverage in current full‑lifecycle members (166 pops):  
     - Adult 94, Smolt 21, Fry 46, Egg&Alevin 47

2. **Creation workflow fixes**
   - `pilot_migrate_component.py` now uses:
     - `Ext_Inputs_v2.InputCount` for `egg_count_*`
     - earliest lifecycle stage for creation selection
     - `--creation-window-days` (default 60) to widen initial selection for pre‑adult stages
   - Current creation totals for `FT-FE01C284-H078`:
     - `total_eggs_received`: 6,576,209
     - `creation_actions`: 105
     - `sum(egg_count_actual)`: 8,494,585 (high; needs investigation)

3. **Infrastructure grouping improved**
   - `bulk_extract_fishtalk.py` now extracts:
     - `ext_populations.csv`
     - `population_links.csv`
     - `grouped_organisation.csv`
   - `etl_loader.py` supports grouped organisation + input counts.
   - Hall parsing fixed for `Høll` variants (e.g., `Høll B` → `Hall B`).

4. **Environmental and mortality reruns**
   - Environmental rerun (sqlite):  
     `created=784,168`, `updated=327,058`, `env rows for batch=1,111,226`
   - Mortality rerun completed (CSV):  
     `created=7,502`, `updated=3,739`, `rows=12,339`  
     (Total batch mortality now 16,172)

---

## ✅ Current migr_dev State (as of 2026‑01‑26)

```
=== Vár 2024 Full Lifecycle ===
Batch: FT-FE01C284-H078
Component key: FE01C284-7315-44CC-B61C-B42F6BAFC426

Assignments: 229
Transfers: 3 workflows / 175 actions
Creation: 1 workflow / 105 actions
Mortality: 16,172
Feeding: 12,461
Treatments: 2,013
Lice counts: 3,596
Journal: 1,353
Growth samples: 786
Environmental: 1,111,226
```

**Note:** assignments are accumulating across reruns (old populations remain).  
This likely inflates lifecycle totals and contributes to “Adult > Smolt.”

---

## ⚠️ Open Issues / Investigation Targets

1. **Mortality migration performance**
   - `pilot_migrate_component_mortality.py` still takes ~45–55 minutes and times out in wrapper.
   - Likely bottleneck: `ETLDataLoader.get_mortality_actions_for_populations()` scans the full CSV list.
   - Fix options:
     - Add pandas filter (similar to status_values).
     - Add sqlite index for `mortality_actions.csv` (like environmental).
     - Pre‑filter mortality extract by population IDs for batch‑specific runs.

2. **Egg counts unusually high (~8.5M)**
   - Current creation actions sum to 8.49M; typical input should be ~3–6M.
   - Hypotheses:
     - Multiple FW sub‑batches combined (likely).
     - `InputCount` might already represent post‑mortality fry counts or duplicated inputs.
     - Old assignments not cleaned out after reruns.
   - Need to inspect:
     - `CreationAction` rows for workflow 241
     - `Ext_Inputs_v2` for populations used in creation window
     - Duplicates / overlaps across selected FW batches

3. **Lifecycle totals inconsistent (Adult > Smolt)**
   - Current assignment totals for `FT-FE01C284-H078`:
     - Adult: 5,303,414
     - Smolt: 1,630,544
     - Fry: 4,815,858
     - Egg&Alevin: 3,560,000
   - Hypotheses:
     - Reruns leave old assignments (not removed).
     - Population snapshots are taken per container and can overlap across stages.
     - FishTalk model changes in 2023 might alter stage encoding or population creation.

4. **FishTalk data model changes (2023)**
   - Need deeper schema re‑inspection; 2023 changes likely break FW→Sea linking assumptions.
   - Review `MIGRATION_LESSONS_LEARNED.md` and schema snapshots for post‑2023 diffs.

---

## 🔧 Commands & Artifacts

### Rebuild full lifecycle members
```bash
python scripts/migration/tools/input_full_lifecycle_stitching.py \
  --batch-key "Vár 2024|1|2024" \
  --csv-dir scripts/migration/data/extract/ \
  --output-dir scripts/migration/output/input_stitching
```

### Full rerun (skip environmental)
```bash
PYTHONPATH=/Users/aquarian247/Projects/AquaMind SKIP_CELERY_SIGNALS=1 \
  python scripts/migration/tools/pilot_migrate_input_batch.py \
  --batch-key "Vár 2024|1|2024" \
  --use-csv scripts/migration/data/extract/ \
  --full-lifecycle --full-lifecycle-rebuild --skip-environmental
```

### Mortality rerun (manual)
```bash
PYTHONPATH=/Users/aquarian247/Projects/AquaMind SKIP_CELERY_SIGNALS=1 \
  python scripts/migration/tools/pilot_migrate_component_mortality.py \
  --component-key FE01C284-7315-44CC-B61C-B42F6BAFC426 \
  --report-dir scripts/migration/output/input_batch_migration/Vár_2024_1_2024 \
  --use-csv scripts/migration/data/extract/
```

### Environmental rerun (sqlite)
```bash
PYTHONPATH=/Users/aquarian247/Projects/AquaMind SKIP_CELERY_SIGNALS=1 \
  python scripts/migration/tools/pilot_migrate_component_environmental.py \
  --component-key FE01C284-7315-44CC-B61C-B42F6BAFC426 \
  --report-dir scripts/migration/output/input_batch_migration/Vár_2024_1_2024 \
  --use-sqlite scripts/migration/data/extract/environmental_readings.sqlite
```

### Quick validation
```bash
PYTHONPATH=/Users/aquarian247/Projects/AquaMind \
  python scripts/migration/tools/migration_counts_report.py
```

---

## 📌 Key Files Modified/Added

| File | Purpose |
|------|---------|
| `scripts/migration/tools/input_full_lifecycle_stitching.py` | Full‑lifecycle stitching logic |
| `scripts/migration/tools/bulk_extract_fishtalk.py` | Added `ext_populations`, `population_links`, `grouped_organisation` |
| `scripts/migration/tools/etl_loader.py` | Grouped org + input counts helpers |
| `scripts/migration/tools/pilot_migrate_component.py` | Creation workflow fixes + stage selection |
| `scripts/migration/tools/pilot_migrate_input_batch.py` | Full‑lifecycle migration options |

---

## Next Session Focus

1. **Optimize mortality migration** (CSV filter or sqlite index)
2. **Investigate egg count inflation** in creation actions
3. **Audit assignment totals per stage** and rerun with cleanup strategy
4. **Deep dive into FishTalk post‑2023 model changes**

---

## Notes
- Source data snapshot is Oct 2025; long gaps in feed/mortality are expected.
- Growth chart anomalies at the end likely due to missing data and UI range to current date.
- **Suspicion:** reruns may be accumulating assignments when population membership changes between reruns. If counts keep growing, confirm by comparing assignment IDs before/after reruns; consider cleanup or fresh DB reset for clean counts.
