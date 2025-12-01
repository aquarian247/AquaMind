"""
Signal handlers for the planning app.

Handles automatic activity generation from templates and workflow completion synchronization.
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from apps.batch.models import Batch, BatchTransferWorkflow
from .models import ActivityTemplate, PlannedActivity


@receiver(post_save, sender=Batch)
def auto_generate_activities_from_templates(sender, instance, created, **kwargs):
    """Auto-generate planned activities when a new batch is created."""
    if not created:
        return  # Only run for new batches
    
    # Get the default scenario for this batch (if exists)
    # Note: Batches may not always have scenarios initially
    default_scenario = instance.scenarios.filter(is_baseline=True).first()
    if not default_scenario:
        return  # No scenario to attach activities to
    
    # Get all active templates with DAY_OFFSET trigger
    templates = ActivityTemplate.objects.filter(
        is_active=True,
        trigger_type='DAY_OFFSET'
    )
    
    # Generate activities
    for template in templates:
        template.generate_activity(
            scenario=default_scenario,
            batch=instance
        )


@receiver(post_save, sender=BatchTransferWorkflow)
def sync_workflow_completion_to_activity(sender, instance, created, **kwargs):
    """Update linked planned activity when workflow completes."""
    if created:
        return  # Only run on updates
    
    if instance.status == 'COMPLETED' and instance.planned_activity:
        activity = instance.planned_activity
        if activity.status != 'COMPLETED':
            # Use the workflow's completed_by, or fall back to initiated_by
            completing_user = instance.completed_by or instance.initiated_by
            activity.mark_completed(user=completing_user)

