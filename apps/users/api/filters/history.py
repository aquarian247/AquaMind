"""
History filters for Users models.

These filters provide date range, user, and change type filtering
for historical records across all users models.
"""

import django_filters as filters
from aquamind.utils.history_utils import HistoryFilter
from apps.users.models import UserProfile


class UserProfileHistoryFilter(HistoryFilter):
    """Filter class for UserProfile historical records."""

    class Meta:
        model = UserProfile.history.model
        fields = ['user', 'geography', 'subsidiary', 'role']
