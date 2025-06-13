# Database Management Guide

## Overview

This document outlines the database management practices for the AquaMind project, with special focus on TimescaleDB integration, migration strategies, and best practices for maintaining data integrity and performance.

## Database Architecture

### PostgreSQL with TimescaleDB

AquaMind uses PostgreSQL with the TimescaleDB extension for efficient time-series data management. This combination provides:

- Standard relational database capabilities for entity relationships
- Optimized time-series data storage and querying
- Automatic partitioning of time-series data
- Advanced aggregation and downsampling capabilities

### Database Connection

The database connection is defined in `aquamind/settings.py`:

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'aquamind_db',
        'USER': 'postgres',
        'PASSWORD': 'aquapass12345',
        'HOST': 'timescale-db',
        'PORT': '5432',
        'OPTIONS': {
            'options': '-c search_path=public'
        }
    }
}
```

For security in production environments, these values should be loaded from environment variables rather than hardcoded.

## Data Model

The complete data model is defined in `docs/data_model.md`. Always refer to this document when making schema changes to ensure consistency with the overall data architecture.

## TimescaleDB Hypertables

### What are Hypertables?

Hypertables are TimescaleDB's version of partitioned tables, specifically optimized for time-series data. They automatically partition data across time and space (if configured), providing significant performance benefits for time-based queries.

### Hypertable Usage in AquaMind

In AquaMind, the following tables are implemented as hypertables:

1. `environmental_environmentalreading` - For sensor readings
2. `environmental_weatherdata` - For weather information

### Creating Hypertables

Hypertables are created after the standard Django table creation, typically in a migration file:

```python
# Example migration for creating a hypertable
from django.db import migrations
from django.db import connections

def create_hypertable(apps, schema_editor):
    with connections['default'].cursor() as cursor:
        cursor.execute(
            "SELECT create_hypertable('environmental_environmentalreading', 'timestamp', 
            chunk_time_interval => interval '1 day', if_not_exists => TRUE);"
        )

class Migration(migrations.Migration):
    dependencies = [
        ('environmental', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(create_hypertable),
    ]
```

### Hypertable Best Practices

1. **Choose the Right Time Column**: Select a column that will be used frequently in WHERE clauses
2. **Set Appropriate Chunk Intervals**: Default is 7 days, adjust based on data volume
3. **Create Indexes on Common Query Patterns**: Add indexes for frequently queried columns
4. **Consider Compression**: Enable compression for older data chunks

```python
# Example of enabling compression
def enable_compression(apps, schema_editor):
    with connections['default'].cursor() as cursor:
        cursor.execute(
            "ALTER TABLE environmental_environmentalreading SET (
                timescaledb.compress,
                timescaledb.compress_segmentby = 'sensor_id'
            );"
        )
        cursor.execute(
            "SELECT add_compression_policy('environmental_environmentalreading', INTERVAL '30 days');"
        )
```

## Migration Strategy

### Django Migrations

AquaMind uses Django's migration system for all schema changes. Never alter the database schema manually.

### Migration Best Practices

1. **Small, Focused Migrations**: Create separate migrations for different types of changes
2. **Test Migrations**: Always test migrations on a copy of production data
3. **Data Migrations**: Use data migrations for data transformations
4. **Backward Compatibility**: Ensure migrations can be rolled back if needed

### Migration Workflow

1. **Create Migration**:
   ```bash
   python manage.py makemigrations app_name
   ```

2. **Review Migration**:
   - Check the generated migration file
   - Ensure it does what you expect
   - Add any custom operations (like creating hypertables)

3. **Apply Migration**:
   ```bash
   python manage.py migrate app_name
   ```

4. **Test After Migration**:
   - Verify data integrity
   - Check application functionality
   - Monitor query performance

### TimescaleDB-Specific Migrations

For TimescaleDB-specific operations that can't be expressed in Django's migration framework, use raw SQL:

```python
from django.db import migrations

