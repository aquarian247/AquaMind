# Generated migration for growth analysis performance optimization
# Issue: Growth analysis recomputation times out after 300s per batch
# Solution: Add composite indexes for common query patterns

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('batch', '0037_add_assignment_to_mortality_event'),
    ]

    operations = [
        # MortalityEvent: Used in _get_mortality() - filter by assignment and event_date
        migrations.AddIndex(
            model_name='mortalityevent',
            index=models.Index(
                fields=['assignment', 'event_date'],
                name='idx_mortality_assign_date'
            ),
        ),
        # TransferAction: Used in _get_placements() - filter by dest_assignment, execution_date, status
        migrations.AddIndex(
            model_name='transferaction',
            index=models.Index(
                fields=['dest_assignment', 'actual_execution_date', 'status'],
                name='idx_transfer_dest_date_status'
            ),
        ),
        # TransferAction: Also used in _detect_anchors() - source_assignment queries
        migrations.AddIndex(
            model_name='transferaction',
            index=models.Index(
                fields=['source_assignment', 'actual_execution_date', 'status'],
                name='idx_transfer_src_date_status'
            ),
        ),
        # BatchContainerAssignment: Used to get overlapping assignments
        migrations.AddIndex(
            model_name='batchcontainerassignment',
            index=models.Index(
                fields=['batch', 'assignment_date'],
                name='idx_bca_batch_assign_date'
            ),
        ),
        migrations.AddIndex(
            model_name='batchcontainerassignment',
            index=models.Index(
                fields=['batch', 'departure_date'],
                name='idx_bca_batch_depart_date'
            ),
        ),
    ]
















