"""
Tests for HealthLabSample assignment validation.

Tests that lab samples properly validate assignment date ranges including
departure_date checks and consistent error formatting.
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from rest_framework.exceptions import ValidationError
from decimal import Decimal
from datetime import date, timedelta

from apps.health.models import HealthLabSample, SampleType
from apps.health.api.serializers.lab_sample import HealthLabSampleSerializer
from apps.batch.models import BatchContainerAssignment
from apps.batch.tests.models.test_utils import (
    create_test_species,
    create_test_lifecycle_stage,
    create_test_batch,
    create_test_container
)

User = get_user_model()


class HealthLabSampleAssignmentValidationTest(TestCase):
    """Test HealthLabSample validates assignment date ranges properly."""
    
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
        self.batch = create_test_batch(
            species=self.species,
            lifecycle_stage=self.lifecycle_stage,
            batch_number="LAB_TEST_BATCH"
        )
        self.container = create_test_container(name="Lab Test Container")
        
        # Create sample type
        self.sample_type = SampleType.objects.create(
            name='Blood Sample',
            description='Blood test for disease screening'
        )
        
        # Create active assignment (started 30 days ago, still active)
        self.active_assignment = BatchContainerAssignment.objects.create(
            batch=self.batch,
            container=self.container,
            lifecycle_stage=self.lifecycle_stage,
            population_count=1000,
            avg_weight_g=Decimal("100.0"),
            assignment_date=date.today() - timedelta(days=30),
            is_active=True
        )
        
        # Create ended assignment (started 60 days ago, ended 10 days ago)
        self.ended_assignment = BatchContainerAssignment.objects.create(
            batch=self.batch,
            container=create_test_container(name="Old Container"),
            lifecycle_stage=self.lifecycle_stage,
            population_count=1000,
            avg_weight_g=Decimal("100.0"),
            assignment_date=date.today() - timedelta(days=60),
            departure_date=date.today() - timedelta(days=10),
            is_active=False
        )
    
    def test_active_assignment_sample_accepted(self):
        """Test that samples for active assignments are accepted."""
        url = '/api/v1/health/health-lab-samples/'
        data = {
            'batch_id': self.batch.id,
            'container_id': self.container.id,
            'sample_type': self.sample_type.id,
            'sample_date': date.today().isoformat(),
            'findings_summary': 'Test sample'
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(HealthLabSample.objects.count(), 1)
        
        # Verify correct assignment was used
        sample = HealthLabSample.objects.first()
        self.assertEqual(sample.batch_container_assignment, self.active_assignment)
    
    def test_sample_after_departure_date_rejected(self):
        """Test that samples taken after assignment departure are rejected."""
        url = '/api/v1/health/health-lab-samples/'
        
        # Try to create sample dated after the ended assignment's departure_date
        sample_date_after_departure = date.today() - timedelta(days=5)  # 5 days after departure
        
        data = {
            'batch_id': self.batch.id,
            'container_id': self.ended_assignment.container.id,
            'sample_type': self.sample_type.id,
            'sample_date': sample_date_after_departure.isoformat(),
            'findings_summary': 'Test sample after departure'
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('sample_date', response.data)
        error_message = str(response.data['sample_date'][0])
        self.assertIn('departure date', error_message.lower())
        self.assertIn('ended', error_message.lower())
        
        # Verify no sample was created
        self.assertEqual(HealthLabSample.objects.count(), 0)
    
    def test_sample_before_departure_date_accepted(self):
        """Test that samples taken before departure are accepted for ended assignments."""
        url = '/api/v1/health/health-lab-samples/'
        
        # Sample taken 20 days ago (before the departure 10 days ago)
        sample_date_before_departure = date.today() - timedelta(days=20)
        
        data = {
            'batch_id': self.batch.id,
            'container_id': self.ended_assignment.container.id,
            'sample_type': self.sample_type.id,
            'sample_date': sample_date_before_departure.isoformat(),
            'findings_summary': 'Historical sample before departure'
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Verify correct ended assignment was used
        sample = HealthLabSample.objects.first()
        self.assertEqual(sample.batch_container_assignment, self.ended_assignment)
    
    def test_sample_before_assignment_date_rejected(self):
        """Test that samples before assignment start are rejected."""
        url = '/api/v1/health/health-lab-samples/'
        
        # Sample dated before assignment started
        sample_date_before_start = date.today() - timedelta(days=40)
        
        data = {
            'batch_id': self.batch.id,
            'container_id': self.container.id,
            'sample_type': self.sample_type.id,
            'sample_date': sample_date_before_start.isoformat(),
            'findings_summary': 'Sample before assignment'
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('sample_date', response.data)
        
        # Verify no sample was created
        self.assertEqual(HealthLabSample.objects.count(), 0)
    
    def test_sample_before_batch_start_rejected(self):
        """Test that samples before batch start are rejected."""
        url = '/api/v1/health/health-lab-samples/'
        
        # Sample before batch started but after assignment date
        # Since assignment_date is checked first, we need sample after assignment but before batch
        # Actually, if sample is before batch start, no assignment would exist with assignment_date <= sample_date
        # So this will fail at "no assignment found" rather than batch start date check
        sample_date_before_batch = self.batch.start_date - timedelta(days=5)
        
        data = {
            'batch_id': self.batch.id,
            'container_id': self.container.id,
            'sample_type': self.sample_type.id,
            'sample_date': sample_date_before_batch.isoformat(),
            'findings_summary': 'Sample before batch'
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('sample_date', response.data)
        error_message = str(response.data['sample_date'][0])
        # Will fail with "no assignment found" since sample is before all assignments
        self.assertIn("no active or relevant assignment", error_message.lower())
        
        # Verify no sample was created
        self.assertEqual(HealthLabSample.objects.count(), 0)
    
    def test_sample_after_batch_end_rejected(self):
        """Test that samples after batch end are rejected."""
        # Set batch end date
        self.batch.actual_end_date = date.today() - timedelta(days=5)
        self.batch.save()
        
        url = '/api/v1/health/health-lab-samples/'
        
        # Sample after batch ended
        data = {
            'batch_id': self.batch.id,
            'container_id': self.container.id,
            'sample_type': self.sample_type.id,
            'sample_date': date.today().isoformat(),
            'findings_summary': 'Sample after batch end'
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('sample_date', response.data)
        error_message = str(response.data['sample_date'][0])
        self.assertIn("batch's effective end date", error_message.lower())
        
        # Verify no sample was created
        self.assertEqual(HealthLabSample.objects.count(), 0)
    
    def test_error_format_consistency(self):
        """Test that all validation errors use consistent dict format."""
        url = '/api/v1/health/health-lab-samples/'
        
        # Test various validation failures
        test_cases = [
            # Missing batch
            {
                'container_id': self.container.id,
                'sample_type': self.sample_type.id,
                'sample_date': date.today().isoformat()
            },
            # Invalid batch ID
            {
                'batch_id': 99999,
                'container_id': self.container.id,
                'sample_type': self.sample_type.id,
                'sample_date': date.today().isoformat()
            },
            # Invalid container ID
            {
                'batch_id': self.batch.id,
                'container_id': 99999,
                'sample_type': self.sample_type.id,
                'sample_date': date.today().isoformat()
            }
        ]
        
        for test_data in test_cases:
            response = self.client.post(url, test_data, format='json')
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            
            # Error response should be a dict with field keys
            self.assertIsInstance(response.data, dict)
    
    def test_serializer_validation_departure_date(self):
        """Test serializer directly for departure_date validation."""
        # Sample after departure should fail
        data = {
            'batch_id': self.batch.id,
            'container_id': self.ended_assignment.container.id,
            'sample_type': self.sample_type.id,
            'sample_date': date.today(),  # After departure_date
            'findings_summary': 'Test'
        }
        
        serializer = HealthLabSampleSerializer(data=data, context={'request': None})
        
        with self.assertRaises(ValidationError) as context:
            serializer.is_valid(raise_exception=True)
        
        # Verify error format is dict
        self.assertIn('sample_date', context.exception.detail)
        error_message = str(context.exception.detail['sample_date'][0])
        self.assertIn('departure date', error_message.lower())
    
    def test_multiple_assignments_selects_correct_one(self):
        """Test that the most recent relevant assignment is selected."""
        # Create another container with unique name
        historical_container = create_test_container(name="Historical_Container_Unique")
        
        # Create another assignment for same batch but different container
        # Assignment started 20 days ago, ended 15 days ago
        earlier_assignment = BatchContainerAssignment.objects.create(
            batch=self.batch,
            container=historical_container,
            lifecycle_stage=self.lifecycle_stage,
            population_count=800,
            avg_weight_g=Decimal("80.0"),
            assignment_date=date.today() - timedelta(days=20),
            departure_date=date.today() - timedelta(days=15),
            is_active=False
        )
        
        url = '/api/v1/health/health-lab-samples/'
        
        # Sample taken 17 days ago (within earlier assignment period: 20-15 days ago)
        sample_date = date.today() - timedelta(days=17)
        
        data = {
            'batch_id': self.batch.id,
            'container_id': historical_container.id,
            'sample_type': self.sample_type.id,
            'sample_date': sample_date.isoformat(),
            'findings_summary': 'Historical sample'
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Verify correct historical assignment was selected
        sample = HealthLabSample.objects.first()
        self.assertEqual(sample.batch_container_assignment, earlier_assignment)
    
    def test_on_departure_date_accepted(self):
        """Test that sample on the exact departure date is accepted."""
        url = '/api/v1/health/health-lab-samples/'
        
        # Sample on the exact departure date
        data = {
            'batch_id': self.batch.id,
            'container_id': self.ended_assignment.container.id,
            'sample_type': self.sample_type.id,
            'sample_date': self.ended_assignment.departure_date.isoformat(),
            'findings_summary': 'Sample on departure date'
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Verify sample created
        sample = HealthLabSample.objects.first()
        self.assertEqual(sample.batch_container_assignment, self.ended_assignment)

