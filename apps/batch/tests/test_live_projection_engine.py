"""
Tests for Live Forward Projection Engine.

Tests the core computation engine including:
- Engine initialization and scenario requirements
- Temperature bias calculation
- TGC-based growth projections
- ContainerForecastSummary updates
- API endpoint integration

Issue: Live Forward Projection Feature
"""
from datetime import date, timedelta
from decimal import Decimal

from django.test import TestCase, override_settings
from django.utils import timezone
from django.contrib.auth import get_user_model

from rest_framework.test import APIClient
from rest_framework import status

from apps.batch.models import (
    Batch, BatchContainerAssignment, Species, LifeCycleStage,
    ActualDailyAssignmentState, LiveForwardProjection,
    ContainerForecastSummary,
)
from apps.infrastructure.models import Container, ContainerType, Area, Geography
from apps.scenario.models import (
    Scenario, TGCModel, FCRModel, MortalityModel, TemperatureProfile,
    TemperatureReading, ProjectionRun,
)
from apps.batch.services.live_projection_engine import LiveProjectionEngine

User = get_user_model()


class LiveProjectionTestMixin:
    """Mixin providing test data setup for live projection tests."""

    def create_test_data(self):
        """Create minimal test data for projection engine tests."""
        # Geography & Infrastructure
        self.geography = Geography.objects.create(
            name='Test Region',
            description='Test geography'
        )
        self.area = Area.objects.create(
            name='Test Area',
            geography=self.geography,
            latitude=Decimal('60.0'),
            longitude=Decimal('-5.0'),
            max_biomass=Decimal('100000')
        )
        self.container_type = ContainerType.objects.create(
            name='Sea Pen',
            category='PEN',
            max_volume_m3=Decimal('5000')
        )
        self.container = Container.objects.create(
            name='Test-001',
            container_type=self.container_type,
            area=self.area,
            volume_m3=Decimal('5000'),
            max_biomass_kg=Decimal('50000'),
            active=True
        )

        # Species & Stage
        self.species = Species.objects.create(
            name='Atlantic Salmon',
            scientific_name='Salmo salar'
        )
        self.stage = LifeCycleStage.objects.create(
            species=self.species,
            name='Adult',
            order=5
        )

        # Temperature Profile
        self.temp_profile = TemperatureProfile.objects.create(
            name='Test Profile'
        )
        # Add temp readings (730 days for full salmon lifecycle)
        readings = []
        for day_num in range(1, 731):
            # Sinusoidal temp pattern (8-14°C)
            temp = 11 + 3 * (1 if day_num % 365 < 182 else -1) * abs(
                (day_num % 365) - 91
            ) / 91
            readings.append(TemperatureReading(
                profile=self.temp_profile,
                day_number=day_num,
                temperature=round(temp, 1)
            ))
        TemperatureReading.objects.bulk_create(readings)

        # TGC Model
        self.tgc_model = TGCModel.objects.create(
            name='Test TGC',
            tgc_value=Decimal('2.40'),  # Standard TGC value
            profile=self.temp_profile
        )

        # Mortality Model
        self.mortality_model = MortalityModel.objects.create(
            name='Test Mortality',
            frequency='daily',
            rate=0.05
        )

        # FCR Model
        self.fcr_model = FCRModel.objects.create(
            name='Test FCR'
        )

        # Create a user for scenario
        self.test_user = User.objects.create_user(
            username='scenariouser',
            password='testpass123',
            email='scenario@example.com'
        )

        # Scenario
        self.scenario = Scenario.objects.create(
            name='Test Scenario',
            duration_days=730,
            start_date=date.today() - timedelta(days=300),
            initial_count=100000,
            initial_weight=0.5,
            genotype='Test Genotype',
            supplier='Test Supplier',
            tgc_model=self.tgc_model,
            fcr_model=self.fcr_model,
            mortality_model=self.mortality_model,
            created_by=self.test_user
        )

        # Batch
        self.batch = Batch.objects.create(
            batch_number='TEST-001',
            species=self.species,
            lifecycle_stage=self.stage,
            start_date=date.today() - timedelta(days=300),
            status='ACTIVE'
        )

        # Projection Run
        self.projection_run = ProjectionRun.objects.create(
            scenario=self.scenario,
            run_number=1,
            label='Initial'
        )
        
        # Pin the projection run to the batch
        self.batch.pinned_projection_run = self.projection_run
        self.batch.save()

        # Assignment
        self.assignment = BatchContainerAssignment.objects.create(
            batch=self.batch,
            container=self.container,
            lifecycle_stage=self.stage,
            assignment_date=date.today() - timedelta(days=300),
            population_count=100000,
            biomass_kg=Decimal('50'),
            is_active=True
        )

        # Create actual daily states for last 30 days
        states = []
        for day_offset in range(30):
            state_date = date.today() - timedelta(days=29 - day_offset)
            day_number = (state_date - self.batch.start_date).days + 1
            weight = Decimal('2000') + Decimal(str(day_offset * 15))

            # Simulate sensor-derived temps for some days
            if day_offset % 2 == 0:  # Every other day has sensor data
                temp_source = 'measured'
                temp_c = Decimal('11.5')  # Slightly above profile (simulating bias)
            else:
                temp_source = 'profile'
                temp_c = Decimal('11.0')

            state = ActualDailyAssignmentState(
                assignment=self.assignment,
                batch=self.batch,
                container=self.container,
                date=state_date,
                day_number=day_number,
                avg_weight_g=weight,
                population=95000 - day_offset * 50,
                biomass_kg=(weight * (95000 - day_offset * 50)) / Decimal('1000000'),
                temp_c=temp_c,
                mortality_count=50,
                lifecycle_stage=self.stage,
                sources={'temp': temp_source, 'weight': 'tgc_computed'},
                confidence_scores={'temp': 0.9, 'weight': 0.85, 'mortality': 0.8},
            )
            states.append(state)

        ActualDailyAssignmentState.objects.bulk_create(states)


