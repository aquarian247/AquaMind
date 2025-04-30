"""
Tests for the health app API serializers.
"""
import datetime
from decimal import Decimal
import unittest
from unittest.mock import Mock

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.test import APITestCase # To mock request context

from apps.infrastructure.models import Area, Container, Geography, ContainerType
from apps.batch.models import Species, Batch, BatchContainerAssignment, LifeCycleStage, GrowthSample
from apps.health.models import HealthParameter, JournalEntry, HealthObservation
from apps.health.api.serializers import (
    HealthParameterSerializer,
    HealthObservationSerializer,
    JournalEntrySerializer
)
from apps.batch.api.serializers import GrowthSampleSerializer

User = get_user_model()


class HealthParameterSerializerTestCase(TestCase):
    """Test cases for the HealthParameterSerializer."""

    @classmethod
    def setUpTestData(cls):
        # Create a parameter for testing
        cls.parameter = HealthParameter.objects.create(
            name='Test Parameter',
            description_score_1='Poor',
            description_score_2='Fair',
            description_score_3='Average',
            description_score_4='Good',
            description_score_5='Excellent'
        )

    def test_valid_parameter_serialization(self):
        """Test valid serialization of HealthParameter."""
        data = {
            'name': 'Fin Rot',
            'description_score_1': 'No signs',
            'description_score_2': 'Mild fraying',
            'description_score_3': 'Moderate erosion',
            'description_score_4': 'Significant damage',
            'description_score_5': 'Complete erosion'
        }
        serializer = HealthParameterSerializer(data=data)
        self.assertTrue(serializer.is_valid(), msg=serializer.errors)
        parameter = serializer.save()
        self.assertEqual(parameter.name, 'Fin Rot')
        self.assertEqual(parameter.description_score_5, 'Complete erosion')


class HealthObservationSerializerTest(TestCase):
    """Tests for HealthObservationSerializer."""

    @classmethod
    def setUpTestData(cls):
        cls.serializer_context = {'request': Mock()}
        cls.serializer_context['request'].user = cls.user = User.objects.create_user(username='testuser', password='testpass')

        # Create common objects needed for all tests
        cls.species = Species.objects.create(name='Atlantic Salmon')
        cls.stage = LifeCycleStage.objects.create(species=cls.species, name='Adult', order=5)
        
        # Setup infrastructure
        cls.geography = Geography.objects.create(name='Test Region JEntry')
        # Updated: added required fields
        cls.area = Area.objects.create(
            name='Test Area JEntry', 
            geography=cls.geography,
            latitude=Decimal('60.0'),
            longitude=Decimal('5.0'),
            max_biomass=Decimal('5000.0')
        )
        cls.container_type = ContainerType.objects.create(name='Test Cage Type JEntry', category='CAGE', max_volume_m3=1000)

        # Create batch
        cls.batch = Batch.objects.create(
            batch_number='B001', 
            species=cls.species, 
            start_date=datetime.date.today(), 
            population_count=1000, 
            biomass_kg=Decimal('500'), 
            lifecycle_stage=cls.stage
        )

        # Create container
        cls.container = Container.objects.create(
            name='TestCage1', 
            area=cls.area, 
            container_type=cls.container_type,
            volume_m3=500,
            max_biomass_kg=5000
        )

        # Create container assignment - include lifecycle_stage which is required
        cls.assignment = BatchContainerAssignment.objects.create(
            batch=cls.batch,
            container=cls.container,
            lifecycle_stage=cls.stage,  # Required field
            assignment_date=datetime.date.today(),
            population_count=1000,
            biomass_kg=Decimal('500')
        )
        cls.journal_entry = JournalEntry.objects.create(
            batch=cls.assignment.batch,
            container=cls.assignment.container,
            user=cls.user,
            category='observation',
            entry_date=timezone.now(),
            description='Test journal entry'
        )
        cls.parameter = HealthParameter.objects.create(
            name='Test Parameter',
            description_score_1='Poor',
            description_score_2='Fair',
            description_score_3='Average',
            description_score_4='Good',
            description_score_5='Excellent'
        )

    def test_valid_observation_serialization(self):
        """Test valid serialization of HealthObservation."""
        data = {
            'journal_entry': self.journal_entry.id, # Passed by context in JournalEntrySerializer
            'parameter': self.parameter.id,
            'score': 3,
            'fish_identifier': 'F-001'
        }
        # Note: Typically tested via JournalEntrySerializer's nesting
        # Standalone test needs careful handling of read_only 'journal_entry'
        serializer = HealthObservationSerializer(data=data)
        # Need to provide context if testing standalone and journal_entry is required/set by context
        # Since journal_entry is read_only=True in the serializer definition for nesting,
        # testing it standalone like this isn't the primary use case.
        # Let's adapt test to reflect its use within JournalEntrySerializer
        # We'll focus on validating fields like 'score' and 'fish_identifier'

        valid_data_for_nesting = {
            'parameter': self.parameter.id,
            'score': 5, # Test max score
            'fish_identifier': 1, # UPDATED: Changed to integer
            'journal_entry': self.journal_entry.id # ADDED: Required field
        }
        serializer_nested = HealthObservationSerializer(data=valid_data_for_nesting)
        self.assertTrue(serializer_nested.is_valid(), msg=serializer_nested.errors)

        # Test score validation (min)
        invalid_score_data = valid_data_for_nesting.copy()
        invalid_score_data['score'] = 0
        serializer_invalid = HealthObservationSerializer(data=invalid_score_data)
        self.assertFalse(serializer_invalid.is_valid())
        self.assertIn('score', serializer_invalid.errors)

        # Test score validation (max)
        invalid_score_data['score'] = 6
        serializer_invalid = HealthObservationSerializer(data=invalid_score_data)
        self.assertFalse(serializer_invalid.is_valid())
        self.assertIn('score', serializer_invalid.errors)

        # Test fish_identifier is optional
        data_no_identifier = {
            'parameter': self.parameter.id,
            'score': 1,
            'journal_entry': self.journal_entry.id # ADDED: Required field
        }
        serializer_no_id = HealthObservationSerializer(data=data_no_identifier)
        self.assertTrue(serializer_no_id.is_valid(), msg=serializer_no_id.errors) # Added msg


