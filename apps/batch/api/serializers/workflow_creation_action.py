"""
Serializers for Creation Actions (egg delivery actions).

Handles individual egg delivery actions within a batch creation workflow.
"""
from rest_framework import serializers
from django.utils import timezone

from apps.batch.models import CreationAction, BatchContainerAssignment


class CreationActionSerializer(serializers.ModelSerializer):
    """
    Serializer for creation actions (list and detail views).
    """
    dest_container_name = serializers.CharField(
        source='dest_assignment.container.name',
        read_only=True
    )
    dest_container_type = serializers.CharField(
        source='dest_assignment.container.container_type.name',
        read_only=True
    )
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    delivery_method_display = serializers.CharField(source='get_delivery_method_display', read_only=True, allow_null=True)
    executed_by_username = serializers.CharField(source='executed_by.username', read_only=True, allow_null=True)
    
    # Computed fields
    eggs_actually_received = serializers.SerializerMethodField()
    mortality_rate_percentage = serializers.SerializerMethodField()
    days_since_expected = serializers.SerializerMethodField()
    
    class Meta:
        model = CreationAction
        fields = [
            'id',
            'workflow',
            'action_number',
            'status',
            'status_display',
            'dest_assignment',
            'dest_container_name',
            'dest_container_type',
            'egg_count_planned',
            'egg_count_actual',
            'mortality_on_arrival',
            'eggs_actually_received',
            'mortality_rate_percentage',
            'expected_delivery_date',
            'actual_delivery_date',
            'days_since_expected',
            'delivery_method',
            'delivery_method_display',
            'water_temp_on_arrival',
            'egg_quality_score',
            'execution_duration_minutes',
            'executed_by_username',
            'notes',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'egg_count_actual',
            'actual_delivery_date',
            'executed_by_username',
            'created_at',
            'updated_at',
        ]
    
    def get_eggs_actually_received(self, obj):
        """Calculate eggs actually added to container (planned - mortality)."""
        if obj.status == 'COMPLETED':
            return obj.egg_count_actual
        return None
    
    def get_mortality_rate_percentage(self, obj):
        """Calculate mortality rate percentage."""
        if obj.status == 'COMPLETED' and obj.egg_count_planned > 0:
            return round((obj.mortality_on_arrival / obj.egg_count_planned) * 100, 2)
        return None
    
    def get_days_since_expected(self, obj):
        """Calculate days since expected delivery (negative if early, positive if late)."""
        if obj.actual_delivery_date:
            delta = (obj.actual_delivery_date - obj.expected_delivery_date).days
            return delta
        elif obj.status in ['PENDING', 'FAILED']:
            # For pending actions, show days until expected
            delta = (timezone.now().date() - obj.expected_delivery_date).days
            return delta if delta > 0 else None  # Only show if overdue
        return None


class CreationActionCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating a new creation action.
    
    Creates a placeholder destination assignment if needed.
    """
    dest_container_id = serializers.IntegerField(write_only=True)
    
    class Meta:
        model = CreationAction
        fields = [
            'id',
            'workflow',
            'action_number',
            'dest_container_id',
            'egg_count_planned',
            'expected_delivery_date',
            'notes',
        ]
        read_only_fields = ['id']
    
    def validate(self, attrs):
        """
        Validate action creation.
        
        Checks:
        - Workflow can accept actions
        - No mixed batch conflict (container occupied beyond expected date)
        """
        workflow = attrs.get('workflow')
        dest_container_id = attrs.get('dest_container_id')
        expected_delivery_date = attrs.get('expected_delivery_date')
        
        # Check if workflow can accept actions
        if not workflow.can_add_actions():
            raise serializers.ValidationError({
                'workflow': f'Cannot add actions to workflow in {workflow.status} status'
            })
        
        # Check for mixed batch conflict
        from apps.infrastructure.models import Container
        from apps.batch.models import BatchContainerAssignment
        
        dest_container = Container.objects.get(id=dest_container_id)
        
        # Get active assignments in destination container
        active_assignments = BatchContainerAssignment.objects.filter(
            container=dest_container,
            is_active=True
        ).exclude(batch=workflow.batch)
        
        for assignment in active_assignments:
            expected_departure = assignment.expected_departure_date
            if expected_departure and expected_delivery_date <= expected_departure:
                # Conflict: trying to deliver eggs while another batch still there
                raise serializers.ValidationError({
                    'dest_container_id': (
                        f'Container {dest_container.name} is occupied by batch '
                        f'{assignment.batch.batch_number} until {expected_departure}. '
                        f'Choose a different container or adjust your delivery date to after {expected_departure}.'
                    )
                })
        
        return attrs
    
    def create(self, validated_data):
        """
        Create action and placeholder destination assignment.
        
        The assignment starts with population=0 and is_active=False.
        It will be updated when the action is executed.
        """
        from django.db import transaction
        
        workflow = validated_data['workflow']
        dest_container_id = validated_data.pop('dest_container_id')
        
        with transaction.atomic():
            # Get or create placeholder destination assignment
            dest_assignment, created = BatchContainerAssignment.objects.get_or_create(
                batch=workflow.batch,
                container_id=dest_container_id,
                lifecycle_stage=workflow.batch.lifecycle_stage,
                defaults={
                    'population_count': 0,
                    'biomass_kg': '0.00',
                    'assignment_date': workflow.planned_start_date,
                    'is_active': False,  # Will become True on execution
                    'notes': f'Placeholder for workflow {workflow.workflow_number}',
                }
            )
            
            # Create the action
            action = CreationAction.objects.create(
                dest_assignment=dest_assignment,
                **validated_data
            )
            
            # Update workflow total_actions count
            workflow.total_actions += 1
            workflow.save(update_fields=['total_actions'])
            
            return action


class CreationActionExecuteSerializer(serializers.Serializer):
    """
    Serializer for executing a creation action (delivery).
    
    Records actual delivery details and updates populations.
    """
    mortality_on_arrival = serializers.IntegerField(
        min_value=0,
        required=True,
        help_text="Number of eggs DOA (dead on arrival)"
    )
    delivery_method = serializers.ChoiceField(
        choices=CreationAction.DELIVERY_METHOD_CHOICES,
        required=False,
        allow_null=True
    )
    water_temp_on_arrival = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        required=False,
        allow_null=True,
        help_text="Water temperature in °C"
    )
    egg_quality_score = serializers.IntegerField(
        min_value=1,
        max_value=5,
        required=False,
        allow_null=True,
        help_text="Quality score 1-5 (1=poor, 5=excellent)"
    )
    execution_duration_minutes = serializers.IntegerField(
        min_value=1,
        required=False,
        allow_null=True,
        help_text="Duration of delivery operation in minutes"
    )
    notes = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="Notes about delivery conditions, etc."
    )
    
    def validate_mortality_on_arrival(self, value):
        """Ensure mortality doesn't exceed planned eggs."""
        action = self.context.get('action')
        if action and value > action.egg_count_planned:
            raise serializers.ValidationError(
                f"Mortality ({value}) cannot exceed planned eggs ({action.egg_count_planned})"
            )
        return value


class CreationActionSkipSerializer(serializers.Serializer):
    """Serializer for skipping an action."""
    reason = serializers.CharField(required=True, min_length=10)
    
    def validate_reason(self, value):
        """Ensure reason is meaningful."""
        if len(value.strip()) < 10:
            raise serializers.ValidationError(
                "Skip reason must be at least 10 characters"
            )
        return value.strip()

