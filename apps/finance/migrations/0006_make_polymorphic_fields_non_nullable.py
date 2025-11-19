# Migration to make content_type and object_id fields non-nullable in IntercompanyTransaction

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('finance', '0005_transfer_finance_integration_phase1'),
    ]

    operations = [
        # Make content_type non-nullable on main model
        migrations.AlterField(
            model_name='intercompanytransaction',
            name='content_type',
            field=models.ForeignKey(
                help_text='Source model type (HarvestEvent or BatchTransferWorkflow)',
                limit_choices_to=models.Q(
                    app_label='harvest', model='harvestevent'
                ) | models.Q(
                    app_label='batch', model='batchtransferworkflow'
                ),
                on_delete=models.PROTECT,
                to='contenttypes.contenttype',
            ),
        ),

        # Make object_id non-nullable on main model
        migrations.AlterField(
            model_name='intercompanytransaction',
            name='object_id',
            field=models.PositiveIntegerField(
                help_text='Source object ID',
            ),
        ),

        # For historical model, keep nullable since historical records might have been created before these fields existed
        migrations.AlterField(
            model_name='historicalintercompanytransaction',
            name='content_type',
            field=models.ForeignKey(
                blank=True,
                db_constraint=False,
                help_text='Source model type (HarvestEvent or BatchTransferWorkflow)',
                null=True,
                on_delete=models.DO_NOTHING,
                related_name='+',
                to='contenttypes.contenttype',
            ),
        ),

        # Keep object_id nullable on historical model
        migrations.AlterField(
            model_name='historicalintercompanytransaction',
            name='object_id',
            field=models.PositiveIntegerField(
                blank=True,
                help_text='Source object ID',
                null=True,
            ),
        ),
    ]
