class TestLiveProjectionEngine(LiveProjectionTestMixin, TestCase):
    """Test suite for LiveProjectionEngine."""

    def setUp(self):
        """Set up test fixtures."""
        self.create_test_data()

    def test_engine_initialization(self):
        """Test engine initializes correctly with valid assignment."""
        engine = LiveProjectionEngine(self.assignment)

        self.assertEqual(engine.assignment, self.assignment)
        self.assertEqual(engine.batch, self.batch)
        self.assertEqual(engine.scenario, self.scenario)
        self.assertIsNotNone(engine.tgc_calculator)
        self.assertIsNotNone(engine.mortality_calculator)
        self.assertEqual(engine.temp_profile, self.temp_profile)

    def test_engine_requires_scenario(self):
        """Test engine raises error when no scenario available."""
        # Remove pinned projection run
        self.batch.pinned_projection_run = None
        self.batch.save()

        # Remove all scenario references
        self.scenario.batch = None
        self.scenario.save()

        with self.assertRaises(ValueError) as ctx:
            LiveProjectionEngine(self.assignment)
        
        self.assertIn("No scenario available", str(ctx.exception))

    def test_compute_and_store_creates_projections(self):
        """Test compute_and_store creates projection records."""
        engine = LiveProjectionEngine(self.assignment)
        computed_date = date.today()

        result = engine.compute_and_store(computed_date)

        # Check result stats
        self.assertIn('rows_created', result)
        self.assertGreater(result['rows_created'], 0)

        # Verify projections in database
        projections = LiveForwardProjection.objects.filter(
            assignment=self.assignment,
            computed_date=computed_date
        )
        self.assertGreater(projections.count(), 0)

    def test_compute_and_store_updates_summary(self):
        """Test compute_and_store updates ContainerForecastSummary."""
        engine = LiveProjectionEngine(self.assignment)
        engine.compute_and_store(date.today())

        # Check summary exists and is populated
        summary = ContainerForecastSummary.objects.filter(
            assignment=self.assignment
        ).first()

        self.assertIsNotNone(summary)
        self.assertIsNotNone(summary.current_weight_g)
        self.assertIsNotNone(summary.current_population)
        self.assertIsNotNone(summary.computed_date)

    def test_projection_idempotency(self):
        """Test running projection twice on same day replaces old data."""
        engine = LiveProjectionEngine(self.assignment)
        computed_date = date.today()

        # First run
        result1 = engine.compute_and_store(computed_date)
        count1 = LiveForwardProjection.objects.filter(
            assignment=self.assignment,
            computed_date=computed_date
        ).count()

        # Second run (should replace)
        result2 = engine.compute_and_store(computed_date)
        count2 = LiveForwardProjection.objects.filter(
            assignment=self.assignment,
            computed_date=computed_date
        ).count()

        self.assertEqual(count1, count2)
        self.assertEqual(result1['rows_created'], result2['rows_created'])

    def test_projection_weight_increases(self):
        """Test projected weight increases over time (growth)."""
        engine = LiveProjectionEngine(self.assignment)
        engine.compute_and_store(date.today())

        projections = list(LiveForwardProjection.objects.filter(
            assignment=self.assignment
        ).order_by('projection_date')[:30])

        # Weight should generally increase
        for i in range(1, len(projections)):
            self.assertGreaterEqual(
                projections[i].projected_weight_g,
                projections[i-1].projected_weight_g
            )

    def test_projection_population_decreases(self):
        """Test projected population decreases over time (mortality)."""
        engine = LiveProjectionEngine(self.assignment)
        engine.compute_and_store(date.today())

        projections = list(LiveForwardProjection.objects.filter(
            assignment=self.assignment
        ).order_by('projection_date')[:30])

        # Population should decrease
        for i in range(1, len(projections)):
            self.assertLessEqual(
                projections[i].projected_population,
                projections[i-1].projected_population
            )

    def test_no_projection_without_actual_state(self):
        """Test engine gracefully handles missing actual states."""
        # Delete all actual states
        ActualDailyAssignmentState.objects.filter(
            assignment=self.assignment
        ).delete()

        engine = LiveProjectionEngine(self.assignment)
        result = engine.compute_and_store(date.today())

        # Should handle gracefully with error indication
        self.assertFalse(result.get('success', True))
        self.assertIn('error', result)


