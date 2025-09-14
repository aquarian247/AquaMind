"""
Serializer for the BatchTransfer model.

This serializer handles the conversion between JSON and Django model instances
for batch transfer data, including validation of transfer counts and biomass.
"""
from rest_framework import serializers
from apps.batch.models import BatchTransfer
from apps.batch.api.serializers.utils import NestedModelMixin
from typing import Dict, Any, Optional


class BatchTransferSerializer(NestedModelMixin, serializers.ModelSerializer):
    """Serializer for the BatchTransfer model."""

    source_batch_number = serializers.StringRelatedField(
        source='source_batch', read_only=True
    )
    destination_batch_number = serializers.StringRelatedField(
        source='destination_batch', read_only=True
    )
    transfer_type_display = serializers.CharField(
        source='get_transfer_type_display', read_only=True
    )
    source_lifecycle_stage_name = serializers.StringRelatedField(
        source='source_lifecycle_stage', read_only=True
    )
    destination_lifecycle_stage_name = serializers.StringRelatedField(
        source='destination_lifecycle_stage', read_only=True
    )
    # Container information fields from assignments
    source_container_name = serializers.StringRelatedField(
        source='source_assignment.container', read_only=True
    )
    destination_container_name = serializers.StringRelatedField(
        source='destination_assignment.container', read_only=True
    )
    source_batch_info = serializers.SerializerMethodField()
    destination_batch_info = serializers.SerializerMethodField()

    class Meta:
        model = BatchTransfer
        fields = '__all__'
        read_only_fields = ('created_at',)

    def get_source_batch_info(self, obj) -> Optional[Dict[str, Any]]:
        """Get basic source batch information."""
        return self.get_nested_info(obj, 'source_batch', {
            'id': 'id',
            'batch_number': 'batch_number'
        })

    def get_destination_batch_info(self, obj) -> Optional[Dict[str, Any]]:
        """Get basic destination batch information."""
        return self.get_nested_info(obj, 'destination_batch', {
            'id': 'id',
            'batch_number': 'batch_number'
        })

    def validate(self, data):
        """
        Validate transfer data including:
        - Transfer count doesn't exceed source batch population
        - Source/dest fields correct for transfer type
        """
        errors = {}

        # Validate transfer count against source batch
        if 'transferred_count' in data:
            self._validate_transfer_count(data, errors)

        # Validate transfer type requirements
        if 'transfer_type' in data:
            self._validate_transfer_type_requirements(data, errors)

        # Validate biomass transfer
        if 'source_biomass_kg' in data and 'transferred_biomass_kg' in data:
            self._validate_biomass_transfer(data, errors)

        if errors:
            raise serializers.ValidationError(errors)

        return data

    def _validate_transfer_count(self, data, errors):
        """Validate transfer count against source batch population."""
        source_batch = data.get('source_batch')
        if not source_batch:
            return

        transferred_count = data['transferred_count']
        source_population = source_batch.calculated_population_count

        if transferred_count > source_population:
            errors['transferred_count'] = (
                f"Transfer count ({transferred_count}) "
                "exceeds source batch population "
                f"({source_population})."
            )

    def _validate_transfer_type_requirements(self, data, errors):
        """Validate requirements based on transfer type."""
        transfer_type = data['transfer_type']

        if transfer_type == 'LIFECYCLE':
            self._validate_lifecycle_transfer(data, errors)
        elif transfer_type == 'CONTAINER':
            self._validate_container_transfer(data, errors)
        elif transfer_type == 'SPLIT':
            self._validate_split_transfer(data, errors)
        elif transfer_type == 'MERGE':
            self._validate_merge_transfer(data, errors)

    def _validate_lifecycle_transfer(self, data, errors):
        """Validate lifecycle transfer requirements."""
        if not data.get('destination_lifecycle_stage'):
            errors['destination_lifecycle_stage'] = (
                "Destination lifecycle stage is required for lifecycle transfers."
            )

    def _validate_container_transfer(self, data, errors):
        """Validate container transfer requirements."""
        if not data.get('destination_assignment'):
            errors['destination_assignment'] = (
                "Destination assignment is required for container transfers."
            )

    def _validate_split_transfer(self, data, errors):
        """Validate batch split requirements."""
        if not data.get('destination_batch'):
            errors['destination_batch'] = (
                "Destination batch is required for batch splits."
            )

    def _validate_merge_transfer(self, data, errors):
        """Validate batch merge requirements."""
        if not data.get('destination_batch'):
            errors['destination_batch'] = (
                "Destination batch is required for batch merges."
            )

    def _validate_biomass_transfer(self, data, errors):
        """Validate biomass transfer amounts."""
        transferred_biomass = data['transferred_biomass_kg']
        source_biomass = data['source_biomass_kg']

        if transferred_biomass > source_biomass:
            errors['transferred_biomass_kg'] = (
                f"Transferred biomass ({transferred_biomass} kg) "
                "exceeds source biomass "
                f"({source_biomass} kg)."
            )
