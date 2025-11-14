# Generated migration for batch growth assimilation - Issue #112
# Phase 1: Add pinned_scenario_id to Batch model

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('batch', '0031_add_measured_fields_to_transferaction'),
        ('scenario', '0001_initial'),  # Ensure scenario app is migrated
    ]

    operations = [
        migrations.AddField(
            model_name='batch',
            name='pinned_scenario',
            field=models.ForeignKey(
                blank=True,
                help_text="Pinned scenario used for daily actual state calculations. Defaults to baseline scenario.",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='pinned_batches',
                to='scenario.scenario',
                verbose_name="Pinned Scenario"
            ),
        ),
        # Add to historical table as well
        migrations.AddField(
            model_name='historicalbatch',
            name='pinned_scenario',
            field=models.ForeignKey(
                blank=True,
                db_constraint=False,
                help_text="Pinned scenario used for daily actual state calculations. Defaults to baseline scenario.",
                null=True,
                on_delete=django.db.models.deletion.DO_NOTHING,
                related_name='+',
                to='scenario.scenario',
                verbose_name="Pinned Scenario"
            ),
        ),
    ]

