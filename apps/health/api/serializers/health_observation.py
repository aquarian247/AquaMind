"""
Health observation serializers for health monitoring.

This module defines serializers for health observation models, including
HealthParameter, HealthSamplingEvent, IndividualFishObservation, and FishParameterScore.
"""

from rest_framework import serializers
from django.db import transaction
from typing import Dict, Any, Optional

from ...models import (
    HealthParameter,
    ParameterScoreDefinition,
    HealthSamplingEvent,
    IndividualFishObservation,
    FishParameterScore
)
from ..utils import (
    calculate_k_factor, validate_assignment_date_range,
    HealthDecimalFieldsMixin, NestedHealthModelMixin, UserAssignmentMixin
)
from .base import HealthBaseSerializer


class ParameterScoreDefinitionSerializer(HealthBaseSerializer):
    """Serializer for parameter score definitions."""
    
    class Meta:
        model = ParameterScoreDefinition
        fields = [
            'id', 'parameter', 'score_value', 'label', 
            'description', 'display_order', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class FishParameterScoreSerializer(HealthBaseSerializer):
    """Serializer for FishParameterScore model.
    
    Uses HealthBaseSerializer for consistent error handling and field management.
    """
    parameter_name = serializers.CharField(
        source='parameter.name', 
        read_only=True,
        help_text="Name of the health parameter being scored."
    )
    parameter = serializers.PrimaryKeyRelatedField(
        queryset=HealthParameter.objects.filter(is_active=True),
        help_text="ID of the health parameter being scored. Must reference an active parameter."
    )
    score = serializers.IntegerField(
        help_text="Score value (typically 1-5) representing the health assessment for this parameter."
    )

    class Meta:
        model = FishParameterScore
        fields = ['id', 'parameter', 'parameter_name', 'score', 'created_at', 'updated_at']
        read_only_fields = ['id', 'parameter_name', 'created_at', 'updated_at']


class FishParameterScoreInputSerializer(serializers.Serializer):
    """Input serializer for nested fish parameter scores.
    
    Note: Score validation is performed dynamically based on the parameter's min/max range.
    """

    parameter = serializers.PrimaryKeyRelatedField(
        queryset=HealthParameter.objects.filter(is_active=True),
        help_text="ID of the active health parameter being scored."
    )
    score = serializers.IntegerField(
        help_text="Score value - range defined by parameter's min_score/max_score"
    )
    
    def validate(self, data):
        """Validate score is within parameter's defined range."""
        parameter = data.get('parameter')
        score = data.get('score')
        
        if parameter and score is not None:
            if not (parameter.min_score <= score <= parameter.max_score):
                raise serializers.ValidationError({
                    'score': f"{parameter.name} score must be between {parameter.min_score} "
                             f"and {parameter.max_score}. You entered {score}."
                })
        
        return data


class IndividualFishObservationInputSerializer(HealthDecimalFieldsMixin, serializers.Serializer):
    """Input serializer for nested individual fish observations."""

    fish_identifier = serializers.CharField(
        help_text="Unique identifier for the individual fish within this sampling event."
    )
    weight_g = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=False,
        allow_null=True,
        help_text="Weight of the fish in grams."
    )
    length_cm = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=False,
        allow_null=True,
        help_text="Length of the fish in centimeters."
    )
    parameter_scores = FishParameterScoreInputSerializer(
        many=True,
        required=False,
        help_text="List of parameter scores for this fish observation."
    )

    def validate(self, data):
        """Ensure positive decimal values where provided."""
        weight_g = data.get('weight_g')
        length_cm = data.get('length_cm')

        if weight_g is not None:
            data['weight_g'] = self.validate_positive_decimal(weight_g, 'weight_g')

        if length_cm is not None:
            data['length_cm'] = self.validate_positive_decimal(length_cm, 'length_cm')

        data['fish_identifier'] = str(data['fish_identifier'])
        return data


