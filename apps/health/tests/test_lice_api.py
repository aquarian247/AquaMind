"""
Tests for enhanced lice count API endpoints.

This module tests the LiceType and LiceCount ViewSets, including
the new summary and trends aggregation endpoints.
"""

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from django.contrib.auth import get_user_model
from datetime import datetime, timedelta

from apps.health.models import LiceCount, LiceType
from apps.batch.models import Batch, Species, LifeCycleStage
from apps.infrastructure.models import (
    Geography, Area, Container, ContainerType
)

User = get_user_model()


class LiceTypeAPITest(TestCase):
    """Test cases for LiceType API endpoints."""

    def setUp(self):
        """Set up test data."""
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.client.force_authenticate(user=self.user)

        # Get or create lice types (may exist from migration)
        self.adult_female, _ = LiceType.objects.get_or_create(
            species='Lepeophtheirus salmonis',
            gender='female',
            development_stage='adult',
            defaults={
                'description': 'Gravid adult female salmon louse'
            }
        )
        self.juvenile, _ = LiceType.objects.get_or_create(
            species='Unknown',
            gender='unknown',
            development_stage='juvenile',
            defaults={
                'description': 'Unidentified juvenile lice'
            }
        )

    def test_list_lice_types(self):
        """Test listing lice types."""
        url = reverse('lice-type-list')
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data['results']), 2)

    def test_retrieve_lice_type(self):
        """Test retrieving a specific lice type."""
        url = reverse('lice-type-detail', args=[self.adult_female.id])
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data['species'],
            'Lepeophtheirus salmonis'
        )
        self.assertEqual(response.data['gender'], 'female')

    def test_filter_by_species(self):
        """Test filtering lice types by species."""
        url = reverse('lice-type-list')
        response = self.client.get(
            url,
            {'species': 'Lepeophtheirus salmonis'}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data['results']), 2)

    def test_filter_by_development_stage(self):
        """Test filtering lice types by development stage."""
        url = reverse('lice-type-list')
        response = self.client.get(url, {'development_stage': 'adult'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data['results']
        for lice_type in results:
            self.assertEqual(lice_type['development_stage'], 'adult')


class LiceCountSummaryAPITest(TestCase):
    """Test cases for LiceCount summary endpoint."""

    def setUp(self):
        """Set up test data."""
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.client.force_authenticate(user=self.user)

        # Create infrastructure
        self.geography = Geography.objects.create(name='Test Geo')
        self.area = Area.objects.create(
            name='Test Area',
            geography=self.geography,
            latitude=62.0,
            longitude=-6.8,
            max_biomass=10000
        )
        self.container_type = ContainerType.objects.create(
            name='Test Pen',
            category='PEN',
            max_volume_m3=5000
        )
        self.container = Container.objects.create(
            name='Pen 1',
            container_type=self.container_type,
            area=self.area,
            volume_m3=1000,
            max_biomass_kg=8000
        )

        # Create batch
        self.species, _ = Species.objects.get_or_create(
            name='Atlantic Salmon',
            defaults={'scientific_name': 'Salmo salar'}
        )
        self.lifecycle_stage, _ = LifeCycleStage.objects.get_or_create(
            name='Post-Smolt',
            species=self.species,
            defaults={'order': 5}
        )
        self.batch = Batch.objects.create(
            batch_number='TEST-001',
            species=self.species,
            lifecycle_stage=self.lifecycle_stage,
            status='ACTIVE',
            start_date='2024-01-01',
            batch_type='STANDARD',
            notes='Test batch for lice API tests'
        )

        # Get or create lice types (may exist from migration)
        self.adult_female, _ = LiceType.objects.get_or_create(
            species='Lepeophtheirus salmonis',
            gender='female',
            development_stage='adult',
            defaults={
                'description': 'Gravid adult female salmon louse'
            }
        )

        # Create lice counts using new format
        LiceCount.objects.create(
            batch=self.batch,
            container=self.container,
            user=self.user,
            lice_type=self.adult_female,
            count_value=100,
            fish_sampled=20
        )

        # Create lice count using legacy format
        LiceCount.objects.create(
            batch=self.batch,
            container=self.container,
            user=self.user,
            adult_female_count=30,
            adult_male_count=20,
            juvenile_count=50,
            fish_sampled=10
        )

    def test_lice_count_summary_basic(self):
        """Test basic lice count summary."""
        url = reverse('lice-count-summary')
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data

        self.assertIn('total_counts', data)
        self.assertIn('average_per_fish', data)
        self.assertIn('fish_sampled', data)
        self.assertEqual(data['fish_sampled'], 30)  # 20 + 10
        self.assertEqual(data['total_counts'], 200)  # 100 + 100

    def test_lice_count_summary_by_geography(self):
        """Test summary filtered by geography."""
        url = reverse('lice-count-summary')
        response = self.client.get(
            url,
            {'geography': self.geography.id}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreater(response.data['total_counts'], 0)

    def test_lice_count_summary_alert_levels(self):
        """Test alert level calculation."""
        url = reverse('lice-count-summary')
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('alert_level', response.data)
        self.assertIn(
            response.data['alert_level'],
            ['good', 'warning', 'critical']
        )

    def test_lice_count_summary_by_species(self):
        """Test summary includes species breakdown."""
        url = reverse('lice-count-summary')
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('by_species', response.data)
        species_data = response.data['by_species']
        if 'Lepeophtheirus salmonis' in species_data:
            self.assertGreater(
                species_data['Lepeophtheirus salmonis'],
                0
            )


class LiceCountTrendsAPITest(TestCase):
    """Test cases for LiceCount trends endpoint."""

    def setUp(self):
        """Set up test data."""
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.client.force_authenticate(user=self.user)

        # Create minimal infrastructure
        self.geography = Geography.objects.create(name='Test Geo')
        self.area = Area.objects.create(
            name='Test Area',
            geography=self.geography,
            latitude=62.0,
            longitude=-6.8,
            max_biomass=10000
        )
        self.container_type = ContainerType.objects.create(
            name='Test Pen',
            category='PEN',
            max_volume_m3=5000
        )
        self.container = Container.objects.create(
            name='Pen 1',
            container_type=self.container_type,
            area=self.area,
            volume_m3=1000,
            max_biomass_kg=8000
        )

        # Create batch
        self.species, _ = Species.objects.get_or_create(
            name='Atlantic Salmon',
            defaults={'scientific_name': 'Salmo salar'}
        )
        self.lifecycle_stage, _ = LifeCycleStage.objects.get_or_create(
            name='Post-Smolt',
            species=self.species,
            defaults={'order': 5}
        )
        self.batch = Batch.objects.create(
            batch_number='TEST-001',
            species=self.species,
            lifecycle_stage=self.lifecycle_stage,
            status='ACTIVE',
            start_date='2024-01-01',
            batch_type='STANDARD',
            notes='Test batch for lice API tests'
        )

        # Create lice count from 30 days ago using legacy format
        past_date = datetime.now() - timedelta(days=30)
        LiceCount.objects.create(
            batch=self.batch,
            container=self.container,
            user=self.user,
            adult_female_count=50,
            adult_male_count=30,
            juvenile_count=20,
            fish_sampled=10,
            count_date=past_date
        )

    def test_lice_count_trends_weekly(self):
        """Test weekly trends aggregation."""
        url = reverse('lice-count-trends')
        response = self.client.get(url, {'interval': 'weekly'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('trends', response.data)
        trends = response.data['trends']
        self.assertIsInstance(trends, list)

        if len(trends) > 0:
            trend = trends[0]
            self.assertIn('period', trend)
            self.assertIn('average_per_fish', trend)
            self.assertIn('total_counts', trend)
            self.assertIn('fish_sampled', trend)

    def test_lice_count_trends_monthly(self):
        """Test monthly trends aggregation."""
        url = reverse('lice-count-trends')
        response = self.client.get(url, {'interval': 'monthly'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('trends', response.data)

    def test_lice_count_trends_date_range(self):
        """Test trends with custom date range."""
        url = reverse('lice-count-trends')
        start = (datetime.now() - timedelta(days=60)).strftime(
            '%Y-%m-%d'
        )
        end = datetime.now().strftime('%Y-%m-%d')

        response = self.client.get(
            url,
            {'start_date': start, 'end_date': end, 'interval': 'weekly'}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('trends', response.data)

