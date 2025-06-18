"""
Router configuration for Scenario Planning API.

Registers all viewsets and defines URL patterns for the API endpoints.
"""
from rest_framework import routers

from .viewsets import (
    TemperatureProfileViewSet, TGCModelViewSet, FCRModelViewSet,
    MortalityModelViewSet, ScenarioViewSet, DataEntryViewSet,
    BiologicalConstraintsViewSet
)

# Create router
router = routers.DefaultRouter()

# Register viewsets
router.register(r'temperature-profiles', TemperatureProfileViewSet, basename='temperature-profile')
router.register(r'tgc-models', TGCModelViewSet, basename='tgc-model')
router.register(r'fcr-models', FCRModelViewSet, basename='fcr-model')
router.register(r'mortality-models', MortalityModelViewSet, basename='mortality-model')
router.register(r'biological-constraints', BiologicalConstraintsViewSet, basename='biological-constraints')
router.register(r'scenarios', ScenarioViewSet, basename='scenario')
router.register(r'data-entry', DataEntryViewSet, basename='data-entry')

# The router will generate the following URL patterns:
# 
# Temperature Profiles:
# - /api/v1/scenario/temperature-profiles/ - List/Create temperature profiles
# - /api/v1/scenario/temperature-profiles/{id}/ - Retrieve/Update/Delete profile
# - /api/v1/scenario/temperature-profiles/upload_csv/ - Upload CSV data
# - /api/v1/scenario/temperature-profiles/bulk_date_ranges/ - Create from date ranges
# - /api/v1/scenario/temperature-profiles/download_template/ - Download CSV template
# - /api/v1/scenario/temperature-profiles/{id}/statistics/ - Get temperature statistics
#
# TGC Models:
# - /api/v1/scenario/tgc-models/ - TGC model CRUD
# - /api/v1/scenario/tgc-models/templates/ - Get predefined templates
# - /api/v1/scenario/tgc-models/{id}/duplicate/ - Duplicate a model
#
# FCR Models:
# - /api/v1/scenario/fcr-models/ - FCR model CRUD
# - /api/v1/scenario/fcr-models/templates/ - Get predefined templates
# - /api/v1/scenario/fcr-models/{id}/stage_summary/ - Get stage summary
#
# Mortality Models:
# - /api/v1/scenario/mortality-models/ - Mortality model CRUD
# - /api/v1/scenario/mortality-models/templates/ - Get predefined templates
#
# Biological Constraints:
# - /api/v1/scenario/biological-constraints/ - Constraint set CRUD
# - /api/v1/scenario/biological-constraints/active/ - Get active constraints
#
# Scenarios:
# - /api/v1/scenario/scenarios/ - Scenario CRUD
# - /api/v1/scenario/scenarios/{id}/duplicate/ - Duplicate scenario
# - /api/v1/scenario/scenarios/from_batch/ - Create from batch
# - /api/v1/scenario/scenarios/compare/ - Compare multiple scenarios
# - /api/v1/scenario/scenarios/{id}/run_projection/ - Run projections
# - /api/v1/scenario/scenarios/{id}/sensitivity_analysis/ - Run sensitivity analysis
# - /api/v1/scenario/scenarios/{id}/projections/ - Get projections
# - /api/v1/scenario/scenarios/{id}/chart_data/ - Get chart-formatted data
# - /api/v1/scenario/scenarios/{id}/export_projections/ - Export as CSV
# - /api/v1/scenario/scenarios/summary_stats/ - Get user's summary statistics
#
# Data Entry:
# - /api/v1/scenario/data-entry/validate_csv/ - Validate CSV
# - /api/v1/scenario/data-entry/csv_template/ - Get CSV template
# - /api/v1/scenario/data-entry/import_status/ - Check import status 