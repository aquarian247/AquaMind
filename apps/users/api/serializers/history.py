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

    # Include user information from the related User model
    username = serializers.CharField(source='user.username', read_only=True, help_text="Username of the user")
    email = serializers.EmailField(source='user.email', read_only=True, help_text="Email address of the user")
    user_full_name = serializers.CharField(source='user.full_name', read_only=True, help_text="Full name from User model")

    class Meta:
        model = UserProfile.history.model
        fields = [
            # History fields
            'history_user',
            'history_date',
            'history_type',
            'history_change_reason',

            # UserProfile fields
            'id',
            'full_name',
            'phone',
            'profile_picture',
            'job_title',
            'department',
            'geography',
            'subsidiary',
            'role',
            'language_preference',
            'date_format_preference',
            'created_at',
            'updated_at',
            'user',

            # Custom user fields
            'username',
            'email',
            'user_full_name',
        ]
