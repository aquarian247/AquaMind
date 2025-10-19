"""
Serializers for the batch app.

This package contains all serializers related to fish batch management, including:
- Species
- Lifecycle stages
- Batch tracking
- Container assignments
- Batch compositions
- Transfers between containers (legacy)
- Transfer workflows (new architecture)
- Transfer actions (workflow execution)
- Mortality events
- Growth samples
- Utility functions and mixins for common serializer patterns
- Validation functions for complex validation logic
- Base serializer classes for standardizing patterns
"""

from apps.batch.api.serializers.species import (
    SpeciesSerializer, LifeCycleStageSerializer
)
from apps.batch.api.serializers.batch import BatchSerializer
from apps.batch.api.serializers.assignment import (
    BatchContainerAssignmentSerializer
)
from apps.batch.api.serializers.composition import BatchCompositionSerializer
from apps.batch.api.serializers.transfer import BatchTransferSerializer
from apps.batch.api.serializers.workflow import (
    BatchTransferWorkflowListSerializer,
    BatchTransferWorkflowDetailSerializer,
    BatchTransferWorkflowCreateSerializer,
)
from apps.batch.api.serializers.workflow_action import (
    TransferActionListSerializer,
    TransferActionDetailSerializer,
    TransferActionExecuteSerializer,
    TransferActionSkipSerializer,
    TransferActionRollbackSerializer,
)
from apps.batch.api.serializers.mortality import (
    MortalityEventSerializer
)
from apps.batch.api.serializers.growth import GrowthSampleSerializer
from apps.batch.api.serializers.utils import (
    DecimalFieldsMixin, NestedModelMixin,
    format_decimal, calculate_biomass_kg, validate_date_order
)
from apps.batch.api.serializers.validation import (
    validate_container_capacity, validate_batch_population,
    validate_individual_measurements,
    validate_sample_size_against_population,
    validate_min_max_weight
)
from apps.batch.api.serializers.base import (
    StandardErrorMixin, ReadWriteFieldsMixin, BatchBaseSerializer
)

__all__ = [
    # Serializers
    'SpeciesSerializer',
    'LifeCycleStageSerializer',
    'BatchSerializer',
    'BatchContainerAssignmentSerializer',
    'BatchCompositionSerializer',
    'BatchTransferSerializer',
    'BatchTransferWorkflowListSerializer',
    'BatchTransferWorkflowDetailSerializer',
    'BatchTransferWorkflowCreateSerializer',
    'TransferActionListSerializer',
    'TransferActionDetailSerializer',
    'TransferActionExecuteSerializer',
    'TransferActionSkipSerializer',
    'TransferActionRollbackSerializer',
    'MortalityEventSerializer',
    'GrowthSampleSerializer',

    # Utility functions and mixins
    'DecimalFieldsMixin',
    'NestedModelMixin',
    'format_decimal',
    'calculate_biomass_kg',
    'validate_date_order',

    # Validation functions
    'validate_container_capacity',
    'validate_batch_population',
    'validate_individual_measurements',
    'validate_sample_size_against_population',
    'validate_min_max_weight',

    # Base serializer classes
    'StandardErrorMixin',
    'ReadWriteFieldsMixin',
    'BatchBaseSerializer',
]
