# Generated migration to complete pinned_scenario -> pinned_projection_run migration

from django.db import migrations


class Migration(migrations.Migration):
    """
    Remove the deprecated pinned_scenario field from Batch model.
    
    This completes the migration to pinned_projection_run, which provides
    version control for scenario projections. Data migration was completed
    in 0040_migrate_pinned_scenario_to_run.py.
    """

    dependencies = [
        ("batch", "0041_add_planned_activity_link"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="batch",
            name="pinned_scenario",
        ),
        migrations.RemoveField(
            model_name="historicalbatch",
            name="pinned_scenario",
        ),
    ]

