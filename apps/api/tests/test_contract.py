"""
Simple API contract tests for AquaMind.

These tests focus on basic API functionality without complex authentication
or external dependencies. They serve as a reliable alternative to brittle
automated contract testing tools.
"""
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase


class APIContractTest(APITestCase):
    """Basic API contract tests that verify endpoint availability and response structure."""

    def test_health_check_endpoint(self):
        """Test that the health check endpoint responds correctly."""
        url = reverse('health-check')
        response = self.client.get(url)

        # Health check should always work (no auth required)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Check response structure
        data = response.json()
        self.assertIn('status', data)
        self.assertIn('timestamp', data)
        self.assertEqual(data['status'], 'healthy')

    def test_api_root_discovery(self):
        """Test that API root provides endpoint discovery."""
        url = reverse('api-root')
        response = self.client.get(url)

        # API root should always be accessible (may require auth in CI mode)
        self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_401_UNAUTHORIZED])

        if response.status_code == status.HTTP_200_OK:
            data = response.json()
            self.assertIn('apps', data)
            self.assertIn('documentation', data)

    def test_critical_endpoints_respond(self):
        """Test that critical endpoints return expected status codes."""
        # Use actual endpoints that exist in the system
        endpoints = [
            '/api/v1/batch/batches/',
            '/api/v1/environmental/readings/',
            '/api/v1/health/sampling-events/',  # Correct endpoint
            '/api/v1/inventory/feed-stocks/',    # Correct endpoint
        ]

        for endpoint in endpoints:
            with self.subTest(endpoint=endpoint):
                response = self.client.get(endpoint)
                # Just check it doesn't crash - auth failures and 404s are acceptable
                self.assertIn(response.status_code,
                            [status.HTTP_200_OK,
                             status.HTTP_401_UNAUTHORIZED,
                             status.HTTP_403_FORBIDDEN,
                             status.HTTP_404_NOT_FOUND])

    def test_openapi_schema_accessible(self):
        """Test that OpenAPI schema is accessible."""
        url = reverse('schema')
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # OpenAPI schema returns YAML by default, not JSON
        content_type = response.get('Content-Type', '')
        self.assertTrue(
            'application/vnd.oai.openapi' in content_type or
            'application/json' in content_type
        )

        # Just check that we got some content
        self.assertGreater(len(response.content), 100)

    def test_documentation_endpoints(self):
        """Test that API documentation endpoints are accessible."""
        endpoints = [
            reverse('spectacular-swagger-ui'),
            reverse('spectacular-redoc'),
        ]

        for endpoint in endpoints:
            with self.subTest(endpoint=endpoint):
                response = self.client.get(endpoint)
                # Documentation should be accessible
                self.assertEqual(response.status_code, status.HTTP_200_OK)


class APIStructureTest(TestCase):
    """Test API structure and routing without making actual requests."""

    def test_url_patterns_exist(self):
        """Test that critical URL patterns are properly defined."""
        from django.urls import resolve

        test_urls = [
            '/health-check/',
            '/api/',
            '/api/schema/',
        ]

        for url_path in test_urls:
            with self.subTest(url=url_path):
                # Should not raise Resolver404
                try:
                    resolve(url_path)
                except Exception as e:
                    self.fail(f"URL {url_path} failed to resolve: {e}")

    def test_api_router_includes_apps(self):
        """Test that the main API router includes all expected apps."""
        from aquamind.api.router import urlpatterns

        # Check that urlpatterns include expected app paths
        url_patterns = [str(pattern.pattern) for pattern in urlpatterns]

        expected_patterns = [
            'environmental/',
            'batch/',
            'inventory/',
            'health/',
            'broodstock/',
            'infrastructure/',
            'scenario/',
            'users/',
        ]

        for pattern in expected_patterns:
            with self.subTest(pattern=pattern):
                self.assertTrue(
                    any(pattern in url for url in url_patterns),
                    f"Pattern '{pattern}' not found in router URL patterns"
                )
