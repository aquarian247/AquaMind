-- TimescaleDB CAGG Setup for Daily Temperature by Container
-- Issue #112 - Phase 2: Production Deployment Script
--
-- This script creates a continuous aggregate for daily temperature averages
-- per container. This CAGG provides efficient access to temperature data
-- needed for batch growth assimilation calculations.
--
-- Prerequisites:
-- 1. PostgreSQL with TimescaleDB extension installed
-- 2. environmental_environmentalreading must be a TimescaleDB hypertable
-- 3. Django migrations applied (environmental/0014 must be complete)
--
-- Usage:
--   psql -U <user> -d <database> -f setup_temperature_cagg.sql

-- Verify environmental_environmentalreading is a hypertable
DO $$
DECLARE
    is_hypertable BOOLEAN;
BEGIN
    SELECT EXISTS(
        SELECT 1 FROM timescaledb_information.hypertables 
        WHERE hypertable_name = 'environmental_environmentalreading'
    ) INTO is_hypertable;
    
    IF NOT is_hypertable THEN
        RAISE EXCEPTION 'environmental_environmentalreading is not a hypertable. Run environmental hypertable setup first.';
    END IF;
    
    RAISE NOTICE 'Verified: environmental_environmentalreading is a hypertable ✓';
END $$;

-- Step 1: Drop existing view if it exists (for idempotency)

DROP MATERIALIZED VIEW IF EXISTS env_daily_temp_by_container CASCADE;

\echo 'Step 1/3: Dropped existing view (if any) ✓'

-- Step 2: Create continuous aggregate
-- Computes daily average, min, max temperature per container
-- Groups by container_id and day bucket

CREATE MATERIALIZED VIEW env_daily_temp_by_container
WITH (timescaledb.continuous) AS
SELECT
    er.container_id,
    time_bucket('1 day', er.reading_time) AS day,
    AVG(er.value) AS avg_temp_c,
    MIN(er.value) AS min_temp_c,
    MAX(er.value) AS max_temp_c,
    COUNT(*) AS reading_count
FROM environmental_environmentalreading er
INNER JOIN environmental_environmentalparameter ep ON er.parameter_id = ep.id
WHERE ep.name = 'temperature'
GROUP BY er.container_id, day
WITH NO DATA;

\echo 'Step 2/3: Created env_daily_temp_by_container continuous aggregate ✓'

-- Step 3: Add refresh policy
-- Refresh every hour, covering data from last 7 days

SELECT add_continuous_aggregate_policy('env_daily_temp_by_container',
    start_offset => INTERVAL '7 days',
    end_offset => INTERVAL '1 hour',
    schedule_interval => INTERVAL '1 hour'
);

\echo 'Step 3/3: Added refresh policy (hourly, last 7 days) ✓'

-- Verification Query
-- Check that CAGG is configured correctly

SELECT 
    view_name,
    materialization_hypertable_name,
    compression_enabled
FROM timescaledb_information.continuous_aggregates 
WHERE view_name = 'env_daily_temp_by_container';

\echo ''
\echo '✅ env_daily_temp_by_container CAGG fully configured!'
\echo ''
\echo 'Expected Output:'
\echo '  view_name: env_daily_temp_by_container'
\echo '  materialization_hypertable_name: _timescaledb_internal._materialized_hypertable_*'
\echo '  compression_enabled: t (true)'
\echo ''
\echo 'Usage in Python:'
\echo '  # Query daily temperature for a container'
\echo '  SELECT avg_temp_c FROM env_daily_temp_by_container'
\echo '  WHERE container_id = 123 AND day >= ''2023-01-01'''

