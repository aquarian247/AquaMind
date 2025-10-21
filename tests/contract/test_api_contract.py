"""
API Contract Tests for AquaMind.

This module contains tests that verify the API contract is correctly
implemented and documented according to the OpenAPI specification.
"""
import inspect
import re
from importlib import import_module
from typing import Dict, List, Set, Tuple, Type, Optional

import pkgutil

from django.apps import apps
from django.conf import settings
from django.test import TestCase, override_settings
from django.urls import URLPattern, URLResolver, get_resolver
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.routers import SimpleRouter, DefaultRouter
from rest_framework.serializers import Serializer
from rest_framework.test import APITestCase

from drf_spectacular.generators import SchemaGenerator
from drf_spectacular.validation import validate_schema

# Import all viewsets from all apps
# This ensures we can check all viewsets are properly registered
# NOTE:
# The original import list referenced several viewsets that no longer
# exist (or have been renamed) in the current code-base.  Import errors
# prevented the contract tests from running.  The list below reflects
# the actual viewsets available in each app’s `api.viewsets` modules.
from apps.batch.api.viewsets import (
    BatchViewSet,
    SpeciesViewSet,
    LifeCycleStageViewSet,
    BatchContainerAssignmentViewSet,
    BatchCompositionViewSet,
    BatchTransferWorkflowViewSet,
    MortalityEventViewSet,
    GrowthSampleViewSet,
)
from apps.environmental.api.viewsets import (
    EnvironmentalParameterViewSet,
    EnvironmentalReadingViewSet,
    PhotoperiodDataViewSet,
    WeatherDataViewSet,
    StageTransitionEnvironmentalViewSet
)
from apps.health.api.viewsets import (
    JournalEntryViewSet,
    MortalityReasonViewSet,
    MortalityRecordViewSet,
    LiceCountViewSet,
    VaccinationTypeViewSet,
    TreatmentViewSet,
    SampleTypeViewSet,
    HealthParameterViewSet,
    HealthSamplingEventViewSet,
    IndividualFishObservationViewSet,
    FishParameterScoreViewSet,
    HealthLabSampleViewSet,
)
from apps.inventory.api.viewsets.container_stock import FeedContainerStockViewSet
from apps.inventory.api.viewsets.feeding import FeedingEventViewSet
from apps.inventory.api.viewsets.summary import BatchFeedingSummaryViewSet
from apps.inventory.api.viewsets.feed import FeedViewSet
from apps.inventory.api.viewsets.purchase import FeedPurchaseViewSet
from apps.scenario.api import viewsets as scenario_viewsets
from apps.users.views import UserViewSet

# Import router configuration
from aquamind.api.router import router as main_router


