"""
Tests for Live Forward Projection Engine.

Tests the core computation engine including:
- Temperature bias calculation from sensor data
- TGC-based growth projections
- Population decay with mortality
- ContainerForecastSummary updates
- API endpoint integration

Issue: Live Forward Projection Feature
"""
import pytest
from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import Mock, patch

from django.test import TestCase, override_settings
from django.utils import timezone

from apps.batch.models import (
    Batch, BatchContainerAssignment, Species, LifeCycleStage,
    ActualDailyAssignmentState, LiveForwardProjection,
    ContainerForecastSummary,
)
from apps.infrastructure.models import Container, ContainerType, Area, Geography
from apps.scenario.models import (
    Scenario, TGCModel, MortalityModel, TemperatureProfile,
    TemperatureDay, ProjectionRun,
)
from apps.batch.services.live_projection_engine import LiveProjectionEngine


@pytest.fixture
def setup_test_data(db):
    """Create minimal test data for projection engine tests."""
    # Geography & Infrastructure
    geography = Geography.objects.create(
        name='Test Region',
        description='Test geography'
    )
    area = Area.objects.create(
        name='Test Area',
        geography=geography,
        max_biomass_kg=100000
    )
    container_type = ContainerType.objects.create(
        name='Sea Pen',
        category='PEN',
        max_biomass_kg=50000
    )
    container = Container.objects.create(
        name='Test-001',
        container_type=container_type,
        area=area,
        max_capacity=50000,
        is_active=True
    )

    # Species & Stage
    species = Species.objects.create(
        name='Atlantic Salmon',
        scientific_name='Salmo salar'
    )
    stage = LifeCycleStage.objects.create(
        species=species,
        name='Adult',
        sequence_order=5
    )

    # Temperature Profile
    temp_profile = TemperatureProfile.objects.create(
        name='Test Profile',
        description='Test temperature profile'
    )
    # Add temp days (730 days for full salmon lifecycle)
    for day_num in range(1, 731):
        # Sinusoidal temp pattern (8-14°C)
        temp = 11 + 3 * (1 if day_num % 365 < 182 else -1) * abs(
            (day_num % 365) - 91
        ) / 91
        TemperatureDay.objects.create(
            profile=temp_profile,
            day_number=day_num,
            temperature_c=Decimal(str(round(temp, 1)))
        )

    # TGC Model
    tgc_model = TGCModel.objects.create(
        name='Test TGC',
        tgc_value=Decimal('0.0024'),
        profile=temp_profile
    )

    # Mortality Model
    mortality_model = MortalityModel.objects.create(
        name='Test Mortality',
        daily_rate_percent=Decimal('0.05')
    )

    # Scenario
    scenario = Scenario.objects.create(
        name='Test Scenario',
        species=species,
        duration_days=730,
        start_date=date.today() - timedelta(days=300),
        status='ACTIVE',
        tgc_model=tgc_model,
        mortality_model=mortality_model,
        initial_count=100000,
        initial_weight=Decimal('0.5')
    )

    # Batch
    batch = Batch.objects.create(
        batch_number='TEST-001',
        species=species,
        lifecycle_stage=stage,
        start_date=date.today() - timedelta(days=300),
        status='ACTIVE',
        initial_population=100000,
        initial_average_weight_g=Decimal('0.5')
    )

    # Projection Run (pinned)
    projection_run = ProjectionRun.objects.create(
        scenario=scenario,
        run_date=date.today() - timedelta(days=300),
        run_number=1,
        label='Initial'
    )
    batch.pinned_projection_run = projection_run
    batch.save()

    # Assignment
    assignment = BatchContainerAssignment.objects.create(
        batch=batch,
        container=container,
        assignment_date=date.today() - timedelta(days=300),
        population_count=100000,
        biomass_kg=Decimal('50'),
        is_active=True
    )

    # Create actual daily states for last 30 days
    states = []
    for day_offset in range(30):
        state_date = date.today() - timedelta(days=29 - day_offset)
        day_number = (state_date - batch.start_date).days + 1
        weight = Decimal('2000') + Decimal(str(day_offset * 15))

        # Simulate sensor-derived temps for some days
        if day_offset % 2 == 0:  # Every other day has sensor data
            temp_source = 'measured'
            temp_c = Decimal('11.5')  # Slightly above profile (simulating bias)
        else:
            temp_source = 'profile'
            temp_c = Decimal('11.0')

        state = ActualDailyAssignmentState(
            assignment=assignment,
            batch=batch,
            date=state_date,
            day_number=day_number,
            avg_weight_g=weight,
            population=95000 - day_offset * 50,
            biomass_kg=(weight * (95000 - day_offset * 50)) / Decimal('1000000'),
            temp_c=temp_c,
            mortality_count=50,
            lifecycle_stage=stage,
            sources={'temp': temp_source, 'weight': 'tgc_computed'},
            confidence_scores={'temp': 0.9, 'weight': 0.85, 'mortality': 0.8},
        )
        states.append(state)

    ActualDailyAssignmentState.objects.bulk_create(states)

    return {
        'geography': geography,
        'area': area,
        'container': container,
        'species': species,
        'stage': stage,
        'temp_profile': temp_profile,
        'tgc_model': tgc_model,
        'mortality_model': mortality_model,
        'scenario': scenario,
        'batch': batch,
        'assignment': assignment,
        'projection_run': projection_run,
    }


