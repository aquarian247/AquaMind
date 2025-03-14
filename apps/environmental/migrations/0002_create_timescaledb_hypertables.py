from django.db import migrations

class Migration(migrations.Migration):
    """
    Custom migration to set up TimescaleDB hypertables for time-series data.
    Following the windsurf rule: 'Always define hypertables with create_hypertable after table creation'
    """

    dependencies = [
        ('environmental', '0001_initial'),
    ]

    operations = [
        # Step 1: Create hypertables
        migrations.RunSQL(
            """
            SELECT create_hypertable('environmental_environmentalreading', 'reading_time', 
                                    if_not_exists => TRUE);
            """,
            reverse_sql="SELECT 1;"  # No need to reverse this operation
        ),
        migrations.RunSQL(
            """
            SELECT create_hypertable('environmental_weatherdata', 'timestamp', 
                                    if_not_exists => TRUE);
            """,
            reverse_sql="SELECT 1;"  # No need to reverse this operation
        ),
        
        # Step 2: Enable compression on hypertables (need to do this before adding compression policies)
        migrations.RunSQL(
            """
            -- Enable compression on environmental readings
            ALTER TABLE environmental_environmentalreading SET (
                timescaledb.compress,
                timescaledb.compress_segmentby = 'container_id,parameter_id'
            );
            """,
            reverse_sql="""
            ALTER TABLE environmental_environmentalreading SET (
                timescaledb.compress = false
            );
            """
        ),
        migrations.RunSQL(
            """
            -- Enable compression on weather data
            ALTER TABLE environmental_weatherdata SET (
                timescaledb.compress,
                timescaledb.compress_segmentby = 'area_id'
            );
            """,
            reverse_sql="""
            ALTER TABLE environmental_weatherdata SET (
                timescaledb.compress = false
            );
            """
        ),
        
        # Step 3: Add compression policy with a 7-day retention policy
        migrations.RunSQL(
            """
            -- Set compression policy for environmental readings (older than 7 days)
            SELECT add_compression_policy('environmental_environmentalreading', 
                                        INTERVAL '7 days',
                                        if_not_exists => TRUE);
            """,
            reverse_sql="""
            SELECT remove_compression_policy('environmental_environmentalreading', if_not_exists => TRUE);
            """
        ),
        migrations.RunSQL(
            """
            -- Set compression policy for weather data (older than 7 days)
            SELECT add_compression_policy('environmental_weatherdata', 
                                        INTERVAL '7 days',
                                        if_not_exists => TRUE);
            """,
            reverse_sql="""
            SELECT remove_compression_policy('environmental_weatherdata', if_not_exists => TRUE);
            """
        ),
    ]
