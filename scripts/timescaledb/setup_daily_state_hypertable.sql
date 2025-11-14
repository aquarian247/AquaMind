-- TimescaleDB Hypertable Setup for ActualDailyAssignmentState
-- Issue #112 - Phase 2: Production Deployment Script
--
-- This script converts batch_actualdailyassignmentstate to a TimescaleDB hypertable
-- with compression enabled. Run this ONCE in production after migrations.
--
-- Prerequisites:
-- 1. PostgreSQL with TimescaleDB extension installed
-- 2. Django migrations applied (batch/0033 must be complete)
-- 3. Database user has superuser or appropriate TimescaleDB privileges
--
-- Usage:
--   psql -U <user> -d <database> -f setup_daily_state_hypertable.sql

-- Step 1: Update primary key to include partitioning column
-- TimescaleDB requires the partitioning column (date) to be part of the primary key

ALTER TABLE batch_actualdailyassignmentstate 
DROP CONSTRAINT IF EXISTS batch_actualdailyassignmentstate_pkey CASCADE;

ALTER TABLE batch_actualdailyassignmentstate 
ADD PRIMARY KEY (id, date);

\echo 'Step 1/4: Updated primary key to (id, date) ✓'

-- Step 2: Convert to hypertable with 14-day chunks
-- This partitions the table by date for efficient time-series queries

SELECT create_hypertable(
    'batch_actualdailyassignmentstate',
    'date',
    chunk_time_interval => INTERVAL '14 days',
    if_not_exists => TRUE
);

\echo 'Step 2/4: Converted to hypertable with 14-day chunks ✓'

-- Step 3: Enable compression
-- Segment by assignment_id (queries typically filter by assignment)
-- Order by date DESC (recent data accessed more frequently)

ALTER TABLE batch_actualdailyassignmentstate SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'assignment_id',
    timescaledb.compress_orderby = 'date DESC'
);

\echo 'Step 3/4: Enabled compression (segment by assignment_id) ✓'

-- Step 4: Add compression policy
-- Compress chunks older than 30 days automatically

SELECT add_compression_policy('batch_actualdailyassignmentstate', 
    INTERVAL '30 days');

\echo 'Step 4/4: Added compression policy (compress after 30 days) ✓'

-- Verification Query
-- Check that hypertable is configured correctly

SELECT 
    hypertable_schema,
    hypertable_name,
    compression_enabled
FROM timescaledb_information.hypertables 
WHERE hypertable_name = 'batch_actualdailyassignmentstate';

\echo ''
\echo 'Verification complete! Check output above.'
\echo 'Expected: compression_enabled = t (true)'