def run_timescale_operation(apps, schema_editor):
    with schema_editor.connection.cursor() as cursor:
        # TimescaleDB-specific operations
        cursor.execute("SELECT add_retention_policy('environmental_environmentalreading', INTERVAL '1 year');")

class Migration(migrations.Migration):
    dependencies = [
        ('environmental', '0002_create_hypertable'),
    ]

    operations = [
        migrations.RunPython(run_timescale_operation, reverse_code=migrations.RunPython.noop),
    ]
```

## Environment-Specific Database Management

### Development Environment

- Use Docker container with TimescaleDB for consistent development
- Use smaller datasets for faster development cycles
- Enable DEBUG logging for SQL queries

### Testing Environment

- Use SQLite for standard tests without TimescaleDB features
- Use a dedicated TimescaleDB instance for TimescaleDB-specific tests
- Skip TimescaleDB-specific tests in CI environments without TimescaleDB

### Production Environment

- Use a properly sized PostgreSQL with TimescaleDB instance
- Implement regular backups
- Monitor database performance and growth
- Implement retention policies for time-series data

## Database Inspection

### Using the Database Inspection Script

AquaMind includes a database inspection script to help understand the current database schema. Use it when:

1. You need to verify the current state of the database
2. You're planning schema changes
3. You suspect schema drift between environments

To run the inspection script:

```bash
python manage.py inspect_db
```

For more details, refer to `docs/database_inspection_rule.md`.

### Manual Database Inspection

For direct inspection of the database, connect using `psql`:

```bash
psql -h timescale-db -U postgres -d aquamind_db
```

Useful commands:

- `\dt` - List all tables
- `\d+ table_name` - Describe a table
- `SELECT * FROM timescaledb_information.hypertables;` - List all hypertables

## Query Optimization

### General Query Optimization

1. **Use Django's QuerySet Methods**:
   - `select_related` for ForeignKey relationships
   - `prefetch_related` for reverse relationships
   - `only` and `defer` to limit retrieved fields

2. **Indexing Strategy**:
   - Add indexes for frequently queried fields
   - Use composite indexes for multi-field queries
   - Consider partial indexes for filtered queries

### TimescaleDB-Specific Optimization

1. **Time-Bucket Aggregation**:
   ```sql
   SELECT time_bucket('1 hour', timestamp) AS hour, 
          AVG(temperature) AS avg_temp
   FROM environmental_environmentalreading
   WHERE sensor_id = 123
   GROUP BY hour
   ORDER BY hour;
   ```

2. **Continuous Aggregates**:
   ```python
   def create_continuous_aggregate(apps, schema_editor):
       with connections['default'].cursor() as cursor:
           cursor.execute("""
               CREATE MATERIALIZED VIEW environmental_daily_avg
               WITH (timescaledb.continuous) AS
               SELECT time_bucket('1 day', timestamp) AS day,
                      sensor_id,
                      AVG(temperature) AS avg_temp,
                      MIN(temperature) AS min_temp,
                      MAX(temperature) AS max_temp
               FROM environmental_environmentalreading
               GROUP BY day, sensor_id;
           """)
   ```

3. **Retention Policies**:
   ```python
   def add_retention_policy(apps, schema_editor):
       with connections['default'].cursor() as cursor:
           cursor.execute(
               "SELECT add_retention_policy('environmental_environmentalreading', INTERVAL '1 year');"
           )
   ```

## Data Migration Across Environments

### Exporting Data

For transferring data between environments:

```bash
# Export schema and data
pg_dump -h timescale-db -U postgres -d aquamind_db -F c -f aquamind_backup.dump

# Export schema only
pg_dump -h timescale-db -U postgres -d aquamind_db -s -f aquamind_schema.sql

# Export specific tables
pg_dump -h timescale-db -U postgres -d aquamind_db -t 'public.batch' -F c -f batch_data.dump
```

### Importing Data

```bash
# Restore full database
pg_restore -h target-db -U postgres -d aquamind_db -c aquamind_backup.dump

# Apply schema only
psql -h target-db -U postgres -d aquamind_db -f aquamind_schema.sql

