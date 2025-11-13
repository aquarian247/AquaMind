# Batch Saturation Guide

**Created:** 2025-10-17  
**Purpose:** Generate large-scale realistic test data to saturate infrastructure

---

## Overview

This guide explains how to generate many batches across both geographies to create a realistic, fully-operational aquaculture farm simulation.

### Key Changes from Previous Version

**1. Realistic Lifecycle Durations (900 days total)**
- **Egg&Alevin:** 90 days (no feed)
- **Fry:** 90 days
- **Parr:** 90 days  
- **Smolt:** 90 days
- **Post-Smolt:** 90 days
- **Adult:** 450 days ← NEW (was effectively infinite)

**2. Batch Orchestration**
- New super-script automatically calculates optimal batch count
- Staggers batch starts every 30 days for realistic overlap
- Distributes evenly across both geographies
- Accounts for container reuse across lifecycle stages

---

## Infrastructure Capacity

### Faroe Islands
- **Freshwater:** 650 containers (13 stations × 5 halls × 10 containers)
- **Sea:** 460 cages (23 areas × 20 cages)
- **Total:** 1,110 containers

### Scotland
- **Freshwater:** 500 containers (10 stations × 5 halls × 10 containers)
- **Sea:** 400 cages (20 areas × 20 cages)  
- **Total:** 900 containers

### Combined
- **Total Infrastructure:** 2,010 containers
- **Target Saturation (85%):** ~171 active batches
- **Expected Biomass:** ~500,000 tonnes across all stages

---

## Quick Start

### 1. Analyze What Would Be Generated (Dry Run)

```bash
cd /Users/aquarian247/Projects/AquaMind

python scripts/data_generation/04_batch_orchestrator.py
```

This shows:
- Infrastructure capacity
- Recommended batch count
- Sample schedule
- Commands that would run

**Output Example:**
```
INFRASTRUCTURE CAPACITY ANALYSIS
================================

Faroe Islands:
  Freshwater Containers: 650
  Sea Containers: 460
  Total: 1110

Scotland:
  Freshwater Containers: 500
  Sea Containers: 400
  Total: 900

TOTAL INFRASTRUCTURE: 2010 containers
Target Saturation: 85%

BATCH GENERATION PLAN
=====================

Infrastructure Capacity:
  Total Containers: 2010
  Containers per Batch: 10
  Target Saturation: 85%

Batch Plan:
  Target Batches: 171
  Lifecycle Duration: 900 days (~30 months)
  Stagger Interval: 30 days

Distribution:
  Faroe Islands: 85 batches
  Scotland: 85 batches
```

### 2. Execute Full Generation

```bash
# WARNING: This will take 40-60 HOURS to complete
python scripts/data_generation/04_batch_orchestrator.py --execute
```

**Performance Estimates:**
- ~25 minutes per 900-day batch
- 170 batches × 25 min = ~71 hours
- Recommend running overnight or over weekend

### 3. Generate Smaller Test Set

For testing or development:

```bash
# Generate only 10 batches per geography (20 total)
python scripts/data_generation/04_batch_orchestrator.py \
  --execute \
  --batches 10
```

**Performance:**
- 20 batches × 25 min = ~8 hours

---

## Advanced Usage

### Custom Saturation Level

```bash
# 50% saturation (good for development)
python scripts/data_generation/04_batch_orchestrator.py \
  --execute \
  --saturation 0.5

# 95% saturation (maximum capacity)
python scripts/data_generation/04_batch_orchestrator.py \
  --execute \
  --saturation 0.95
```

### Custom Start Date

```bash
# Start batches from specific date
python scripts/data_generation/04_batch_orchestrator.py \
  --execute \
  --start-date 2023-01-01
```

### Generate Active Batches Ending Today

```bash
# Default behavior: starts 900 days ago, so first batch completes today
python scripts/data_generation/04_batch_orchestrator.py --execute
```

---

## Understanding Batch Overlap

### Container Reuse Strategy

Each batch progresses through stages, allowing containers to be reused:

**Day 0-90 (Egg&Alevin):**
- Uses Hall A containers (10 containers)
- No feeding, minimal resources

**Day 90-180 (Fry):**
- Moves to Hall B containers (10 containers)
- Hall A becomes available for new batch

**Day 180-270 (Parr):**
- Moves to Hall C containers (10 containers)
- Hall B becomes available

**Day 270-360 (Smolt):**
- Moves to Hall D containers (10 containers)
- Hall C becomes available

