# Hall-Stage Identifier Fix for Migration

**Date:** 2025-11-13  
**Priority:** Required for migration scripts

---

## Problem

Current test data scripts identify halls by string matching on names:
```python
hall_a = Hall.objects.filter(name__contains="-Hall-A").first()
```

**Issues:**
1. Fragile - breaks if hall naming changes
2. Inconsistent - some halls named "Hall A", others "FI-FW-01-Hall-A"
3. Not migration-safe - legacy system uses different naming
4. No semantic relationship between Hall and LifeCycleStage

---

## Solution

Add `lifecycle_stage` foreign key to Hall model:

```python
class Hall(models.Model):
    name = models.CharField(max_length=100)
    freshwater_station = models.ForeignKey(FreshwaterStation, ...)
    
    # NEW: Explicit stage relationship
    lifecycle_stage = models.ForeignKey(
        LifeCycleStage,
        null=True,  # Nullable for multi-purpose halls
        blank=True,
        on_delete=models.PROTECT,
        related_name='halls',
        help_text="Primary lifecycle stage this hall supports (Egg&Alevin, Fry, etc.)"
    )
    
    # ... existing fields ...
```

**Migration steps:**
1. Add nullable `lifecycle_stage` field
2. Populate based on container types:
   - Halls with TRAY containers → Egg&Alevin
   - Halls with containers named "Fry*" → Fry
   - Halls with containers named "Parr*" → Parr
   - etc.
3. Update test data scripts to use FK
4. Migration scripts use FK (not names)

---

## Usage After Fix

**Test data generation:**
```python
# OLD (fragile)
hall = Hall.objects.filter(name__contains="-Hall-A").first()

# NEW (proper)
hall = Hall.objects.filter(
    freshwater_station=station,
    lifecycle_stage=target_stage
).first()
```

**Migration scripts:**
```python
# Map legacy hall identifiers to stages, then lookup by FK
stage = LifeCycleStage.objects.get(name='Fry')
hall = Hall.objects.get(
    freshwater_station=station,
    lifecycle_stage=stage
)
```

---

## Migration File

**Location:** `apps/infrastructure/migrations/00XX_add_hall_lifecycle_stage.py`

**Data migration:** Use container types to infer stage for existing halls

---

**Status:** Required before production migration





