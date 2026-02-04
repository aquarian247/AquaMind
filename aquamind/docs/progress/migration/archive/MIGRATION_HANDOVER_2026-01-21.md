# FishTalk → AquaMind Migration Handover (2026-01-21)

## Reading List (In Order)

1. **@AquaMind/aquamind/docs/progress/migration/MIGRATION_LESSONS_LEARNED.md** - Critical: What works, what doesn't, and the newly discovered cohort issue
2. **@AquaMind/aquamind/docs/progress/migration/MIGRATION_CANONICAL.md** - Runbook and commands
3. **@AquaMind/aquamind/docs/progress/migration/DATA_MAPPING_DOCUMENT.md** - Section 3.0 for batch identification context

## Current State

### What Was Done This Session
- Built SQLite environmental index (19GB, 123M rows) - works well
- Fixed `feeding_percentage` numeric overflow bug (capped at 99.99)
- Migrated 15 project batches (all scripts completed 8/8)
- **Discovered critical stitching flaw** - project tuples span multiple biological cohorts

### Infrastructure Ready
- FishTalk SQL Server running in Docker (port 1433)
- Migration preview stack: Backend http://localhost:8001, Frontend http://localhost:5002
- CSV extracts in `scripts/migration/data/extract/` (~12GB)
- SQLite environmental index ready for parallel workers

### The Core Problem (Unsolved)

**FishTalk's data model doesn't have a clean "biological batch" identifier.**

We tried:
| Approach | Result |
|----------|--------|
| UUID component stitching | Arbitrary groupings |
| PublicTransfers linking | Broken since Jan 2023 |
| SubTransfers chain linking | Over-aggregation (70M fish batches) |
| Project tuple grouping | **Current approach** - works for ~67% of tuples, but ~20% span multiple year-classes |

The project tuple `(ProjectNumber, InputYear, RunningNumber)` appears to be an **administrative grouping** (like a facility or program), not a biological cohort identifier.

**Evidence from batch 326 (project 1/24/58):**
- Contains populations starting Oct 2023 (Parr stage) AND Oct 2024 (Eye-egg stage)
- Eye-egg appearing 12 months after Parr is biologically impossible
- These are different generations of fish incorrectly grouped together

## What NOT To Do

1. **Do NOT link project tuples together** - This caused 70M fish super-batches
2. **Do NOT assume InputYear is the actual year-class** - It's administrative
3. **Do NOT create per-population workflows** - Causes workflow explosion
4. **Do NOT rely on PublicTransfers** - Broken since Jan 2023
5. **Do NOT skip reading MIGRATION_LESSONS_LEARNED.md** - Contains critical context

## Potential Approaches (Not Yet Validated)

The next agent should explore these with fresh eyes:

### 1. Time-Based Cohort Splitting
Split project tuples into sub-batches based on population start time gaps (e.g., 90-day windows). Initial analysis suggests this could work but Cohort 2 still had mixed stages.

### 2. Stage-Sequence Validation  
Filter populations that don't follow valid lifecycle progression (Egg→Fry→Parr→Smolt→Adult). Reject "impossible" combinations.

### 3. SubTransfers Chain Tracing
Start from "origin" populations (Egg/Alevin with no source transfer) and trace forward through SubTransfers. May produce cleaner biological lineages.

### 4. Year-Class Detection from Population Names
Some FishTalk population names contain year indicators (e.g., "S24", "MAR 23"). Could extract actual year-class from naming conventions.

### 5. Container-Based Cohort Detection
Fish in the same container at the same time are likely the same cohort. Could use container assignment overlap to cluster populations.

### 6. Hybrid Approach
Combine multiple signals: time clustering + stage validation + container overlap.

## Key Questions to Investigate

1. What does `InputYear` actually represent in FishTalk's data model?
2. Are there FishTalk tables we haven't explored that track biological lineage?
3. Do population names follow a consistent convention that encodes year-class?
4. Can SubTransfers trace back to a "creation" event that defines cohort origin?
5. Is there business logic documentation from Mowi/Bakkafrost about how they use project tuples?

## Useful Commands

```bash
# Clear migration DB
python scripts/migration/clear_migration_db.py

# Run project stitching report
python scripts/migration/tools/project_based_stitching_report.py --min-stages 4

# Migrate a single batch
PYTHONPATH=/path/to/AquaMind SKIP_CELERY_SIGNALS=1 \
  python scripts/migration/tools/pilot_migrate_project_batch.py \
  --project-key "1/24/27" --skip-environmental

# Check counts
python scripts/migration/tools/migration_counts_report.py
```

## Key Files

| File | Purpose |
|------|---------|
| `scripts/migration/tools/project_based_stitching_report.py` | Generates batch candidates - **needs cohort logic** |
| `scripts/migration/tools/pilot_migrate_project_batch.py` | End-to-end batch migration |
| `scripts/migration/data/extract/populations.csv` | All FishTalk populations |
| `scripts/migration/data/extract/population_stages.csv` | Stage assignments |
| `scripts/migration/data/extract/sub_transfers.csv` | Physical fish movements |
| `apps/inventory/utils.py` | Contains the fixed `calculate_feeding_percentage()` |

## Success Criteria

A correct batch should have:
- Populations that follow a valid lifecycle progression (Egg→...→Adult)
- Time span of <12 months (ideally <6 months for FW, <18 months for sea)
- 1-3 million fish (typical salmon batch size)
- Container assignments in chronological stage order

## Summary

The migration pipeline works mechanically, but the **batch identification logic needs refinement**. The FishTalk data model's project tuple conflates multiple biological cohorts. The next session should explore cohort detection approaches before running another large-scale migration.

Don't be afraid to question the assumptions - we may still be misunderstanding FishTalk's data model.