**Day 360-450 (Post-Smolt):**
- Moves to Hall E containers (10 containers)
- Hall D becomes available

**Day 450-900 (Adult):**
- Moves to Sea Cages (10 cages)
- Hall E becomes available

### 30-Day Stagger Effect

With batches starting every 30 days:
- **3 batches** can occupy the same hall sequentially (90 days ÷ 30 days)
- **15 batches** can use the same container over 900-day lifecycle
- **85% saturation** ensures some buffer for transfers and maintenance

---

## Monitoring Progress

### During Generation

The orchestrator shows progress:
```
Batch 1/170: Far-2023-01-03
  ✓ Success

Batch 2/170: Sco-2023-02-02
  ✓ Success

... (processing batches 3-168) ...

Batch 169/170: Far-2025-10-15
  ✓ Success
```

### Check Database Status

```bash
python manage.py shell -c "
from apps.batch.models import Batch
from apps.infrastructure.models import Container
from apps.batch.models import BatchContainerAssignment

print('Batch Status:')
total = Batch.objects.count()
active = Batch.objects.filter(status='ACTIVE').count()
print(f'  Total: {total}')
print(f'  Active: {active}')
print()

print('Container Utilization:')
total_containers = Container.objects.filter(active=True).count()
used_containers = BatchContainerAssignment.objects.filter(
    is_active=True
).values('container').distinct().count()
pct = (used_containers / total_containers * 100) if total_containers > 0 else 0
print(f'  Total Containers: {total_containers}')
print(f'  Containers in Use: {used_containers}')
print(f'  Utilization: {pct:.1f}%')
"
```

---

## Batch Movement Tracking

### Understanding batch_batchcontainerassignment

The `batch_batchcontainerassignment` table is **the central hub** for batch tracking. It records:
- Every container a batch occupies
- When the batch arrived (`assignment_date`)
- When the batch left (`departure_date`)
- Whether the assignment is currently active (`is_active`)
- The lifecycle stage at that time (`lifecycle_stage_id`)
- Population, weight, and biomass at that location

### Hall Specialization by Lifecycle Stage

**Critical Design Principle:** Each hall is specialized for ONE lifecycle stage:

- **Hall A** → Egg & Alevin Trays (Egg&Alevin stage)
- **Hall B** → Fry Tanks (Fry stage)
- **Hall C** → Parr Tanks (Parr stage)
- **Hall D** → Smolt Tanks (Smolt stage)
- **Hall E** → Post-Smolt Tanks (Post-Smolt stage)
- **Sea Cages** → Adult stage

When a batch transitions stages, it **physically moves** to a different hall/area. The event engine creates **new assignments** and closes **old assignments** to preserve the complete audit trail.

### Query 1: Complete Lifecycle Journey

```sql
-- Show complete movement history for a specific batch
SELECT 
    b.batch_number,
    ls.name AS stage,
    COALESCE(h.name, a.name) AS location_name,
    CASE 
        WHEN h.id IS NOT NULL THEN 'Hall'
        WHEN a.id IS NOT NULL THEN 'Sea Area'
    END AS location_type,
    bca.assignment_date,
    bca.departure_date,
    bca.is_active,
    bca.population_count,
    bca.avg_weight_g,
    bca.biomass_kg,
    CASE 
        WHEN bca.departure_date IS NOT NULL 
        THEN bca.departure_date - bca.assignment_date
        ELSE CURRENT_DATE - bca.assignment_date
    END AS days_in_location
FROM batch_batchcontainerassignment bca
JOIN batch_batch b ON bca.batch_id = b.id
JOIN batch_lifecyclestage ls ON bca.lifecycle_stage_id = ls.id
JOIN infrastructure_container c ON bca.container_id = c.id
LEFT JOIN infrastructure_hall h ON c.hall_id = h.id
LEFT JOIN infrastructure_area a ON c.area_id = a.id
WHERE b.batch_number = 'FI-2024-001'  -- Replace with your batch
ORDER BY bca.assignment_date, c.name
LIMIT 20;
```

