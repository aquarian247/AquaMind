from django.db import migrations


def _drop_tables_postgresql(cursor, quote_name, table_names):
    for table_name in table_names:
        cursor.execute(
            f"DROP TABLE IF EXISTS {quote_name(table_name)} CASCADE"
        )


def _drop_tables_sqlite(cursor, quote_name, table_names):
    for table_name in table_names:
        cursor.execute(f"DROP TABLE IF EXISTS {quote_name(table_name)}")


def _drop_tables_generic(connection, cursor, quote_name, table_names):
    existing_tables = set(connection.introspection.table_names(cursor))
    for table_name in table_names:
        if table_name in existing_tables:
            cursor.execute(f"DROP TABLE {quote_name(table_name)}")


def drop_legacy_batchtransfer_tables(apps, schema_editor):
    """
    Ensure deprecated BatchTransfer tables are removed on the target DB alias.

    IMPORTANT:
    Use schema_editor.connection (not django.db.connection) so this runs on the
    database currently being migrated (default, migr_dev, test DBs, etc.).
    """
    connection = schema_editor.connection
    quote_name = connection.ops.quote_name

    # Historical table can exist independently in drifted DBs.
    legacy_tables = [
        "batch_historicalbatchtransfer",
        "batch_batchtransfer",
    ]

    with connection.cursor() as cursor:
        if connection.vendor == "postgresql":
            _drop_tables_postgresql(cursor, quote_name, legacy_tables)
        elif connection.vendor == "sqlite":
            _drop_tables_sqlite(cursor, quote_name, legacy_tables)
        else:
            _drop_tables_generic(
                connection,
                cursor,
                quote_name,
                legacy_tables,
            )


class Migration(migrations.Migration):

    dependencies = [
        ("batch", "0050_batchtransferworkflow_dynamic_completed_at_and_more"),
    ]

    operations = [
        migrations.RunPython(
            drop_legacy_batchtransfer_tables,
            reverse_code=migrations.RunPython.noop,
        ),
    ]
