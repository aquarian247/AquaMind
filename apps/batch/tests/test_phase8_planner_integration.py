"""
Tests for Phase 8: Production Planner Integration

Tests the bidirectional integration between Batch Growth Assimilation
and the Production Planner.
"""

import uuid
from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status

from apps.batch.models import (
    Batch,
    ActualDailyAssignmentState,
)
from apps.batch.tests.models.test_utils import (
    create_test_species,
    create_test_lifecycle_stage,
    create_test_container,
    create_test_batch_container_assignment,
)
from apps.scenario.tests.test_helpers import create_test_scenario
from apps.planning.models import PlannedActivity, ActivityTemplate

User = get_user_model()


@override_settings(SKIP_CELERY_SIGNALS='1')
class TestTemplateTriggerLogic(TestCase):
    """Test weight and stage threshold trigger logic."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username=f'testuser-{uuid.uuid4().hex[:6]}',
            email='test@example.com',
            password='testpass123'
        )
        unique_id = uuid.uuid4().hex[:6]
        self.species = create_test_species(name=f'Test Species {unique_id}')
        self.stage_fry = create_test_lifecycle_stage(
            name=f'Fry-{unique_id}',
            species=self.species,
            order=1
        )
        self.stage_parr = create_test_lifecycle_stage(
            name=f'Parr-{unique_id}',
            species=self.species,
            order=2
        )
    
    def test_weight_threshold_template_trigger_type(self):
        """Weight threshold template should have correct trigger type."""
        template = ActivityTemplate.objects.create(
            name='Test Weight Trigger',
            activity_type='SAMPLING',
            trigger_type='WEIGHT_THRESHOLD',
            weight_threshold_g=Decimal('10.0'),
            is_active=True
        )
        
        self.assertEqual(template.trigger_type, 'WEIGHT_THRESHOLD')
        self.assertEqual(float(template.weight_threshold_g), 10.0)
    
    def test_stage_transition_template_trigger_type(self):
        """Stage transition template should have correct trigger type."""
        template = ActivityTemplate.objects.create(
            name='Parr Stage Trigger',
            activity_type='FEED_CHANGE',
            trigger_type='STAGE_TRANSITION',
            target_lifecycle_stage=self.stage_parr,
            is_active=True
        )
        
        self.assertEqual(template.trigger_type, 'STAGE_TRANSITION')
        self.assertEqual(template.target_lifecycle_stage, self.stage_parr)
    
    def test_inactive_template_filtered(self):
        """Inactive templates should be filtered correctly."""
        ActivityTemplate.objects.create(
            name='Active Template',
            activity_type='TREATMENT',
            trigger_type='WEIGHT_THRESHOLD',
            weight_threshold_g=Decimal('5.0'),
            is_active=True
        )
        ActivityTemplate.objects.create(
            name='Inactive Template',
            activity_type='TREATMENT',
            trigger_type='WEIGHT_THRESHOLD',
            weight_threshold_g=Decimal('5.0'),
            is_active=False
        )
        
        active_templates = ActivityTemplate.objects.filter(
            trigger_type='WEIGHT_THRESHOLD',
            is_active=True
        )
        
        self.assertEqual(active_templates.count(), 1)
        self.assertEqual(active_templates.first().name, 'Active Template')


@override_settings(SKIP_CELERY_SIGNALS='1')
class TestPlannedActivityFKOnDailyState(TestCase):
    """Test planned_activity FK on ActualDailyAssignmentState."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username=f'testuser-{uuid.uuid4().hex[:6]}',
            email='test@example.com',
            password='testpass123'
        )
        unique_id = uuid.uuid4().hex[:6]
        self.species = create_test_species(name=f'Test Species {unique_id}')
        self.stage = create_test_lifecycle_stage(
            name=f'Fry-{unique_id}',
            species=self.species,
            order=1
        )
        self.container = create_test_container(name=f'Tank-{unique_id}')
        
        self.batch = Batch.objects.create(
            batch_number=f'TEST-{unique_id}',
            species=self.species,
            lifecycle_stage=self.stage,
            start_date=date.today() - timedelta(days=30),
            status='ACTIVE'
        )
        
        self.assignment = create_test_batch_container_assignment(
            batch=self.batch,
            container=self.container,
            lifecycle_stage=self.stage,
            population_count=1000,
            avg_weight_g=Decimal('2.0')
        )
        
        self.scenario = create_test_scenario(user=self.user)
        self.batch.scenarios.add(self.scenario)
    
    def test_daily_state_can_link_to_planned_activity(self):
        """Daily state should be able to reference a PlannedActivity."""
        activity = PlannedActivity.objects.create(
            scenario=self.scenario,
            batch=self.batch,
            activity_type='VACCINATION',
            due_date=date.today(),
            status='COMPLETED',
            completed_at=date.today(),
            created_by=self.user
        )
        
        state = ActualDailyAssignmentState.objects.create(
            assignment=self.assignment,
            batch=self.batch,
            container=self.container,
            lifecycle_stage=self.stage,
            date=date.today(),
            day_number=30,
            avg_weight_g=Decimal('10.0'),
            population=9900,
            biomass_kg=Decimal('99.0'),
            anchor_type='planned_activity',
            planned_activity=activity,
            sources={'weight': 'measured'},
            confidence_scores={'weight': 1.0}
        )
        
        self.assertEqual(state.planned_activity, activity)
        self.assertEqual(state.anchor_type, 'planned_activity')
    
    def test_planned_activity_anchor_type_valid(self):
        """'planned_activity' should be a valid anchor type choice."""
        valid_choices = [choice[0] for choice in ActualDailyAssignmentState.ANCHOR_TYPE_CHOICES]
        self.assertIn('planned_activity', valid_choices)


