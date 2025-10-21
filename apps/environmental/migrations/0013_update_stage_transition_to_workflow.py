# Generated migration to update StageTransitionEnvironmental to use BatchTransferWorkflow
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('environmental', '0012_add_history_to_models'),
        ('batch', '0024_remove_batchtransfer'),
    ]

    operations = [
        # Since there's no data, we can safely drop and recreate
        migrations.RemoveField(
            model_name='stagetransitionenvironmental',
            name='batch_transfer',
        ),
        migrations.RemoveField(
            model_name='historicalstagetransitionenvironmental',
            name='batch_transfer',
        ),
        migrations.AddField(
            model_name='stagetransitionenvironmental',
            name='batch_transfer_workflow',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='environmental_conditions',
                to='batch.batchtransferworkflow'
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='historicalstagetransitionenvironmental',
            name='batch_transfer_workflow',
            field=models.ForeignKey(
                blank=True,
                db_constraint=False,
                null=True,
                on_delete=django.db.models.deletion.DO_NOTHING,
                related_name='+',
                to='batch.batchtransferworkflow'
            ),
        ),
    ]

