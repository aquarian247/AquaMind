"""
Serializers for Batch Creation Workflows.

Handles creation of new batches from eggs (external or internal broodstock).
"""
from rest_framework import serializers
from decimal import Decimal

from apps.batch.models import BatchCreationWorkflow, Batch, LifeCycleStage
from apps.broodstock.models import EggProduction, EggSupplier
from apps.batch.api.serializers.batch import BatchSerializer


class BatchCreationWorkflowListSerializer(serializers.ModelSerializer):
    """
    Serializer for list view of batch creation workflows.
    
    Includes basic info for table display.
    """
    batch_number = serializers.CharField(source='batch.batch_number', read_only=True)
    species_name = serializers.CharField(source='batch.species.name', read_only=True)
    lifecycle_stage_name = serializers.CharField(source='batch.lifecycle_stage.name', read_only=True)
    egg_source_display = serializers.CharField(source='get_egg_source_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    created_by_username = serializers.CharField(source='created_by.username', read_only=True, allow_null=True)
    
    class Meta:
        model = BatchCreationWorkflow
        fields = [
            'id',
            'workflow_number',
            'batch',
            'batch_number',
            'species_name',
            'lifecycle_stage_name',
            'status',
            'status_display',
            'egg_source_type',
            'egg_source_display',
            'total_eggs_planned',
            'total_eggs_received',
            'total_mortality_on_arrival',
            'total_actions',
            'actions_completed',
            'progress_percentage',
            'planned_start_date',
            'actual_start_date',
            'planned_completion_date',
            'actual_completion_date',
            'created_by_username',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'workflow_number',
            'total_eggs_received',
            'total_mortality_on_arrival',
            'total_actions',
            'actions_completed',
            'progress_percentage',
            'actual_start_date',
            'actual_completion_date',
            'created_at',
            'updated_at',
        ]


class BatchCreationWorkflowDetailSerializer(serializers.ModelSerializer):
    """
    Detailed serializer for batch creation workflow.
    
    Includes nested batch info, source details, and all fields.
    """
    batch_detail = BatchSerializer(source='batch', read_only=True)
    egg_source_display = serializers.CharField(source='get_egg_source_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    # Source info
    egg_production_detail = serializers.SerializerMethodField()
    external_supplier_detail = serializers.SerializerMethodField()
    
    # User attribution
    created_by_username = serializers.CharField(source='created_by.username', read_only=True, allow_null=True)
    cancelled_by_username = serializers.CharField(source='cancelled_by.username', read_only=True, allow_null=True)
    
    # Computed fields
    mortality_percentage = serializers.SerializerMethodField()
    estimated_total_cost = serializers.SerializerMethodField()
    
    class Meta:
        model = BatchCreationWorkflow
        fields = '__all__'
        read_only_fields = [
            'id',
            'workflow_number',
            'total_eggs_received',
            'total_mortality_on_arrival',
            'total_actions',
            'actions_completed',
            'progress_percentage',
            'actual_start_date',
            'actual_completion_date',
            'cancelled_at',
            'cancelled_by',
            'created_at',
            'updated_at',
        ]
    
    def get_egg_production_detail(self, obj):
        """Return egg production details if internal source."""
        if obj.egg_production:
            return {
                'id': obj.egg_production.id,
                'production_date': obj.egg_production.production_date,
                'estimated_egg_count': obj.egg_production.estimated_egg_count,
                # Add more fields as needed
            }
        return None
    
    def get_external_supplier_detail(self, obj):
        """Return supplier details if external source."""
        if obj.external_supplier:
            return {
                'id': obj.external_supplier.id,
                'name': obj.external_supplier.name,
                'country': obj.external_supplier.country,
                # Add more fields as needed
            }
        return None
    
    def get_mortality_percentage(self, obj):
        """Calculate mortality percentage."""
        total_delivered = obj.total_eggs_received + obj.total_mortality_on_arrival
        if total_delivered > 0:
            return round((obj.total_mortality_on_arrival / total_delivered) * 100, 2)
        return 0.0
    
    def get_estimated_total_cost(self, obj):
        """Calculate estimated total cost for external eggs."""
        if obj.egg_source_type == 'EXTERNAL' and obj.external_cost_per_thousand:
            cost_per_egg = obj.external_cost_per_thousand / 1000
            return float(obj.total_eggs_planned * Decimal(str(cost_per_egg)))
        return None


class BatchCreationWorkflowCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating a new batch creation workflow.
    
    Creates the batch automatically with status PLANNED.
    """
    # Batch creation fields
    batch_number = serializers.CharField(write_only=True)
    species_id = serializers.IntegerField(write_only=True)
    lifecycle_stage_id = serializers.IntegerField(write_only=True)
    
    class Meta:
        model = BatchCreationWorkflow
        fields = [
            # Workflow fields
            'id',
            'workflow_number',
            'status',
            'egg_source_type',
            'egg_production',
            'external_supplier',
            'external_supplier_batch_number',
            'external_cost_per_thousand',
            'total_eggs_planned',
            'planned_start_date',
            'planned_completion_date',
            'notes',
            # Batch creation fields
            'batch_number',
            'species_id',
            'lifecycle_stage_id',
        ]
        read_only_fields = ['id', 'workflow_number', 'status']
    
    def validate(self, attrs):
        """Validate egg source consistency."""
        egg_source_type = attrs.get('egg_source_type')
        
        if egg_source_type == 'INTERNAL':
            if not attrs.get('egg_production'):
                raise serializers.ValidationError({
                    'egg_production': 'Internal egg source requires egg_production'
                })
            if attrs.get('external_supplier'):
                raise serializers.ValidationError({
                    'external_supplier': 'Internal egg source cannot have external_supplier'
                })
        elif egg_source_type == 'EXTERNAL':
            if not attrs.get('external_supplier'):
                raise serializers.ValidationError({
                    'external_supplier': 'External egg source requires external_supplier'
                })
            if attrs.get('egg_production'):
                raise serializers.ValidationError({
                    'egg_production': 'External egg source cannot have egg_production'
                })
        
        return attrs
    
    def create(self, validated_data):
        """
        Create workflow and batch together.
        
        Batch is created with status PLANNED.
        Workflow number is auto-generated.
        """
        from django.db import transaction
        from datetime import date
        
        # Extract batch creation fields
        batch_number = validated_data.pop('batch_number')
        species_id = validated_data.pop('species_id')
        lifecycle_stage_id = validated_data.pop('lifecycle_stage_id')
        
        with transaction.atomic():
            # Create batch with PLANNED status
            batch = Batch.objects.create(
                batch_number=batch_number,
                species_id=species_id,
                lifecycle_stage_id=lifecycle_stage_id,
                status='PLANNED',
                batch_type='STANDARD',
                start_date=validated_data.get('planned_start_date', date.today()),
                notes=f"Created via creation workflow"
            )
            
            # Generate workflow number (CRT-YYYY-XXX format)
            year = date.today().year
            count = BatchCreationWorkflow.objects.filter(
                workflow_number__startswith=f'CRT-{year}-'
            ).count() + 1
            workflow_number = f'CRT-{year}-{count:03d}'
            
            # Create workflow
            workflow = BatchCreationWorkflow.objects.create(
                workflow_number=workflow_number,
                batch=batch,
                status='DRAFT',
                **validated_data
            )
            
            # Create broodstock linkage if internal eggs
            if workflow.egg_source_type == 'INTERNAL' and workflow.egg_production:
                from apps.broodstock.models import BatchParentage
                BatchParentage.objects.create(
                    batch=batch,
                    egg_production=workflow.egg_production,
                    parentage_type='FULL',  # Assuming full parentage from egg production
                    notes=f"Created via workflow {workflow.workflow_number}"
                )
            
            return workflow


class BatchCreationWorkflowCancelSerializer(serializers.Serializer):
    """Serializer for cancelling a workflow."""
    reason = serializers.CharField(required=True, min_length=10)
    
    def validate_reason(self, value):
        """Ensure reason is meaningful."""
        if len(value.strip()) < 10:
            raise serializers.ValidationError(
                "Cancellation reason must be at least 10 characters"
            )
        return value.strip()

