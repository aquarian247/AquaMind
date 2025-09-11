"""
History viewsets for Users models.

These viewsets provide read-only access to historical records
for all users models with filtering and pagination.
"""

from aquamind.utils.history_utils import HistoryViewSet
from rest_framework.viewsets import ReadOnlyModelViewSet
from apps.users.models import UserProfile
from ..serializers.history import UserProfileHistorySerializer
from ..filters.history import UserProfileHistoryFilter


class UserProfileHistoryViewSet(HistoryViewSet, ReadOnlyModelViewSet):
    """ViewSet for UserProfile historical records."""
    queryset = UserProfile.history.all()
    serializer_class = UserProfileHistorySerializer
    filterset_class = UserProfileHistoryFilter
