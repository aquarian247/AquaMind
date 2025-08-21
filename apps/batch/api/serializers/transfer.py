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

        source_batch = data.get('source_batch')
        if source_batch and 'transferred_count' in data:
            if data['transferred_count'] > \
                    source_batch.calculated_population_count:
                errors['transferred_count'] = (
                    f"Transfer count ({data['transferred_count']}) "
                    "exceeds source batch population "
                    f"({source_batch.calculated_population_count})."
                )

        if 'transfer_type' in data:
            transfer_type = data['transfer_type']
            if transfer_type == 'LIFECYCLE' and \
                    not data.get('destination_lifecycle_stage'):
                errors['destination_lifecycle_stage'] = (
                    "Destination lifecycle stage is required for "
                    "lifecycle transfers."
                )

            if transfer_type == 'CONTAINER' and \
                    not data.get('destination_assignment'):
                errors['destination_assignment'] = (
                    "Destination assignment is required for container "
                    "transfers."
                )

            if transfer_type == 'SPLIT' and \
                    not data.get('destination_batch'):
                errors['destination_batch'] = (
                    "Destination batch is required for batch splits."
                )

            if transfer_type == 'MERGE' and \
                    not data.get('destination_batch'):
                errors['destination_batch'] = (
                    "Destination batch is required for batch merges."
                )

        if 'source_biomass_kg' in data and \
                'transferred_biomass_kg' in data:
            if data['transferred_biomass_kg'] > data['source_biomass_kg']:
                errors['transferred_biomass_kg'] = (
                    f"Transferred biomass ({data['transferred_biomass_kg']} kg) "
                    "exceeds source biomass "
                    f"({data['source_biomass_kg']} kg)."
                )

        if errors:
            raise serializers.ValidationError(errors)

        return data
