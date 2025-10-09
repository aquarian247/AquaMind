"""
Audit Trail Mixins for Django REST Framework

This module provides reusable mixins for capturing change reasons in DRF viewsets
when using django-simple-history. These mixins ensure that all CUD operations
(create, update, delete) include human-readable change reasons for audit trails.

Usage:
    class MyViewSet(HistoryReasonMixin, viewsets.ModelViewSet):
        # The mixin will automatically capture change reasons for:
        # - POST (create): "created via API by {user}"
        # - PUT/PATCH (update): "updated via API by {user}"
        # - DELETE (delete): "deleted via API by {user}"
        pass
"""

from simple_history.utils import update_change_reason
from rest_framework import mixins


class HistoryReasonMixin:
    """
    DRF mixin for capturing change reasons in django-simple-history.

    This mixin automatically updates the change reason on all CUD operations
    performed through the API, providing clear audit trails with user attribution.

    The change reasons follow the pattern: "{action} via API by {username}"
    where action is one of: "created", "updated", "deleted".
    """

    def _reason(self, action: str) -> str:
        """
        Generate a standardized change reason string.

        Args:
            action: The action being performed ("created", "updated", "deleted")

        Returns:
            A formatted change reason string including the user who performed the action
        """
        return f"{action} via API by {self.request.user}"

    def perform_create(self, serializer):
        """
        Override perform_create to capture change reasons for create operations.

        This method saves the instance and updates the change reason
        to indicate it was created via API by the current user.
        
        Compatible with UserAssignmentMixin: Auto-populates user field if viewset has user_field attribute.
        """
        # Check if viewset has a user_field (for UserAssignmentMixin compatibility)
        kwargs = {}
        if hasattr(self, 'user_field') and self.request.user.is_authenticated:
            kwargs[self.user_field] = self.request.user
        
        instance = serializer.save(**kwargs)
        # For new instances, we need to refresh the instance to get the latest historical record
        instance.refresh_from_db()
        if hasattr(instance, 'history') and instance.history.exists():
            latest_history = instance.history.latest()
            if latest_history:
                latest_history.history_change_reason = self._reason("created")
                latest_history.save()
        return instance

    def perform_update(self, serializer):
        """
        Override perform_update to capture change reasons for update operations.

        This method saves the instance and updates the change reason
        to indicate it was updated via API by the current user.
        """
        instance = serializer.save()
        # For updates, the historical record should already exist
        if hasattr(instance, 'history') and instance.history.exists():
            latest_history = instance.history.latest()
            if latest_history:
                latest_history.history_change_reason = self._reason("updated")
                latest_history.save()
        return instance

    def perform_destroy(self, instance):
        """
        Override perform_destroy to capture change reasons for delete operations.

        This method updates the change reason to indicate the instance was deleted
        via API by the current user, then performs the actual deletion.
        """
        # For deletions, update the change reason on the latest historical record
        if hasattr(instance, 'history') and instance.history.exists():
            latest_history = instance.history.latest()
            if latest_history:
                latest_history.history_change_reason = self._reason("deleted")
                latest_history.save()
        instance.delete()
