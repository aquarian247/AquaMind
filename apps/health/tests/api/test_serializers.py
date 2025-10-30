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
from apps.batch.models import Batch, BatchContainerAssignment, Species, LifeCycleStage
 
from apps.health.models import (
    HealthParameter, ParameterScoreDefinition, JournalEntry, 
    HealthSamplingEvent,
    IndividualFishObservation,
    FishParameterScore
)
from apps.health.api.serializers import (
    HealthParameterSerializer,
    ParameterScoreDefinitionSerializer,
    JournalEntrySerializer, 
    HealthSamplingEventSerializer,
    IndividualFishObservationSerializer,
    FishParameterScoreSerializer
)

User = get_user_model()


class HealthParameterSerializerTestCase(TestCase):
    """Test cases for the HealthParameterSerializer with new normalized structure."""

    @classmethod
    def setUpTestData(cls):
        # Create a parameter with new schema
        cls.parameter = HealthParameter.objects.create(
            name='Test Parameter',
            description='Test health parameter',
            min_score=0,
            max_score=3,
            is_active=True
        )
        
        # Create score definitions
        ParameterScoreDefinition.objects.create(
            parameter=cls.parameter,
            score_value=0,
            label='Excellent',
            description='No issues detected',
            display_order=0
        )
        ParameterScoreDefinition.objects.create(
            parameter=cls.parameter,
            score_value=1,
            label='Good',
            description='Minor issues',
            display_order=1
        )
        ParameterScoreDefinition.objects.create(
            parameter=cls.parameter,
            score_value=2,
            label='Fair',
            description='Moderate issues',
            display_order=2
        )
        ParameterScoreDefinition.objects.create(
            parameter=cls.parameter,
            score_value=3,
            label='Poor',
            description='Severe issues',
            display_order=3
        )

    def test_parameter_with_score_definitions(self):
        """Test serialization includes nested score definitions."""
        serializer = HealthParameterSerializer(instance=self.parameter)
        data = serializer.data
        
        self.assertEqual(data['name'], 'Test Parameter')
        self.assertEqual(data['description'], 'Test health parameter')
        self.assertEqual(data['min_score'], 0)
        self.assertEqual(data['max_score'], 3)
        self.assertEqual(len(data['score_definitions']), 4)
        self.assertEqual(data['score_definitions'][0]['score_value'], 0)
        self.assertEqual(data['score_definitions'][0]['label'], 'Excellent')
        self.assertEqual(data['score_definitions'][1]['score_value'], 1)
        self.assertEqual(data['score_definitions'][1]['label'], 'Good')
    
    def test_create_parameter(self):
        """Test creating a new parameter."""
        data = {
            'name': 'Fin Condition Test',
            'description': 'Assessment of fin integrity',
            'min_score': 0,
            'max_score': 3,
            'is_active': True
        }
        serializer = HealthParameterSerializer(data=data)
        self.assertTrue(serializer.is_valid(), msg=serializer.errors)
        parameter = serializer.save()
        self.assertEqual(parameter.name, 'Fin Condition Test')
        self.assertEqual(parameter.min_score, 0)
        self.assertEqual(parameter.max_score, 3)


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
        cls.geography = Geography.objects.create(name='Test Geography JE')
        cls.area = Area.objects.create(
            name='Test Area JE', 
            geography=cls.geography,
            latitude=Decimal('60.1'),
            longitude=Decimal('5.1'),
            max_biomass=Decimal('6000.0')
        )
        cls.container_type = ContainerType.objects.create(name='Test Cage Type JE', category='CAGE', max_volume_m3=1200)
        cls.species = Species.objects.create(name='Test Species JE')
        cls.stage = LifeCycleStage.objects.create(species=cls.species, name='Test Stage JE', order=1)
        
        cls.batch = Batch.objects.create(
            batch_number='B002_JE',
            species=cls.species,
            start_date=datetime.date.today(),
            lifecycle_stage=cls.stage,
        )
        cls.container = Container.objects.create(
            name='TestCage2_JE',
            area=cls.area,
            container_type=cls.container_type,
            volume_m3=600,
            max_biomass_kg=6000
        )
        # This assignment is for JournalEntry, not directly for health sampling tests here
        cls.assignment_for_journal_entry = BatchContainerAssignment.objects.create(
            batch=cls.batch,
            container=cls.container,
            lifecycle_stage=cls.stage,
            assignment_date=datetime.date.today() - datetime.timedelta(days=10),
            population_count=2000,
            biomass_kg=Decimal('1000')
        )
        cls.health_parameter = HealthParameter.objects.create(
            name='Skin Condition JE',
            min_score=0,
            max_score=3
        )

    def setUp(self):
        self.client.force_authenticate(user=self.user)
        # Common data for JournalEntry creation
        self.journal_entry_data = {
            'batch': self.assignment_for_journal_entry.batch.id,
            'container': self.assignment_for_journal_entry.container.id,
            'category': 'observation',
            'severity': 'low',
            'description': 'Initial observation for batch B002_JE.',
            'user': self.user.id,
            # 'health_observations': [] # Ensure this is handled if JournalEntrySerializer changed
        }

    def test_create_journal_entry_valid(self):
        """Test creating a valid journal entry."""
        serializer = JournalEntrySerializer(data=self.journal_entry_data, context={'request': Mock(user=self.user)})
        self.assertTrue(serializer.is_valid(), msg=serializer.errors)
        entry = serializer.save()
        self.assertEqual(entry.batch, self.assignment_for_journal_entry.batch)
        self.assertEqual(entry.description, 'Initial observation for batch B002_JE.')
        self.assertEqual(entry.user, self.user)

    # Add more tests for JournalEntrySerializer as needed, e.g., updates, invalid data
    # Especially focusing on how it handles or doesn't handle health observations now


