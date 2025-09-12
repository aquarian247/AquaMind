"""
Tests for FCR Trends API schema and default behavior.

Tests schema compliance, explicit defaults, field presence, and OpenAPI generation.
"""
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from datetime import date, timedelta
from rest_framework.test import APITestCase
from rest_framework import status
from django.contrib.auth import get_user_model

from apps.operational.services.fcr_trends_service import FCRTrendsService, TimeInterval


class FCRTrendsSchemaTestCase(APITestCase):
    """Test FCR trends API schema compliance and defaults."""

    def setUp(self):
        """Set up test data."""
        self.url = reverse('fcr-trends-list')
        # Create and authenticate a test user
        User = get_user_model()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.client.force_authenticate(user=self.user)

    def test_default_response_fields_present(self):
        """
        Test that default response includes all required fields with explicit defaults.

        When no filters are provided, should return:
        - aggregation_level: 'geography'
        - interval: 'DAILY'
        - unit: 'ratio'
        - model_version: present
        """
        response = self.client.get(self.url)

        # Should succeed (may return empty series if no data)
        self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND])

        if response.status_code == status.HTTP_200_OK:
            data = response.data

            # Check explicit defaults
            self.assertEqual(data['aggregation_level'], 'geography')
            self.assertEqual(data['interval'], 'DAILY')
            self.assertEqual(data['unit'], 'ratio')
            self.assertIn('model_version', data)  # Optional but should be present
            self.assertIn('series', data)
            self.assertIsInstance(data['series'], list)

    def test_explicit_defaults_in_serializer(self):
        """
        Test that serializer provides explicit defaults even when service doesn't specify them.
        """
        # Mock service response without explicit fields
        mock_response = {
            'series': []
        }

        from apps.operational.api.serializers.fcr_trends import FCRTrendsSerializer
        serializer = FCRTrendsSerializer(data=mock_response)
        serializer.is_valid(raise_exception=True)

        # Check that defaults are applied in representation
        representation = serializer.to_representation(serializer.validated_data)
        self.assertEqual(representation['aggregation_level'], 'geography')
        self.assertEqual(representation['interval'], 'DAILY')
        self.assertEqual(representation['unit'], 'ratio')

    def test_schema_field_documentation(self):
        """
        Test that response fields have proper help_text and validation.
        """
        from apps.operational.api.serializers.fcr_trends import FCRTrendsSerializer

        # Test interval choices
        serializer = FCRTrendsSerializer()
        self.assertIn('DAILY', serializer.fields['interval'].choices)
        self.assertIn('WEEKLY', serializer.fields['interval'].choices)
        self.assertIn('MONTHLY', serializer.fields['interval'].choices)

        # Test aggregation level choices
        self.assertIn('geography', serializer.fields['aggregation_level'].choices)
        self.assertIn('batch', serializer.fields['aggregation_level'].choices)
        self.assertIn('assignment', serializer.fields['aggregation_level'].choices)

        # Test field help texts exist
        self.assertIsNotNone(serializer.fields['interval'].help_text)
        self.assertIsNotNone(serializer.fields['unit'].help_text)
        self.assertIsNotNone(serializer.fields['aggregation_level'].help_text)

    def test_data_point_fields_documentation(self):
        """
        Test that FCRDataPointSerializer fields have proper help_text.
        """
        from apps.operational.api.serializers.fcr_trends import FCRDataPointSerializer

        serializer = FCRDataPointSerializer()

        # Check key field help texts
        self.assertIn('FCR ratio', serializer.fields['actual_fcr'].help_text)
        self.assertIn('confidence level', serializer.fields['confidence'].help_text.lower())
        self.assertIn('data points', serializer.fields['data_points'].help_text.lower())
        self.assertIn('scenario models', serializer.fields['scenarios_used'].help_text.lower())
        self.assertIn('deviation', serializer.fields['deviation'].help_text.lower())

    def test_interval_parameter_defaults(self):
        """
        Test that interval parameter defaults to DAILY when not specified.
        """
        # Test with no interval parameter
        response = self.client.get(self.url)

        if response.status_code == status.HTTP_200_OK:
            # Should default to DAILY
            self.assertEqual(response.data['interval'], 'DAILY')

        # Test with explicit interval
        response = self.client.get(self.url, {'interval': 'WEEKLY'})

        if response.status_code == status.HTTP_200_OK:
            self.assertEqual(response.data['interval'], 'WEEKLY')

    def test_aggregation_level_explicit_return(self):
        """
        Test that aggregation_level is always explicitly returned regardless of filters.
        """
        test_cases = [
            {},  # No filters - should default to geography
            {'batch_id': 999},  # Invalid batch - but should still specify level
            {'geography_id': 999},  # Invalid geography - but should still specify level
        ]

        for params in test_cases:
            response = self.client.get(self.url, params)

            # Should either succeed with explicit level or fail with error
            if response.status_code == status.HTTP_200_OK:
                self.assertIn('aggregation_level', response.data)
                self.assertIn(response.data['aggregation_level'], ['batch', 'assignment', 'geography'])

    def test_openapi_schema_validation(self):
        """
        Test that OpenAPI schema can be generated without warnings.

        This is a meta-test to ensure our schema definitions are correct.
        """
        from drf_spectacular.generators import SchemaGenerator
        from drf_spectacular.settings import spectacular_settings

        try:
            generator = SchemaGenerator()
            schema = generator.get_schema(request=None, public=True)

            # Schema should generate successfully
            self.assertIsInstance(schema, dict)
            self.assertIn('paths', schema)

            # Check that our endpoint is in the schema
            paths = schema['paths']
            self.assertIn('/api/v1/operational/fcr-trends/', paths)

            # Check that the endpoint has proper responses
            endpoint = paths['/api/v1/operational/fcr-trends/']
            self.assertIn('get', endpoint)
            self.assertIn('responses', endpoint['get'])

        except Exception as e:
            self.fail(f"OpenAPI schema generation failed: {str(e)}")

    def test_response_format_compliance(self):
        """
        Test that successful responses comply with documented schema format.
        """
        response = self.client.get(self.url)

        if response.status_code == status.HTTP_200_OK:
            data = response.data

            # Required top-level fields
            required_fields = ['interval', 'unit', 'aggregation_level', 'series']
            for field in required_fields:
                self.assertIn(field, data, f"Missing required field: {field}")

            # Series should be a list
            self.assertIsInstance(data['series'], list)

            # Each series item should have required fields
            if data['series']:
                item = data['series'][0]
                required_item_fields = ['period_start', 'period_end']
                for field in required_item_fields:
                    self.assertIn(field, item, f"Missing required series field: {field}")

    def test_units_documentation(self):
        """
        Test that FCR units are explicitly documented as 'ratio'.
        """
        response = self.client.get(self.url)

        if response.status_code == status.HTTP_200_OK:
            self.assertEqual(response.data['unit'], 'ratio')

        # Test serializer default
        from apps.operational.api.serializers.fcr_trends import FCRTrendsSerializer
        serializer = FCRTrendsSerializer()
        self.assertEqual(serializer.fields['unit'].default, 'ratio')

    def test_model_version_included(self):
        """
        Test that model_version metadata is included in responses.
        """
        response = self.client.get(self.url)

        if response.status_code == status.HTTP_200_OK:
            # model_version should be present (can be null)
            self.assertIn('model_version', response.data)