class JournalEntrySerializerTest(APITestCase):
    """Tests for JournalEntrySerializer."""

    @classmethod
    def setUpTestData(cls):
        # Create a user for authentication and as a foreign key reference
        cls.user = User.objects.create_user(
            username='serializer_test_user',
            password='testpass123',
            email='serializer_test@example.com'
        )

        # Create related objects needed for journal entries
        try:
            cls.geography = Geography.objects.create(
                name='Test Geography',
                description='Test description'
            )
        except Exception as e:
            raise

        try:
            cls.area = Area.objects.create(
                name='Test Area',
                geography=cls.geography,
                latitude=60.1234,
                longitude=-1.2345,
                max_biomass=10000.00,
                active=True
            )
        except Exception as e:
            raise

        try:
            cls.container_type = ContainerType.objects.create(
                name='Cage Type',
                category='CAGE',
                max_volume_m3=1000.00
            )
        except Exception as e:
            raise

        try:
            cls.container = Container.objects.create(
                area=cls.area,
                container_type=cls.container_type,
                name='Test Cage',
                volume_m3=500.00,
                max_biomass_kg=10000.00
            )
        except Exception as e:
            raise

        try:
            cls.species = Species.objects.create(
                name='Atlantic Salmon',
                scientific_name='Salmo salar'
            )
        except Exception as e:
            raise

        try:
            cls.lifecycle_stage = LifeCycleStage.objects.create(
                name='Active',
                species=cls.species,
                order=1
            )
        except Exception as e:
            raise

        try:
            cls.lifecycle_stage_growout = LifeCycleStage.objects.create(
                name='Growout',
                species=cls.species,
                order=2
            )
        except Exception as e:
            raise

        try:
            cls.batch = Batch.objects.create(
                batch_number='B003',
                species=cls.species,
                lifecycle_stage=cls.lifecycle_stage,
                start_date=datetime.date.today(),
                population_count=100,
                biomass_kg=50.00,
                avg_weight_g=500.00,
            )
        except Exception as e:
            raise
            
        try:
            cls.assignment = BatchContainerAssignment.objects.create(
                batch=cls.batch,
                container=cls.container,
                assignment_date=datetime.date.today() - datetime.timedelta(days=10),
                population_count=100,
                biomass_kg=50.00,
                lifecycle_stage=cls.lifecycle_stage
            )
        except Exception as e:
            raise

        try:
            cls.parameter = HealthParameter.objects.create(
                name='Gill Health',
                description_score_1='Healthy',
                description_score_2='Mild damage',
                description_score_3='Moderate damage',
                description_score_4='Significant damage',
                description_score_5='Severe damage',
                is_active=True
            )
        except Exception as e:
            raise

        # Create a mock request and set the user
        cls.mock_request = Mock()
        cls.mock_request.user = cls.user

        # Set serializer context with the mock request
        cls.serializer_context = {'request': cls.mock_request}

    def test_valid_journal_entry_no_nested(self):
        """Test creating a JournalEntry without observations or growth sample."""
        data = {
            'batch': self.batch.id,
            'container': self.container.id,
            'category': 'observation',  # Required field in the model
            'entry_date': timezone.now().isoformat(),
            'description': 'Simple journal entry'
        }
        serializer = JournalEntrySerializer(data=data, context=self.serializer_context)
        self.assertTrue(serializer.is_valid(), msg=serializer.errors)
        entry = serializer.save()
        self.assertEqual(entry.batch, self.batch)
        self.assertEqual(entry.container, self.container)
        self.assertEqual(entry.description, 'Simple journal entry')
        self.assertEqual(entry.user, self.user)
        self.assertFalse(entry.health_observations.exists())
        self.assertFalse(hasattr(entry, 'growth_sample')) # Check via related manager

    def test_create_journal_entry_without_observations(self):
        """Test creating a basic JournalEntry without any observations."""
        data = {
            'batch': self.batch.id,
            'container': self.container.id,
            'category': 'observation',  # Required field
            'entry_date': timezone.now().isoformat(),
            'description': 'Routine check'
        }
        serializer = JournalEntrySerializer(data=data, context=self.serializer_context)
        self.assertTrue(serializer.is_valid(), msg=serializer.errors)
        entry = serializer.save()
        self.assertEqual(entry.batch, self.batch)
        self.assertEqual(entry.container, self.container)
        self.assertEqual(entry.description, 'Routine check')
        self.assertEqual(entry.user, self.user)
        self.assertFalse(entry.health_observations.exists())
        self.assertFalse(hasattr(entry, 'growth_sample')) # Check via related manager

    def test_create_journal_entry_with_observations(self):
        """Test creating a JournalEntry with nested HealthObservations."""
        data = {
            'batch': self.batch.id,
            'container': self.container.id,
            'category': 'observation',  # Required field
            'entry_date': timezone.now().isoformat(),
            'description': 'Journal entry with observations',
            'health_observations_write': [
                {
                    'parameter': self.parameter.id,
                    'score': 3, 
                    'fish_identifier': 1
                },
                {
                    'parameter': self.parameter.id,
                    'score': 4, 
                    'fish_identifier': 2
                }
            ]
        }
        serializer = JournalEntrySerializer(data=data, context=self.serializer_context)
        self.assertTrue(serializer.is_valid(), msg=serializer.errors)
        entry = serializer.save()
        self.assertEqual(entry.batch, self.batch) # Verify derivation worked
        self.assertEqual(entry.container, self.container) # Verify derivation worked
        self.assertEqual(entry.description, 'Journal entry with observations')
        self.assertEqual(entry.health_observations.count(), 2)
        obs1 = entry.health_observations.get(fish_identifier=1)
        obs2 = entry.health_observations.get(fish_identifier=2)
        self.assertEqual(obs1.score, 3) 
        self.assertEqual(obs1.fish_identifier, 1) 
        self.assertEqual(obs2.score, 4) 
        self.assertEqual(obs2.fish_identifier, 2) 
        self.assertEqual(entry.user, self.user)

    def test_update_journal_entry_replace_observations(self):
        """Test updating a JournalEntry by replacing its observations."""
        # Create initial entry with observations
        initial_obs_data = [
            {'parameter': self.parameter.id, 'score': 3, 'fish_identifier': 1}
        ]
        create_data = {
            'batch': self.batch.id,
            'container': self.container.id,
            'category': 'observation',  # Required field
            'description': 'Initial observation entry',  # Required field
            'entry_date': timezone.now().isoformat(),
            'health_observations_write': initial_obs_data
        }
        create_serializer = JournalEntrySerializer(data=create_data, context=self.serializer_context)
        self.assertTrue(create_serializer.is_valid(), msg=create_serializer.errors)
        journal_entry = create_serializer.save()

        # Ensure the parameter instance is available for update
        update_parameter = HealthParameter.objects.create(
            name='Update Test Parameter',
            description_score_1='Score 1 description for update',
            description_score_2='Score 2 description for update',
            description_score_3='Score 3 description for update',
            description_score_4='Score 4 description for update',
            description_score_5='Score 5 description for update',
            is_active=True
        )

        # Update with new observations
        update_obs_data = [
            {'parameter': update_parameter.id, 'score': 4, 'fish_identifier': 3}
        ]
        update_data = {
            'entry_date': timezone.now().isoformat(),
            'description': 'Updated entry',
            'health_observations_write': update_obs_data
        }
        update_serializer = JournalEntrySerializer(journal_entry, data=update_data, partial=True, context=self.serializer_context)
        if not update_serializer.is_valid():
            print(f"[Debug] Update serializer errors: {update_serializer.errors}")
        self.assertTrue(update_serializer.is_valid(), msg=update_serializer.errors)
        updated_entry = update_serializer.save()
        self.assertEqual(updated_entry.health_observations.count(), 1, "Should have exactly one observation after update")
        # Check the updated observation details
        updated_obs = updated_entry.health_observations.first()
        self.assertEqual(updated_obs.parameter, update_parameter)
        self.assertEqual(updated_obs.score, 4)
        self.assertEqual(updated_obs.fish_identifier, 3) # ADDED assertion
        self.assertEqual(updated_entry.description, 'Updated entry')
