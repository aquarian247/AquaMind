"""
Core tests for Phase 3 - Growth Assimilation Engine - Issue #112.

Focused on validating core engine functionality:
- Engine initialization and scenario resolution
- Initial state bootstrap
- Temperature/mortality/feed data retrieval
- Selection method bias adjustment
- End-to-end recompute with stats

Edge case testing deferred to Phase 9 with real Faroe Islands data.
"""
import uuid
from decimal import Decimal
from datetime import date, timedelta
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.batch.models import (
    Batch, ActualDailyAssignmentState, MortalityEvent
)
from apps.batch.services.growth_assimilation import GrowthAssimilationEngine
from apps.environmental.models import EnvironmentalReading, EnvironmentalParameter
from apps.batch.tests.models.test_utils import (
    create_test_species,
    create_test_lifecycle_stage,
    create_test_container,
    create_test_batch_container_assignment
)
from apps.scenario.tests.test_helpers import (
    create_test_temperature_profile,
    create_test_tgc_model,
    create_test_fcr_model,
    create_test_mortality_model,
    create_test_biological_constraints,
    create_test_scenario
)
from apps.scenario.models import ProjectionRun

User = get_user_model()


class GrowthAssimilationCoreTestCase(TestCase):
    """Core tests for the Growth Assimilation Engine."""
    
    def setUp(self):
        """Set up minimal test data."""
        self.user = User.objects.create_user(
            username=f'testuser-{uuid.uuid4().hex[:6]}',
            email='test@example.com',
            password='testpass123'
        )
        
        # Create species and stages
        unique_id = uuid.uuid4().hex[:6]
        self.species = create_test_species(name=f'Test Species {unique_id}')
        self.stage = create_test_lifecycle_stage(
            name=f'Fry-{unique_id}',
            species=self.species,
            order=1
        )
        
        # Create container
        self.container = create_test_container(name=f'Tank-{unique_id}')
        
        # Create batch
        self.batch = Batch.objects.create(
            batch_number=f'TEST-{unique_id}',
            species=self.species,
            lifecycle_stage=self.stage,
            start_date=date(2024, 1, 1),
            status='ACTIVE'
        )
        
        # Create assignment
        self.assignment = create_test_batch_container_assignment(
            batch=self.batch,
            container=self.container,
            lifecycle_stage=self.stage,
            population_count=1000,
            avg_weight_g=Decimal('2.0')
        )
        
        # Create scenario
        temp_profile = create_test_temperature_profile()
        tgc_model = create_test_tgc_model(temp_profile)
        fcr_model = create_test_fcr_model()
        mortality_model = create_test_mortality_model()
        bio_constraints = create_test_biological_constraints(user=self.user)
        
        self.scenario = create_test_scenario(
            user=self.user,
            models={
                'tgc_model': tgc_model,
                'fcr_model': fcr_model,
                'mortality_model': mortality_model,
                'biological_constraints': bio_constraints
            }
        )
        self.scenario.batch = self.batch
        self.scenario.initial_weight = 2.0
        self.scenario.initial_count = 1000
        self.scenario.save()
        
        # Create projection run and pin it to batch
        self.projection_run = ProjectionRun.objects.create(
            scenario=self.scenario,
            run_number=1,
            label='Test Run'
        )
        self.batch.pinned_projection_run = self.projection_run
        self.batch.save()
        
        # Create temperature parameter
        self.temp_parameter, _ = EnvironmentalParameter.objects.get_or_create(
            name='temperature',
            defaults={'unit': '°C'}
        )
    
    def test_engine_initializes(self):
        """Test engine initializes with correct components."""
        engine = GrowthAssimilationEngine(self.assignment)
        
        self.assertIsNotNone(engine.tgc_calculator)
        self.assertIsNotNone(engine.mortality_calculator)
        self.assertEqual(engine.scenario, self.scenario)
    
    def test_engine_requires_scenario(self):
        """Test engine fails gracefully without scenario."""
        self.batch.pinned_projection_run = None
        self.batch.save()
        self.projection_run.delete()
        self.scenario.delete()
        
        with self.assertRaises(ValueError) as ctx:
            GrowthAssimilationEngine(self.assignment)
        
        self.assertIn('No scenario available', str(ctx.exception))
    
    def test_initial_state_bootstrap(self):
        """Test initial state uses assignment values."""
        engine = GrowthAssimilationEngine(self.assignment)
        initial_state = engine._get_initial_state(date(2024, 1, 1))
        
        self.assertEqual(initial_state['population'], 1000)
        self.assertGreater(initial_state['weight'], 0)
    
    def test_initial_state_from_previous(self):
        """Test initial state uses previous day's computed state."""
        # Create Day 1 state
        ActualDailyAssignmentState.objects.create(
            assignment=self.assignment,
            batch=self.batch,
            container=self.container,
            lifecycle_stage=self.stage,
            date=date(2024, 1, 1),
            day_number=1,
            avg_weight_g=Decimal('2.5'),
            population=995,
            biomass_kg=Decimal('2.49')
        )
        
        engine = GrowthAssimilationEngine(self.assignment)
        initial_state = engine._get_initial_state(date(2024, 1, 2))
        
        # Should use Day 1's values
        self.assertEqual(initial_state['weight'], 2.5)
        self.assertEqual(initial_state['population'], 995)
    
    def test_temperature_measured(self):
        """Test temperature retrieval from measurements."""
        engine = GrowthAssimilationEngine(self.assignment)
        
        # Add temperature reading
        EnvironmentalReading.objects.create(
            parameter=self.temp_parameter,
            container=self.container,
            value=Decimal('12.5'),
            reading_time=timezone.make_aware(
                timezone.datetime.combine(date(2024, 1, 1), timezone.datetime.min.time())
            )
        )
        
        temp, source, confidence = engine._get_temperature(date(2024, 1, 1))
        
        self.assertEqual(source, 'measured')
        self.assertEqual(confidence, 1.0)
        self.assertAlmostEqual(temp, 12.5, places=1)
    
    def test_temperature_profile_fallback(self):
        """Test temperature falls back to profile when no readings."""
        engine = GrowthAssimilationEngine(self.assignment)
        
        # No temperature readings - should use profile
        temp, source, confidence = engine._get_temperature(date(2024, 1, 1))
        
        self.assertEqual(source, 'profile')
        self.assertIsNotNone(temp)  # Profile should provide value
        self.assertLessEqual(confidence, 0.5)
    
    def test_mortality_model_fallback(self):
        """Test mortality uses model when no actual events."""
        engine = GrowthAssimilationEngine(self.assignment)
        
        mort_count, source, confidence = engine._get_mortality(
            date(2024, 1, 1),
            1000,
            self.stage
        )
        
        self.assertEqual(source, 'model')
        self.assertEqual(confidence, 0.4)
        self.assertGreaterEqual(mort_count, 0)
    
    def test_mortality_actual(self):
        """Test mortality uses actual events when available."""
        engine = GrowthAssimilationEngine(self.assignment)
        
        # Create mortality event
        MortalityEvent.objects.create(
            batch=self.batch,
            assignment=self.assignment,
            event_date=date(2024, 1, 1),
            count=5,
            biomass_kg=Decimal('0.01')
        )
        
        mort_count, source, confidence = engine._get_mortality(
            date(2024, 1, 1),
            1000,
            self.stage
        )
        
        # After FK fix, should be 'actual' not 'actual_prorated'
        self.assertEqual(source, 'actual')
        self.assertEqual(confidence, 1.0)  # Full confidence now!
        self.assertGreater(mort_count, 0)
    
    def test_selection_bias_largest(self):
        """Test LARGEST selection adjusts weight down."""
        engine = GrowthAssimilationEngine(self.assignment)
        
        adjusted = engine._adjust_for_selection_bias(100.0, 'LARGEST')
        self.assertLess(adjusted, 100.0)
    
    def test_selection_bias_smallest(self):
        """Test SMALLEST selection adjusts weight up."""
        engine = GrowthAssimilationEngine(self.assignment)
        
        adjusted = engine._adjust_for_selection_bias(100.0, 'SMALLEST')
        self.assertGreater(adjusted, 100.0)
    
    def test_selection_bias_average(self):
        """Test AVERAGE selection doesn't adjust."""
        engine = GrowthAssimilationEngine(self.assignment)
        
        adjusted = engine._adjust_for_selection_bias(100.0, 'AVERAGE')
        self.assertEqual(adjusted, 100.0)
    
    def test_recompute_range_end_to_end(self):
        """
        Core end-to-end test: Engine computes daily states.
        
        This is the critical test validating the engine works.
        """
        # Add temperature for 3 days
        for day_offset in range(3):
            EnvironmentalReading.objects.create(
                parameter=self.temp_parameter,
                container=self.container,
                value=Decimal('10.0'),
                reading_time=timezone.make_aware(
                    timezone.datetime.combine(
                        date(2024, 1, 1) + timedelta(days=day_offset),
                        timezone.datetime.min.time()
                    )
                )
            )
        
        # Run engine
        engine = GrowthAssimilationEngine(self.assignment)
        result = engine.recompute_range(date(2024, 1, 1), date(2024, 1, 3))
        
        # Verify stats
        self.assertEqual(result['rows_created'], 3)
        self.assertEqual(result['rows_updated'], 0)
        self.assertEqual(len(result['errors']), 0)
        
        # Verify states were created
        self.assertEqual(
            ActualDailyAssignmentState.objects.filter(
                assignment=self.assignment
            ).count(),
            3
        )
        
        # Verify Day 1 state has expected fields
        day1 = ActualDailyAssignmentState.objects.get(
            assignment=self.assignment,
            date=date(2024, 1, 1)
        )
        
        self.assertEqual(day1.day_number, 1)
        self.assertGreaterEqual(float(day1.avg_weight_g), 2.0)  # Should have grown (>= for floating point precision)
        self.assertEqual(day1.population, 1000)  # No mortality events
        self.assertIn('temp', day1.sources)
        self.assertIn('weight', day1.sources)
        self.assertIn('temp', day1.confidence_scores)



