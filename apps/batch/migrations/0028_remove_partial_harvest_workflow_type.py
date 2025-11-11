# Generated manually on 2025-11-11
# Remove PARTIAL_HARVEST workflow type after verification

from django.db import migrations, models


def check_for_partial_harvest_workflows(apps, schema_editor):
    """
    Check if any workflows use PARTIAL_HARVEST type.
    If found, raise error with instructions for manual migration.
    """
    BatchTransferWorkflow = apps.get_model('batch', 'BatchTransferWorkflow')
    
    partial_harvest_count = BatchTransferWorkflow.objects.filter(
        workflow_type='PARTIAL_HARVEST'
    ).count()
    
    if partial_harvest_count > 0:
        raise Exception(
            f"Found {partial_harvest_count} workflow(s) with type PARTIAL_HARVEST. "
            f"This workflow type is being removed because harvest operations use "
            f"the separate harvest_harvestevent model (direct tube transfer to factory). "
            f"\n\nPlease manually migrate these workflows to CONTAINER_REDISTRIBUTION "
            f"or EMERGENCY_CASCADE, or delete them if they were test data. "
            f"\n\nSQL to view affected workflows:"
            f"\nSELECT id, workflow_number, batch_id, status FROM batch_batchtransferworkflow "
            f"WHERE workflow_type = 'PARTIAL_HARVEST';"
        )
    
    # If we get here, no PARTIAL_HARVEST workflows exist - safe to proceed
    print("✅ No PARTIAL_HARVEST workflows found - safe to remove workflow type")


def reverse_check(apps, schema_editor):
    """No reverse operation needed - this is a safety check only."""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('batch', '0027_remove_historicalbatchtransfer_destination_assignment_and_more'),
    ]

    operations = [
        # First: Check for existing PARTIAL_HARVEST workflows
        migrations.RunPython(
            check_for_partial_harvest_workflows,
            reverse_check
        ),
        
        # Second: Update field choices (removing PARTIAL_HARVEST)
        migrations.AlterField(
            model_name='batchtransferworkflow',
            name='workflow_type',
            field=models.CharField(
                choices=[
                    ('LIFECYCLE_TRANSITION', 'Lifecycle Stage Transition'),
                    ('CONTAINER_REDISTRIBUTION', 'Container Redistribution'),
                    ('EMERGENCY_CASCADE', 'Emergency Cascading Transfer'),
                ],
                default='LIFECYCLE_TRANSITION',
                max_length=30,
            ),
        ),
        
        # Third: Update historical model choices
        migrations.AlterField(
            model_name='historicalbatchtransferworkflow',
            name='workflow_type',
            field=models.CharField(
                choices=[
                    ('LIFECYCLE_TRANSITION', 'Lifecycle Stage Transition'),
                    ('CONTAINER_REDISTRIBUTION', 'Container Redistribution'),
                    ('EMERGENCY_CASCADE', 'Emergency Cascading Transfer'),
                ],
                default='LIFECYCLE_TRANSITION',
                max_length=30,
            ),
        ),
    ]

