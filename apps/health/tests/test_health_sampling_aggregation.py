"""
Tests for HealthSamplingEvent aggregate metrics calculation.

Verifies that aggregate metrics are calculated correctly during POST operations
and that test-specific branches have been removed from production code.
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from decimal import Decimal
from datetime import date

from apps.health.models import (
    HealthSamplingEvent, IndividualFishObservation,
    HealthParameter, FishParameterScore
)
from apps.batch.tests.models.test_utils import (
    create_test_species,
    create_test_lifecycle_stage,
    create_test_batch_with_assignment
)

User = get_user_model()


class HealthSamplingAggregationTest(TestCase):
    """Test that aggregate metrics are calculated correctly."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            email='test@example.com'
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        
        # Create batch and assignment
        self.species = create_test_species()
        self.lifecycle_stage = create_test_lifecycle_stage(species=self.species)
        self.batch, self.assignment = create_test_batch_with_assignment(
            species=self.species,
            lifecycle_stage=self.lifecycle_stage,
            population_count=1000,
            avg_weight_g=Decimal("100.0")
        )
        
        # Create health parameters
        self.param_gill = HealthParameter.objects.create(
            name='Gill Condition',
            description_score_1='Excellent',
            description_score_2='Good',
            description_score_3='Fair',
            description_score_4='Poor'
        )
    
    def test_aggregation_during_post_request(self):
        """Test that aggregate metrics are calculated during POST."""
        url = '/api/v1/health/health-sampling-events/'
        data = {
            'assignment': self.assignment.id,
            'sampling_date': '2025-10-04',
            'number_of_fish_sampled': 3,
            'individual_fish_observations': [
                {
                    'fish_identifier': '1',
                    'weight_g': '100.00',
                    'length_cm': '10.00'
                },
                {
                    'fish_identifier': '2',
                    'weight_g': '110.00',
                    'length_cm': '10.50'
                },
                {
                    'fish_identifier': '3',
                    'weight_g': '120.00',
                    'length_cm': '11.00'
                }
            ]
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Verify aggregate metrics were calculated
        self.assertIn('avg_weight_g', response.data)
        self.assertIn('avg_length_cm', response.data)
        self.assertIn('std_dev_weight_g', response.data)
        self.assertIn('std_dev_length_cm', response.data)
        self.assertIn('avg_k_factor', response.data)
        self.assertIn('calculated_sample_size', response.data)
        
        # Verify values are not None (actual calculation happened)
        self.assertIsNotNone(response.data['avg_weight_g'])
        self.assertIsNotNone(response.data['avg_length_cm'])
        self.assertIsNotNone(response.data['std_dev_weight_g'])
        self.assertIsNotNone(response.data['std_dev_length_cm'])
        self.assertIsNotNone(response.data['avg_k_factor'])
        self.assertEqual(response.data['calculated_sample_size'], 3)
        
        # Verify averages are correct
        self.assertAlmostEqual(
            Decimal(str(response.data['avg_weight_g'])),
            Decimal('110.00'),
            places=2
        )
        self.assertAlmostEqual(
            Decimal(str(response.data['avg_length_cm'])),
            Decimal('10.50'),
            places=2
        )
    
    def test_aggregation_with_missing_data(self):
        """Test aggregation handles missing weight/length correctly."""
        url = '/api/v1/health/health-sampling-events/'
        data = {
            'assignment': self.assignment.id,
            'sampling_date': '2025-10-04',
            'number_of_fish_sampled': 4,
            'individual_fish_observations': [
                {
                    'fish_identifier': '1',
                    'weight_g': '100.00',
                    'length_cm': '10.00'
                },
                {
                    'fish_identifier': '2',
                    'weight_g': None,  # Missing weight
                    'length_cm': '11.00'
                },
                {
                    'fish_identifier': '3',
                    'weight_g': '120.00',
                    'length_cm': None  # Missing length
                },
                {
                    'fish_identifier': '4',
                    'weight_g': '115.00',
                    'length_cm': '10.50'
                }
            ]
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Avg weight should use fish 1, 3, 4 (100, 120, 115)
        expected_avg_weight = (Decimal('100.00') + Decimal('120.00') + Decimal('115.00')) / 3
        self.assertAlmostEqual(
            Decimal(str(response.data['avg_weight_g'])),
            expected_avg_weight,
            places=2
        )
        
        # Avg length should use fish 1, 2, 4 (10, 11, 10.5)
        expected_avg_length = (Decimal('10.00') + Decimal('11.00') + Decimal('10.50')) / 3
        self.assertAlmostEqual(
            Decimal(str(response.data['avg_length_cm'])),
            expected_avg_length,
            places=2
        )
        
        # Min/max should be correct
        self.assertEqual(Decimal(str(response.data['min_weight_g'])), Decimal('100.00'))
        self.assertEqual(Decimal(str(response.data['max_weight_g'])), Decimal('120.00'))
        self.assertEqual(Decimal(str(response.data['min_length_cm'])), Decimal('10.00'))
        self.assertEqual(Decimal(str(response.data['max_length_cm'])), Decimal('11.00'))
        
        # K-factor only calculated for fish with both weight and length (fish 1 and 4)
        self.assertEqual(response.data['calculated_sample_size'], 2)
        self.assertIsNotNone(response.data['avg_k_factor'])
    
    def test_aggregation_empty_observations(self):
        """Test aggregation when no individual observations provided."""
        url = '/api/v1/health/health-sampling-events/'
        data = {
            'assignment': self.assignment.id,
            'sampling_date': '2025-10-04',
            'number_of_fish_sampled': 0,
            'individual_fish_observations': []
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # All aggregate fields should be None when no observations
        self.assertIsNone(response.data['avg_weight_g'])
        self.assertIsNone(response.data['avg_length_cm'])
        self.assertIsNone(response.data['std_dev_weight_g'])
        self.assertIsNone(response.data['std_dev_length_cm'])
        self.assertIsNone(response.data['avg_k_factor'])
        self.assertEqual(response.data['calculated_sample_size'], 0)
    
    def test_aggregation_with_parameter_scores(self):
        """Test aggregation works when fish have parameter scores."""
        url = '/api/v1/health/health-sampling-events/'
        data = {
            'assignment': self.assignment.id,
            'sampling_date': '2025-10-04',
            'number_of_fish_sampled': 2,
            'individual_fish_observations': [
                {
                    'fish_identifier': '1',
                    'weight_g': '100.00',
                    'length_cm': '10.00',
                    'parameter_scores': [
                        {
                            'parameter': self.param_gill.id,
                            'score': 2
                        }
                    ]
                },
                {
                    'fish_identifier': '2',
                    'weight_g': '110.00',
                    'length_cm': '10.50',
                    'parameter_scores': [
                        {
                            'parameter': self.param_gill.id,
                            'score': 1
                        }
                    ]
                }
            ]
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Verify aggregate metrics calculated despite having parameter scores
        self.assertIsNotNone(response.data['avg_weight_g'])
        self.assertIsNotNone(response.data['avg_length_cm'])
        self.assertEqual(response.data['calculated_sample_size'], 2)
        
        # Verify parameter scores were created
        event_id = response.data['id']
        event = HealthSamplingEvent.objects.get(id=event_id)
        total_scores = FishParameterScore.objects.filter(
            individual_fish_observation__sampling_event=event
        ).count()
        self.assertEqual(total_scores, 2)
    
    def test_update_recalculates_aggregates(self):
        """Test that updating observations recalculates aggregates."""
        # Create initial event
        event = HealthSamplingEvent.objects.create(
            assignment=self.assignment,
            sampling_date=date(2025, 10, 4),
            sampled_by=self.user,
            number_of_fish_sampled=2
        )
        
        IndividualFishObservation.objects.create(
            sampling_event=event,
            fish_identifier='1',
            weight_g=Decimal('100.00'),
            length_cm=Decimal('10.00')
        )
        
        event.calculate_aggregate_metrics()
        
        # Verify initial state
        self.assertEqual(event.avg_weight_g, Decimal('100.00'))
        self.assertIsNone(event.std_dev_weight_g)  # Single observation has no std dev
        
        # Add another observation
        IndividualFishObservation.objects.create(
            sampling_event=event,
            fish_identifier='2',
            weight_g=Decimal('120.00'),
            length_cm=Decimal('11.00')
        )
        
        # Recalculate
        event.calculate_aggregate_metrics()
        
        # Verify updated aggregates
        self.assertEqual(event.avg_weight_g, Decimal('110.00'))
        self.assertIsNotNone(event.std_dev_weight_g)  # Now has std dev
        self.assertEqual(event.calculated_sample_size, 2)