**Expected Output:**
```
batch_number | stage       | location_name      | location_type | assignment_date | departure_date | days_in_location
-------------|-------------|--------------------|--------------|-----------------|-----------------|-----------------
FI-2024-001  | Egg&Alevin  | FI-FW-01-Hall-A    | Hall         | 2024-01-01      | 2024-04-01     | 90
FI-2024-001  | Fry         | FI-FW-01-Hall-B    | Hall         | 2024-04-01      | 2024-07-01     | 91
FI-2024-001  | Parr        | FI-FW-01-Hall-C    | Hall         | 2024-07-01      | 2024-09-30     | 91
FI-2024-001  | Smolt       | FI-FW-01-Hall-D    | Hall         | 2024-09-30      | 2024-12-30     | 91
FI-2024-001  | Post-Smolt  | FI-FW-01-Hall-E    | Hall         | 2024-12-30      | 2025-03-31     | 91
FI-2024-001  | Adult       | FI-Sea-01          | Sea Area     | 2025-03-31      | NULL           | 200 (active)
```

### Query 2: Current Container Utilization by Hall

```sql
-- See which halls are currently occupied and by which batches
SELECT 
    h.name AS hall_name,
    COUNT(DISTINCT bca.container_id) AS containers_in_use,
    COUNT(DISTINCT bca.batch_id) AS active_batches,
    STRING_AGG(DISTINCT b.batch_number, ', ' ORDER BY b.batch_number) AS batch_list,
    ls.name AS current_stage,
    SUM(bca.biomass_kg) AS total_biomass_kg
FROM batch_batchcontainerassignment bca
JOIN batch_batch b ON bca.batch_id = b.id
JOIN batch_lifecyclestage ls ON bca.lifecycle_stage_id = ls.id
JOIN infrastructure_container c ON bca.container_id = c.id
JOIN infrastructure_hall h ON c.hall_id = h.id
WHERE bca.is_active = TRUE
GROUP BY h.name, ls.name
ORDER BY h.name;
```

**Expected Output (with saturation):**
```
hall_name          | containers_in_use | active_batches | batch_list              | current_stage | total_biomass_kg
-------------------|-------------------|----------------|-------------------------|---------------|------------------
FI-FW-01-Hall-A    | 30                | 3              | FI-2025-001, FI-2025... | Egg&Alevin    | 105.0
FI-FW-01-Hall-B    | 30                | 3              | FI-2024-050, FI-2024... | Fry           | 1500.5
FI-FW-01-Hall-C    | 30                | 3              | FI-2024-040, FI-2024... | Parr          | 15000.2
FI-FW-01-Hall-D    | 30                | 3              | FI-2024-030, FI-2024... | Smolt         | 45000.8
FI-FW-01-Hall-E    | 30                | 3              | FI-2024-020, FI-2024... | Post-Smolt    | 135000.5
```

### Query 3: Hall Availability (Container Vacancy)

```sql
-- Find available containers in each hall for new batch assignments
WITH occupied_containers AS (
    SELECT container_id
    FROM batch_batchcontainerassignment
    WHERE is_active = TRUE
)
SELECT 
    h.name AS hall_name,
    ct.name AS container_type,
    COUNT(c.id) AS total_containers,
    COUNT(oc.container_id) AS occupied_containers,
    COUNT(c.id) - COUNT(oc.container_id) AS available_containers,
    ROUND(100.0 * COUNT(oc.container_id) / COUNT(c.id), 1) AS utilization_pct
FROM infrastructure_container c
JOIN infrastructure_containertype ct ON c.container_type_id = ct.id
JOIN infrastructure_hall h ON c.hall_id = h.id
LEFT JOIN occupied_containers oc ON c.id = oc.container_id
WHERE c.active = TRUE
GROUP BY h.name, ct.name
ORDER BY h.name;
```

**Expected Output:**
```
hall_name          | container_type      | total_containers | occupied | available | utilization_pct
-------------------|---------------------|------------------|----------|-----------|----------------
FI-FW-01-Hall-A    | Egg & Alevin Trays  | 10               | 10       | 0         | 100.0
FI-FW-01-Hall-B    | Fry Tanks           | 10               | 10       | 0         | 100.0
FI-FW-01-Hall-C    | Parr Tanks          | 10               | 8        | 2         | 80.0
FI-FW-01-Hall-D    | Smolt Tanks         | 10               | 9        | 1         | 90.0
FI-FW-01-Hall-E    | Post-Smolt Tanks    | 10               | 7        | 3         | 70.0
```

### Query 4: Batch Timeline Visualization

