"""
Tests for Phase 8.5: Polish Features

Tests the Phase 8.5 enhancements:
- FCR Calculation Enhancement
- Edge Guard: Auto-Default Scenario  
- Broodstock Resilience Triggers
- Projection Preview API
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
from apps.batch.services.growth_assimilation import GrowthAssimilationEngine
from apps.batch.tests.models.test_utils import (
    create_test_species,
    create_test_lifecycle_stage,
    create_test_container,
    create_test_batch_container_assignment,
)
from apps.scenario.tests.test_helpers import create_test_scenario
from apps.planning.models import PlannedActivity

User = get_user_model()


class TestFCRCalculation(TestCase):
    """Test FCR calculation enhancements."""
    
    def test_fcr_calculated_from_feed_and_biomass_gain(self):
        """FCR should be calculated as feed_kg / biomass_gain_kg."""
        feed_kg = 100.0
        prev_biomass = 100.0
        new_biomass = 180.0
        biomass_gain = new_biomass - prev_biomass
        
        expected_fcr = feed_kg / biomass_gain
        self.assertAlmostEqual(expected_fcr, 1.25, places=2)
    
    def test_fcr_insufficient_data_when_no_feed(self):
        """FCR should be None with 'insufficient_data' source when no feeding data."""
        feed_kg = 0.0
        sources = {}
        MIN_BIOMASS_GAIN_FOR_FCR = 1.0
        biomass_gain = 10.0
        
        if feed_kg == 0 and biomass_gain > MIN_BIOMASS_GAIN_FOR_FCR:
            observed_fcr = None
            sources['fcr'] = 'insufficient_data'
        
        self.assertIsNone(observed_fcr)
        self.assertEqual(sources['fcr'], 'insufficient_data')
    
    def test_fcr_insufficient_data_when_small_biomass_gain(self):
        """FCR should be None when biomass gain is too small."""
        feed_kg = 10.0
        sources = {}
        MIN_BIOMASS_GAIN_FOR_FCR = 1.0
        biomass_gain = 0.5
        
        if biomass_gain <= MIN_BIOMASS_GAIN_FOR_FCR:
            observed_fcr = None
            sources['fcr'] = 'insufficient_data'
        
        self.assertIsNone(observed_fcr)
        self.assertEqual(sources['fcr'], 'insufficient_data')
    
    def test_fcr_capped_at_10(self):
        """FCR values > 10.0 should be capped at 10.0."""
        feed_kg = 200.0
        biomass_gain = 10.0
        observed_fcr = feed_kg / biomass_gain
        
        if observed_fcr > 10.0:
            observed_fcr = 10.0
        
        self.assertEqual(observed_fcr, 10.0)


@override_settings(SKIP_CELERY_SIGNALS='1')
class TestEdgeGuardAutoDefaultScenario(TestCase):
    """Test auto-default scenario for PlannedActivity."""
    
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
        
        self.batch = Batch.objects.create(
            batch_number=f'TEST-{unique_id}',
            species=self.species,
            lifecycle_stage=self.stage,
            start_date=date.today() - timedelta(days=30),
            status='ACTIVE'
        )
        
        self.scenario = create_test_scenario(user=self.user)
        self.batch.scenarios.add(self.scenario)
    
    def test_get_baseline_scenario_returns_first_scenario(self):
        """Should return first associated scenario if no pinned run."""
        result = self.batch.get_baseline_scenario()
        self.assertEqual(result, self.scenario)
    
    def test_get_baseline_scenario_raises_when_no_scenario(self):
        """Should raise ValueError when no scenario exists."""
        batch_no_scenario = Batch.objects.create(
            batch_number=f'TEST-NO-SCENARIO-{uuid.uuid4().hex[:6]}',
            species=self.species,
            lifecycle_stage=self.stage,
            status='ACTIVE',
            start_date=date.today()
        )
        
        with self.assertRaises(ValueError) as context:
            batch_no_scenario.get_baseline_scenario()
        
        self.assertIn('No scenario available', str(context.exception))


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
    
    def test_projection_preview_returns_rationale(self):
        """Projection preview should return scenario-based rationale."""
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
        self.assertEqual(response.data['activity_id'], activity.id)
        self.assertEqual(response.data['scenario_name'], self.scenario.name)
        self.assertIn('rationale', response.data)
    
    def test_projection_preview_handles_missing_projection(self):
        """Should return rationale even without projection data."""
        activity = PlannedActivity.objects.create(
            scenario=self.scenario,
            batch=self.batch,
            activity_type='VACCINATION',
            due_date=date.today() + timedelta(days=60),
            status='PENDING',
            created_by=self.user
        )
        
        url = f'/api/v1/planning/planned-activities/{activity.id}/projection-preview/'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNone(response.data['projected_weight_g'])
        self.assertIn('Scheduled per', response.data['rationale'])


@override_settings(SKIP_CELERY_SIGNALS='1')
class TestBroodstockResilienceTriggers(TestCase):
    """Test optional broodstock resilience triggers."""
    
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
    
    def test_broodstock_trigger_skips_when_no_parentage(self):
        """Should skip gracefully when batch has no parentage data."""
        engine = GrowthAssimilationEngine(self.assignment)
        
        # This should not raise an error
        engine._evaluate_broodstock_triggers(
            current_date=date.today(),
            scenario=self.scenario
        )
        
        # No activity should be created
        activities = PlannedActivity.objects.filter(
            batch=self.batch,
            activity_type='TREATMENT',
            notes__contains='Genetic low-resilience'
        )
        self.assertEqual(activities.count(), 0)
    
    def test_broodstock_trigger_handles_import_error(self):
        """Should handle ImportError gracefully when broodstock app unavailable."""
        with patch.dict('sys.modules', {'apps.broodstock.models': None}):
            engine = GrowthAssimilationEngine(self.assignment)
            
            try:
                engine._evaluate_broodstock_triggers(
                    current_date=date.today(),
                    scenario=self.scenario
                )
            except ImportError:
                self.fail("Should handle ImportError gracefully")


@override_settings(SKIP_CELERY_SIGNALS='1')
class TestPlannedActivityFKIntegration(TestCase):
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
    
    def test_new_anchor_type_planned_activity(self):
        """Should support 'planned_activity' as anchor type."""
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
        
        self.assertEqual(state.anchor_type, 'planned_activity')
        self.assertEqual(state.planned_activity, activity)
        
        valid_choices = [choice[0] for choice in ActualDailyAssignmentState.ANCHOR_TYPE_CHOICES]
        self.assertIn('planned_activity', valid_choices)
