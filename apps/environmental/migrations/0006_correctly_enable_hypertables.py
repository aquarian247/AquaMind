# Generated by Django 4.2.11 on 2025-03-31.
# This migration correctly enables TimescaleDB hypertables for key environmental tables.
from django.db import migrations
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

# SQL to drop the default primary key constraint if it exists
# We need specific names which might vary, but common patterns are used.
# Using IF EXISTS prevents errors if the constraint was already dropped or renamed.
DROP_DEFAULT_PK_SQL = '''
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.table_constraints 
               WHERE constraint_name = '{table_name}_pkey' 
               AND table_name = '{table_name}' 
               AND table_schema = 'public') THEN
        EXECUTE 'ALTER TABLE public.{table_name} DROP CONSTRAINT {table_name}_pkey;';
        RAISE NOTICE 'Dropped default PK constraint for {table_name}';
    END IF;
END $$;
'''

# SQL to set the composite primary key
SET_COMPOSITE_PK_SQL = '''
ALTER TABLE public.{table_name} ADD PRIMARY KEY ({pk_columns});
'''

# SQL to create the hypertable with space partitioning
CREATE_HYPERTABLE_SQL = '''
SELECT create_hypertable(
    '{table_name}', 
    '{time_column}', 
    partitioning_column => '{partition_column}', 
    number_partitions => {num_partitions},
    chunk_time_interval => INTERVAL '{chunk_interval}',
    if_not_exists => TRUE
);
'''

class Migration(migrations.Migration):

    dependencies = [
        # Depend on the LAST known migration in the app before this one
        ('environmental', '0005_fix_timescaledb_integration'), 
    ]

    operations = [
        # --- Environmental Reading ---
        
        # 1. Drop default 'id' based primary key if it exists
        migrations.RunSQL(
            sql=DROP_DEFAULT_PK_SQL.format(table_name='environmental_environmentalreading'),
            reverse_sql=migrations.RunSQL.noop, # Reversing complex PK changes is tricky
        ),

        # 2. Set the composite primary key (reading_time, sensor_id)
        migrations.RunSQL(
            sql=SET_COMPOSITE_PK_SQL.format(
                table_name='environmental_environmentalreading', 
                pk_columns='reading_time, sensor_id'
            ),
            reverse_sql=migrations.RunSQL.noop, # Define reverse if needed, e.g., back to 'id'
        ),

        # 3. Create the hypertable
        migrations.RunSQL(
            sql=CREATE_HYPERTABLE_SQL.format(
                table_name='environmental_environmentalreading',
                time_column='reading_time',
                partition_column='sensor_id',
                num_partitions=16,
                chunk_interval='7 days'
            ),
            reverse_sql="SELECT 1;", # Simplistic reverse
        ),

        # --- Weather Data ---
        
        # 1. Drop default 'id' based primary key if it exists
        migrations.RunSQL(
            sql=DROP_DEFAULT_PK_SQL.format(table_name='environmental_weatherdata'),
            reverse_sql=migrations.RunSQL.noop,
        ),

        # 2. Set the composite primary key (timestamp, area_id)
        migrations.RunSQL(
            sql=SET_COMPOSITE_PK_SQL.format(
                table_name='environmental_weatherdata', 
                pk_columns='timestamp, area_id'
            ),
            reverse_sql=migrations.RunSQL.noop,
        ),

        # 3. Create the hypertable
        migrations.RunSQL(
            sql=CREATE_HYPERTABLE_SQL.format(
                table_name='environmental_weatherdata',
                time_column='timestamp',
                partition_column='area_id',
                num_partitions=16,
                chunk_interval='1 month'
            ),
            reverse_sql="SELECT 1;", # Simplistic reverse
        ),
    ]