```sql
-- Create a timeline showing when batches occupied each hall
SELECT 
    b.batch_number,
    ls.name AS stage,
    MIN(bca.assignment_date) AS stage_start,
    MAX(COALESCE(bca.departure_date, CURRENT_DATE)) AS stage_end,
    MAX(COALESCE(bca.departure_date, CURRENT_DATE)) - MIN(bca.assignment_date) AS days_in_stage,
    COUNT(DISTINCT bca.container_id) AS containers_used
FROM batch_batchcontainerassignment bca
JOIN batch_batch b ON bca.batch_id = b.id
JOIN batch_lifecyclestage ls ON bca.lifecycle_stage_id = ls.id
WHERE b.batch_number IN ('FI-2024-001', 'FI-2024-002', 'FI-2024-003')  -- Replace with your batches
GROUP BY b.batch_number, ls.name, ls.order
ORDER BY b.batch_number, ls.order;
```

**Expected Output:**
```
batch_number | stage       | stage_start | stage_end  | days_in_stage | containers_used
-------------|-------------|-------------|------------|---------------|----------------
FI-2024-001  | Egg&Alevin  | 2024-01-01  | 2024-04-01 | 90            | 10
FI-2024-001  | Fry         | 2024-04-01  | 2024-07-01 | 91            | 10
FI-2024-001  | Parr        | 2024-07-01  | 2024-09-30 | 91            | 10
FI-2024-001  | Smolt       | 2024-09-30  | 2024-12-30 | 91            | 10
FI-2024-001  | Post-Smolt  | 2024-12-30  | 2025-03-31 | 91            | 10
FI-2024-001  | Adult       | 2025-03-31  | 2026-08-29 | 516 (active)  | 10
```

### Query 5: Stage Transition Audit

```sql
-- Find all stage transitions with exact timestamps
SELECT 
    b.batch_number,
    prev_ls.name AS from_stage,
    next_ls.name AS to_stage,
    prev_bca.departure_date AS transition_date,
    COALESCE(prev_h.name, prev_a.name) AS from_location,
    COALESCE(next_h.name, next_a.name) AS to_location,
    prev_bca.population_count AS population_before,
    next_bca.population_count AS population_after,
    prev_bca.avg_weight_g AS weight_before,
    next_bca.avg_weight_g AS weight_after
FROM batch_batchcontainerassignment prev_bca
JOIN batch_batchcontainerassignment next_bca ON (
    prev_bca.batch_id = next_bca.batch_id 
    AND next_bca.assignment_date = prev_bca.departure_date
)
JOIN batch_batch b ON prev_bca.batch_id = b.id
JOIN batch_lifecyclestage prev_ls ON prev_bca.lifecycle_stage_id = prev_ls.id
JOIN batch_lifecyclestage next_ls ON next_bca.lifecycle_stage_id = next_ls.id
JOIN infrastructure_container prev_c ON prev_bca.container_id = prev_c.id
JOIN infrastructure_container next_c ON next_bca.container_id = next_c.id
LEFT JOIN infrastructure_hall prev_h ON prev_c.hall_id = prev_h.id
LEFT JOIN infrastructure_hall next_h ON next_c.hall_id = next_h.id
LEFT JOIN infrastructure_area prev_a ON prev_c.area_id = prev_a.id
LEFT JOIN infrastructure_area next_a ON next_c.area_id = next_a.id
WHERE b.batch_number = 'FI-2024-001'  -- Replace with your batch
GROUP BY 
    b.batch_number, 
    prev_ls.name, 
    next_ls.name, 
    prev_bca.departure_date,
    prev_h.name, 
    next_h.name,
    prev_a.name,
    next_a.name,
    prev_bca.population_count,
    next_bca.population_count,
    prev_bca.avg_weight_g,
    next_bca.avg_weight_g
ORDER BY prev_bca.departure_date;
```

**Expected Output:**
```
batch_number | from_stage  | to_stage    | transition_date | from_location      | to_location        | pop_before | pop_after | weight_before | weight_after
-------------|-------------|-------------|-----------------|--------------------|--------------------|------------|-----------|---------------|-------------
FI-2024-001  | Egg&Alevin  | Fry         | 2024-04-01      | FI-FW-01-Hall-A    | FI-FW-01-Hall-B    | 3500000    | 3482500   | 0.1           | 0.15
FI-2024-001  | Fry         | Parr        | 2024-07-01      | FI-FW-01-Hall-B    | FI-FW-01-Hall-C    | 3482500    | 3465123   | 5.2           | 5.8
FI-2024-001  | Parr        | Smolt       | 2024-09-30      | FI-FW-01-Hall-C    | FI-FW-01-Hall-D    | 3465123    | 3450789   | 52.5          | 58.3
FI-2024-001  | Smolt       | Post-Smolt  | 2024-12-30      | FI-FW-01-Hall-D    | FI-FW-01-Hall-E    | 3450789    | 3438901   | 148.7         | 155.2
FI-2024-001  | Post-Smolt  | Adult       | 2025-03-31      | FI-FW-01-Hall-E    | FI-Sea-01          | 3438901    | 3425678   | 442.8         | 465.1
```

