"""Aggregated serializers for Scenario API use."""

from .temperature import TemperatureProfileSerializer, TemperatureReadingSerializer
from .modeling import (
    FCRModelSerializer,
    FCRModelStageSerializer,
    MortalityModelSerializer,
    MortalityModelStageSerializer,
    TGCModelSerializer,
    TGCModelStageSerializer,
)
from .constraints import BiologicalConstraintsSerializer, ScenarioModelChangeSerializer
from .scenario import ScenarioSerializer
from .projections import (
    ProjectionChartSerializer,
    ScenarioComparisonSerializer,
    ScenarioProjectionSerializer,
)
from .bulk import (
    BatchInitializationSerializer,
    BulkDateRangeSerializer,
    CSVTemplateRequestSerializer,
    CSVUploadSerializer,
    DataValidationResultSerializer,
    DateRangeEntrySerializer,
    ScenarioDuplicateSerializer,
)

__all__ = [
    "TemperatureReadingSerializer",
    "TemperatureProfileSerializer",
    "TGCModelStageSerializer",
    "TGCModelSerializer",
    "FCRModelStageSerializer",
    "FCRModelSerializer",
    "MortalityModelStageSerializer",
    "MortalityModelSerializer",
    "ScenarioModelChangeSerializer",
    "BiologicalConstraintsSerializer",
    "ScenarioSerializer",
    "ScenarioProjectionSerializer",
    "ProjectionChartSerializer",
    "ScenarioComparisonSerializer",
    "CSVUploadSerializer",
    "DateRangeEntrySerializer",
    "BulkDateRangeSerializer",
    "DataValidationResultSerializer",
    "CSVTemplateRequestSerializer",
    "ScenarioDuplicateSerializer",
    "BatchInitializationSerializer",
]
