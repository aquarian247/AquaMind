# Generated migration to remove deprecated BatchTransfer model
from django.db import migrations, connection


def drop_batchtransfer_tables(apps, schema_editor):
    """
    Drop BatchTransfer tables if they exist.
    
    This checks for table existence before dropping to avoid errors in fresh databases.
    Safe to run multiple times and handles both existing and fresh databases.
    """
    # Skip if this is a fresh database (tables never existed)
    with connection.cursor() as cursor:
        # Check if tables exist before dropping
        if connection.vendor == 'postgresql':
            # PostgreSQL: Check information_schema
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = 'batch_batchtransfer'
                )
            """)
            table_exists = cursor.fetchone()[0]
            
            if table_exists:
                cursor.execute("DROP TABLE batch_batchtransfer CASCADE")
                cursor.execute("DROP TABLE IF EXISTS batch_historicalbatchtransfer CASCADE")
        
        elif connection.vendor == 'sqlite':
            # SQLite: Check sqlite_master
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='batch_batchtransfer'
            """)
            table_exists = cursor.fetchone()
            
            if table_exists:
                cursor.execute("DROP TABLE batch_batchtransfer")
                cursor.execute("DROP TABLE IF EXISTS batch_historicalbatchtransfer")


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

