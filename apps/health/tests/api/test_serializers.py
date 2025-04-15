"""
Tests for the health app API serializers.
"""
import datetime
from decimal import Decimal

from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.test import APIRequestFactory # To mock request context

from apps.health.models import JournalEntry, HealthParameter, HealthObservation
from apps.health.api.serializers import (
    HealthParameterSerializer,
    HealthObservationSerializer,
    JournalEntrySerializer
)
from apps.batch.models import (
    Species, LifeCycleStage, Batch, Container, BatchContainerAssignment, GrowthSample
)
from apps.batch.api.serializers import GrowthSampleSerializer

User = get_user_model()


class HealthParameterSerializerTest(TestCase):
    """Tests for HealthParameterSerializer."""

    def test_valid_parameter_serialization(self):
        """Test valid serialization of HealthParameter."""
        data = {
            'name': 'Fin Rot',
            'description_score_1': 'No signs',
            'description_score_2': 'Mild fraying',
            'description_score_3': 'Moderate erosion',
            'description_score_4': 'Severe erosion',
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
        cls.user = User.objects.create_user(username='tester', password='password')
        cls.parameter = HealthParameter.objects.create(name='Gill Condition')
        # Need a JournalEntry to link to
        cls.species = Species.objects.create(name="Cod")
        cls.stage = LifeCycleStage.objects.create(species=cls.species, name="Adult", order=5)
        cls.batch = Batch.objects.create(batch_number='B002', species=cls.species, start_date=datetime.date.today())
        cls.container = Container.objects.create(name='Pen 1')
        cls.assignment = BatchContainerAssignment.objects.create(
            batch=cls.batch, container=cls.container, assignment_date=datetime.date.today(),
            population_count=500, biomass_kg=Decimal('100'), lifecycle_stage=cls.stage
        )
        cls.journal_entry = JournalEntry.objects.create(
            assignment=cls.assignment,
            entry_type='HEALTH_CHECK',
            entry_date=datetime.date.today(),
            created_by=cls.user
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
            'fish_identifier': 'F-002'
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
            'score': 1
        }
        serializer_no_id = HealthObservationSerializer(data=data_no_identifier)
        self.assertTrue(serializer_no_id.is_valid())


class JournalEntrySerializerTest(TestCase):
    """Tests for JournalEntrySerializer."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username='journaltester', password='password')
        cls.species = Species.objects.create(name="Salmon")
        cls.stage = LifeCycleStage.objects.create(species=cls.species, name="Smolt", order=4)
        cls.batch = Batch.objects.create(batch_number='B003', species=cls.species, start_date=datetime.date.today())
        cls.container = Container.objects.create(name='Cage 1')
        cls.assignment = BatchContainerAssignment.objects.create(
            batch=cls.batch, container=cls.container, assignment_date=datetime.date.today(),
            population_count=2000, biomass_kg=Decimal('500'), lifecycle_stage=cls.stage
        )
        cls.parameter1 = HealthParameter.objects.create(name='Skin Condition')
        cls.parameter2 = HealthParameter.objects.create(name='Eye Clarity')

        # Mock request for context
        cls.factory = APIRequestFactory()
        cls.request = cls.factory.post('/') # Dummy request
        cls.request.user = cls.user # Attach user to the request
        cls.serializer_context = {'request': cls.request}

    def test_valid_journal_entry_no_nested(self):
        """Test creating a JournalEntry without observations or growth sample."""
        data = {
            'assignment': self.assignment.id,
            'entry_type': 'OBSERVATION',
            'entry_date': datetime.date.today(),
            'description': 'General check, all clear.'
        }
        serializer = JournalEntrySerializer(data=data, context=self.serializer_context)
        self.assertTrue(serializer.is_valid(), msg=serializer.errors)
        entry = serializer.save()
        self.assertEqual(entry.assignment, self.assignment)
        self.assertEqual(entry.description, 'General check, all clear.')
        self.assertEqual(entry.created_by, self.user)
        self.assertEqual(entry.observations.count(), 0)
        # Check that no GrowthSample was created implicitly
        gs_exists = GrowthSample.objects.filter(assignment=self.assignment, sample_date=entry.entry_date).exists()
        self.assertFalse(gs_exists)

    def test_create_journal_entry_with_observations(self):
        """Test creating a JournalEntry with nested HealthObservations."""
        observations_data = [
            {'parameter': self.parameter1.id, 'score': 1, 'fish_identifier': 'S-01'},
            {'parameter': self.parameter2.id, 'score': 2}
        ]
        data = {
            'assignment': self.assignment.id,
            'entry_type': 'HEALTH_CHECK',
            'entry_date': datetime.date.today(),
            'description': 'Routine health check.',
            'observations': observations_data
        }
        serializer = JournalEntrySerializer(data=data, context=self.serializer_context)
        self.assertTrue(serializer.is_valid(), msg=serializer.errors)
        entry = serializer.save()
        self.assertEqual(entry.observations.count(), 2)
        obs1 = entry.observations.get(parameter=self.parameter1)
        obs2 = entry.observations.get(parameter=self.parameter2)
        self.assertEqual(obs1.score, 1)
        self.assertEqual(obs1.fish_identifier, 'S-01')
        self.assertEqual(obs2.score, 2)
        self.assertIsNone(obs2.fish_identifier)
        self.assertEqual(entry.created_by, self.user)

    def test_create_journal_entry_with_growth_sample(self):
        """Test creating a JournalEntry with a nested GrowthSample (using averages)."""
        growth_data = {
            # 'assignment' and 'sample_date' derived from JournalEntry
            'sample_size': 20,
            'avg_weight_g': Decimal('150.5'),
            'avg_length_cm': Decimal('22.3'),
            'std_deviation_weight': Decimal('10.1'),
            'std_deviation_length': Decimal('1.5')
            # K factor calculated by model/serializer
        }
        data = {
            'assignment': self.assignment.id,
            'entry_type': 'GROWTH_SAMPLE',
            'entry_date': datetime.date.today(),
            'description': 'Routine growth sample.',
            'growth_sample': growth_data
        }
        serializer = JournalEntrySerializer(data=data, context=self.serializer_context)
        self.assertTrue(serializer.is_valid(), msg=serializer.errors)
        entry = serializer.save()

        # Verify GrowthSample creation
        gs = GrowthSample.objects.filter(assignment=self.assignment, sample_date=entry.entry_date).first()
        self.assertIsNotNone(gs)
        self.assertEqual(gs.sample_size, 20)
        self.assertEqual(gs.avg_weight_g, Decimal('150.5'))
        self.assertEqual(gs.avg_length_cm, Decimal('22.3'))
        self.assertIsNotNone(gs.condition_factor)
        self.assertEqual(entry.created_by, self.user)
        self.assertEqual(entry.observations.count(), 0) # No observations created

    def test_create_journal_entry_with_growth_sample_individuals(self):
        """Test creating a JournalEntry with a nested GrowthSample using individual lists."""
        weights = [Decimal('140'), Decimal('150'), Decimal('160')]
        lengths = [Decimal('21.0'), Decimal('22.0'), Decimal('23.0')]
        growth_data = {
            'sample_size': 3,
            'individual_weights': [str(w) for w in weights],
            'individual_lengths': [str(l) for l in lengths]
            # Averages, std devs, K factor calculated by GrowthSampleSerializer
        }
        data = {
            'assignment': self.assignment.id,
            'entry_type': 'GROWTH_SAMPLE',
            'entry_date': datetime.date.today(),
            'description': 'Growth sample with individuals.',
            'growth_sample': growth_data
        }
        serializer = JournalEntrySerializer(data=data, context=self.serializer_context)
        self.assertTrue(serializer.is_valid(), msg=serializer.errors)
        entry = serializer.save()

        gs = GrowthSample.objects.filter(assignment=self.assignment, sample_date=entry.entry_date).first()
        self.assertIsNotNone(gs)
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
        """Test updating a JournalEntry, replacing existing observations."""
        # Create initial entry with one observation
        initial_obs_data = [{'parameter': self.parameter1.id, 'score': 4}]
        create_data = {
            'assignment': self.assignment.id, 'entry_type': 'HEALTH_CHECK',
            'entry_date': datetime.date.today(), 'observations': initial_obs_data
        }
        create_serializer = JournalEntrySerializer(data=create_data, context=self.serializer_context)
        self.assertTrue(create_serializer.is_valid())
        entry = create_serializer.save()
        self.assertEqual(entry.observations.count(), 1)

        # Update with different observations
        update_obs_data = [
            {'parameter': self.parameter2.id, 'score': 1, 'fish_identifier': 'S-UPDATED'}
        ]
        update_data = {
            'description': 'Updated description.',
            'observations': update_obs_data
        }
        update_serializer = JournalEntrySerializer(entry, data=update_data, partial=True, context=self.serializer_context)
        self.assertTrue(update_serializer.is_valid(), msg=update_serializer.errors)
        updated_entry = update_serializer.save()

        self.assertEqual(updated_entry.description, 'Updated description.')
        self.assertEqual(updated_entry.observations.count(), 1)
        new_obs = updated_entry.observations.first()
        self.assertEqual(new_obs.parameter, self.parameter2)
        self.assertEqual(new_obs.score, 1)
        self.assertEqual(new_obs.fish_identifier, 'S-UPDATED')

    def test_update_journal_entry_add_growth_sample(self):
        """Test updating a JournalEntry to add a GrowthSample."""
        # Create entry without growth sample
        entry = JournalEntry.objects.create(
            assignment=self.assignment, entry_type='OBSERVATION',
            entry_date=datetime.date.today(), created_by=self.user
        )
        self.assertFalse(GrowthSample.objects.filter(assignment=self.assignment, sample_date=entry.entry_date).exists())

        # Update to add growth sample
        growth_data = {'sample_size': 5, 'avg_weight_g': Decimal('120')}
        update_data = {'growth_sample': growth_data}
        update_serializer = JournalEntrySerializer(entry, data=update_data, partial=True, context=self.serializer_context)
        self.assertTrue(update_serializer.is_valid(), msg=update_serializer.errors)
        update_serializer.save()

        gs = GrowthSample.objects.filter(assignment=self.assignment, sample_date=entry.entry_date).first()
        self.assertIsNotNone(gs)
        self.assertEqual(gs.sample_size, 5)
        self.assertEqual(gs.avg_weight_g, Decimal('120'))

    def test_update_journal_entry_update_growth_sample(self):
        """Test updating a JournalEntry that already has a GrowthSample."""
        # Create entry with growth sample
        initial_growth_data = {'sample_size': 10, 'avg_weight_g': Decimal('100')}
        create_data = {
            'assignment': self.assignment.id, 'entry_type': 'GROWTH_SAMPLE',
            'entry_date': datetime.date.today(), 'growth_sample': initial_growth_data
        }
        create_serializer = JournalEntrySerializer(data=create_data, context=self.serializer_context)
        self.assertTrue(create_serializer.is_valid())
        entry = create_serializer.save()
        gs = GrowthSample.objects.get(assignment=self.assignment, sample_date=entry.entry_date)
        self.assertEqual(gs.sample_size, 10)

        # Update with new growth sample data
        update_growth_data = {'sample_size': 15, 'avg_weight_g': Decimal('110')}
        update_data = {'growth_sample': update_growth_data}
        update_serializer = JournalEntrySerializer(entry, data=update_data, partial=True, context=self.serializer_context)
        self.assertTrue(update_serializer.is_valid(), msg=update_serializer.errors)
        update_serializer.save()

        gs.refresh_from_db()
        self.assertEqual(gs.sample_size, 15)
        self.assertEqual(gs.avg_weight_g, Decimal('110'))

    def test_update_journal_entry_remove_growth_sample_via_null(self):
        """Test updating a JournalEntry to remove GrowthSample by sending null (optional behavior)."""
        # Create entry with growth sample
        initial_growth_data = {'sample_size': 8, 'avg_weight_g': Decimal('90')}
        create_data = {
            'assignment': self.assignment.id, 'entry_type': 'GROWTH_SAMPLE',
            'entry_date': datetime.date.today(), 'growth_sample': initial_growth_data
        }
        create_serializer = JournalEntrySerializer(data=create_data, context=self.serializer_context)
        self.assertTrue(create_serializer.is_valid())
        entry = create_serializer.save()
        self.assertTrue(GrowthSample.objects.filter(assignment=self.assignment, sample_date=entry.entry_date).exists())

        # Update sending null for growth_sample
        update_data = {'growth_sample': None}
        update_serializer = JournalEntrySerializer(entry, data=update_data, partial=True, context=self.serializer_context)
        self.assertTrue(update_serializer.is_valid(), msg=update_serializer.errors)
        update_serializer.save()

        # Current serializer logic does NOT delete the sample when null is sent.
        # Verify the sample still exists.
        # If deletion on null is desired, the serializer update logic needs modification.
        self.assertTrue(GrowthSample.objects.filter(assignment=self.assignment, sample_date=entry.entry_date).exists())

