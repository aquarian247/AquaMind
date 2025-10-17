"""
Tests for enhanced LiceCount model with LiceType integration.

This module tests the new normalized lice tracking format alongside
backward compatibility with the legacy format.
"""

from django.test import TestCase
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model

from apps.health.models import LiceCount, LiceType
from apps.batch.models import Batch, Species, LifeCycleStage
from apps.infrastructure.models import (
    Geography, Area, Container, ContainerType
)

User = get_user_model()


class EnhancedLiceCountModelTest(TestCase):
    """Test cases for enhanced LiceCount model."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )

        # Create geography
        self.geography = Geography.objects.create(
            name='Test Geography'
        )

        # Create area
        self.area = Area.objects.create(
            name='Test Area',
            geography=self.geography,
            latitude=62.0,
            longitude=-6.8,
            max_biomass=10000
        )

        # Create container type and container
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

        # Create species and lifecycle stage
        self.species, _ = Species.objects.get_or_create(
            name='Atlantic Salmon',
            defaults={'scientific_name': 'Salmo salar'}
        )
        self.lifecycle_stage, _ = LifeCycleStage.objects.get_or_create(
            name='Post-Smolt',
            species=self.species,
            defaults={'order': 5}
        )

        # Create batch
        self.batch = Batch.objects.create(
            batch_number='TEST-001',
            species=self.species,
            lifecycle_stage=self.lifecycle_stage,
            status='ACTIVE',
            start_date='2024-01-01',
            batch_type='STANDARD',
            notes='Test batch for lice count tests'
        )

        # Get or create lice types (may exist from migration)
        self.adult_female_type, _ = LiceType.objects.get_or_create(
            species='Lepeophtheirus salmonis',
            gender='female',
            development_stage='adult',
            defaults={
                'description': 'Gravid adult female salmon louse'
            }
        )
        self.juvenile_type, _ = LiceType.objects.get_or_create(
            species='Unknown',
            gender='unknown',
            development_stage='juvenile',
            defaults={
                'description': 'Unidentified juvenile lice'
            }
        )

    def test_create_lice_count_with_new_format(self):
        """Test creating lice count with new normalized format."""
        lice_count = LiceCount.objects.create(
            batch=self.batch,
            container=self.container,
            user=self.user,
            lice_type=self.adult_female_type,
            count_value=50,
            fish_sampled=10,
            detection_method='manual',
            confidence_level=0.95
        )

        self.assertEqual(lice_count.lice_type, self.adult_female_type)
        self.assertEqual(lice_count.count_value, 50)
        self.assertEqual(lice_count.detection_method, 'manual')
        self.assertEqual(lice_count.confidence_level, 0.95)
        self.assertEqual(lice_count.total_count, 50)
        self.assertEqual(lice_count.average_per_fish, 5.0)

    def test_create_lice_count_with_legacy_format(self):
        """Test creating lice count with legacy format."""
        lice_count = LiceCount.objects.create(
            batch=self.batch,
            container=self.container,
            user=self.user,
            adult_female_count=30,
            adult_male_count=20,
            juvenile_count=50,
            fish_sampled=10
        )

        self.assertEqual(lice_count.adult_female_count, 30)
        self.assertEqual(lice_count.adult_male_count, 20)
        self.assertEqual(lice_count.juvenile_count, 50)
        self.assertEqual(lice_count.total_count, 100)
        self.assertEqual(lice_count.average_per_fish, 10.0)

    def test_validation_prevents_mixed_formats(self):
        """Test validation prevents using both formats."""
        lice_count = LiceCount(
            batch=self.batch,
            user=self.user,
            # Using both formats - should fail
            adult_female_count=30,
            lice_type=self.adult_female_type,
            count_value=50,
            fish_sampled=10
        )
        with self.assertRaises(ValidationError):
            lice_count.full_clean()

    def test_validation_requires_format(self):
        """Test validation requires at least one format."""
        lice_count = LiceCount(
            batch=self.batch,
            user=self.user,
            fish_sampled=10
            # No counts provided
        )
        with self.assertRaises(ValidationError):
            lice_count.full_clean()

    def test_validation_requires_both_lice_type_and_count(self):
        """Test both lice_type and count_value must be provided."""
        lice_count = LiceCount(
            batch=self.batch,
            user=self.user,
            lice_type=self.adult_female_type,
            # count_value not provided
            fish_sampled=10
        )
        with self.assertRaises(ValidationError):
            lice_count.full_clean()

    def test_confidence_level_validation(self):
        """Test confidence level must be between 0 and 1."""
        lice_count = LiceCount(
            batch=self.batch,
            user=self.user,
            lice_type=self.adult_female_type,
            count_value=50,
            fish_sampled=10,
            confidence_level=1.5  # Invalid - > 1.0
        )
        with self.assertRaises(ValidationError):
            lice_count.full_clean()

    def test_total_count_with_new_format(self):
        """Test total_count property with new format."""
        lice_count = LiceCount.objects.create(
            batch=self.batch,
            user=self.user,
            lice_type=self.adult_female_type,
            count_value=75,
            fish_sampled=10
        )
        self.assertEqual(lice_count.total_count, 75)

    def test_total_count_with_legacy_format(self):
        """Test total_count property with legacy format."""
        lice_count = LiceCount.objects.create(
            batch=self.batch,
            user=self.user,
            adult_female_count=30,
            adult_male_count=20,
            juvenile_count=10,
            fish_sampled=10
        )
        self.assertEqual(lice_count.total_count, 60)

    def test_average_per_fish_with_new_format(self):
        """Test average_per_fish with new format."""
        lice_count = LiceCount.objects.create(
            batch=self.batch,
            user=self.user,
            lice_type=self.adult_female_type,
            count_value=100,
            fish_sampled=20
        )
        self.assertEqual(lice_count.average_per_fish, 5.0)

    def test_average_per_fish_with_zero_fish(self):
        """Test average_per_fish returns 0 when no fish sampled."""
        lice_count = LiceCount(
            batch=self.batch,
            user=self.user,
            adult_female_count=50,
            fish_sampled=0
        )
        self.assertEqual(lice_count.average_per_fish, 0)

    def test_string_representation_new_format(self):
        """Test __str__ with new format."""
        lice_count = LiceCount.objects.create(
            batch=self.batch,
            user=self.user,
            lice_type=self.adult_female_type,
            count_value=50,
            fish_sampled=10
        )
        self.assertIn('50', str(lice_count))
        self.assertIn('L. salmonis', str(lice_count))

    def test_string_representation_legacy_format(self):
        """Test __str__ with legacy format."""
        lice_count = LiceCount.objects.create(
            batch=self.batch,
            user=self.user,
            adult_female_count=30,
            adult_male_count=20,
            juvenile_count=10,
            fish_sampled=10
        )
        self.assertIn('60', str(lice_count))

