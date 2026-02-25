"""
Signal handlers for the planning app.

Handles automatic activity generation from templates and workflow completion
synchronization.
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
    try:
        # Try to get baseline scenario (field may not exist in all versions)
        default_scenario = instance.scenarios.filter(is_baseline=True).first()
    except Exception:
        # If is_baseline field doesn't exist, get first scenario or batch.pinned_scenario
        default_scenario = (
            getattr(instance, 'pinned_scenario', None) or instance.scenarios.first()
        )

    if not default_scenario:
        return  # No scenario to attach activities to

    # Get all active templates with DAY_OFFSET trigger
    templates = ActivityTemplate.objects.filter(
        is_active=True,
        trigger_type='DAY_OFFSET',
    )

    # Generate activities
    for template in templates:
        template.generate_activity(
            scenario=default_scenario,
            batch=instance,
        )


def _find_matching_transfer_activity(workflow):
    candidates = PlannedActivity.objects.filter(
        batch=workflow.batch,
        activity_type='TRANSFER',
        status__in=['PENDING', 'IN_PROGRESS'],
        transfer_workflow__isnull=True,
    )
    if not candidates.exists():
        return None

    target_date = workflow.planned_start_date or workflow.actual_completion_date
    if target_date:
        activity = min(
            candidates,
            key=lambda activity: abs((activity.due_date - target_date).days),
        )
        if abs((activity.due_date - target_date).days) > 3:
            return None
        return activity

    return candidates.order_by('due_date').first()


def _is_legacy_migration_workflow(workflow):
    """Return True when workflow originates from legacy FishTalk migration."""
    workflow_number = (workflow.workflow_number or "").upper()
    if (
        workflow_number.startswith("FT-TRF-")
        or workflow_number.startswith("FT-STG-")
    ):
        return True

    notes = (workflow.notes or "").lower()
    return (
        "fishtalk operationid=" in notes
        or "fishtalk stage transition" in notes
        or "fishtalk migration" in notes
    )


def _resolve_completed_transfer_activity(workflow):
    """Resolve activity for a completed workflow under migration guardrails."""
    if workflow.planned_activity:
        return workflow.planned_activity
    if _is_legacy_migration_workflow(workflow):
        return None
    return _find_matching_transfer_activity(workflow)


def _attach_workflow_to_activity(activity, workflow):
    """Set transfer_workflow only when unset."""
    if activity.transfer_workflow_id:
        return
    activity.transfer_workflow = workflow
    activity.save(update_fields=['transfer_workflow', 'updated_at'])


def _complete_activity_from_workflow(activity, workflow):
    """Mark activity completed when workflow is completed."""
    if activity.status == 'COMPLETED':
        return
    completing_user = workflow.completed_by or workflow.initiated_by
    activity.mark_completed(user=completing_user)


@receiver(post_save, sender=BatchTransferWorkflow)
def sync_workflow_completion_to_activity(sender, instance, created, **kwargs):
    """Update linked planned activity when workflow completes."""
    if created or instance.status != 'COMPLETED':
        return

    activity = _resolve_completed_transfer_activity(instance)
    if not activity:
        return
    _attach_workflow_to_activity(activity, instance)
    _complete_activity_from_workflow(activity, instance)

