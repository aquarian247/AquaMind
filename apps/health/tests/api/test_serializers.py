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

    def test_create_journal_entry_with_growth_sample(self):
        """Test creating a JournalEntry with a nested GrowthSample (using averages)."""
        sample_date = datetime.date.today() - datetime.timedelta(days=1)
        growth_data = {
            'sample_date': sample_date,  # Explicitly set sample_date
            'sample_size': 15,
            'avg_weight_g': Decimal('200.0'),
            'avg_length_cm': Decimal('25.0')
        }
        data = {
            'assignment': self.assignment.id,
            'entry_date': timezone.now().isoformat(),
            'description': 'Entry with average growth sample',
            'growth_sample': growth_data
        }
        serializer = JournalEntrySerializer(data=data, context=self.serializer_context)
        self.assertTrue(serializer.is_valid(), msg=serializer.errors)
        entry = serializer.save()
        self.assertEqual(entry.batch, self.batch)
        self.assertEqual(entry.container, self.container)
        self.assertEqual(entry.user, self.user)
        # Check related GrowthSample was created
        try:
            gs = GrowthSample.objects.get(assignment=self.assignment, sample_date=sample_date)
            self.assertEqual(gs.sample_size, 10)
            self.assertEqual(gs.avg_weight_g, Decimal('150.5'))
            self.assertEqual(gs.avg_length_mm, Decimal('200.2'))
            self.assertIsNotNone(gs.condition_factor)
            self.assertEqual(entry.user, self.user)
            self.assertEqual(entry.health_observations.count(), 0)  
        except GrowthSample.DoesNotExist:
            self.fail("GrowthSample was not created.")

    def test_create_journal_entry_with_growth_sample_individuals(self):
        """Test creating a JournalEntry with a nested GrowthSample using individual lists."""
        # Use a unique date for this test to avoid conflicts with other tests
        sample_date = datetime.date.today() - datetime.timedelta(days=5)
        growth_data = {
            'sample_date': sample_date,  # Add sample_date to growth_data
            'sample_size': 3,
            'individual_weights_g': [100, 110, 120],
            'individual_lengths_mm': [150, 155, 160],
            'individual_condition_factors': [1.0, 1.1, 1.2]
        }
        data = {
            'assignment': self.assignment.id,
            'entry_date': timezone.now().isoformat(),
            'description': 'Entry with individual growth sample',
            'growth_sample': growth_data
        }
        serializer = JournalEntrySerializer(data=data, context=self.serializer_context)
        self.assertTrue(serializer.is_valid(), msg=serializer.errors)
        entry = serializer.save()
        self.assertEqual(entry.batch, self.batch)
        self.assertEqual(entry.container, self.container)
        self.assertEqual(entry.user, self.user)
        # Check related GrowthSample was created
        try:
            gs = GrowthSample.objects.get(assignment=self.assignment, sample_date=sample_date)
            self.assertEqual(gs.sample_size, 3)
            self.assertListEqual(gs.individual_weights_g, [100, 110, 120])
            self.assertListEqual(gs.individual_lengths_mm, [150, 155, 160])
            self.assertListEqual(gs.individual_condition_factors, [1.0, 1.1, 1.2])
            self.assertIsNone(gs.avg_weight_g)
        except GrowthSample.DoesNotExist:
            self.fail("GrowthSample was not created")

    def test_create_journal_entry_with_growth_sample(self):
        """Test creating a JournalEntry with a nested GrowthSample (using averages)."""
        # Use a unique date for this test to avoid conflicts with other tests
        sample_date = datetime.date.today() - datetime.timedelta(days=1)
        growth_data = {
            # 'assignment' derived from JournalEntry
            'sample_date': sample_date,  # Use unique date
            'sample_size': 20,
            'avg_weight_g': Decimal('150.5'),
            'avg_length_cm': Decimal('22.3'),
            'std_deviation_weight': Decimal('10.1'),
            'std_deviation_length': Decimal('1.5')
            # K factor calculated by model/serializer
        }
        data = {
            'batch': self.batch.id,
            'container': self.container.id,
            'category': 'sample',  # Required field
            'entry_date': timezone.now().isoformat(),
            'description': 'Routine growth sample.',
            'growth_sample': growth_data
        }
        serializer = JournalEntrySerializer(data=data, context=self.serializer_context)
        self.assertTrue(serializer.is_valid(), msg=serializer.errors)
        entry = serializer.save()

        # Verify GrowthSample creation - must use the sample_date we explicitly set
        gs = GrowthSample.objects.filter(assignment=self.assignment, sample_date=sample_date).first()
        self.assertIsNotNone(gs, "GrowthSample should have been created")
        self.assertEqual(gs.sample_size, 20)
        self.assertEqual(gs.avg_weight_g, Decimal('150.5'))
        self.assertEqual(gs.avg_length_cm, Decimal('22.3'))
        self.assertIsNotNone(gs.condition_factor)
        self.assertEqual(entry.user, self.user)
        self.assertEqual(entry.health_observations.count(), 0)  

    def test_create_journal_entry_with_growth_sample_individuals(self):
        """Test creating a JournalEntry with a nested GrowthSample using individual lists."""
        weights = [Decimal('140'), Decimal('150'), Decimal('160')]
        lengths = [Decimal('21.0'), Decimal('22.0'), Decimal('23.0')]
        # Use a unique date for this test to avoid conflicts with other tests
        sample_date = datetime.date.today() - datetime.timedelta(days=2)
        growth_data = {
            'sample_date': sample_date,  # Use unique date
            'sample_size': 3,
            'individual_weights': [str(w) for w in weights],
            'individual_lengths': [str(l) for l in lengths]
            # Averages, std devs, K factor calculated by GrowthSampleSerializer
        }
        data = {
            'batch': self.batch.id,
            'container': self.container.id,
            'category': 'sample',  # Required field
            'entry_date': timezone.now().isoformat(),
            'description': 'Growth sample with individuals.',
            'growth_sample': growth_data
        }
        serializer = JournalEntrySerializer(data=data, context=self.serializer_context)
        self.assertTrue(serializer.is_valid(), msg=serializer.errors)
        entry = serializer.save()

        # Use the sample_date we explicitly set, not the entry_date
        gs = GrowthSample.objects.filter(assignment=self.assignment, sample_date=sample_date).first()
        self.assertIsNotNone(gs, "GrowthSample should have been created with the specified sample_date")
        self.assertEqual(gs.sample_size, 3)

        # Verify calculated fields (using quantize for precision)
        quantizer = Decimal('0.01')
        import statistics
        expected_avg_w = statistics.mean(weights)
        expected_std_w = statistics.stdev(weights)
        expected_avg_l = statistics.mean(lengths)
        expected_std_l = statistics.stdev(lengths)
        k_factors = [(100 * w) / (l ** 3) for w, l in zip(weights, lengths) if l > 0]
        expected_avg_k = statistics.mean(k_factors)

        self.assertEqual(gs.avg_weight_g.quantize(quantizer), expected_avg_w.quantize(quantizer))
        self.assertEqual(gs.std_deviation_weight.quantize(quantizer), expected_std_w.quantize(quantizer))
        self.assertEqual(gs.avg_length_cm.quantize(quantizer), expected_avg_l.quantize(quantizer))
        self.assertEqual(gs.std_deviation_length.quantize(quantizer), expected_std_l.quantize(quantizer))
        self.assertIsNotNone(gs.condition_factor)
        self.assertEqual(gs.condition_factor.quantize(quantizer), expected_avg_k.quantize(quantizer))

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

    def test_update_journal_entry_add_growth_sample(self):
        """Test updating a JournalEntry to add a GrowthSample."""
        # Create entry with no growth sample
        create_data = {
            'batch': self.batch.id, 
            'container': self.container.id, 
            'category': 'sample',
            'entry_date': timezone.now().isoformat(), 
            'description': 'Initial entry'
        }
        create_serializer = JournalEntrySerializer(data=create_data, context=self.serializer_context)
        self.assertTrue(create_serializer.is_valid(), msg=create_serializer.errors)
        entry = create_serializer.save()
        # Check if a GrowthSample exists for this assignment and date
        self.assertFalse(GrowthSample.objects.filter(assignment=self.assignment, sample_date=entry.entry_date.date()).exists())

        # Update to add growth sample
        # Use a unique date for this test to avoid conflicts with other tests
        sample_date = datetime.date.today() - datetime.timedelta(days=5)
        growth_data = {
            'sample_date': sample_date,  # Use a unique date different from entry_date
            'sample_size': 5, 
            'avg_weight_g': Decimal('120')
        }
        update_data = {'growth_sample': growth_data}
        update_serializer = JournalEntrySerializer(entry, data=update_data, partial=True, context=self.serializer_context)
        self.assertTrue(update_serializer.is_valid(), msg=update_serializer.errors)
        update_serializer.save()

        # Look for the growth sample with the correct sample_date (not entry_date)
        gs = GrowthSample.objects.filter(assignment=self.assignment, sample_date=sample_date).first()
        self.assertIsNotNone(gs, "GrowthSample should have been created with the specified sample_date")
        self.assertEqual(gs.sample_size, 5)
        self.assertEqual(gs.avg_weight_g, Decimal('120'))

    def test_update_journal_entry_update_growth_sample(self):
        """Test updating a JournalEntry that already has a GrowthSample."""
        # Create entry with growth sample
        # Use a unique date for this test to avoid conflicts with other tests
        sample_date = datetime.date.today() - datetime.timedelta(days=3)
        initial_growth_data = {
            'sample_date': sample_date,  # Use unique date
            'sample_size': 10, 
            'avg_weight_g': Decimal('100')
        }
        create_data = {
            'batch': self.batch.id, 
            'container': self.container.id, 
            'category': 'sample',
            'entry_date': timezone.now().isoformat(),
            'description': 'Initial growth sample',  # Required field
            'growth_sample': initial_growth_data
        }
        create_serializer = JournalEntrySerializer(data=create_data, context=self.serializer_context)
        self.assertTrue(create_serializer.is_valid(), msg=create_serializer.errors)
        entry = create_serializer.save()
        gs = GrowthSample.objects.get(assignment=self.assignment, sample_date=sample_date)
        self.assertEqual(gs.sample_size, 10)

        # Update with new growth sample data - must include sample_date
        update_growth_data = {
            'sample_date': sample_date,  # Use the same date as the original
            'sample_size': 15, 
            'avg_weight_g': Decimal('110')
        }
        update_data = {'growth_sample': update_growth_data}
        update_serializer = JournalEntrySerializer(entry, data=update_data, partial=True, context=self.serializer_context)
        self.assertTrue(update_serializer.is_valid(), msg=update_serializer.errors)
        update_serializer.save()

        gs.refresh_from_db()
        self.assertEqual(gs.sample_size, 15)
        self.assertEqual(gs.avg_weight_g, Decimal('110'))

    def test_update_journal_entry_remove_growth_sample_via_null(self):
        """Test updating a JournalEntry to remove a GrowthSample by passing null."""
        # Create entry with growth sample
        # Use a unique date for this test to avoid conflicts with other tests
        sample_date = datetime.date.today() - datetime.timedelta(days=4)
        initial_growth_data = {
            'sample_date': sample_date,  # Use unique date
            'sample_size': 8, 
            'avg_weight_g': Decimal('90')
        }
        create_data = {
            'batch': self.batch.id, 
            'container': self.container.id, 
            'category': 'sample',
            'entry_date': timezone.now().isoformat(),
            'description': 'Growth sample to be removed',  # Required field
            'growth_sample': initial_growth_data
        }
        create_serializer = JournalEntrySerializer(data=create_data, context=self.serializer_context)
        self.assertTrue(create_serializer.is_valid())
        entry = create_serializer.save()
        # Verify GrowthSample exists using the correct sample_date
        self.assertTrue(GrowthSample.objects.filter(assignment=self.assignment, sample_date=sample_date).exists(), "GrowthSample should exist after creation")

        # Update sending null for growth_sample
        update_data = {'growth_sample': None}
        update_serializer = JournalEntrySerializer(entry, data=update_data, partial=True, context=self.serializer_context)
        self.assertTrue(update_serializer.is_valid(), msg=update_serializer.errors)
        update_serializer.save()

        # The serializer should now delete the sample when null is sent
        # Verify the sample no longer exists
        # Check if a GrowthSample exists for this assignment and date - using the correct sample_date
        self.assertFalse(GrowthSample.objects.filter(assignment=self.assignment, sample_date=sample_date).exists(), "GrowthSample should have been deleted")
