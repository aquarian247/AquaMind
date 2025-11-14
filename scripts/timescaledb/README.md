# TimescaleDB Production Setup Scripts

**Issue**: #112 - Batch Growth Assimilation  
**Purpose**: Configure TimescaleDB hypertables and continuous aggregates in production

---

## Overview

Per the [TimescaleDB Testing Strategy](../../aquamind/docs/quality_assurance/timescaledb_testing_strategy.md), TimescaleDB-specific features are configured manually in production rather than through Django migrations. This approach:

- ✅ Keeps migrations database-agnostic
- ✅ Prevents transaction issues in dev/test
- ✅ Allows fine-tuned production configuration
- ✅ Maintains CI/CD pipeline simplicity

---

## Scripts

### 1. `setup_daily_state_hypertable.sql`
**Purpose**: Convert `batch_actualdailyassignmentstate` to TimescaleDB hypertable

**What it does**:
- Updates primary key to (id, date) for partitioning
- Creates hypertable with 14-day chunks
- Enables compression (segment by assignment_id, order by date DESC)
- Adds compression policy (compress after 30 days)

**When to run**: After Django migration `batch/0033` is applied

**Command**:
```bash
psql -U postgres -d aquamind_production -f setup_daily_state_hypertable.sql
```

### 2. `setup_temperature_cagg.sql`
**Purpose**: Create continuous aggregate for daily temperature by container

**What it does**:
- Verifies `environmental_environmentalreading` is a hypertable
- Creates `env_daily_temp_by_container` materialized view
- Adds refresh policy (hourly, last 7 days)

**When to run**: After `environmental_environmentalreading` is configured as hypertable

**Command**:
```bash
psql -U postgres -d aquamind_production -f setup_temperature_cagg.sql
```

---

## Production Deployment Checklist

### Prerequisites
- [ ] PostgreSQL 12+ installed
- [ ] TimescaleDB extension installed and enabled
- [ ] Django migrations applied (`python manage.py migrate`)
- [ ] Database backup created
- [ ] Maintenance window scheduled (low impact but recommend off-peak)

### Step 1: Configure Environmental Hypertable (if not already done)
```bash
# Check if environmental_environmentalreading is a hypertable
psql -U postgres -d aquamind_production -c "
  SELECT hypertable_name FROM timescaledb_information.hypertables 
  WHERE hypertable_name = 'environmental_environmentalreading';
"
```

If not a hypertable, configure it first (see `apps/environmental/migrations/` for reference scripts).

### Step 2: Configure ActualDailyAssignmentState Hypertable
```bash
psql -U postgres -d aquamind_production -f scripts/timescaledb/setup_daily_state_hypertable.sql
```

**Expected output**:
```
Step 1/4: Updated primary key to (id, date) ✓
Step 2/4: Converted to hypertable with 14-day chunks ✓
Step 3/4: Enabled compression (segment by assignment_id) ✓
Step 4/4: Added compression policy (compress after 30 days) ✓
✅ batch_actualdailyassignmentstate hypertable fully configured!
```

### Step 3: Configure Temperature CAGG
```bash
psql -U postgres -d aquamind_production -f scripts/timescaledb/setup_temperature_cagg.sql
```

**Expected output**:
```
Step 1/3: Dropped existing view (if any) ✓
Step 2/3: Created env_daily_temp_by_container continuous aggregate ✓
Step 3/3: Added refresh policy (hourly, last 7 days) ✓
✅ env_daily_temp_by_container CAGG fully configured!
```

### Step 4: Verify Configuration
```bash
# Check hypertable
psql -U postgres -d aquamind_production -c "
  SELECT hypertable_name, chunk_time_interval, compression_enabled
  FROM timescaledb_information.hypertables 
  WHERE hypertable_name = 'batch_actualdailyassignmentstate';
"

# Check CAGG
psql -U postgres -d aquamind_production -c "
  SELECT view_name, compression_enabled
  FROM timescaledb_information.continuous_aggregates 
  WHERE view_name = 'env_daily_temp_by_container';
"

# Check compression policies
psql -U postgres -d aquamind_production -c "
  SELECT hypertable_name, compress_after
  FROM timescaledb_information.compression_settings;
"
```