class APIContractTestCase(TestCase):
    """Test case for validating API contract compliance."""
    
    def setUp(self):
        """Set up test data."""
        self.router = main_router
        self.viewsets = self._get_all_viewsets()
        self.registered_viewsets = self._get_registered_viewsets()
        self.url_patterns = self._get_all_url_patterns()
    
    def _get_all_viewsets(self) -> List[Type[viewsets.ViewSet]]:
        """Get all viewset classes defined in the project."""
        all_viewsets = []
        
        # Iterate through all installed apps
        for app_config in apps.get_app_configs():
            if app_config.name.startswith('apps.') or app_config.name == 'aquamind':
                # Try to import viewsets from common locations
                for module_name in ['api.viewsets', 'views']:
                    try:
                        module_path = f"{app_config.name}.{module_name}"
                        module = import_module(module_path)
                        
                        # Find all viewset classes in the module
                        for name, obj in inspect.getmembers(module, inspect.isclass):
                            if (issubclass(obj, viewsets.ViewSet) and 
                                obj != viewsets.ViewSet and
                                obj != viewsets.GenericViewSet and
                                obj != viewsets.ModelViewSet and
                                obj != viewsets.ReadOnlyModelViewSet):
                                all_viewsets.append(obj)
                    except (ImportError, ModuleNotFoundError):
                        # Module doesn't exist, skip
                        pass
                
                # Also check for nested viewsets in api/viewsets/ directory
                try:
                    module_path = f"{app_config.name}.api.viewsets"
                    module = import_module(module_path)
                    
                    # If this is a package with submodules, try to import them
                    if hasattr(module, '__path__'):
                        for submodule_info in pkgutil.iter_modules(module.__path__):
                            try:
                                submodule = import_module(f"{module_path}.{submodule_info.name}")
                                for name, obj in inspect.getmembers(submodule, inspect.isclass):
                                    if (issubclass(obj, viewsets.ViewSet) and 
                                        obj != viewsets.ViewSet and
                                        obj != viewsets.GenericViewSet and
                                        obj != viewsets.ModelViewSet and
                                        obj != viewsets.ReadOnlyModelViewSet):
                                        all_viewsets.append(obj)
                            except ImportError:
                                pass
                except (ImportError, ModuleNotFoundError):
                    # Module doesn't exist, skip
                    pass
        
        # Remove duplicates while preserving order
        seen = set()
        unique_viewsets = []
        for vs in all_viewsets:
            if vs not in seen:
                seen.add(vs)
                unique_viewsets.append(vs)
        
        return unique_viewsets
    
    def _get_registered_viewsets(self) -> Dict[str, Type[viewsets.ViewSet]]:
        """Get all viewsets registered in the router."""
        registered = {}
        
        # Check main router
        for prefix, viewset, basename in self.router.registry:
            registered[basename] = viewset
        
        # Check included routers
        for pattern in self._get_all_url_patterns():
            if hasattr(pattern, 'url_patterns'):
                for sub_pattern in pattern.url_patterns:
                    if hasattr(sub_pattern, 'callback') and sub_pattern.callback:
                        callback = sub_pattern.callback
                        if hasattr(callback, 'cls') and issubclass(callback.cls, viewsets.ViewSet):
                            name = getattr(callback, 'basename', None) or sub_pattern.name
                            if name:
                                registered[name] = callback.cls
        
        return registered
    
    def _get_all_url_patterns(self) -> List[URLPattern]:
        """Get all URL patterns in the project."""
        resolver = get_resolver()
        return self._extract_patterns(resolver)
    
    def _extract_patterns(self, resolver) -> List[URLPattern]:
        """Recursively extract URL patterns from a resolver."""
        patterns = []
        for pattern in resolver.url_patterns:
            if isinstance(pattern, URLResolver):
                patterns.append(pattern)
                patterns.extend(self._extract_patterns(pattern))
            else:
                patterns.append(pattern)
        return patterns
    
    def _get_api_url_patterns(self) -> List[URLPattern]:
        """Get all API URL patterns (/api/v1/...)."""
        api_patterns = []
        for pattern in self._get_all_url_patterns():
            if hasattr(pattern, 'pattern'):
                pattern_str = str(pattern.pattern)
                if 'api/v1/' in pattern_str:
                    api_patterns.append(pattern)
        return api_patterns
    
    def test_all_viewsets_are_registered(self):
        """Test that all viewsets are registered in the router."""
        unregistered_viewsets = []
        
        for viewset in self.viewsets:
            if viewset not in self.registered_viewsets.values():
                unregistered_viewsets.append(viewset.__name__)
        
        self.assertEqual(
            unregistered_viewsets, [], 
            f"The following viewsets are not registered in the router: {unregistered_viewsets}"
        )
    
    def test_viewsets_have_serializer_class(self):
        """Test that all viewsets have a serializer_class or get_serializer_class method."""
        viewsets_without_serializer = []
        
        for viewset in self.viewsets:
            has_serializer = False
            
            # Check for serializer_class attribute
            if hasattr(viewset, 'serializer_class'):
                serializer_class = getattr(viewset, 'serializer_class')
                if serializer_class and issubclass(serializer_class, Serializer):
                    has_serializer = True
            
            # Check for get_serializer_class method
            if hasattr(viewset, 'get_serializer_class') and callable(getattr(viewset, 'get_serializer_class')):
                has_serializer = True
            
            # Check for serializer_classes attribute (for action-specific serializers)
            if hasattr(viewset, 'serializer_classes') and isinstance(getattr(viewset, 'serializer_classes'), dict):
                has_serializer = True
            
            # Check for action_serializers attribute (alternative pattern)
            if hasattr(viewset, 'action_serializers') and isinstance(getattr(viewset, 'action_serializers'), dict):
                has_serializer = True
            
            if not has_serializer:
                viewsets_without_serializer.append(viewset.__name__)
        
        self.assertEqual(
            viewsets_without_serializer, [],
            f"The following viewsets don't have a serializer_class or get_serializer_class method: {viewsets_without_serializer}"
        )
    
    def test_viewsets_have_queryset_or_get_queryset(self):
        """Test that all model viewsets have a queryset or get_queryset method."""
        model_viewsets_without_queryset = []
        
        for viewset in self.viewsets:
            # Only check model viewsets
            if not issubclass(viewset, viewsets.ModelViewSet) and not issubclass(viewset, viewsets.ReadOnlyModelViewSet):
                continue
                
            has_queryset = False
            
            # Check for queryset attribute
            if hasattr(viewset, 'queryset'):
                has_queryset = True
            
            # Check for get_queryset method
            if hasattr(viewset, 'get_queryset') and callable(getattr(viewset, 'get_queryset')):
                has_queryset = True
            
            if not has_queryset:
                model_viewsets_without_queryset.append(viewset.__name__)
        
        self.assertEqual(
            model_viewsets_without_queryset, [],
            f"The following model viewsets don't have a queryset or get_queryset method: {model_viewsets_without_queryset}"
        )
    
    def test_viewsets_have_authentication(self):
        """Test that all viewsets have authentication configured."""
        viewsets_without_auth = []
        
        for viewset in self.viewsets:
            has_auth = False
            
            # Check for permission_classes attribute
            if hasattr(viewset, 'permission_classes'):
                permission_classes = getattr(viewset, 'permission_classes')
                # Check if IsAuthenticated or a custom permission is in the list
                if permission_classes and any(
                    issubclass(p, IsAuthenticated) or p != AllowAny 
                    for p in permission_classes
                ):
                    has_auth = True
            
            # Check for get_permissions method
            if hasattr(viewset, 'get_permissions') and callable(getattr(viewset, 'get_permissions')):
                has_auth = True
            
            # Skip authentication check for specific viewsets that might be public by design
            if viewset.__name__ in ['SchemaViewSet', 'OpenAPIViewSet', 'SwaggerUIViewSet', 'RedocViewSet']:
                has_auth = True
            
            if not has_auth:
                viewsets_without_auth.append(viewset.__name__)
        
        self.assertEqual(
            viewsets_without_auth, [],
            f"The following viewsets don't have authentication configured: {viewsets_without_auth}"
        )
    
    def test_api_urls_follow_versioning_pattern(self):
        """Test that all API URLs follow the /api/v1/... pattern."""
        non_compliant_patterns = []
        api_patterns = self._get_api_url_patterns()
        
        for pattern in api_patterns:
            pattern_str = str(pattern.pattern)
            if not re.search(r'api/v\d+/', pattern_str):
                non_compliant_patterns.append(pattern_str)
        
        self.assertEqual(
            non_compliant_patterns, [],
            f"The following API URL patterns don't follow the /api/v1/... format: {non_compliant_patterns}"
        )
    
    def test_openapi_schema_generation(self):
        """Test that the OpenAPI schema can be generated without errors."""
        generator = SchemaGenerator(
            title='AquaMind API',
            version='1.0.0',
            description='AquaMind API Documentation',
        )
        
        try:
            schema = generator.get_schema()
            validation_errors = validate_schema(schema)
            # validate_schema returns `None` when the schema is valid.
            # Treat that as a passing case; otherwise ensure the list is empty.
            if validation_errors is not None:
                self.assertEqual(
                    validation_errors, [],
                    f"OpenAPI schema validation errors: {validation_errors}"
                )
        except Exception as e:
            self.fail(f"OpenAPI schema generation failed: {str(e)}")
    
    def test_security_definitions_in_schema(self):
        """Test that the OpenAPI schema has security definitions."""
        generator = SchemaGenerator(
            title='AquaMind API',
            version='1.0.0',
            description='AquaMind API Documentation',
        )
        
        schema = generator.get_schema()
        
        # Check that security schemes are defined
        self.assertIn('components', schema)
        self.assertIn('securitySchemes', schema['components'])
        
        # Check that at least one security scheme is defined
        security_schemes = schema['components']['securitySchemes']
        self.assertGreater(len(security_schemes), 0)
        
        # Check that paths have security requirements
        secure_paths = 0
        for path, methods in schema['paths'].items():
            for method, operation in methods.items():
                if method != 'parameters':  # Skip parameters key
                    if 'security' in operation:
                        secure_paths += 1
                        break
        
        # At least some paths should have security requirements
        self.assertGreater(secure_paths, 0)


class APIVersioningTestCase(APITestCase):
    """Test case for API versioning."""
    
    def test_api_version_header(self):
        """Test that API responses include version headers."""
        # Skip if version headers are not configured
        if not hasattr(settings, 'REST_FRAMEWORK') or 'DEFAULT_VERSION' not in settings.REST_FRAMEWORK:
            self.skipTest("API versioning not configured in settings")
        
        # Make a request to the API root
        response = self.client.get('/api/v1/')
        
        # Check for version header
        self.assertIn('API-Version', response.headers)
        self.assertEqual(response.headers['API-Version'], settings.REST_FRAMEWORK['DEFAULT_VERSION'])