class IndividualFishObservationSerializer(HealthDecimalFieldsMixin, NestedHealthModelMixin, HealthBaseSerializer):
    """Serializer for IndividualFishObservation model.
    
    Uses HealthBaseSerializer for consistent error handling and field management.
    Includes HealthDecimalFieldsMixin for decimal field validation and
    NestedHealthModelMixin for handling nested models.
    """
    parameter_scores = FishParameterScoreSerializer(
        many=True, 
        required=False,
        help_text="List of parameter scores for this fish observation."
    )
    calculated_k_factor = serializers.SerializerMethodField(
        help_text="Calculated K-factor (condition factor) based on weight and length measurements."
    )
    sampling_event = serializers.PrimaryKeyRelatedField(
        queryset=HealthSamplingEvent.objects.all(),
        required=False,
        allow_null=True,
        help_text="The sampling event this fish observation belongs to."
    )
    fish_identifier = serializers.CharField(
        help_text="Unique identifier for the individual fish within this sampling event."
    )
    weight_g = serializers.DecimalField(
        max_digits=10, 
        decimal_places=2,
        required=False,
        allow_null=True,
        help_text="Weight of the fish in grams."
    )
    length_cm = serializers.DecimalField(
        max_digits=10, 
        decimal_places=2,
        required=False,
        allow_null=True,
        help_text="Length of the fish in centimeters."
    )

    class Meta:
        model = IndividualFishObservation
        fields = [
            'id', 'sampling_event', 'fish_identifier',
            'weight_g', 'length_cm', 'parameter_scores', 'calculated_k_factor'
        ]
        read_only_fields = ['id', 'calculated_k_factor']

    def get_calculated_k_factor(self, obj) -> Optional[float]:
        """Calculate K-factor if weight and length are provided.

        Args:
            obj: The IndividualFishObservation instance.

        Returns:
            Decimal or None: The calculated K-factor, or None if data is insufficient.
        """
        return calculate_k_factor(obj.weight_g, obj.length_cm)

    def validate(self, data):
        """Validate fish observation data.

        Ensures fish_identifier is a string and validates positive decimal values
        for weight_g and length_cm if provided.

        Args:
            data (dict): The data to validate.

        Returns:
            dict: The validated data.
        """
        weight_g = data.get('weight_g')
        length_cm = data.get('length_cm')
        
        # Ensure fish_identifier is a string
        if 'fish_identifier' in data and not isinstance(data['fish_identifier'], str):
            data['fish_identifier'] = str(data['fish_identifier'])

        # Validate weight and length if provided
        if weight_g is not None:
            data['weight_g'] = self.validate_positive_decimal(weight_g, 'weight_g')
        
        if length_cm is not None:
            data['length_cm'] = self.validate_positive_decimal(length_cm, 'length_cm')

        if not data.get('sampling_event') and not self.instance:
            raise serializers.ValidationError({
                'sampling_event': "This field is required when creating observations directly."
            })

        return data

    @transaction.atomic
    def create(self, validated_data):
        """Create a new fish observation with nested parameter scores.

        Args:
            validated_data (dict): The data for creating the observation.

        Returns:
            IndividualFishObservation: The created instance.
        """
        parameter_scores_data = validated_data.pop('parameter_scores', [])
        fish_observation = IndividualFishObservation.objects.create(**validated_data)

        # Create parameter scores
        for score_data in parameter_scores_data:
            FishParameterScore.objects.create(
                individual_fish_observation=fish_observation,
                **score_data
            )

        return fish_observation

    @transaction.atomic
    def update(self, instance, validated_data):
        """Update a fish observation with nested parameter scores.

        This method uses a replace-all strategy for nested parameter_scores.

        Args:
            instance (IndividualFishObservation): The instance to update.
            validated_data (dict): The data for updating the instance.

        Returns:
            IndividualFishObservation: The updated instance.
        """
        parameter_scores_data = validated_data.pop('parameter_scores', None)
        
        # Update fish observation fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # Update parameter scores if provided
        if parameter_scores_data is not None:
            # Clear existing scores and create new ones
            instance.parameter_scores.all().delete()
            for score_data in parameter_scores_data:
                FishParameterScore.objects.create(
                    individual_fish_observation=instance,
                    **score_data
                )

        return instance


