# Generated migration to handle BatchTransfer model removal
# The BatchTransfer and HistoricalBatchTransfer tables were already dropped by migration 0024.
# This migration exists only to inform Django that these models no longer exist in the codebase.

from django.db import migrations


def noop_forward(apps, schema_editor):
    """
    No-op forward migration.

    The BatchTransfer and HistoricalBatchTransfer tables were already dropped
    by migration 0024. This migration exists only to inform Django that these
    models no longer exist in the codebase.
    """
    pass


def noop_reverse(apps, schema_editor):
    """No-op reverse migration."""
    pass


class Migration(migrations.Migration):

    dependencies = [
        (
            "batch",
            "0026_remove_historicalbatchtransfer_destination_assignment_and_more",
        ),
    ]

    operations = [
        # Use RunPython no-op instead of RemoveField/DeleteModel operations
        # since the tables were already dropped by migration 0024
        migrations.RunPython(
            noop_forward,
            reverse_code=noop_reverse,
            elidable=True,
        ),
    ]