---

## Rollback

If you need to revert the TimescaleDB configuration:

```sql
-- Drop compression policy
SELECT remove_compression_policy('batch_actualdailyassignmentstate');

-- Disable compression
ALTER TABLE batch_actualdailyassignmentstate SET (timescaledb.compress = false);

-- Drop CAGG
DROP MATERIALIZED VIEW IF EXISTS env_daily_temp_by_container CASCADE;

-- Note: Cannot easily revert hypertable to regular table with data
-- Recommend backup before running setup scripts
```

---

## Troubleshooting

### Error: "cannot create a unique index without the column 'date'"
**Cause**: Primary key doesn't include partitioning column  
**Solution**: Script step 1 updates the primary key - ensure it completes successfully

### Error: "hypertable already exists"
**Cause**: Script was run multiple times  
**Solution**: Scripts use `if_not_exists => TRUE` for idempotency - safe to ignore

### Error: "cannot create continuous aggregate on non-hypertable"
**Cause**: Source table is not a hypertable  
**Solution**: Run environmental hypertable setup first, then temperature CAGG

### Performance: Queries are slow
**Check**:
1. Compression policy is active: `SELECT * FROM timescaledb_information.jobs WHERE proc_name LIKE '%compression%';`
2. CAGG is refreshed: `CALL refresh_continuous_aggregate('env_daily_temp_by_container', NULL, NULL);`
3. Indexes exist: `\d batch_actualdailyassignmentstate`

---

## Monitoring

### Check Chunk Status
```sql
SELECT chunk_name, range_start, range_end, is_compressed
FROM timescaledb_information.chunks
WHERE hypertable_name = 'batch_actualdailyassignmentstate'
ORDER BY range_start DESC
LIMIT 10;
```

### Check Compression Stats
```sql
SELECT 
    pg_size_pretty(before_compression_total_bytes) AS uncompressed,
    pg_size_pretty(after_compression_total_bytes) AS compressed,
    ROUND((1 - after_compression_total_bytes::numeric / before_compression_total_bytes) * 100, 2) AS compression_ratio_pct
FROM timescaledb_information.compression_settings
WHERE hypertable_name = 'batch_actualdailyassignmentstate';
```

### Check CAGG Freshness
```sql
SELECT view_name, 
       completed_threshold,
       invalidation_threshold
FROM timescaledb_information.continuous_aggregate_stats
WHERE view_name = 'env_daily_temp_by_container';
```

---

## Performance Expectations

| Operation | Without TimescaleDB | With TimescaleDB |
|-----------|---------------------|------------------|
| Insert daily states (1000 rows) | ~500ms | ~200ms (chunked) |
| Query 1 assignment, 900 days | ~100ms | ~20ms (compressed) |
| Query 33 batches, 30 days | ~2s | ~300ms (indexed chunks) |
| Aggregate batch-level, 900 days | ~5s | ~500ms (compressed) |
| Storage (13.5M rows) | ~13.5 GB | ~2-4 GB (70-85% compression) |

---

## Future Enhancements

**Potential improvements** (not included in Phase 2):

1. **Retention Policies**: Automatically drop old data
   ```sql
   SELECT add_retention_policy('batch_actualdailyassignmentstate', INTERVAL '5 years');
   ```

2. **Distributed Hypertables**: For multi-node TimescaleDB clusters
3. **Additional CAGGs**: Weekly/monthly rollups (Phase 5)
4. **Replication**: Streaming replication for read replicas

---

## References

- [TimescaleDB Testing Strategy](../../aquamind/docs/quality_assurance/timescaledb_testing_strategy.md)
- [Phase 2 Implementation Plan](../../aquamind/docs/progress/batch_growth_assimilation/batch-growth-assimilation-plan.md#phase-2--hypertable--temperature-daily-cagg)
- [TimescaleDB Documentation](https://docs.timescale.com/)