class HealthSamplingEventSerializer(HealthDecimalFieldsMixin, NestedHealthModelMixin, UserAssignmentMixin, HealthBaseSerializer):
    """Serializer for HealthSamplingEvent model.
    
    Uses HealthBaseSerializer for consistent error handling and field management.
    Includes HealthDecimalFieldsMixin for decimal field validation,
    NestedHealthModelMixin for handling nested models, and
    UserAssignmentMixin for automatic user assignment.
    
    This serializer handles complex nested data structures for fish health sampling events,
    including individual fish observations and their parameter scores.
    """
    # Write-only for creating nested observations
    individual_fish_observations = IndividualFishObservationInputSerializer(
        many=True,
        required=False,
        write_only=True,
        help_text="Fish observations to create (write-only, for POST/PUT)."
    )
    
    # Read-only for displaying nested observations
    fish_observations = IndividualFishObservationSerializer(
        source='individual_fish_observations',
        many=True,
        read_only=True,
        help_text="Individual fish observations with parameter scores (read-only, for GET)."
    )
    
    # Read-only fields for displaying related data
    batch_number = serializers.SerializerMethodField()
    container_name = serializers.SerializerMethodField()
    sampled_by_username = serializers.SerializerMethodField()
    
    # Sampling event fields
    class Meta:
        model = HealthSamplingEvent
        fields = [
            'id', 'assignment', 'sampling_date', 'number_of_fish_sampled',
            'avg_weight_g', 'std_dev_weight_g', 'min_weight_g', 'max_weight_g',
            'individual_fish_observations',  # write-only field for creating nested objects
            'fish_observations',  # read-only field for displaying nested objects
            'avg_length_cm', 'std_dev_length_cm', 'min_length_cm', 'max_length_cm',
            'avg_k_factor', 'calculated_sample_size', 'notes', 'sampled_by',
            'batch_number', 'container_name', 'sampled_by_username'
        ]
        read_only_fields = [
            'id', 'avg_weight_g', 'std_dev_weight_g', 'min_weight_g', 'max_weight_g',
            'avg_length_cm', 'std_dev_length_cm', 'min_length_cm', 'max_length_cm',
            'avg_k_factor', 'calculated_sample_size', 'batch_number', 'container_name', 
            'sampled_by_username', 'fish_observations'
        ]
    
    def get_batch_number(self, obj) -> Optional[str]:
        """Get the batch number from the assignment.

        Args:
            obj: The HealthSamplingEvent instance.

        Returns:
            str or None: The batch number, or None if not available.
        """
        if obj.assignment and obj.assignment.batch:
            return obj.assignment.batch.batch_number
        return None
    
    def get_container_name(self, obj) -> Optional[str]:
        """Get the container name from the assignment.

        Args:
            obj: The HealthSamplingEvent instance.

        Returns:
            str or None: The container name, or None if not available.
        """
        if obj.assignment and obj.assignment.container:
            return obj.assignment.container.name
        return None
    
    def get_sampled_by_username(self, obj) -> Optional[str]:
        """Get the username of the user who performed the sampling.

        Args:
            obj: The HealthSamplingEvent instance.

        Returns:
            str or None: The username, or None if not available.
        """
        if obj.sampled_by:
            return obj.sampled_by.username
        return None
    
    def validate_assignment(self, value):
        """Validate that the assignment exists and is active.

        Args:
            value (BatchContainerAssignment): The assignment instance.

        Returns:
            BatchContainerAssignment: The validated assignment instance.

        Raises:
            serializers.ValidationError: If the assignment is not found or inactive.
        """
        if not value.is_active:
            raise serializers.ValidationError("The batch container assignment must be active.")
        
        return value
    
    def validate(self, data):
        """Validate sampling event data.

        Ensures that the sampling_date is within the assignment's date range
        and that number_of_fish_sampled is positive.

        Args:
            data (dict): The data to validate.

        Returns:
            dict: The validated data.
        """
        # Add any additional validation here
        sampling_date = data.get('sampling_date')
        assignment = data.get('assignment')
        
        # Validate that sampling_date is within the assignment period
        if sampling_date and assignment:
            validate_assignment_date_range(assignment, sampling_date, 'sampling_date')
        
        return data
    
    @transaction.atomic
    def create(self, validated_data):
        """Create a health sampling event with nested individual fish observations.

        This method handles a complex nested creation process:
        1. Creates the parent HealthSamplingEvent object.
        2. Creates IndividualFishObservation objects for each fish.
        3. Creates FishParameterScore objects for each parameter score.
        4. Calculates aggregate metrics based on the individual observations.

        The entire operation is wrapped in a transaction to ensure data integrity.

        Args:
            validated_data (dict): The data for creating the event.

        Returns:
            HealthSamplingEvent: The created instance.
        """
        # Extract nested data for individual fish observations
        individual_fish_observations_data = validated_data.pop('individual_fish_observations', [])
        
        # Set the user who performed the sampling if not provided
        # Uses the UserAssignmentMixin to handle user assignment consistently
        if 'sampled_by' not in validated_data and 'request' in self.context:
            validated_data = self.assign_user(validated_data, self.context.get('request'), 'sampled_by')
        
        # Create the parent health sampling event
        health_sampling_event = HealthSamplingEvent.objects.create(**validated_data)
        
        # Create individual fish observations (children of the sampling event)
        for fish_data in individual_fish_observations_data:
            parameter_scores_data = fish_data.pop('parameter_scores', [])

            fish_observation = IndividualFishObservation.objects.create(
                sampling_event=health_sampling_event,
                **fish_data
            )

            for score_data in parameter_scores_data:
                FishParameterScore.objects.create(
                    individual_fish_observation=fish_observation,
                    **score_data
                )
        
        # Calculate aggregate metrics (avg weight, length, etc.) based on individual observations
        # Always calculate metrics after creation to ensure data consistency
        health_sampling_event.calculate_aggregate_metrics()
        
        return health_sampling_event
        
    @transaction.atomic
    def update(self, instance, validated_data):
        """Update a health sampling event with nested fish observations.

        This method handles a complex nested update process:
        1. Updates the parent HealthSamplingEvent object with new field values.
        2. If individual fish observations are provided:
           - Removes all existing observations (with cascade delete to parameter scores).
           - Creates new IndividualFishObservation objects for each fish.
           - Creates new FishParameterScore objects for each parameter score.
        3. Recalculates aggregate metrics based on the updated individual observations.

        The entire operation is wrapped in a transaction to ensure data integrity.
        Note: This uses a replace-all approach for nested objects.

        Args:
            instance (HealthSamplingEvent): The instance to update.
            validated_data (dict): The data for updating the instance.

        Returns:
            HealthSamplingEvent: The updated instance.
        """
        individual_fish_observations_data = validated_data.pop('individual_fish_observations', None)
        
        # Update the health sampling event fields using direct attribute assignment
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # Update individual fish observations if provided
        if individual_fish_observations_data is not None:
            # Replace strategy: Clear all existing observations and create new ones
            # This also cascades to delete all associated parameter scores
            instance.individual_fish_observations.all().delete()
            
            # Create new observations with the updated data
            for fish_data in individual_fish_observations_data:
                # Set the reference to the parent sampling event
                fish_data['sampling_event'] = instance
                
                # Extract parameter scores data if present
                parameter_scores_data = fish_data.pop('parameter_scores', [])
                
                # Create the new fish observation
                fish_observation = IndividualFishObservation.objects.create(**fish_data)
                
                # Create new parameter scores for this fish observation
                for score_data in parameter_scores_data:
                    FishParameterScore.objects.create(
                        individual_fish_observation=fish_observation,
                        **score_data
                    )
        
        # Recalculate all aggregate metrics based on the updated observations
        # This ensures that derived values (averages, min/max, etc.) are consistent
        instance.calculate_aggregate_metrics()
        
        return instance


class HealthParameterSerializer(HealthBaseSerializer):
    """Serializer for the HealthParameter model with nested score definitions.
    
    Uses HealthBaseSerializer for consistent error handling and field management.
    Includes nested score_definitions for flexible parameter scoring.
    """
    score_definitions = ParameterScoreDefinitionSerializer(
        many=True, 
        read_only=True,
        help_text="Score definitions for this parameter (e.g., 0-3 scale with labels and descriptions)."
    )
    
    class Meta:
        model = HealthParameter
        fields = [
            'id', 'name', 'description', 'min_score', 'max_score',
            'score_definitions',  # Nested score definitions
            'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