class HealthSamplingEventSerializerTestCase(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username='health_sample_user', password='password')
        cls.species = Species.objects.create(name='Test Species HS')
        cls.lifecycle_stage = LifeCycleStage.objects.create(species=cls.species, name='Test Stage HS', order=1)
        cls.batch = Batch.objects.create(batch_number='B003_HS', species=cls.species, lifecycle_stage=cls.lifecycle_stage, start_date=timezone.now().date())
        cls.container_type = ContainerType.objects.create(name='Test Tank HS', category='TANK', max_volume_m3=Decimal('100.0'))
        # Need a Hall or Area for the container
        cls.geography_hs = Geography.objects.create(name='Test Geo HS')
        cls.area_hs = Area.objects.create(name='Test Area HS', geography=cls.geography_hs, latitude=Decimal('60.1'), longitude=Decimal('5.1'), max_biomass=Decimal('6000.0'))
        cls.container = Container.objects.create(name='T001_HS', container_type=cls.container_type, volume_m3=50, max_biomass_kg=1000, area=cls.area_hs)
        cls.assignment = BatchContainerAssignment.objects.create(
            batch=cls.batch, container=cls.container, lifecycle_stage=cls.lifecycle_stage,
            assignment_date=timezone.now().date(), population_count=500, biomass_kg=Decimal('250')
        )
        cls.health_parameter = HealthParameter.objects.create(
            name='Gill Health HS',
            min_score=0,
            max_score=3
        )

    def setUp(self):
        self.client.force_authenticate(user=self.user)

    def test_create_health_sampling_event_valid(self):
        data = {
            'assignment': self.assignment.id,
            'sampling_date': timezone.now().date(),
            'number_of_fish_sampled': 10,
            'sampled_by': self.user.id,
            'notes': 'Routine check',
            'individual_fish_observations': [
                {
                    'fish_identifier': 1,
                    'length_cm': Decimal('10.2'),
                    'weight_g': Decimal('150.5'),
                    'parameter_scores': [
                        {
                            'parameter': self.health_parameter.id,
                            'score': 2
                        }
                    ]
                }
            ]
        }
        serializer = HealthSamplingEventSerializer(data=data, context={'request': Mock(user=self.user)})
        self.assertTrue(serializer.is_valid(), msg=serializer.errors)
        instance = serializer.save()
        self.assertEqual(instance.number_of_fish_sampled, 10)
        self.assertEqual(instance.individual_fish_observations.count(), 1)
        self.assertEqual(instance.individual_fish_observations.first().parameter_scores.count(), 1)


