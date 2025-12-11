from rest_framework import serializers
from apps.planning.models import ActivityTemplate


class ActivityTemplateSerializer(serializers.ModelSerializer):
    """Serializer for ActivityTemplate model."""
    
    activity_type_display = serializers.CharField(
        source='get_activity_type_display',
        read_only=True
    )
    trigger_type_display = serializers.CharField(
        source='get_trigger_type_display',
        read_only=True
    )
    
    class Meta:
        model = ActivityTemplate
        fields = [
            'id',
            'name',
            'description',
            'activity_type',
            'activity_type_display',
            'trigger_type',
            'trigger_type_display',
            'day_offset',
            'weight_threshold_g',
            'target_lifecycle_stage',
            'notes_template',
            'is_active',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']







