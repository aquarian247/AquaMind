# Generated migration to update StageTransitionEnvironmental to use BatchTransferWorkflow
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('environmental', '0012_add_history_to_models'),
        ('batch', '0024_remove_batchtransfer'),
    ]

    operations = [
        # The initial migration was updated to use batch_transfer_workflow directly,
        # so we don't need to remove the old field. Just ensure the field exists with correct properties.
        migrations.AlterField(
            model_name='stagetransitionenvironmental',
            name='batch_transfer_workflow',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='environmental_conditions',
                to='batch.batchtransferworkflow'
            ),
        ),
        migrations.AlterField(
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