@override_settings(SKIP_CELERY_SIGNALS='1')
class TestVarianceFromActualAPI(APITestCase):
    """Test variance-from-actual API endpoint."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username=f'testuser-{uuid.uuid4().hex[:6]}',
            email='test@example.com',
            password='testpass123'
        )
        self.client.force_authenticate(user=self.user)
        
        unique_id = uuid.uuid4().hex[:6]
        self.species = create_test_species(name=f'Test Species {unique_id}')
        self.stage = create_test_lifecycle_stage(
            name=f'Fry-{unique_id}',
            species=self.species,
            order=1
        )
        self.container = create_test_container(name=f'Tank-{unique_id}')
        
        self.batch = Batch.objects.create(
            batch_number=f'TEST-{unique_id}',
            species=self.species,
            lifecycle_stage=self.stage,
            start_date=date.today() - timedelta(days=30),
            status='ACTIVE'
        )
        
        self.assignment = create_test_batch_container_assignment(
            batch=self.batch,
            container=self.container,
            lifecycle_stage=self.stage,
            population_count=1000,
            avg_weight_g=Decimal('2.0')
        )
        
        self.scenario = create_test_scenario(user=self.user)
        self.batch.scenarios.add(self.scenario)
    
    def test_variance_from_actual_endpoint_exists(self):
        """Variance-from-actual endpoint should be accessible."""
        activity = PlannedActivity.objects.create(
            scenario=self.scenario,
            batch=self.batch,
            activity_type='SAMPLING',
            due_date=date.today(),
            status='COMPLETED',
            completed_at=date.today(),
            created_by=self.user
        )
        
        url = f'/api/v1/planning/planned-activities/{activity.id}/variance-from-actual/'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['activity_id'], activity.id)
    
    def test_variance_from_actual_with_daily_state(self):
        """Should return weight/FCR data from daily state."""
        activity = PlannedActivity.objects.create(
            scenario=self.scenario,
            batch=self.batch,
            activity_type='SAMPLING',
            due_date=date.today() - timedelta(days=5),
            status='COMPLETED',
            completed_at=date.today(),
            created_by=self.user
        )
        
        ActualDailyAssignmentState.objects.create(
            assignment=self.assignment,
            batch=self.batch,
            container=self.container,
            lifecycle_stage=self.stage,
            date=date.today(),
            day_number=30,
            avg_weight_g=Decimal('15.5'),
            population=9800,
            biomass_kg=Decimal('151.9'),
            observed_fcr=Decimal('1.15'),
            sources={'weight': 'measured'},
            confidence_scores={'weight': 1.0}
        )
        
        url = f'/api/v1/planning/planned-activities/{activity.id}/variance-from-actual/'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['weight_at_completion_g'], 15.5)
        self.assertEqual(response.data['fcr_at_completion'], 1.15)
        self.assertEqual(response.data['days_variance'], 5)


@override_settings(SKIP_CELERY_SIGNALS='1')
class TestProjectionPreviewAPI(APITestCase):
    """Test projection-preview API endpoint."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username=f'testuser-{uuid.uuid4().hex[:6]}',
            email='test@example.com',
            password='testpass123'
        )
        self.client.force_authenticate(user=self.user)
        
        unique_id = uuid.uuid4().hex[:6]
        self.species = create_test_species(name=f'Test Species {unique_id}')
        self.stage = create_test_lifecycle_stage(
            name=f'Fry-{unique_id}',
            species=self.species,
            order=1
        )
        
        self.batch = Batch.objects.create(
            batch_number=f'TEST-{unique_id}',
            species=self.species,
            lifecycle_stage=self.stage,
            start_date=date.today() - timedelta(days=30),
            status='ACTIVE'
        )
        
        self.scenario = create_test_scenario(user=self.user)
        self.batch.scenarios.add(self.scenario)
    
    def test_projection_preview_endpoint_exists(self):
        """Projection preview endpoint should be accessible."""
        activity = PlannedActivity.objects.create(
            scenario=self.scenario,
            batch=self.batch,
            activity_type='TRANSFER',
            due_date=date.today() + timedelta(days=30),
            status='PENDING',
            created_by=self.user
        )
        
        url = f'/api/v1/planning/planned-activities/{activity.id}/projection-preview/'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('rationale', response.data)
        self.assertIn('scenario_name', response.data)