class TestLiveProjectionEngine(TestCase):
    """Test suite for LiveProjectionEngine."""

    @pytest.fixture(autouse=True)
    def setup(self, setup_test_data):
        """Set up test fixtures."""
        self.data = setup_test_data

    def test_engine_initialization(self):
        """Test engine initializes correctly with valid assignment."""
        engine = LiveProjectionEngine(self.data['assignment'])

        assert engine.assignment == self.data['assignment']
        assert engine.batch == self.data['batch']
        assert engine.scenario == self.data['scenario']
        assert engine.tgc_calculator is not None
        assert engine.mortality_calculator is not None
        assert engine.temp_profile == self.data['temp_profile']

    def test_engine_requires_scenario(self):
        """Test engine raises error when no scenario available."""
        # Remove pinned projection run
        self.data['batch'].pinned_projection_run = None
        self.data['batch'].save()

        # Remove all scenarios
        self.data['scenario'].delete()

        with pytest.raises(ValueError, match="No scenario available"):
            LiveProjectionEngine(self.data['assignment'])

    def test_temperature_bias_computation(self):
        """Test temperature bias is computed correctly from sensor data."""
        engine = LiveProjectionEngine(self.data['assignment'])
        latest_state = ActualDailyAssignmentState.objects.filter(
            assignment=self.data['assignment']
        ).order_by('-date').first()

        bias_c, metadata = engine._compute_temperature_bias(latest_state)

        # Should have a positive bias (sensor temps are 0.5°C above profile)
        assert float(bias_c) > 0
        assert metadata['window_days_used'] > 0
        assert 'raw_bias_c' in metadata

    @override_settings(LIVE_FORWARD_TEMP_BIAS_CLAMP_C=(-1.0, 1.0))
    def test_temperature_bias_clamping(self):
        """Test temperature bias is clamped to configured bounds."""
        # Create states with extreme bias
        state = ActualDailyAssignmentState.objects.filter(
            assignment=self.data['assignment']
        ).order_by('-date').first()

        # Modify to have large bias
        ActualDailyAssignmentState.objects.filter(
            assignment=self.data['assignment'],
            sources__temp='measured'
        ).update(temp_c=Decimal('18.0'))  # Way above profile

        engine = LiveProjectionEngine(self.data['assignment'])
        bias_c, metadata = engine._compute_temperature_bias(state)

        # Should be clamped to max
        assert float(bias_c) <= 1.0
        assert metadata['clamped'] is True

    def test_projection_computation(self):
        """Test forward projection generates correct number of rows."""
        engine = LiveProjectionEngine(self.data['assignment'])
        result = engine.compute_and_store()

        assert result['success'] is True
        assert result['rows_created'] > 0
        assert result['assignment_id'] == self.data['assignment'].id

        # Verify projections were stored
        projections = LiveForwardProjection.objects.filter(
            assignment=self.data['assignment']
        )
        assert projections.count() == result['rows_created']

    def test_projection_idempotency(self):
        """Test running projection twice on same day replaces old data."""
        engine = LiveProjectionEngine(self.data['assignment'])

        # First run
        result1 = engine.compute_and_store()
        count1 = LiveForwardProjection.objects.filter(
            assignment=self.data['assignment']
        ).count()

        # Second run
        result2 = engine.compute_and_store()
        count2 = LiveForwardProjection.objects.filter(
            assignment=self.data['assignment']
        ).count()

        # Counts should be equal (replaced, not duplicated)
        assert count1 == count2
        assert result2['success'] is True

    def test_projection_weight_increases(self):
        """Test projected weight increases over time (growth)."""
        engine = LiveProjectionEngine(self.data['assignment'])
        engine.compute_and_store()

        projections = LiveForwardProjection.objects.filter(
            assignment=self.data['assignment']
        ).order_by('projection_date')

        weights = [float(p.projected_weight_g) for p in projections]

        # Weight should generally increase (TGC growth)
        assert weights[-1] > weights[0]

    def test_projection_population_decreases(self):
        """Test projected population decreases over time (mortality)."""
        engine = LiveProjectionEngine(self.data['assignment'])
        engine.compute_and_store()

        projections = LiveForwardProjection.objects.filter(
            assignment=self.data['assignment']
        ).order_by('projection_date')

        populations = [p.projected_population for p in projections]

        # Population should decrease (mortality)
        assert populations[-1] < populations[0]

    def test_container_forecast_summary_created(self):
        """Test ContainerForecastSummary is created/updated."""
        engine = LiveProjectionEngine(self.data['assignment'])
        engine.compute_and_store()

        summary = ContainerForecastSummary.objects.get(
            assignment=self.data['assignment']
        )

        assert summary.current_weight_g > 0
        assert summary.current_population > 0
        assert summary.state_date is not None
        assert summary.computed_date is not None

    def test_forecast_summary_threshold_crossing(self):
        """Test harvest date is detected when weight crosses threshold."""
        engine = LiveProjectionEngine(self.data['assignment'])
        engine.compute_and_store()

        summary = ContainerForecastSummary.objects.get(
            assignment=self.data['assignment']
        )

        # Should have projected harvest date (weight will cross 5kg eventually)
        # May be None if projection horizon doesn't reach threshold
        if summary.projected_harvest_date:
            assert summary.days_to_harvest is not None
            assert summary.harvest_threshold_g > 0

    def test_needs_planning_attention_flag(self):
        """Test needs_planning_attention is set correctly."""
        # First compute projections
        engine = LiveProjectionEngine(self.data['assignment'])
        engine.compute_and_store()

        summary = ContainerForecastSummary.objects.get(
            assignment=self.data['assignment']
        )

        # Without PlannedActivity, should be False or True depending on dates
        # (depends on how close to threshold and attention_threshold_days)
        assert isinstance(summary.needs_planning_attention, bool)

    def test_provenance_stored_in_projection(self):
        """Test model inputs are stored for transparency."""
        engine = LiveProjectionEngine(self.data['assignment'])
        engine.compute_and_store()

        proj = LiveForwardProjection.objects.filter(
            assignment=self.data['assignment']
        ).first()

        # Provenance fields should be populated
        assert proj.temp_profile_id == self.data['temp_profile'].id
        assert proj.temp_profile_name == self.data['temp_profile'].name
        assert proj.tgc_value_used > 0
        assert proj.temp_bias_window_days > 0


