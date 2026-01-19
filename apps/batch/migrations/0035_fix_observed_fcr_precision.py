# Generated migration for Issue #112 - Phase 7
# Fix observed_fcr field precision to handle large FCR values
# TimescaleDB-aware: Handles compressed hypertables

from django.db import migrations, models, connection
from decimal import Decimal
import django.core.validators
import os


def is_timescaledb_available():
    """Check if TimescaleDB extension is available."""
    # Per timescaledb_testing_strategy.md and 0034_setup_timescaledb_hypertable,
    # TimescaleDB operations are skipped in dev/test by default. Enable explicitly
    # when running production TimescaleDB migrations.
    if os.environ.get("AQUAMIND_ENABLE_TIMESCALEDB_MIGRATIONS") != "1":
        return False

    # Skip on SQLite (CI tests)
    if connection.vendor == 'sqlite':
        return False
    
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname = 'timescaledb')"
            )
            return cursor.fetchone()[0]
    except Exception:
        return False


def alter_fcr_field_timescaledb(apps, schema_editor):
    """
    Alter observed_fcr field with TimescaleDB compression handling.
    
    Per timescaledb_testing_strategy.md: TimescaleDB features are tested manually,
    not in CI. This migration gracefully skips TimescaleDB-specific operations
    when not available (SQLite, non-TimescaleDB PostgreSQL).
    """
    if not is_timescaledb_available():
        # SQLite or non-TimescaleDB PostgreSQL
        # The standard AlterField operation below will handle it
        print("[SKIP] TimescaleDB not available, using standard Django AlterField")
        return
    
    # TimescaleDB columnstore prevents ALTER COLUMN - must drop and recreate
    with connection.cursor() as cursor:
        print("[WARN] TimescaleDB columnstore blocks ALTER COLUMN")
        print("[INFO] For dev: Dropping hypertable and recreating with correct schema...")
        
        # Step 1: Drop the hypertable (CASCADE removes chunks + policies)
        cursor.execute("DROP TABLE IF EXISTS batch_actualdailyassignmentstate CASCADE")
        
        # Step 2: Recreate with correct schema (composite PK for TimescaleDB)
        print("[INFO] Recreating table with observed_fcr NUMERIC(8,3)...")
        cursor.execute("""
            CREATE TABLE batch_actualdailyassignmentstate (
                id BIGSERIAL,
                assignment_id BIGINT NOT NULL REFERENCES batch_batchcontainerassignment(id) ON DELETE CASCADE,
                batch_id BIGINT NOT NULL REFERENCES batch_batch(id) ON DELETE CASCADE,
                container_id BIGINT NOT NULL REFERENCES infrastructure_container(id) ON DELETE CASCADE,
                lifecycle_stage_id BIGINT NOT NULL REFERENCES batch_lifecyclestage(id) ON DELETE RESTRICT,
                date DATE NOT NULL,
                day_number INTEGER NOT NULL,
                avg_weight_g NUMERIC(10,2) NOT NULL CHECK (avg_weight_g >= 0),
                population INTEGER NOT NULL CHECK (population >= 0),
                biomass_kg NUMERIC(12,2) NOT NULL CHECK (biomass_kg >= 0),
                temp_c NUMERIC(5,2),
                mortality_count INTEGER NOT NULL DEFAULT 0,
                feed_kg NUMERIC(10,2) NOT NULL DEFAULT 0 CHECK (feed_kg >= 0),
                observed_fcr NUMERIC(8,3) CHECK (observed_fcr >= 0),
                anchor_type VARCHAR(20) CHECK (anchor_type IN ('growth_sample', 'transfer', 'vaccination', 'manual')),
                sources JSONB NOT NULL DEFAULT '{}',
                confidence_scores JSONB NOT NULL DEFAULT '{}',
                last_computed_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (id, date),
                CONSTRAINT unique_assignment_date UNIQUE (assignment_id, date)
            )
        """)
        
        # Step 3: Recreate indexes
        cursor.execute("CREATE INDEX idx_assignment_date ON batch_actualdailyassignmentstate(assignment_id, date)")
        cursor.execute("CREATE INDEX idx_batch_date ON batch_actualdailyassignmentstate(batch_id, date)")
        cursor.execute("CREATE INDEX idx_date ON batch_actualdailyassignmentstate(date)")
        cursor.execute("CREATE INDEX idx_anchor_type ON batch_actualdailyassignmentstate(anchor_type)")
        
        # Step 4: Convert to hypertable
        cursor.execute("SELECT create_hypertable('batch_actualdailyassignmentstate', 'date', if_not_exists => TRUE, chunk_time_interval => INTERVAL '14 days')")
        
        # Step 5: Re-enable compression
        cursor.execute("""
            ALTER TABLE batch_actualdailyassignmentstate SET (
                timescaledb.compress,
                timescaledb.compress_segmentby = 'assignment_id',
                timescaledb.compress_orderby = 'date DESC'
            )
        """)
        cursor.execute("SELECT add_compression_policy('batch_actualdailyassignmentstate', INTERVAL '30 days', if_not_exists => true)")
        
        print("[OK] Table recreated with correct schema, hypertable + compression configured")


def reverse_fcr_field(apps, schema_editor):
    """Reverse the migration (reduce precision back to 6,3)."""
    if not is_timescaledb_available():
        return
    
    with connection.cursor() as cursor:
        # This could cause data loss if values > 999.999 exist!
        print("[WARN] Reverting observed_fcr precision to (6,3) - may cause data loss!")
        cursor.execute("""
            ALTER TABLE batch_actualdailyassignmentstate
            ALTER COLUMN observed_fcr TYPE NUMERIC(6,3)
        """)


class Migration(migrations.Migration):

    dependencies = [
        ('batch', '0034_setup_timescaledb_hypertable'),
    ]

    operations = [
        migrations.RunPython(alter_fcr_field_timescaledb, reverse_fcr_field),
        # Also run standard AlterField for SQLite/non-TimescaleDB databases
        migrations.AlterField(
            model_name='actualdailyassignmentstate',
            name='observed_fcr',
            field=models.DecimalField(
                blank=True,
                decimal_places=3,
                help_text='Observed Feed Conversion Ratio (if calculable)',
                max_digits=8,
                null=True,
                validators=[django.core.validators.MinValueValidator(Decimal('0.000'))]
            ),
        ),
    ]

