# Generated manually
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('batch', '0002_add_multicontainer_models'),
    ]

    operations = [
        # Update BatchTransfer options
        migrations.AlterModelOptions(
            name='batchtransfer',
            options={'ordering': ['-transfer_date']},
        ),
        
        # Add is_emergency_mixing field
        migrations.AddField(
            model_name='batchtransfer',
            name='is_emergency_mixing',
            field=models.BooleanField(default=False, help_text='Whether this was an emergency mixing/transfer'),
        ),
        
        # Update transfer_type choices
        migrations.AlterField(
            model_name='batchtransfer',
            name='transfer_type',
            field=models.CharField(choices=[('CONTAINER', 'Container Transfer'), ('LIFECYCLE', 'Lifecycle Stage Change'), ('SPLIT', 'Batch Split'), ('MERGE', 'Batch Merge'), ('MIXED_TRANSFER', 'Mixed Batch Transfer')], max_length=20),
        ),
        
        # Update destination_batch field
        migrations.AlterField(
            model_name='batchtransfer',
            name='destination_batch',
            field=models.ForeignKey(blank=True, help_text='Destination batch for merges or new batch for splits; may be null for simple transfers', null=True, on_delete=django.db.models.deletion.PROTECT, related_name='transfers_in', to='batch.batch'),
        ),
        
        # Add source_assignment field
        migrations.AddField(
            model_name='batchtransfer',
            name='source_assignment',
            field=models.ForeignKey(blank=True, help_text='Source batch-container assignment', null=True, on_delete=django.db.models.deletion.PROTECT, related_name='transfers_as_source', to='batch.batchcontainerassignment'),
        ),
        
        # Add destination_assignment field
        migrations.AddField(
            model_name='batchtransfer',
            name='destination_assignment',
            field=models.ForeignKey(blank=True, help_text='Destination batch-container assignment', null=True, on_delete=django.db.models.deletion.PROTECT, related_name='transfers_as_destination', to='batch.batchcontainerassignment'),
        ),
    ]