class IndividualFishObservationSerializerTestCase(APITestCase):
    @classmethod
    def setUpTestData(cls):
        # Basic setup, can be expanded or reuse HealthSamplingEventSerializerTestCase.setUpTestData
        cls.user = User.objects.create_user(username='fish_obs_user', password='password')
        cls.species = Species.objects.create(name='Test Species FO')
        cls.lifecycle_stage = LifeCycleStage.objects.create(species=cls.species, name='Test Stage FO', order=1)
        cls.batch = Batch.objects.create(batch_number='B004_FO', species=cls.species, lifecycle_stage=cls.lifecycle_stage, start_date=timezone.now().date())
        cls.container_type = ContainerType.objects.create(name='Test Tank FO', category='TANK', max_volume_m3=Decimal('50.0'))
        # Create Geography and Area for the Container
        cls.geography_fo = Geography.objects.create(name='Test Geo FO')
        cls.area_fo = Area.objects.create(name='Test Area FO', geography=cls.geography_fo, latitude=Decimal('60.2'), longitude=Decimal('5.2'), max_biomass=Decimal('5000.0'))
        cls.container = Container.objects.create(name='T002_FO', container_type=cls.container_type, volume_m3=20, max_biomass_kg=200, area=cls.area_fo)
        cls.assignment = BatchContainerAssignment.objects.create(
            batch=cls.batch, container=cls.container, lifecycle_stage=cls.lifecycle_stage,
            assignment_date=timezone.now().date(), population_count=100, biomass_kg=Decimal('50')
        )
        # Create a HealthSamplingEvent
        cls.health_sampling_event = HealthSamplingEvent.objects.create(
            assignment=cls.assignment,
            sampling_date=timezone.now().date(),
            number_of_fish_sampled=5,
            sampled_by=cls.user,
            notes='Routine Check FO'
        )
        cls.health_parameter = HealthParameter.objects.create(
            name='Fin Condition FO',
            min_score=0,
            max_score=3
        )

    def setUp(self):
        self.client.force_authenticate(user=self.user)

    def test_create_individual_fish_observation_valid(self):
        """Test creating a valid IndividualFishObservation."""
        valid_data = {
            'sampling_event': self.health_sampling_event.id, # Link to the sampling event
            'fish_identifier': '1', # Use string to match model's behavior
            'weight_g': Decimal('150.50'),
            'length_cm': Decimal('25.20'),
            'parameter_scores': [
                {
                    'parameter': self.health_parameter.id,
                    'score': 2
                }
            ]
        }
        serializer = IndividualFishObservationSerializer(data=valid_data, context={'request': Mock(user=self.user), 'sampling_event': self.health_sampling_event})
        self.assertTrue(serializer.is_valid(), msg=serializer.errors)
        instance = serializer.save() 
        self.assertEqual(instance.fish_identifier, '1') # Updated assertion
        self.assertEqual(instance.parameter_scores.count(), 1)


class FishParameterScoreSerializerTestCase(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username='param_score_user', password='password')
        cls.species = Species.objects.create(name='Test Species PS')
        cls.lifecycle_stage = LifeCycleStage.objects.create(species=cls.species, name='Test Stage PS', order=1)
        cls.batch = Batch.objects.create(batch_number='B005_PS', species=cls.species, lifecycle_stage=cls.lifecycle_stage, population_count=20, biomass_kg=Decimal('10'), start_date=timezone.now().date())
        cls.container_type = ContainerType.objects.create(name='Test Tank PS', category='TANK', max_volume_m3=Decimal('20.0'))
        # Create Geography and Area for the Container
        cls.geography_ps = Geography.objects.create(name='Test Geo PS')
        cls.area_ps = Area.objects.create(name='Test Area PS', geography=cls.geography_ps, latitude=Decimal('60.3'), longitude=Decimal('5.3'), max_biomass=Decimal('4000.0'))
        cls.container = Container.objects.create(name='T003_PS', container_type=cls.container_type, volume_m3=10, max_biomass_kg=100, area=cls.area_ps)
        cls.assignment = BatchContainerAssignment.objects.create(
            batch=cls.batch, container=cls.container, lifecycle_stage=cls.lifecycle_stage,
            assignment_date=timezone.now().date(), population_count=20, biomass_kg=Decimal('10')
        )
        # Create HealthSamplingEvent and IndividualFishObservation for FishParameterScore
        cls.health_sampling_event_ps = HealthSamplingEvent.objects.create(
            assignment=cls.assignment,
            sampling_date=timezone.now().date(),
            number_of_fish_sampled=3,
            sampled_by=cls.user,
            notes='Routine Check PS'
        )
        cls.individual_fish_observation = IndividualFishObservation.objects.create(
            sampling_event=cls.health_sampling_event_ps,
            fish_identifier=1,  # Changed to integer
            weight_g=Decimal('120.0'),
            length_cm=Decimal('22.0')
        )
        cls.health_parameter_ps = HealthParameter.objects.create(
            name='Skin Lesions PS',
            min_score=0,
            max_score=3
        )

    def setUp(self):
        self.client.force_authenticate(user=self.user)

    # def test_create_fish_parameter_score_valid(self):
    #     """Test creating a valid FishParameterScore."""
    #     valid_data = {
    #         'individual_fish_observation': self.individual_fish_observation.id, # Link to the fish observation
    #         'parameter': self.health_parameter_ps.id,
    #         'score': 3,
    #         'comment': 'Minor lesions observed.'
    #     }
    #     serializer = FishParameterScoreSerializer(data=valid_data, context={'request': Mock(user=self.user), 'individual_fish_observation': self.individual_fish_observation})
    #     self.assertTrue(serializer.is_valid(), msg=serializer.errors)
    #     instance = serializer.save() 
    #     self.assertEqual(instance.score, 3)
    #     self.assertEqual(instance.parameter, self.health_parameter_ps)
