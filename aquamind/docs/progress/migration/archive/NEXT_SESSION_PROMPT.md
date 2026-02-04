# Optimal Prompt for Next Session

Copy and paste this prompt to start the next session:

---

## PROMPT START

I'm working on the FishTalk → AquaMind data migration. **We made significant progress** in the previous session.

### Required Reading (in this exact order)

1. `@AquaMind/aquamind/docs/progress/migration/MIGRATION_HANDOVER_2026-01-22-v2.md` - **START HERE** - Current state and next steps
2. `@AquaMind/aquamind/docs/progress/migration/FISHTALK_SCHEMA_ANALYSIS.md` - Section 7 (Ext_Inputs_v2) and Section 8 (Naming Conventions)
3. `@AquaMind/aquamind/docs/progress/migration/DATA_MAPPING_DOCUMENT.md` - Section 3.0.0: Input-based stitching

### What Was Accomplished

1. ✅ Input-based batch stitching implemented (`input_based_stitching_report.py`)
2. ✅ Batch migration wrapper created (`pilot_migrate_input_batch.py`)
3. ✅ Supplier codes documented (BM=Benchmark, BF=Bakkafrost, SF=Stofnfiskur, AG=AquaGen)
4. ✅ Critical finding: InputName changes at FW→Sea transition
5. ⚠️ Partial migration of "Summar 2024" batch (feeding data mismatch)

### Goal for This Session

**Complete a FULL batch migration** with ALL data types:
- Creation workflow + Transfers + Mortality + Feeding + Treatments + Lice + Environmental

### Priority Tasks

1. **Fix feeding data migration** - The 890MB `feeding_actions.csv` didn't match Summar 2024 populations
2. **Complete Summar 2024** - Or wipe and migrate "Vár 2024" fresh
3. **Verify all data types present** - See success criteria in handover doc

### Technical Notes

- MacBook has **128GB RAM** - can handle large in-memory operations
- Use `--use-csv` mode with all component scripts
- For environmental data, use SQLite index (section 5.5 of MIGRATION_CANONICAL.md)
- All scripts require: `PYTHONPATH=/path/to/AquaMind SKIP_CELERY_SIGNALS=1`

### Available Batches for Migration

| Batch Key | Populations | Fish | Sea Areas |
|-----------|-------------|------|-----------|
| Summar 2024\|1\|2024 | 116 | 4.5M | A25, A47 Gøtuvík |
| Vár 2024\|1\|2024 | 98 | 5.6M | A06 Argir, A18 Hov |
| Heyst 2024\|1\|2024 | ~90 | ~3M | A15, A23, A71 |

### Database Connection

FishTalk SQL Server: Docker container `sqlserver`, database `FishTalk`

```bash
docker exec sqlserver /opt/mssql-tools18/bin/sqlcmd \
  -S localhost -U sa -P '2).nV(Ze2TZ8' -d FishTalk -C -Q "..."
```

### Do NOT

- Use project tuple `(ProjectNumber, InputYear, RunningNumber)` - it's administrative, not biological
- Use `PublicTransfers` - broken since Jan 2023
- Assume InputName stays constant from FW to sea - it changes!

## PROMPT END

---

## Quick Start Commands

```bash
# Check current migration state
cd /Users/aquarian247/Projects/AquaMind
PYTHONPATH=/Users/aquarian247/Projects/AquaMind python -c "
import os; os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'aquamind.settings')
import django; django.setup()
from apps.batch.models import Batch, MortalityEvent
from apps.inventory.models import FeedingEvent
print(f'Batches: {Batch.objects.using(\"migr_dev\").count()}')
print(f'Mortality: {MortalityEvent.objects.using(\"migr_dev\").count()}')
print(f'Feeding: {FeedingEvent.objects.using(\"migr_dev\").count()}')
"

# Wipe and start fresh
PYTHONPATH=/Users/aquarian247/Projects/AquaMind python scripts/migration/clear_migration_db.py
PYTHONPATH=/Users/aquarian247/Projects/AquaMind python scripts/migration/setup_master_data.py

# Migrate a batch
PYTHONPATH=/Users/aquarian247/Projects/AquaMind SKIP_CELERY_SIGNALS=1 \
  python scripts/migration/tools/pilot_migrate_input_batch.py \
  --batch-key "Vár 2024|1|2024"
```

---
