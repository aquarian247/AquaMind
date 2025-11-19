# Generated migration for batch growth assimilation - Issue #112
# Phase 1: Add weighing flags and links to Treatment model

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('health', '0026_remove_legacy_score_descriptions'),
    ]

    operations = [
        migrations.AddField(
            model_name='treatment',
            name='includes_weighing',
            field=models.BooleanField(
                default=False,
                help_text="Whether this treatment included fish weighing. Used as anchor for daily state calculations.",
                verbose_name="Includes Weighing"
            ),
        ),
        migrations.AddField(
            model_name='treatment',
            name='sampling_event',
            field=models.ForeignKey(
                blank=True,
                help_text="Linked health sampling event, if weights were recorded.",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='linked_treatments',
                to='health.healthsamplingevent',
                verbose_name="Sampling Event"
            ),
        ),
        migrations.AddField(
            model_name='treatment',
            name='journal_entry',
            field=models.ForeignKey(
                blank=True,
                help_text="Linked journal entry for traceability.",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='linked_treatments',
                to='health.journalentry',
                verbose_name="Journal Entry"
            ),
        ),
        # Add to historical table as well
        migrations.AddField(
            model_name='historicaltreatment',
            name='includes_weighing',
            field=models.BooleanField(
                default=False,
                help_text="Whether this treatment included fish weighing. Used as anchor for daily state calculations.",
                verbose_name="Includes Weighing"
            ),
        ),
        migrations.AddField(
            model_name='historicaltreatment',
            name='sampling_event',
            field=models.ForeignKey(
                blank=True,
                db_constraint=False,
                help_text="Linked health sampling event, if weights were recorded.",
                null=True,
                on_delete=django.db.models.deletion.DO_NOTHING,
                related_name='+',
                to='health.healthsamplingevent',
                verbose_name="Sampling Event"
            ),
        ),
        migrations.AddField(
            model_name='historicaltreatment',
            name='journal_entry',
            field=models.ForeignKey(
                blank=True,
                db_constraint=False,
                help_text="Linked journal entry for traceability.",
                null=True,
                on_delete=django.db.models.deletion.DO_NOTHING,
                related_name='+',
                to='health.journalentry',
                verbose_name="Journal Entry"
            ),
        ),
    ]

