# Generated migration to remove deprecated BatchTransfer model
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('batch', '0023_batchtransferworkflow_historicaltransferaction_and_more'),
    ]

    operations = [
        # Drop the tables directly (development environment - no production data)
        migrations.RunSQL(
            sql="""
                -- Drop tables with CASCADE to handle any remaining foreign keys
                DROP TABLE IF EXISTS batch_batchtransfer CASCADE;
                DROP TABLE IF EXISTS batch_historicalbatchtransfer CASCADE;
            """,
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]

