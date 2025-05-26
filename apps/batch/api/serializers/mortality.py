"""
Serializer for the MortalityEvent model.

This serializer handles the conversion between JSON and Django model instances
for mortality event data, including validation of mortality counts and biomass.
"""
from rest_framework import serializers
from apps.batch.models import MortalityEvent
from apps.batch.api.serializers.utils import NestedModelMixin, DecimalFieldsMixin


class MortalityEventSerializer(NestedModelMixin, DecimalFieldsMixin, serializers.ModelSerializer):
    """Serializer for the MortalityEvent model."""
    
    batch_number = serializers.StringRelatedField(source='batch', read_only=True)
    cause_display = serializers.CharField(source='get_cause_display', read_only=True)
    batch_info = serializers.SerializerMethodField()
    container_info = serializers.SerializerMethodField()
    reason_info = serializers.SerializerMethodField()

    class Meta:
        model = MortalityEvent
        fields = '__all__'
        read_only_fields = ('created_at',)
    
    def get_batch_info(self, obj):
        """Get basic batch information."""
        return self.get_nested_info(obj, 'batch', {
            'id': 'id',
            'batch_number': 'batch_number'
        })

    def get_container_info(self, obj):
        """Get basic container information."""
        return self.get_nested_info(obj, 'container', {
            'id': 'id',
            'name': 'name'
        })

    def get_reason_info(self, obj):
        """Get mortality reason information."""
        return self.get_nested_info(obj, 'reason', {
            'id': 'id',
            'name': 'name'
        })

    def validate(self, data):
        """
        Validate that mortality count doesn't exceed batch population and
        that mortality biomass doesn't exceed batch biomass.
        """
        errors = {}
        
        # Get the batch from data or database
        batch = data.get('batch')

        if batch:
            # Check if mortality count doesn't exceed batch population
            if 'count' in data:
                if data['count'] > batch.calculated_population_count:
                    errors['count'] = (
                        f"Mortality count ({data['count']}) exceeds batch "
                        f"population ({batch.calculated_population_count})."
                    )
            
            # Check if mortality biomass doesn't exceed batch biomass
            if 'biomass_kg' in data:
                if data['biomass_kg'] > batch.calculated_biomass_kg:
                    errors['biomass_kg'] = (
                        f"Mortality biomass ({data['biomass_kg']} kg) exceeds batch "
                        f"biomass ({batch.calculated_biomass_kg} kg)."
                    )
        
        if errors:
            raise serializers.ValidationError(errors)

        return data