# Restore specific tables
pg_restore -h target-db -U postgres -d aquamind_db -t public.batch batch_data.dump
```

### Selective Data Migration

For migrating specific data between environments:

1. **Create a Django management command**:

```python
# management/commands/export_batches.py
from django.core.management.base import BaseCommand
from django.core import serializers
from apps.batch.models import Batch

class Command(BaseCommand):
    help = 'Export batches to JSON'

    def add_arguments(self, parser):
        parser.add_argument('--output', type=str, default='batches.json')
        parser.add_argument('--start-date', type=str, help='Filter by start date (YYYY-MM-DD)')

    def handle(self, *args, **options):
        queryset = Batch.objects.all()
        
        if options['start_date']:
            queryset = queryset.filter(start_date__gte=options['start_date'])
            
        data = serializers.serialize('json', queryset)
        
        with open(options['output'], 'w') as f:
            f.write(data)
            
        self.stdout.write(self.style.SUCCESS(f'Exported {queryset.count()} batches'))
```

2. **Import the data in the target environment**:

```python
# management/commands/import_batches.py
from django.core.management.base import BaseCommand
from django.core import serializers

class Command(BaseCommand):
    help = 'Import batches from JSON'

    def add_arguments(self, parser):
        parser.add_argument('--input', type=str, default='batches.json')

    def handle(self, *args, **options):
        with open(options['input'], 'r') as f:
            data = f.read()
            
        objects = list(serializers.deserialize('json', data))
        
        for obj in objects:
            obj.save()
            
        self.stdout.write(self.style.SUCCESS(f'Imported {len(objects)} batches'))
```

## Database Backup and Recovery

### Automated Backups

Set up automated backups using a cron job or scheduled task:

```bash
# Example cron job for daily backups
0 2 * * * pg_dump -h timescale-db -U postgres -d aquamind_db -F c -f /backups/aquamind_$(date +\%Y\%m\%d).dump
```

### Backup Retention

Implement a backup retention policy to manage disk space:

```bash
# Example script to keep 30 days of backups
find /backups/ -name "aquamind_*.dump" -type f -mtime +30 -delete
```

### Recovery Procedure

1. **Stop the application**:
   ```bash
   docker-compose stop web
   ```

2. **Restore the database**:
   ```bash
   pg_restore -h timescale-db -U postgres -d aquamind_db -c /backups/aquamind_20250101.dump
   ```

3. **Start the application**:
   ```bash
   docker-compose start web
   ```

## Monitoring and Maintenance

### Regular Maintenance Tasks

1. **VACUUM ANALYZE**:
   ```sql
   VACUUM ANALYZE;
   ```

2. **Reindex**:
   ```sql
   REINDEX DATABASE aquamind_db;
   ```

3. **Update Statistics**:
   ```sql
   ANALYZE;
   ```

### Monitoring Queries

1. **Table Sizes**:
   ```sql
   SELECT
       table_name,
       pg_size_pretty(pg_total_relation_size(table_name)) as total_size,
       pg_size_pretty(pg_relation_size(table_name)) as table_size,
       pg_size_pretty(pg_total_relation_size(table_name) - pg_relation_size(table_name)) as index_size
   FROM (
       SELECT ('"' || table_schema || '"."' || table_name || '"') as table_name
       FROM information_schema.tables
       WHERE table_schema = 'public'
   ) as tables
   ORDER BY pg_total_relation_size(table_name) DESC;
   ```

2. **Hypertable Chunks**:
   ```sql
   SELECT show_chunks('environmental_environmentalreading');
   ```

3. **Slow Queries**:
   ```sql
   SELECT query, calls, total_time, mean_time
   FROM pg_stat_statements
   ORDER BY mean_time DESC
   LIMIT 10;
   ```

## Conclusion

Following these database management guidelines will help maintain a healthy, performant, and reliable database for the AquaMind application. Always prioritize data integrity and follow Django's migration system for all schema changes. For TimescaleDB-specific operations, use raw SQL in migration files to ensure all changes are tracked and versioned.
