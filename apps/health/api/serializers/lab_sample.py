"""
Lab sample serializers for health monitoring.

This module defines serializers for lab sample models, including
SampleType and HealthLabSample.
"""

from rest_framework import serializers

from apps.batch.models import Batch, BatchContainerAssignment
from apps.infrastructure.models import Container
from ...models import SampleType, HealthLabSample
from ..utils import (
    validate_date_order,
    HealthDecimalFieldsMixin, UserAssignmentMixin
)
from .base import HealthBaseSerializer


class SampleTypeSerializer(HealthBaseSerializer):
    """Serializer for the SampleType model.
    
    Uses HealthBaseSerializer for consistent error handling and field management.
    """
    class Meta:
        model = SampleType
        fields = ['id', 'name', 'description']


class HealthLabSampleSerializer(HealthDecimalFieldsMixin, UserAssignmentMixin, HealthBaseSerializer):
    """
    Serializer for the HealthLabSample model.
    
    Handles creating lab samples with historical batch-container assignment lookup
    based on the sample date.
    
    Uses HealthBaseSerializer for consistent error handling and field management.
    Includes HealthDecimalFieldsMixin for decimal field validation and
    UserAssignmentMixin for automatic user assignment.
    """
    # Fields for assignment lookup
    batch_id = serializers.IntegerField(write_only=True)
    container_id = serializers.IntegerField(write_only=True)
    
    # Read-only fields for nested data display
    batch_number = serializers.SerializerMethodField()
    container_name = serializers.SerializerMethodField()
    sample_type_name = serializers.SerializerMethodField()
    recorded_by_username = serializers.SerializerMethodField()
    batch_container_assignment_details = serializers.SerializerMethodField()

    class Meta:
        model = HealthLabSample
        fields = [
            'id', 'batch_container_assignment', 'batch_id', 'container_id',
            'sample_type', 'sample_date', 'date_sent_to_lab', 'date_results_received',
            'lab_reference_id', 'findings_summary', 'quantitative_results',
            'attachment', 'notes', 'recorded_by',
            'created_at', 'updated_at',
            'batch_number', 'container_name', 'sample_type_name', 'recorded_by_username',
            'batch_container_assignment_details'
        ]
        read_only_fields = [
            'id', 'batch_container_assignment', 'created_at', 'updated_at',
            'batch_number', 'container_name', 'sample_type_name', 'recorded_by_username',
            'batch_container_assignment_details'
        ]

    def get_batch_number(self, obj):
        """Get the batch number from the assignment.

        Args:
            obj (HealthLabSample): The lab sample instance.

        Returns:
            str or None: The batch number, or None if not available.
        """
        if obj.batch_container_assignment and obj.batch_container_assignment.batch:
            return obj.batch_container_assignment.batch.batch_number
        return None

    def get_container_name(self, obj):
        """Get the container name from the assignment.

        Args:
            obj (HealthLabSample): The lab sample instance.

        Returns:
            str or None: The container name, or None if not available.
        """
        if obj.batch_container_assignment and obj.batch_container_assignment.container:
            return obj.batch_container_assignment.container.name
        return None

    def get_sample_type_name(self, obj):
        """Get the sample type name.

        Args:
            obj (HealthLabSample): The lab sample instance.

        Returns:
            str or None: The sample type name, or None if not available.
        """
        if obj.sample_type:
            return obj.sample_type.name
        return None

    def get_recorded_by_username(self, obj):
        """Get the username of the user who recorded the sample.

        Args:
            obj (HealthLabSample): The lab sample instance.

        Returns:
            str or None: The username, or None if not available.
        """
        if obj.recorded_by:
            return obj.recorded_by.username
        return None
        
    def get_batch_container_assignment_details(self, obj):
        """Get details of the batch container assignment.

        Args:
            obj (HealthLabSample): The lab sample instance.

        Returns:
            dict or None: A dictionary with assignment details, or None.
        """
        if obj.batch_container_assignment:
            return {
                'assignment_id': obj.batch_container_assignment.id,
                'batch_id': obj.batch_container_assignment.batch_id,
                'container_id': obj.batch_container_assignment.container_id,
                'assignment_date': obj.batch_container_assignment.assignment_date,
                'is_active': obj.batch_container_assignment.is_active
            }
        return None

    def validate(self, data):
        """Validate lab sample data and resolve historical assignment.

        This method finds the BatchContainerAssignment active on the sample_date,
        ensuring historical accuracy for lab results received later. It also
        validates date orders and checks if the sample_date is within the
        batch's lifecycle.

        Args:
            data (dict): The data to validate, including batch_id, container_id,
                         and sample_date.

        Returns:
            dict: The validated data, with 'resolved_assignment_id' added.

        Raises:
            serializers.ValidationError: If lookup fields are missing, entities
                                         are not found, dates are invalid, or no
                                         active assignment is found.
        """
        batch_id_input = data.get('batch_id')
        container_id_input = data.get('container_id')
        sample_date = data.get('sample_date')
        date_sent_to_lab = data.get('date_sent_to_lab')
        date_results_received = data.get('date_results_received')

        # Ensure all required fields for lookup are present
        if not all([batch_id_input, container_id_input, sample_date]):
            # This check is somewhat redundant if fields have required=True, but good for clarity
            raise serializers.ValidationError(
                "batch_id, container_id, and sample_date are required to create a lab sample."
            )

        # Validate date order if dates are provided
        if sample_date and date_sent_to_lab:
            validate_date_order(sample_date, date_sent_to_lab, 'sample_date', 'date_sent_to_lab')
        
        if date_sent_to_lab and date_results_received:
            validate_date_order(date_sent_to_lab, date_results_received, 'date_sent_to_lab', 'date_results_received')

        try:
            batch = Batch.objects.get(id=batch_id_input)
        except Batch.DoesNotExist:
            raise serializers.ValidationError(
                {"batch_id": f"Batch with ID {batch_id_input} not found."}
            )

        try:
            container = Container.objects.get(id=container_id_input)
        except Container.DoesNotExist:
            raise serializers.ValidationError(
                {"container_id": f"Container with ID {container_id_input} not found."}
            )

        # Core logic to find the historical assignment
        # Using assignment_date to filter for the correct historical assignment at the time of sampling
        # This is crucial because lab results may take weeks, and the container might be reassigned
        # to different batches by then.
        # We look for the most recent assignment that was active on or before the sample date.
        assignment = BatchContainerAssignment.objects.filter(
            batch=batch,
            container=container,
            assignment_date__lte=sample_date
        ).order_by('-assignment_date', '-id').first()

        if not assignment:
            raise serializers.ValidationError(
                f"No active or relevant assignment found for Batch {batch.batch_number} "
                f"in Container {container.name} on {sample_date}."
            )

        # Validate sample_date against batch's overall lifecycle
        # Use actual_end_date if available, otherwise expected_end_date
        effective_batch_end_date = batch.actual_end_date or batch.expected_end_date
        if batch.start_date > sample_date:
            raise serializers.ValidationError(
                f"Sample date {sample_date} is before the batch's start date ({batch.start_date})."
            )
        if effective_batch_end_date and effective_batch_end_date < sample_date:
            raise serializers.ValidationError(
                f"Sample date {sample_date} is after the batch's effective end date ({effective_batch_end_date})."
            )
        
        # Store the ID of the resolved assignment to be used in create()
        data['resolved_assignment_id'] = assignment.id
        return data

    def create(self, validated_data):
        """Create a new HealthLabSample instance.

        The 'batch_container_assignment' is set using the 'resolved_assignment_id'
        determined during validation. The 'recorded_by' user is set from the
        request context.

        Args:
            validated_data (dict): The validated data for creating the sample.

        Returns:
            HealthLabSample: The created lab sample instance.
        """
        resolved_assignment_id = validated_data.pop('resolved_assignment_id')
        # Remove temporary fields used for lookup from validated_data before creating HealthLabSample
        validated_data.pop('batch_id', None) 
        validated_data.pop('container_id', None)
        
        validated_data['batch_container_assignment_id'] = resolved_assignment_id
        
        # Set recorded_by to the current authenticated user, if available
        if 'recorded_by' not in validated_data and 'request' in self.context:
            validated_data = self.assign_user(validated_data, self.context.get('request'), 'recorded_by')
        
        return HealthLabSample.objects.create(**validated_data)
