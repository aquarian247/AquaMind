from rest_framework import serializers
from apps.planning.models import PlannedActivity


class PlannedActivitySerializer(serializers.ModelSerializer):
    """Serializer for PlannedActivity model."""
    
    # Read-only computed fields
    activity_type_display = serializers.CharField(
        source='get_activity_type_display',
        read_only=True
    )
    status_display = serializers.CharField(
        source='get_status_display',
        read_only=True
    )
    is_overdue = serializers.ReadOnlyField()
    
    # Nested representations for foreign keys
    created_by_name = serializers.SerializerMethodField()
    completed_by_name = serializers.SerializerMethodField()
    container_name = serializers.CharField(
        source='container.name',
        read_only=True,
        allow_null=True
    )
    batch_number = serializers.CharField(
        source='batch.batch_number',
        read_only=True
    )
    scenario_name = serializers.CharField(
        source='scenario.name',
        read_only=True
    )
    
    class Meta:
        model = PlannedActivity
        fields = [
            'id',
            'scenario',
            'scenario_name',
            'batch',
            'batch_number',
            'activity_type',
            'activity_type_display',
            'due_date',
            'status',
            'status_display',
            'container',
            'container_name',
            'notes',
            'created_by',
            'created_by_name',
            'created_at',
            'updated_at',
            'completed_at',
            'completed_by',
            'completed_by_name',
            'transfer_workflow',
            'is_overdue',
        ]
        read_only_fields = [
            'id',
            'created_by',
            'created_at',
            'updated_at',
            'completed_at',
            'completed_by',
            'transfer_workflow',
        ]
    
    def get_created_by_name(self, obj):
        """Get the full name of the creator."""
        if obj.created_by:
            return obj.created_by.get_full_name() or obj.created_by.username
        return None
    
    def get_completed_by_name(self, obj):
        """Get the full name of the completer."""
        if obj.completed_by:
            return obj.completed_by.get_full_name() or obj.completed_by.username
        return None
    
    def create(self, validated_data):
        """Override create to set created_by from request user."""
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)

