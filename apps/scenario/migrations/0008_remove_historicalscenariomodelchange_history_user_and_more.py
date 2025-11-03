# Generated migration to handle historical scenario model removal
# The HistoricalScenario and HistoricalScenarioModelChange models were already removed.
# This migration exists only to inform Django that these models no longer exist in the codebase.

from django.db import migrations


def noop_forward(apps, schema_editor):
    """
    No-op forward migration.

    The HistoricalScenario and HistoricalScenarioModelChange models were already
    removed from the codebase. This migration exists only to inform Django that
    these models no longer exist.
    """
    pass


def noop_reverse(apps, schema_editor):
    """No-op reverse migration."""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("scenario", "0007_remove_historicalscenariomodelchange_history_user_and_more"),
    ]

    operations = [
        # Use RunPython no-op since the models were already removed
        migrations.RunPython(
            noop_forward,
            reverse_code=noop_reverse,
            elidable=True,
        ),
    ]