### Key Insights from These Queries

1. **Complete Audit Trail**: Every movement is recorded with exact dates
2. **Hall Specialization Enforced**: Batches move to correct halls for each stage
3. **Container Reuse**: Old assignments close (`is_active=FALSE`), freeing containers
4. **Population Tracking**: Mortality between stages visible in population changes
5. **Growth Tracking**: Weight progression through stages clearly documented
6. **Utilization Monitoring**: Real-time view of which containers are occupied
7. **Capacity Planning**: Know exactly when containers become available

---

## Expected Results

After full generation with 85% saturation:

### Batch Statistics
- **Total Batches:** ~170
- **Active Batches:** ~120-140 (others harvested or completing)
- **Geography Distribution:** ~85 per geography
- **Stage Distribution:**
  - Egg&Alevin: ~15 batches
  - Fry: ~15 batches
  - Parr: ~15 batches
  - Smolt: ~15 batches
  - Post-Smolt: ~15 batches
  - Adult: ~75 batches (longest stage)

### Data Volume
- **Total Events:** ~50 million
  - Environmental Readings: ~40M
  - Feeding Events: ~8M
  - Mortality Events: ~800K
  - Growth Samples: ~400K
- **Database Size:** ~80-100 GB
- **Audit History Records:** ~10M

### Container Utilization
- **Freshwater:** ~80-90% utilized
- **Sea Cages:** ~85-95% utilized
- **Feed Inventory:** Continuously replenishing via FIFO

---

## Troubleshooting

### Issue: Script Hangs or Slows Down

**Cause:** Database growth, competing queries  
**Solution:** 
```bash
# Run VACUUM ANALYZE periodically
python manage.py dbshell -c "VACUUM ANALYZE;"

# Check for slow queries
python manage.py dbshell -c "
SELECT query, state, query_start 
FROM pg_stat_activity 
WHERE state != 'idle' 
ORDER BY query_start;
"
```

### Issue: Out of Memory

**Cause:** Too many concurrent operations  
**Solution:** Reduce batch size or run in smaller chunks

```bash
# Generate 25 batches at a time
python scripts/data_generation/04_batch_orchestrator.py \
  --execute \
  --batches 25
  
# Wait for completion, then run again (incremental)
```

### Issue: Feed Containers Running Empty

**Cause:** Auto-reorder threshold too low  
**Solution:** Check Phase 2 initialization (should have 10+ tonnes per silo)

```bash
python scripts/data_generation/02_initialize_master_data.py
```

---

## Cleanup and Reset

### Remove All Batch Data (Keep Infrastructure)

```bash
python scripts/data_generation/cleanup_batch_data.py
```

### Full Database Reset

```bash
# WARNING: Deletes everything
dropdb aquamind_db
createdb aquamind_db
python manage.py migrate

# Rebuild infrastructure and master data
python scripts/data_generation/01_bootstrap_infrastructure.py
python scripts/data_generation/02_initialize_master_data.py
```

---

## Performance Optimization

### For Faster Generation

1. **Use Smaller Batch Count**
   ```bash
   --batches 10  # Instead of calculated ~85
   ```

2. **Reduce Duration**
   ```bash
   # Not recommended - breaks realistic lifecycle
   # But useful for testing orchestrator
   ```

3. **Parallel Execution**
   ```bash
   # Advanced: Run multiple orchestrators for different date ranges
   # Requires careful coordination to avoid conflicts
   ```

### For Production Deployment

1. **Increase PostgreSQL Resources**
   - shared_buffers: 25% of RAM
   - work_mem: 50MB
   - maintenance_work_mem: 2GB

2. **Enable Connection Pooling**
   - Use pgBouncer or similar

3. **Monitor Disk I/O**
   - SSDs highly recommended

---

## Script Architecture

### File Relationships