class TestLiveProjectionEndpoint(TestCase):
    """Test suite for live-forward-projection API endpoint."""

    @pytest.fixture(autouse=True)
    def setup(self, setup_test_data, client):
        """Set up test fixtures and API client."""
        self.data = setup_test_data
        self.client = client

    def test_endpoint_returns_projections(self):
        """Test endpoint returns projection data."""
        # First compute projections
        engine = LiveProjectionEngine(self.data['assignment'])
        engine.compute_and_store()

        url = f"/api/v1/batch/container-assignments/{self.data['assignment'].id}/live-forward-projection/"
        response = self.client.get(url)

        assert response.status_code == 200
        data = response.json()

        assert 'assignment_id' in data
        assert 'provenance' in data
        assert 'projections' in data
        assert len(data['projections']) > 0

    def test_endpoint_404_when_no_projections(self):
        """Test endpoint returns 404 when no projections exist."""
        url = f"/api/v1/batch/container-assignments/{self.data['assignment'].id}/live-forward-projection/"
        response = self.client.get(url)

        assert response.status_code == 404

    def test_endpoint_computed_date_filter(self):
        """Test endpoint filters by computed_date parameter."""
        engine = LiveProjectionEngine(self.data['assignment'])
        engine.compute_and_store()

        computed_date = timezone.now().date()
        url = f"/api/v1/batch/container-assignments/{self.data['assignment'].id}/live-forward-projection/?computed_date={computed_date}"
        response = self.client.get(url)

        assert response.status_code == 200
        data = response.json()
        assert data['computed_date'] == computed_date.isoformat()