@override_settings(SKIP_CELERY_SIGNALS='1')
class TestPlannedActivityScenarioValidation(APITestCase):
    """Test scenario validation on PlannedActivity updates."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username=f'testuser-{uuid.uuid4().hex[:6]}',
            email='test@example.com',
            password='testpass123'
        )
        self.client.force_authenticate(user=self.user)
        
        unique_id = uuid.uuid4().hex[:6]
        self.species = create_test_species(name=f'Test Species {unique_id}')
        self.stage = create_test_lifecycle_stage(
            name=f'Fry-{unique_id}',
            species=self.species,
            order=1
        )
        
        self.batch = Batch.objects.create(
            batch_number=f'TEST-{unique_id}',
            species=self.species,
            lifecycle_stage=self.stage,
            start_date=date.today() - timedelta(days=30),
            status='ACTIVE'
        )
        
        self.scenario = create_test_scenario(user=self.user)
        self.batch.scenarios.add(self.scenario)
        
        self.activity = PlannedActivity.objects.create(
            scenario=self.scenario,
            batch=self.batch,
            activity_type='SAMPLING',
            due_date=date.today() + timedelta(days=7),
            status='PENDING',
            created_by=self.user
        )
    
    def test_update_with_null_scenario_returns_400(self):
        """PATCH with scenario=null should return 400, not 500."""
        url = f'/api/v1/planning/planned-activities/{self.activity.id}/'
        response = self.client.patch(url, {'scenario': None}, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('scenario', response.data)
    
    def test_update_notes_without_changing_scenario_succeeds(self):
        """PATCH updating other fields without scenario should succeed."""
        url = f'/api/v1/planning/planned-activities/{self.activity.id}/'
        response = self.client.patch(url, {'notes': 'Updated notes'}, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.activity.refresh_from_db()
        self.assertEqual(self.activity.notes, 'Updated notes')
        # Scenario should remain unchanged
        self.assertEqual(self.activity.scenario, self.scenario)