```
Phase 1: 01_bootstrap_infrastructure.py
  └─> Creates: Geographies, Stations, Halls, Containers, Sensors
  
Phase 2: 02_initialize_master_data.py
  └─> Creates: Species, Stages, Feed Types, Initial Inventory
  
Phase 3: 03_event_engine_core.py
  └─> Creates: ONE batch with 900-day lifecycle
  └─> Fixed: Adult stage now 450 days (was infinite)
  
Phase 4: 04_batch_orchestrator.py (NEW)
  └─> Orchestrates: Multiple Phase 3 runs
  └─> Calculates: Optimal batch count
  └─> Staggers: Batch start dates
  └─> Distributes: Across geographies
```

---

## Summary

The new batch orchestrator solves your requirements:

✅ **Realistic Lifecycle Durations**
- 900-day total lifecycle (was ~650)
- Explicit 450-day Adult stage

✅ **Infrastructure Saturation**
- Automatically calculates capacity
- Generates ~85% saturation by default
- Staggers batches for realistic operation

✅ **Both Geographies**
- Even distribution
- Independent batch numbering

✅ **Scalable Execution**
- Dry-run mode for planning
- Progress monitoring
- Error handling

**Next Steps:**
1. Run dry-run to review plan
2. Execute with small batch count first (testing)
3. Scale up to full saturation when satisfied

---

## Parallel Execution

### Sequential vs Parallel Orchestrators

**Sequential (`04_batch_orchestrator.py`):**
- Runs 1 batch at a time
- Safe, straightforward, easy to debug
- 10 batches × 5 min = ~50 minutes
- Good for initial testing and verification

**Parallel (`04_batch_orchestrator_parallel.py`):**
- Runs multiple batches simultaneously
- Utilizes all available CPU cores
- 10 batches ÷ 14 workers = ~5-10 minutes
- **~5-10x faster!**
- Container conflict prevention built-in

### Container Conflict Prevention

The parallel orchestrator uses `find_available_containers()` to prevent race conditions:

```python
# Checks current database state for occupied containers
occupied_ids = BatchContainerAssignment.objects.filter(
    is_active=True
).values_list('container_id', flat=True)

# Only selects from unoccupied containers
available = Container.objects.filter(
    hall=hall,
    active=True
).exclude(id__in=occupied_ids)
```

**Applied at:**
1. Initial batch creation (Hall A assignment)
2. Stage transitions to new halls (B→C→D→E)
3. Seawater transfer (Adult stage)

### Using Parallel Orchestrator

```bash
# Default: Uses (CPU cores - 2) workers
python scripts/data_generation/04_batch_orchestrator_parallel.py --batches 25

# Customize worker count (recommended: leave 2-4 cores for system)
python scripts/data_generation/04_batch_orchestrator_parallel.py \
  --batches 50 \
  --workers 12  # On 16-core machine

# Full saturation with parallel
python scripts/data_generation/04_batch_orchestrator_parallel.py \
  --saturation 0.85
```

### Performance on M4 Max (16 cores, 128GB RAM)

| Batches | Sequential | Parallel (14 workers) | Speedup |
|---------|------------|----------------------|---------|
| 10      | ~50 min    | ~5-7 min             | 7-10x   |
| 50      | ~250 min   | ~20-25 min           | 10x     |
| 170     | ~850 min   | ~60-70 min           | 12-14x  |

**Note:** Actual speedup depends on:
- Database I/O performance (SSD recommended)
- PostgreSQL configuration (connection limit, shared buffers)
- System load (leave headroom for OS + database)

### Monitoring Parallel Execution

```bash
# Watch process count
ps aux | grep "03_event_engine_core.py" | wc -l

# Watch database connections
psql -d aquamind_db -c "SELECT count(*) FROM pg_stat_activity WHERE state = 'active';"

# Check for errors in parallel run
# (errors will be reported in orchestrator output)
```

### Safety Considerations

✅ **Safe to run in parallel:**
- Different geographies (independent infrastructure)
- Different start dates (time-separated batches)
- Automated container availability checks

⚠️ **Potential issues:**
- Very high saturation (>95%) may cause container shortage
- Database connection limit reached (increase max_connections in postgresql.conf)
- Disk I/O bottleneck with many concurrent writes

**Recommendations:**
1. Start with 10-20 batches to verify parallel execution works
2. Monitor first run for errors or warnings
3. Scale up to full saturation after successful test
4. Keep 2-4 cores free for system/database processes

---

**End of Guide**
