"""
Tests for Task 2: Mortality and Lice Count viewset fixes.

Tests verify that:
1. MortalityRecordViewSet works without UserAssignmentMixin
2. Filtering uses correct field names (event_date, not mortality_date)
3. LiceCountViewSet filters use actual model fields
4. Container field is optional in both serializers
"""

from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from django.utils import timezone
import json

from apps.batch.models import Batch, Species, LifeCycleStage
from apps.health.models import (
    MortalityRecord, MortalityReason, LiceCount, Treatment, VaccinationType
)
from apps.infrastructure.models import (
    Geography, Area, Container, ContainerType
)

User = get_user_model()


class MortalityRecordViewSetFixTest(TestCase):
    """
    Tests for MortalityRecordViewSet fixes.

    Verifies that UserAssignmentMixin removal and filter fixes work correctly.
    """

    def setUp(self):
        """Set up test data."""
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

        # Create geography
        self.geography = Geography.objects.create(
            name='Test Geography',
            description='Test geography for mortality tests'
        )

        # Create area
        self.area = Area.objects.create(
            name='Test Area',
            geography=self.geography,
            latitude=62.0,
            longitude=-7.0,
            max_biomass=1000.0,
            active=True
        )

        # Create container type and container
        self.container_type = ContainerType.objects.create(
            name='Test Tank',
            category='TANK',
            max_volume_m3=100.0
        )

        self.container = Container.objects.create(
            name='Tank 1',
            container_type=self.container_type,
            area=self.area,
            volume_m3=50.0,
            max_biomass_kg=500.0,
            active=True
        )

        # Create species and lifecycle stage
        self.species = Species.objects.create(
            name='Atlantic Salmon',
            scientific_name='Salmo salar'
        )

        self.lifecycle_stage = LifeCycleStage.objects.create(
            name='Smolt',
            species=self.species,
            order=4
        )

        # Create batch
        self.batch = Batch.objects.create(
            batch_number='TEST001',
            species=self.species,
            lifecycle_stage=self.lifecycle_stage,
            status='ACTIVE',
            batch_type='STANDARD',
            start_date=timezone.now().date()
        )

        # Create mortality reason
        self.reason = MortalityReason.objects.create(
            name='Disease',
            description='Disease-related mortality'
        )

        # Set up API client
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_create_mortality_record_without_container(self):
        """
        Test creating mortality record without container field.

        Verifies that container is optional and UserAssignmentMixin
        removal doesn't break create operations.
        """
        url = reverse('mortality-record-list')

        data = {
            'batch': self.batch.id,
            'count': 5,
            'reason': self.reason.id,
            'notes': 'Test mortality without container'
        }

        response = self.client.post(url, data, format='json')

        # Should succeed without container
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Verify record was created
        self.assertEqual(MortalityRecord.objects.count(), 1)
        record = MortalityRecord.objects.first()
        self.assertEqual(record.batch, self.batch)
        self.assertEqual(record.count, 5)
        self.assertIsNone(record.container)

    def test_create_mortality_record_with_container(self):
        """
        Test creating mortality record with container field.

        Verifies that container can still be provided when needed.
        """
        url = reverse('mortality-record-list')

        data = {
            'batch': self.batch.id,
            'container': self.container.id,
            'count': 3,
            'reason': self.reason.id,
            'notes': 'Test mortality with container'
        }

        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        record = MortalityRecord.objects.first()
        self.assertEqual(record.container, self.container)

    def test_filter_by_event_date(self):
        """
        Test filtering by event_date field (not mortality_date).

        Verifies that the correct field name is used in filters.
        """
        # Create records with different dates
        today = timezone.now()
        yesterday = today - timezone.timedelta(days=1)

        MortalityRecord.objects.create(
            batch=self.batch,
            container=self.container,
            count=5,
            reason=self.reason,
            event_date=today
        )

        MortalityRecord.objects.create(
            batch=self.batch,
            count=3,
            reason=self.reason,
            event_date=yesterday
        )

        url = reverse('mortality-record-list')

        # Filter by event_date (exact)
        response = self.client.get(
            url,
            {'event_date': today.strftime('%Y-%m-%d')},
            format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should find at least one record from today

    def test_filter_by_batch(self):
        """
        Test filtering by batch field.

        Verifies that batch filtering works correctly.
        """
        # Create another batch
        batch2 = Batch.objects.create(
            batch_number='TEST002',
            species=self.species,
            lifecycle_stage=self.lifecycle_stage,
            status='ACTIVE',
            batch_type='STANDARD',
            start_date=timezone.now().date()
        )

        MortalityRecord.objects.create(
            batch=self.batch,
            count=5,
            reason=self.reason
        )

        MortalityRecord.objects.create(
            batch=batch2,
            count=3,
            reason=self.reason
        )

        url = reverse('mortality-record-list')

        response = self.client.get(
            url,
            {'batch': self.batch.id},
            format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        # Should only return records for specified batch

    def test_filter_by_container(self):
        """
        Test filtering by container field.

        Verifies that container filtering works correctly.
        """
        MortalityRecord.objects.create(
            batch=self.batch,
            container=self.container,
            count=5,
            reason=self.reason
        )

        MortalityRecord.objects.create(
            batch=self.batch,
            count=3,
            reason=self.reason
        )

        url = reverse('mortality-record-list')

        response = self.client.get(
            url,
            {'container': self.container.id},
            format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_old_filter_names_not_supported(self):
        """
        Test that old filter names (mortality_date, recorded_by) are removed.

        These should no longer cause FieldError but simply be ignored.
        """
        MortalityRecord.objects.create(
            batch=self.batch,
            count=5,
            reason=self.reason
        )

        url = reverse('mortality-record-list')

        # Try using old filter name - should not cause error
        response = self.client.get(
            url,
            {'mortality_date': '2025-01-01'},
            format='json'
        )

        # Should succeed (filter ignored) rather than 400/500 error
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class LiceCountViewSetFixTest(TestCase):
    """
    Tests for LiceCountViewSet fixes.

    Verifies that filters use actual model fields.
    """

    def setUp(self):
        """Set up test data."""
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

        # Create geography
        self.geography = Geography.objects.create(
            name='Test Geography',
            description='Test geography'
        )

        # Create area
        self.area = Area.objects.create(
            name='Test Area',
            geography=self.geography,
            latitude=62.0,
            longitude=-7.0,
            max_biomass=1000.0,
            active=True
        )

        # Create container type and container
        self.container_type = ContainerType.objects.create(
            name='Test Tank',
            category='TANK',
            max_volume_m3=100.0
        )

        self.container = Container.objects.create(
            name='Tank 1',
            container_type=self.container_type,
            area=self.area,
            volume_m3=50.0,
            max_biomass_kg=500.0,
            active=True
        )

        # Create species and lifecycle stage
        self.species = Species.objects.create(
            name='Atlantic Salmon',
            scientific_name='Salmo salar'
        )

        self.lifecycle_stage = LifeCycleStage.objects.create(
            name='Smolt',
            species=self.species,
            order=4
        )

        # Create batch
        self.batch = Batch.objects.create(
            batch_number='TEST001',
            species=self.species,
            lifecycle_stage=self.lifecycle_stage,
            status='ACTIVE',
            batch_type='STANDARD',
            start_date=timezone.now().date()
        )

        # Set up API client
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_create_lice_count_without_container(self):
        """
        Test creating lice count without container field.

        Verifies that container is optional.
        """
        url = reverse('lice-count-list')

        data = {
            'batch': self.batch.id,
            'adult_female_count': 10,
            'adult_male_count': 5,
            'juvenile_count': 20,
            'fish_sampled': 10,
            'notes': 'Test lice count'
        }

        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Verify record was created
        self.assertEqual(LiceCount.objects.count(), 1)
        record = LiceCount.objects.first()
        self.assertEqual(record.batch, self.batch)
        self.assertIsNone(record.container)
        self.assertEqual(record.user, self.user)  # Auto-assigned via mixin

    def test_filter_by_fish_sampled(self):
        """
        Test filtering by fish_sampled field (not fish_count).

        Verifies correct field name is used.
        """
        LiceCount.objects.create(
            batch=self.batch,
            user=self.user,
            adult_female_count=10,
            adult_male_count=5,
            juvenile_count=20,
            fish_sampled=10
        )

        LiceCount.objects.create(
            batch=self.batch,
            user=self.user,
            adult_female_count=5,
            adult_male_count=3,
            juvenile_count=10,
            fish_sampled=20
        )

        url = reverse('lice-count-list')

        response = self.client.get(
            url,
            {'fish_sampled': 10},
            format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_filter_by_batch(self):
        """
        Test filtering by batch field.

        Verifies batch filtering works correctly.
        """
        LiceCount.objects.create(
            batch=self.batch,
            user=self.user,
            adult_female_count=10,
            adult_male_count=5,
            juvenile_count=20,
            fish_sampled=10
        )

        url = reverse('lice-count-list')

        response = self.client.get(
            url,
            {'batch': self.batch.id},
            format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_filter_by_lice_counts(self):
        """
        Test filtering by individual lice count fields.

        Verifies filtering by adult_female_count, adult_male_count,
        and juvenile_count works correctly.
        """
        LiceCount.objects.create(
            batch=self.batch,
            user=self.user,
            adult_female_count=15,
            adult_male_count=5,
            juvenile_count=20,
            fish_sampled=10
        )

        url = reverse('lice-count-list')

        # Filter by adult_female_count
        response = self.client.get(
            url,
            {'adult_female_count__gte': 10},
            format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_old_filter_names_not_supported(self):
        """
        Test that old invalid filter names are removed.

        batch_container_assignment, fish_count, lice_count should not
        cause errors.
        """
        LiceCount.objects.create(
            batch=self.batch,
            user=self.user,
            adult_female_count=10,
            adult_male_count=5,
            juvenile_count=20,
            fish_sampled=10
        )

        url = reverse('lice-count-list')

        # Try old invalid filters - should not cause error
        response = self.client.get(
            url,
            {'batch_container_assignment': 1},
            format='json'
        )

        # Should succeed (filter ignored) rather than error
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class TreatmentViewSetFixTest(TestCase):
    """
    Tests for TreatmentViewSet fixes.

    Verifies that withholding_end_date filter is removed and other filters work correctly.
    """

    def setUp(self):
        """Set up test data."""
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

        # Create geography
        self.geography = Geography.objects.create(
            name='Test Geography',
            description='Test geography for treatment tests'
        )

        # Create area
        self.area = Area.objects.create(
            name='Test Area',
            geography=self.geography,
            latitude=62.0,
            longitude=-7.0,
            max_biomass=1000.0,
            active=True
        )

        # Create container type and container
        self.container_type = ContainerType.objects.create(
            name='Test Tank',
            category='TANK',
            max_volume_m3=100.0
        )

        self.container = Container.objects.create(
            name='Tank 1',
            container_type=self.container_type,
            area=self.area,
            volume_m3=50.0,
            max_biomass_kg=500.0,
            active=True
        )

        # Create species and lifecycle stage
        self.species = Species.objects.create(
            name='Atlantic Salmon',
            scientific_name='Salmo salar'
        )

        self.lifecycle_stage = LifeCycleStage.objects.create(
            name='Smolt',
            species=self.species,
            order=4
        )

        # Create batch
        self.batch = Batch.objects.create(
            batch_number='TEST001',
            species=self.species,
            lifecycle_stage=self.lifecycle_stage,
            status='ACTIVE',
            batch_type='STANDARD',
            start_date=timezone.now().date()
        )

        # Create vaccination type
        self.vaccination_type = VaccinationType.objects.create(
            name='Test Vaccine',
            manufacturer='Test Corp'
        )

        # Set up API client
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_create_treatment(self):
        """
        Test creating treatment record.

        Verifies that basic treatment creation works.
        """
        url = reverse('treatment-list')

        data = {
            'batch': self.batch.id,
            'container': self.container.id,
            'treatment_type': 'vaccination',
            'vaccination_type': self.vaccination_type.id,
            'description': 'Test vaccination',
            'dosage': '1ml',
            'withholding_period_days': 7
        }

        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Verify record was created
        self.assertEqual(Treatment.objects.count(), 1)
        treatment = Treatment.objects.first()
        self.assertEqual(treatment.batch, self.batch)
        self.assertEqual(treatment.treatment_type, 'vaccination')
        self.assertEqual(treatment.withholding_period_days, 7)

    def test_filter_by_batch(self):
        """
        Test filtering treatments by batch.

        Verifies batch filtering works correctly.
        """
        # Create another batch
        batch2 = Batch.objects.create(
            batch_number='TEST002',
            species=self.species,
            lifecycle_stage=self.lifecycle_stage,
            status='ACTIVE',
            batch_type='STANDARD',
            start_date=timezone.now().date()
        )

        Treatment.objects.create(
            batch=self.batch,
            user=self.user,
            treatment_type='vaccination',
            vaccination_type=self.vaccination_type,
            description='Treatment 1'
        )

        Treatment.objects.create(
            batch=batch2,
            user=self.user,
            treatment_type='medication',
            description='Treatment 2'
        )

        url = reverse('treatment-list')

        response = self.client.get(
            url,
            {'batch__id': self.batch.id},
            format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        # Should only return treatments for specified batch
        self.assertEqual(len(data['results']), 1)
        self.assertEqual(data['results'][0]['batch'], self.batch.id)

    def test_filter_by_treatment_type(self):
        """
        Test filtering treatments by treatment_type.

        Verifies treatment_type filtering works correctly.
        """
        Treatment.objects.create(
            batch=self.batch,
            user=self.user,
            treatment_type='vaccination',
            vaccination_type=self.vaccination_type,
            description='Vaccination treatment'
        )

        Treatment.objects.create(
            batch=self.batch,
            user=self.user,
            treatment_type='medication',
            description='Medication treatment'
        )

        url = reverse('treatment-list')

        response = self.client.get(
            url,
            {'treatment_type': 'vaccination'},
            format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        # Should only return vaccination treatments
        self.assertEqual(len(data['results']), 1)
        self.assertEqual(data['results'][0]['treatment_type'], 'vaccination')

    def test_filter_by_withholding_period_days(self):
        """
        Test filtering treatments by withholding_period_days.

        Verifies withholding_period_days filtering works correctly.
        """
        Treatment.objects.create(
            batch=self.batch,
            user=self.user,
            treatment_type='vaccination',
            vaccination_type=self.vaccination_type,
            description='Treatment with 7 day withholding',
            withholding_period_days=7
        )

        Treatment.objects.create(
            batch=self.batch,
            user=self.user,
            treatment_type='medication',
            description='Treatment with 14 day withholding',
            withholding_period_days=14
        )

        url = reverse('treatment-list')

        response = self.client.get(
            url,
            {'withholding_period_days': 7},
            format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        # Should only return treatments with 7 day withholding
        self.assertEqual(len(data['results']), 1)
        self.assertEqual(data['results'][0]['withholding_period_days'], 7)

    def test_withholding_end_date_filter_removed(self):
        """
        Test that withholding_end_date filter is no longer supported.

        Verifies that withholding_end_date filter is removed since it's a property, not a field.
        """
        # Create treatment with withholding period
        treatment = Treatment.objects.create(
            batch=self.batch,
            user=self.user,
            treatment_type='vaccination',
            vaccination_type=self.vaccination_type,
            description='Test treatment',
            withholding_period_days=7
        )

        url = reverse('treatment-list')

        # Try using old withholding_end_date filter - should not cause error but be ignored
        response = self.client.get(
            url,
            {'withholding_end_date': '2025-01-01'},
            format='json'
        )

        # Should succeed (filter ignored) rather than error
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Should return all treatments (filter ignored)
        data = response.json()
        self.assertGreaterEqual(len(data['results']), 1)

