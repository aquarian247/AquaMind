# Generated migration to remove deprecated BatchTransfer model
from django.db import migrations, connection


def drop_batchtransfer_tables(apps, schema_editor):
    """Drop BatchTransfer tables with database-specific syntax."""
    with connection.cursor() as cursor:
        # SQLite doesn't support CASCADE in DROP TABLE
        if connection.vendor == 'sqlite':
            cursor.execute("DROP TABLE IF EXISTS batch_batchtransfer")
            cursor.execute("DROP TABLE IF EXISTS batch_historicalbatchtransfer")
        else:
            # PostgreSQL supports CASCADE
            cursor.execute("DROP TABLE IF EXISTS batch_batchtransfer CASCADE")
            cursor.execute("DROP TABLE IF EXISTS batch_historicalbatchtransfer CASCADE")


class Migration(migrations.Migration):

    dependencies = [
        ('batch', '0023_batchtransferworkflow_historicaltransferaction_and_more'),
    ]

    operations = [
        migrations.RunPython(
            drop_batchtransfer_tables,
            reverse_code=migrations.RunPython.noop,
        ),
    ]

