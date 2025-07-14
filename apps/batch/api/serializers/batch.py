"""
Serializer for the Batch model.

This serializer handles the conversion between JSON and Django model instances
for batch data, including calculated fields for population, biomass, and average weight.
"""
from datetime import date, timedelta
from rest_framework import serializers
from apps.batch.models import Batch
from apps.batch.api.serializers.utils import format_decimal, validate_date_order
from apps.batch.api.serializers.base import BatchBaseSerializer
from drf_spectacular.utils import extend_schema_field


class BatchSerializer(BatchBaseSerializer):
    """Serializer for the Batch model.

    Handles the representation of Batch instances, including their core attributes,
    related model information (species name), and dynamically calculated metrics
    such as population count, biomass, average weight, current lifecycle stage,
    days in production, and active containers.
    """

    species_name = serializers.CharField(source='species.name', read_only=True, help_text="Name of the species associated with this batch (read-only).")
    calculated_population_count = serializers.IntegerField(read_only=True, help_text="Total current population count for this batch, calculated from active assignments (read-only).")
    calculated_biomass_kg = serializers.SerializerMethodField(help_text="Total current biomass in kilograms for this batch, calculated from active assignments and formatted to two decimal places (read-only).")
    calculated_avg_weight_g = serializers.SerializerMethodField(help_text="Current average weight in grams for individuals in this batch, calculated from active assignments and formatted to two decimal places (read-only).")
    current_lifecycle_stage = serializers.SerializerMethodField(help_text="The current lifecycle stage of the batch (ID, name, order), determined by the latest active assignment (read-only).")
    days_in_production = serializers.SerializerMethodField(help_text="Number of days the batch has been in production since its start date (read-only).")
    active_containers = serializers.SerializerMethodField(help_text="List of IDs of containers currently actively holding this batch (read-only).")

    class Meta:
        model = Batch
        help_text = (
            "Represents a group of aquatic organisms managed together, tracking their "
            "growth, location, and status over time. Includes core attributes and calculated metrics."
        )
        fields = (
            'id',
            'batch_number',
            'species',
            'species_name',
            'lifecycle_stage',
            'status',
            'batch_type',
            'start_date',
            'expected_end_date',
            'notes',
            'created_at',
            'updated_at',
            'calculated_population_count',
            'calculated_biomass_kg',
            'calculated_avg_weight_g',
            'current_lifecycle_stage',
            'days_in_production',
            'active_containers',
        )
        read_only_fields = (
            'id',
            'created_at',
            'updated_at',
            'calculated_population_count',
            'calculated_biomass_kg',
            'calculated_avg_weight_g',
            'current_lifecycle_stage',
            'days_in_production',
            'active_containers',
        )
        extra_kwargs = {
            'id': {'help_text': "Unique read-only identifier for the batch record."},
            'batch_number': {'help_text': "User-defined unique identifier or code for the batch (e.g., BATCH2023-001)."},
            'species': {'help_text': "Foreign key ID of the species for this batch. Must be an existing Species ID."},
            'lifecycle_stage': {'help_text': "Foreign key ID of the initial or primary lifecycle stage for this batch. Must be an existing LifeCycleStage ID appropriate for the selected species."},
            'status': {'help_text': "Current status of the batch. Refer to model choices (e.g., 'Planned', 'Active', 'Harvested')."},
            'batch_type': {'help_text': "Type or category of the batch. Refer to model choices (e.g., 'Production', 'Experimental')."},
            'start_date': {'help_text': "Date when the batch officially started or was created (YYYY-MM-DD)."},
            'expected_end_date': {'help_text': "Anticipated end date for the batch (e.g., for harvest or transfer) (YYYY-MM-DD). Defaults to 30 days after start_date if not provided."},
            'notes': {'help_text': "Any general notes or comments about the batch (optional)."},
            'created_at': {'help_text': "Timestamp of when the batch record was created (read-only)."},
            'updated_at': {'help_text': "Timestamp of the last update to the batch record (read-only)."}
        }

    # Dict with keys: id(int), name(str), order(int) or ``None`` when unavailable
    @extend_schema_field(serializers.JSONField(allow_null=True))
    def get_current_lifecycle_stage(self, obj):
        """Get the current lifecycle stage based on active assignments."""
        # Returned dict contains id(int), name(str), order(int)
        # Using JSONField for flexible but typed representation
        # (alternative would be DictField with explicit children but JSONField is simpler here)
        latest_assignment = obj.batch_assignments.filter(
            is_active=True).order_by('-assignment_date').first()
        if latest_assignment and latest_assignment.lifecycle_stage:
            return {
                'id': latest_assignment.lifecycle_stage.id,
                'name': latest_assignment.lifecycle_stage.name,
                'order': latest_assignment.lifecycle_stage.order
            }
        return None

    @extend_schema_field(serializers.IntegerField())
    def get_days_in_production(self, obj):
        """Calculate the number of days since the batch started."""
        if obj.start_date:
            return (date.today() - obj.start_date).days
        return 0

    @extend_schema_field(serializers.ListField(child=serializers.IntegerField()))
    def get_active_containers(self, obj):
        """Get a list of active container IDs for this batch."""
        active_assignments = obj.batch_assignments.filter(is_active=True)
        return [
            assignment.container.id
            for assignment in active_assignments if assignment.container
        ]

    @extend_schema_field(serializers.FloatField())
    def get_calculated_biomass_kg(self, obj):
        """Get the calculated biomass in kilograms, formatted."""
        return format_decimal(obj.calculated_biomass_kg)

    @extend_schema_field(serializers.FloatField())
    def get_calculated_avg_weight_g(self, obj):
        """Get the calculated average weight in grams, formatted."""
        return format_decimal(obj.calculated_avg_weight_g)

    def create(self, validated_data):
        """Create a new batch instance."""
        if 'expected_end_date' not in validated_data or \
                validated_data['expected_end_date'] is None:
            validated_data['expected_end_date'] = validated_data['start_date'] + \
                                                timedelta(days=30)
        return Batch.objects.create(**validated_data)

    def validate(self, data):
        """Validate the batch data.

        Ensures that expected_end_date is after start_date and that
        the lifecycle_stage belongs to the correct species.
        """
        errors = {}

        # Validate that expected_end_date is after start_date
        start = data.get('start_date')
        end = data.get('expected_end_date')

        if start and end:
            date_error = validate_date_order(
                start,
                end,
                'expected_end_date',
                'Expected end date must be after start date.'
            )
            if date_error:
                errors.update(date_error)

        # Validate that lifecycle_stage belongs to the correct species
        lifecycle_stage = data.get('lifecycle_stage')
        species = data.get('species')

        if lifecycle_stage and species:
            if lifecycle_stage.species.id != species.id:
                self.add_error(
                    errors,
                    'lifecycle_stage',
                    'Lifecycle stage {stage_name} does not belong to species ' +
                    '{species_name}.',
                    stage_name=lifecycle_stage.name,
                    species_name=species.name
                )

        if errors:
            raise serializers.ValidationError(errors)

        return super().validate(data)

    def update(self, instance, validated_data):
        """Update an existing batch."""
        for key, value in validated_data.items():
            setattr(instance, key, value)
        instance.save()
        return instance

