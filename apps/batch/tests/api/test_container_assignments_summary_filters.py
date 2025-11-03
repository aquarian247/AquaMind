"""
Tests for container-assignments summary endpoint filters.

Tests the location-based filtering functionality added to the summary endpoint.
"""
from django.contrib.auth import get_user_model
from django.core.cache import cache
from rest_framework import status
from decimal import Decimal
from tests.base import BaseAPITestCase

from apps.batch.models import BatchContainerAssignment
from apps.batch.tests.api.test_utils import (
    create_test_user,
    create_test_species,
    create_test_lifecycle_stage,
    create_test_batch,
    create_test_geography,
    create_test_area,
    create_test_freshwater_station,
    create_test_hall,
    create_test_container_type,
    create_test_container,
    create_test_batch_container_assignment
)


class ContainerAssignmentsSummaryFiltersTestCase(BaseAPITestCase):
    """Test the container-assignments summary endpoint with location filters."""

    def setUp(self):
        """Set up test data with complex location hierarchy."""
        # Create a test user with ALL geography access (these tests focus on endpoint filtering, not RBAC)
        from apps.users.models import Geography
        self.user = create_test_user(geography=Geography.ALL)
        self.client.force_authenticate(user=self.user)

        # Create species and lifecycle stage
        self.species = create_test_species(name="Atlantic Salmon")
        self.lifecycle_stage = create_test_lifecycle_stage(
            species=self.species,
            name="Fry",
            order=2
        )

        # Create location hierarchy
        self.geography1 = create_test_geography("Geography 1")
        self.geography2 = create_test_geography("Geography 2")

        # Areas directly in geographies
        self.area1 = create_test_area(geography=self.geography1, name="Area 1")
        self.area2 = create_test_area(geography=self.geography2, name="Area 2")

        # Stations in geographies
        self.station1 = create_test_freshwater_station(geography=self.geography1, name="Station 1")
        self.station2 = create_test_freshwater_station(geography=self.geography2, name="Station 2")

        # Halls in stations
        self.hall1 = create_test_hall(station=self.station1, name="Hall 1")
        self.hall2 = create_test_hall(station=self.station2, name="Hall 2")

        # Container types
        self.tank_type = create_test_container_type(name="Tank")
        # Manually set category to TANK
        self.tank_type.category = 'TANK'
        self.tank_type.save()

        self.pen_type = create_test_container_type(name="Pen")
        self.pen_type.category = 'PEN'
        self.pen_type.save()

        # Containers in different locations
        self.container_hall1 = create_test_container(hall=self.hall1, container_type=self.tank_type, name="Tank Hall 1")
        self.container_hall2 = create_test_container(hall=self.hall2, container_type=self.pen_type, name="Pen Hall 2")
        self.container_area1 = create_test_container(area=self.area1, container_type=self.tank_type, name="Tank Area 1")
        self.container_area2 = create_test_container(area=self.area2, container_type=self.pen_type, name="Pen Area 2")

        # Batches
        self.batch1 = create_test_batch(species=self.species, lifecycle_stage=self.lifecycle_stage, batch_number="BATCH001")
        self.batch2 = create_test_batch(species=self.species, lifecycle_stage=self.lifecycle_stage, batch_number="BATCH002")

        # Clear existing assignments and create test assignments
        BatchContainerAssignment.objects.all().delete()

        # Create assignments with known biomass values
        self.assignment_hall1 = create_test_batch_container_assignment(
            batch=self.batch1,
            container=self.container_hall1,
            lifecycle_stage=self.lifecycle_stage,
            population_count=1000,
            avg_weight_g=Decimal("10.0")  # 10 kg biomass
        )
        self.assignment_hall2 = create_test_batch_container_assignment(
            batch=self.batch2,
            container=self.container_hall2,
            lifecycle_stage=self.lifecycle_stage,
            population_count=2000,
            avg_weight_g=Decimal("15.0")  # 30 kg biomass
        )
        self.assignment_area1 = create_test_batch_container_assignment(
            batch=self.batch1,
            container=self.container_area1,
            lifecycle_stage=self.lifecycle_stage,
            population_count=1500,
            avg_weight_g=Decimal("20.0")  # 30 kg biomass
        )
        self.assignment_area2 = create_test_batch_container_assignment(
            batch=self.batch2,
            container=self.container_area2,
            lifecycle_stage=self.lifecycle_stage,
            population_count=500,
            avg_weight_g=Decimal("25.0")  # 12.5 kg biomass
        )

        # Create a different container for inactive assignment (can't reuse same batch+container)
        inactive_container = create_test_container(hall=self.hall1, container_type=self.tank_type, name="Inactive Tank")

        # Create inactive assignment
        self.inactive_assignment = create_test_batch_container_assignment(
            batch=self.batch1,
            container=inactive_container,
            lifecycle_stage=self.lifecycle_stage,
            population_count=300,
            avg_weight_g=Decimal("5.0")  # 1.5 kg biomass
        )
        self.inactive_assignment.is_active = False
        self.inactive_assignment.save()

    def _get_summary_url(self, **params):
        """Helper to build summary URL with query parameters."""
        url = self.get_api_url('batch', 'container-assignments/summary')
        if params:
            from urllib.parse import urlencode
            url += '?' + urlencode(params)
        return url

    def test_summary_no_filters(self):
        """Test summary endpoint without any filters (baseline)."""
        cache.clear()
        url = self._get_summary_url()
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should include all active assignments: 10 + 30 + 30 + 12.5 = 82.5 kg, 4 assignments
        self.assertEqual(response.data['active_biomass_kg'], 82.5)
        self.assertEqual(response.data['count'], 4)

    def test_filter_by_geography(self):
        """Test filtering by geography."""
        cache.clear()

        # Filter by geography 1 (should include hall1 and area1 assignments)
        url = self._get_summary_url(geography=self.geography1.id)
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should include: 10 + 30 = 40 kg, 2 assignments
        self.assertEqual(response.data['active_biomass_kg'], 40.0)
        self.assertEqual(response.data['count'], 2)

        # Filter by geography 2 (should include hall2 and area2 assignments)
        url = self._get_summary_url(geography=self.geography2.id)
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should include: 30 + 12.5 = 42.5 kg, 2 assignments
        self.assertEqual(response.data['active_biomass_kg'], 42.5)
        self.assertEqual(response.data['count'], 2)

    def test_filter_by_area(self):
        """Test filtering by area."""
        cache.clear()

        # Filter by area 1
        url = self._get_summary_url(area=self.area1.id)
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should include only area1 assignment: 30 kg, 1 assignment
        self.assertEqual(response.data['active_biomass_kg'], 30.0)
        self.assertEqual(response.data['count'], 1)

    def test_filter_by_station(self):
        """Test filtering by freshwater station."""
        cache.clear()

        # Filter by station 1
        url = self._get_summary_url(station=self.station1.id)
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should include only hall1 assignment: 10 kg, 1 assignment
        self.assertEqual(response.data['active_biomass_kg'], 10.0)
        self.assertEqual(response.data['count'], 1)

    def test_filter_by_hall(self):
        """Test filtering by hall."""
        cache.clear()

        # Filter by hall 2
        url = self._get_summary_url(hall=self.hall2.id)
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should include only hall2 assignment: 30 kg, 1 assignment
        self.assertEqual(response.data['active_biomass_kg'], 30.0)
        self.assertEqual(response.data['count'], 1)

    def test_filter_by_container_type(self):
        """Test filtering by container type category."""
        cache.clear()

        # Filter by TANK category
        url = self._get_summary_url(container_type='TANK')
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should include tank assignments: hall1 (10) + area1 (30) = 40 kg, 2 assignments
        self.assertEqual(response.data['active_biomass_kg'], 40.0)
        self.assertEqual(response.data['count'], 2)

        # Filter by PEN category
        url = self._get_summary_url(container_type='PEN')
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should include pen assignments: hall2 (30) + area2 (12.5) = 42.5 kg, 2 assignments
        self.assertEqual(response.data['active_biomass_kg'], 42.5)
        self.assertEqual(response.data['count'], 2)

    def test_filter_by_is_active_false(self):
        """Test filtering by inactive assignments."""
        cache.clear()

        # Filter by inactive assignments
        url = self._get_summary_url(is_active='false')
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should include only inactive assignment: 1.5 kg, 1 assignment
        self.assertEqual(response.data['active_biomass_kg'], 1.5)
        self.assertEqual(response.data['count'], 1)

    def test_combined_filters(self):
        """Test combining multiple filters."""
        cache.clear()

        # Filter by geography 1 AND container type TANK
        url = self._get_summary_url(geography=self.geography1.id, container_type='TANK')
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should include hall1 tank (10kg) and area1 tank (30kg): 40 kg, 2 assignments
        self.assertEqual(response.data['active_biomass_kg'], 40.0)
        self.assertEqual(response.data['count'], 2)

    def test_invalid_geography_id(self):
        """Test invalid geography ID returns 400."""
        cache.clear()

        url = self._get_summary_url(geography=99999)
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('geography', response.data)

    def test_invalid_area_id(self):
        """Test invalid area ID returns 400."""
        cache.clear()

        url = self._get_summary_url(area=99999)
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('area', response.data)

    def test_invalid_station_id(self):
        """Test invalid station ID returns 400."""
        cache.clear()

        url = self._get_summary_url(station=99999)
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('station', response.data)

    def test_invalid_hall_id(self):
        """Test invalid hall ID returns 400."""
        cache.clear()

        url = self._get_summary_url(hall=99999)
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('hall', response.data)

    def test_invalid_container_type(self):
        """Test invalid container type returns 400."""
        cache.clear()

        url = self._get_summary_url(container_type='INVALID')
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('container_type', response.data)

    def test_non_integer_ids(self):
        """Test non-integer IDs return 400."""
        cache.clear()

        # Test non-integer geography
        url = self._get_summary_url(geography='not-a-number')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Test non-integer area
        url = self._get_summary_url(area='not-a-number')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Test non-integer station
        url = self._get_summary_url(station='not-a-number')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Test non-integer hall
        url = self._get_summary_url(hall='not-a-number')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_empty_results(self):
        """Test filters that return no results."""
        cache.clear()

        # Create a third geography with no assignments
        empty_geography = create_test_geography("Empty Geography")

        url = self._get_summary_url(geography=empty_geography.id)
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['active_biomass_kg'], 0.0)
        self.assertEqual(response.data['count'], 0)
