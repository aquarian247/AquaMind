"""
History serializers for Users models.

These serializers provide read-only access to historical records
for all users models, exposing change tracking information.
"""

from rest_framework import serializers
from aquamind.utils.history_utils import HistorySerializer
from apps.users.models import UserProfile


class UserProfileHistorySerializer(HistorySerializer):
    """History serializer for UserProfile model."""

    class Meta:
        model = UserProfile.history.model
        fields = '__all__'