class TestLiveProjectionAPI(LiveProjectionTestMixin, TestCase):
    """Test suite for live projection API endpoints."""

    def setUp(self):
        """Set up test fixtures."""
        self.create_test_data()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            email='test@example.com'
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_assignment_live_projection_endpoint(self):
        """Test assignment-level live projection endpoint."""
        # Create projections first
        engine = LiveProjectionEngine(self.assignment)
        engine.compute_and_store(date.today())

        response = self.client.get(
            f'/api/v1/batch/container-assignments/{self.assignment.id}/live-forward-projection/'
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()

        self.assertIn('assignment_id', data)
        self.assertIn('projections', data)
        self.assertEqual(data['assignment_id'], self.assignment.id)

    def test_assignment_projection_404_for_invalid(self):
        """Test 404 returned for non-existent assignment."""
        response = self.client.get(
            '/api/v1/batch/container-assignments/99999/live-forward-projection/'
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_tiered_harvest_endpoint(self):
        """Test tiered harvest forecast endpoint returns data."""
        # Create projections first
        engine = LiveProjectionEngine(self.assignment)
        engine.compute_and_store(date.today())

        response = self.client.get('/api/v1/batch/forecast/tiered-harvest/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()

        self.assertIn('summary', data)
        self.assertIn('forecasts', data)
        # Check that summary contains the count fields
        self.assertIn('planned_count', data['summary'])
        self.assertIn('projected_count', data['summary'])
        self.assertIn('needs_attention_count', data['summary'])
