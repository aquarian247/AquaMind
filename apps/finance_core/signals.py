"""Finance-core signal handlers."""

from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.batch.models import BatchContainerAssignment
from apps.finance_core.services.cost_centers import ensure_cost_center_for_assignment


@receiver(post_save, sender=BatchContainerAssignment)
def ensure_batch_cost_project(sender, instance, created, **kwargs):
    """Auto-create finance-core project links as batches are assigned into biology."""

    if not created:
        return
    ensure_cost_center_for_assignment(instance)
