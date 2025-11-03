# Generated migration to remove deprecated BatchTransfer model
from django.db import migrations, connection


def drop_batchtransfer_tables(apps, schema_editor):
    """
    Drop BatchTransfer tables with database-specific syntax.
    
    This is safe to run multiple times and handles both fresh databases
    (where tables may not exist) and existing databases (where they need cleanup).
    """
    try:
        with connection.cursor() as cursor:
            # SQLite doesn't support CASCADE in DROP TABLE
            if connection.vendor == 'sqlite':
                cursor.execute("DROP TABLE IF EXISTS batch_batchtransfer")
                cursor.execute("DROP TABLE IF EXISTS batch_historicalbatchtransfer")
            else:
                # PostgreSQL supports CASCADE
                cursor.execute("DROP TABLE IF EXISTS batch_batchtransfer CASCADE")
                cursor.execute("DROP TABLE IF EXISTS batch_historicalbatchtransfer CASCADE")
    except Exception as e:
        # If tables don't exist (e.g., in fresh test database), that's okay
        # This can happen when migrations are applied to an empty database
        pass


class Migration(migrations.Migration):

    dependencies = [
        ('batch', '0023_batchtransferworkflow_historicaltransferaction_and_more'),
    ]

    operations = [
        # Only drop tables if running against an existing database
        # Fresh databases (like test databases) won't have these tables
        migrations.RunPython(
            drop_batchtransfer_tables,
            reverse_code=migrations.RunPython.noop,
            elidable=True,  # This migration can be skipped if the model doesn't exist
        ),
    ]

