"""
Tests for the AreaGroup API endpoints.

This module tests CRUD and filtering behavior for hierarchical area groups.
"""

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.infrastructure.models import Geography, AreaGroup


def get_response_items(response):
    """Return list items for paginated or non-paginated API responses."""
    if hasattr(response.data, "get") and "results" in response.data:
        return response.data["results"]
    return response.data


class AreaGroupAPITest(APITestCase):
    """Test suite for AreaGroup API endpoints."""

    def setUp(self):
        """Set up test data."""
        user_model = get_user_model()
        self.admin_user = user_model.objects.create_superuser(
            "admin", "admin@example.com", "password"
        )
        self.client.force_authenticate(user=self.admin_user)

        self.geo_one = Geography.objects.create(
            name="Geo One",
            description="Primary geography",
        )
        self.geo_two = Geography.objects.create(
            name="Geo Two",
            description="Secondary geography",
        )

        self.parent_group = AreaGroup.objects.create(
            name="North Cluster",
            code="NTH",
            geography=self.geo_one,
            active=True,
        )
        self.child_group = AreaGroup.objects.create(
            name="North-East",
            code="NE",
            geography=self.geo_one,
            parent=self.parent_group,
            active=True,
        )

        self.list_url = reverse("area-groups-list")
        self.detail_url = reverse("area-groups-detail", kwargs={"pk": self.child_group.pk})

    def test_list_area_groups(self):
        """Test retrieving area groups."""
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        items = get_response_items(response)
        self.assertGreaterEqual(len(items), 2)

    def test_create_area_group(self):
        """Test creating a child area group."""
        payload = {
            "name": "North-West",
            "code": "NW",
            "geography": self.geo_one.id,
            "parent": self.parent_group.id,
            "active": True,
        }
        response = self.client.post(self.list_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["name"], payload["name"])
        self.assertEqual(response.data["parent"], self.parent_group.id)
        self.assertEqual(response.data["geography"], self.geo_one.id)

    def test_parent_must_match_geography(self):
        """Test validation that parent and child must share geography."""
        payload = {
            "name": "Invalid Group",
            "code": "INV",
            "geography": self.geo_two.id,
            "parent": self.parent_group.id,  # geo_one parent
            "active": True,
        }
        response = self.client.post(self.list_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("parent", response.data)

    def test_filter_by_geography(self):
        """Test filtering area groups by geography."""
        AreaGroup.objects.create(
            name="South Cluster",
            code="STH",
            geography=self.geo_two,
            active=True,
        )

        response = self.client.get(f"{self.list_url}?geography={self.geo_one.id}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        items = get_response_items(response)
        self.assertTrue(all(item["geography"] == self.geo_one.id for item in items))

    def test_filter_root_groups(self):
        """Test filtering only root area groups via parent__isnull."""
        response = self.client.get(f"{self.list_url}?parent__isnull=true")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        items = get_response_items(response)
        self.assertTrue(all(item["parent"] is None for item in items))