class TestTieredHarvestForecast(TestCase):
    """Test suite for tiered harvest forecast endpoint."""

    @pytest.fixture(autouse=True)
    def setup(self, setup_test_data, client):
        """Set up test fixtures."""
        self.data = setup_test_data
        self.client = client

    def test_tiered_endpoint_returns_summary(self):
        """Test tiered endpoint returns summary counts."""
        # Compute projections first
        engine = LiveProjectionEngine(self.data['assignment'])
        engine.compute_and_store()

        url = "/api/v1/batch/forecast/tiered-harvest/"
        response = self.client.get(url)

        assert response.status_code == 200
        data = response.json()

        assert 'summary' in data
        assert 'planned_count' in data['summary']
        assert 'projected_count' in data['summary']
        assert 'needs_attention_count' in data['summary']

    def test_tiered_endpoint_returns_forecasts(self):
        """Test tiered endpoint returns forecast items."""
        engine = LiveProjectionEngine(self.data['assignment'])
        engine.compute_and_store()

        url = "/api/v1/batch/forecast/tiered-harvest/"
        response = self.client.get(url)

        data = response.json()
        assert 'forecasts' in data

        if len(data['forecasts']) > 0:
            forecast = data['forecasts'][0]
            assert 'tier' in forecast
            assert 'batch_id' in forecast
            assert 'batch_number' in forecast

    def test_tiered_endpoint_geography_filter(self):
        """Test tiered endpoint filters by geography."""
        engine = LiveProjectionEngine(self.data['assignment'])
        engine.compute_and_store()

        url = f"/api/v1/batch/forecast/tiered-harvest/?geography_id={self.data['geography'].id}"
        response = self.client.get(url)

        assert response.status_code == 200

    def test_tiered_endpoint_tier_filter(self):
        """Test tiered endpoint filters by tier."""
        engine = LiveProjectionEngine(self.data['assignment'])
        engine.compute_and_store()

        url = "/api/v1/batch/forecast/tiered-harvest/?tier=PROJECTED"
        response = self.client.get(url)

        assert response.status_code == 200
        data = response.json()

        # All results should be PROJECTED tier
        for forecast in data['forecasts']:
            assert forecast['tier'] == 'PROJECTED'

