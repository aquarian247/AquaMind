# Migration Handover Document - 2026-01-22 (Session 3)

## 🎯 Goal: Complete a Full Sea-Phase Batch Migration (with real weights)

**Objective:** Migrate a single active sea batch with ALL associated data, and ensure UI KPIs show biomass + population + avg weight without computing TGC in migration.

Required data types:
- ✅ Batch & Container Assignments
- ✅ Creation Workflow
- ✅ Transfer Workflows
- ✅ Mortality Events
- ✅ Feeding Events
- ✅ Treatments
- ✅ Lice Counts
- ✅ Growth Samples (FishTalk computed weights)
- ⏳ Environmental Data (if time permits)

---

## 📊 Session Progress Summary

### ✅ Completed This Session

1. **Growth Sample Migration Added (FishTalk-computed weights)**
   - New script: `pilot_migrate_component_growth_samples.py`
   - Sources: `Ext_WeightSamples_v2` (preferred) with fallback to `PublicWeightSamples`
   - Uses existing `ExternalIdMap` for Populations → Assignments
   - Added CSV support + integration in `pilot_migrate_input_batch.py`

2. **Weight Sample Extraction Added**
   - `bulk_extract_fishtalk.py` now exports:
     - `public_weight_samples.csv`
     - `ext_weight_samples_v2.csv`
   - Current extract run: 325,890 rows each (identical counts)

3. **Batch KPIs Restored (Biomass + Population)**
   - `pilot_migrate_component.py` now defaults `--assignment-active-window-days` to **365**
   - CSV status lookup now prefers non-zero snapshots
   - Result: Vár 2024 assignments now active enough for UI KPIs

4. **Vár 2024 Growth Samples Migrated**
   - Component key: `1B029B38-0ECF-4D62-91B9-5ACF40B9D44D`
   - 14 growth samples created in `GrowthSample`
   - Latest sample: 2025-05-20, Avg weight 4569.98 g, Sample size 79,639

---

## ✅ Current migr_dev State

```
=== Summar 2024 Migration Status ===
Batch: FT-BA711B17-S03
Component key: BA711B17-F943-4CA7-BE5F-C2450DC2FA7E

Assignments: 116
Assignments active: 1  (needs rerun with new active-window default)
Transfers: 1 workflow / 109 actions
Creation: 1 workflow / 1 action
Mortality: 581
Feeding: 351
Treatments: 45
Lice counts: 97
Growth samples: 0

=== Vár 2024 Migration Status ===
Batch: FT-1B029B38-20
Component key: 1B029B38-0ECF-4D62-91B9-5ACF40B9D44D

Assignments: 98
Assignments active: 38
Transfers: 1 workflow / 94 actions
Creation: 1 workflow / 2 actions
Mortality: 3,074
Feeding: 2,103
Treatments: 357
Lice counts: 600
Growth samples: 14
```

---

## 📋 Next Session Tasks

### Task 1: Fix Summar 2024 Active Assignments (UI KPIs)
Summar still has only 1 active assignment because it was migrated before the new default.

```bash
PYTHONPATH=/path/to/AquaMind SKIP_CELERY_SIGNALS=1 \
  python scripts/migration/tools/pilot_migrate_component.py \
  --component-key BA711B17-F943-4CA7-BE5F-C2450DC2FA7E \
  --report-dir scripts/migration/output/input_batch_migration/Summar_2024_1_2024 \
  --use-csv scripts/migration/data/extract/
```

### Task 2: Migrate Growth Samples for Summar 2024
```bash
PYTHONPATH=/path/to/AquaMind SKIP_CELERY_SIGNALS=1 \
  python scripts/migration/tools/pilot_migrate_component_growth_samples.py \
  --component-key BA711B17-F943-4CA7-BE5F-C2450DC2FA7E \
  --report-dir scripts/migration/output/input_batch_migration/Summar_2024_1_2024 \
  --use-csv scripts/migration/data/extract/
```

### Task 3: Full Batch Rerun (if needed)
Use the wrapper to include growth samples automatically.

```bash
PYTHONPATH=/path/to/AquaMind SKIP_CELERY_SIGNALS=1 \
  python scripts/migration/tools/pilot_migrate_input_batch.py \
  --batch-key "Summar 2024|1|2024" \
  --use-csv scripts/migration/data/extract/
```

---

## 🔑 Key Files Reference

### Migration Scripts (Updated/Added)
| Script | Purpose |
|--------|---------|
| `pilot_migrate_component_growth_samples.py` | **NEW** - migrates weight samples to `GrowthSample` |
| `bulk_extract_fishtalk.py` | Adds `public_weight_samples` + `ext_weight_samples_v2` extracts |
| `etl_loader.py` | New `get_weight_samples_for_populations` helper |
| `pilot_migrate_input_batch.py` | Runs growth samples + CSV support whitelist |
| `pilot_migrate_component.py` | Active-window default 365 + non-zero status snapshots |

### Output Directories
| Path | Contents |
|------|----------|
| `scripts/migration/output/input_batch_migration/` | Per-batch component CSVs |
| `scripts/migration/data/extract/` | Extracted FishTalk CSVs |

---

## ⚠️ Known Issues & Notes

1. **Summar 2024 still shows 1 active assignment**
   - Needs re-run of `pilot_migrate_component.py` with new active-window default.

2. **FCR summary warnings during growth-sample import**
   - Recompute tasks warn: "Batch FCR summary not created... (insufficient data)"
   - Not blocking; appears because feeding + biomass timeline is incomplete.

3. **Weight units heuristic**
   - Growth sample import treats AvgWeight as kg if `<= 50`, otherwise grams.
   - Adjust if FishTalk confirms different unit conventions.

---

## 🔌 Database Connection

```bash
# FishTalk SQL Server (Docker)
docker exec sqlserver /opt/mssql-tools18/bin/sqlcmd \
  -S localhost -U sa -P '2).nV(Ze2TZ8' -d FishTalk -C -Q "SELECT ..."

# AquaMind Migration DB
PYTHONPATH=/path/to/AquaMind python manage.py shell
# Then use .using('migr_dev') for all queries
```

---

## 🎯 Success Criteria for Next Session

- Summar 2024 KPIs show non-zero biomass + population in UI
- Growth samples exist for Summar 2024 (FishTalk-computed weights)
- Vár 2024 remains fully populated (already good baseline)
