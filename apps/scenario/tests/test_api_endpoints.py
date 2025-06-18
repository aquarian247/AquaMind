"""
Test suite for Scenario Planning API endpoints.

Tests validation, serialization, and API functionality.
"""
from datetime import date, timedelta
from decimal import Decimal
import json
import io

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status

from apps.batch.models import LifeCycleStage, Batch, Species
from apps.infrastructure.models import Geography, Area, Container, ContainerType
from ..models import (
    TemperatureProfile, TemperatureReading, TGCModel, FCRModel,
    FCRModelStage, MortalityModel, Scenario, ScenarioProjection,
    BiologicalConstraints, StageConstraint
)

User = get_user_model()


class BaseScenarioAPITestCase(TestCase):
    """Base test case with common setup for scenario API tests."""
    
    def setUp(self):
        """Set up test data."""
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.other_user = User.objects.create_user(
            username='otheruser',
            email='other@example.com',
            password='testpass123'
        )
        
        # Create API client
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        
        # Create lifecycle stages
        self.create_lifecycle_stages()
        
        # Create temperature profile
        self.temp_profile = TemperatureProfile.objects.create(
            name='Test Temperature Profile'
        )
        
        # Add temperature readings
        start_date = date.today()
        for i in range(365):
            TemperatureReading.objects.create(
                profile=self.temp_profile,
                reading_date=start_date + timedelta(days=i),
                temperature=10 + (i % 10) * 0.5  # Vary between 10-15°C
            )
        
        # Create models
        self.tgc_model = TGCModel.objects.create(
            name='Test TGC Model',
            location='Test Location',
            release_period='Spring',
            tgc_value=0.025,
            exponent_n=0.33,
            exponent_m=0.66,
            profile=self.temp_profile
        )
        
        self.fcr_model = FCRModel.objects.create(
            name='Test FCR Model'
        )
        
        # Add FCR stages
        for stage in LifeCycleStage.objects.all():
            FCRModelStage.objects.create(
                model=self.fcr_model,
                stage=stage,
                fcr_value=1.0 + (float(stage.expected_weight_min_g or 0)) / 1000,
                duration_days=60
            )
        
        self.mortality_model = MortalityModel.objects.create(
            name='Test Mortality Model',
            frequency='daily',
            rate=0.05
        )
        
        # Create biological constraints
        self.bio_constraints = BiologicalConstraints.objects.create(
            name='Test Constraints',
            description='Test biological constraints',
            is_active=True,
            created_by=self.user
        )
        
        # Add stage constraints
        stages_data = [
            ('egg', 0.1, 0.3, None),
            ('alevin', 0.3, 1.0, None),
            ('fry', 1.0, 5.0, None),
            ('parr', 5.0, 50.0, 50.0),
            ('smolt', 50.0, 150.0, 150.0),
            ('post_smolt', 150.0, 1000.0, None),
            ('harvest', 1000.0, 10000.0, None)
        ]
        
        for stage, min_w, max_w, fw_limit in stages_data:
            StageConstraint.objects.create(
                constraint_set=self.bio_constraints,
                lifecycle_stage=stage,
                min_weight_g=min_w,
                max_weight_g=max_w,
                max_freshwater_weight_g=fw_limit
            )
    
    def create_lifecycle_stages(self):
        """Create lifecycle stages for testing."""
        stages = [
            ('egg', 'Egg', 0.1, 0.3),
            ('alevin', 'Alevin', 0.3, 1.0),
            ('fry', 'Fry', 1.0, 5.0),
            ('parr', 'Parr', 5.0, 50.0),
            ('smolt', 'Smolt', 50.0, 150.0),
            ('post_smolt', 'Post-Smolt', 150.0, 1000.0),
            ('harvest', 'Harvest', 1000.0, 10000.0)
        ]
        
        # Create a species first
        from apps.batch.models import Species
        species = Species.objects.create(
            name='Atlantic Salmon',
            scientific_name='Salmo salar'
        )
        
        for i, (name, display, min_weight, max_weight) in enumerate(stages):
            LifeCycleStage.objects.create(
                name=name,
                species=species,
                order=i + 1,
                description=display,
                expected_weight_min_g=min_weight,
                expected_weight_max_g=max_weight
            )
    
    def get_api_url(self, viewname, **kwargs):
        """Helper to construct API URLs."""
        return f'/api/v1/scenario/{viewname}/'


class TGCModelAPITests(BaseScenarioAPITestCase):
    """Test TGC Model API endpoints."""
    
    def test_create_tgc_model_with_validation(self):
        """Test creating TGC model with validation."""
        url = self.get_api_url('tgc-models')
        
        # Valid data
        data = {
            'name': 'New TGC Model',
            'location': 'Norway',
            'release_period': 'Winter',
            'tgc_value': 0.023,
            'exponent_n': 0.35,
            'exponent_m': 0.65,
            'profile': self.temp_profile.profile_id
        }
        
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['name'], 'New TGC Model')
        
    def test_tgc_validation_errors(self):
        """Test TGC model validation errors."""
        url = self.get_api_url('tgc-models')
        
        # Test negative TGC value
        data = {
            'name': 'Invalid TGC',
            'location': 'Test',
            'release_period': 'Test',
            'tgc_value': -0.01,
            'profile': self.temp_profile.profile_id
        }
        
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('tgc_value', response.data)
        
        # Test TGC value too high
        data['tgc_value'] = 0.2
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('too high', str(response.data['tgc_value']))
        
        # Test invalid exponents
        data['tgc_value'] = 0.025
        data['exponent_n'] = 3.0  # Too high
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('exponent_n', response.data)
    
    def test_tgc_model_templates(self):
        """Test getting TGC model templates."""
        url = self.get_api_url('tgc-models') + 'templates/'
        
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, list)
        self.assertGreater(len(response.data), 0)
        
        # Check template structure
        template = response.data[0]
        self.assertIn('name', template)
        self.assertIn('location', template)
        self.assertIn('tgc_value', template)
        self.assertIn('description', template)
    
    def test_duplicate_tgc_model(self):
        """Test duplicating a TGC model."""
        url = f"{self.get_api_url('tgc-models')}{self.tgc_model.model_id}/duplicate/"
        
        data = {'new_name': 'Duplicated TGC Model'}
        
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['name'], 'Duplicated TGC Model')
        self.assertEqual(float(response.data['tgc_value']), self.tgc_model.tgc_value)
        
        # Test duplicate name error
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class FCRModelAPITests(BaseScenarioAPITestCase):
    """Test FCR Model API endpoints."""
    
    def test_fcr_model_stage_validation(self):
        """Test FCR model stage validation."""
        url = self.get_api_url('fcr-models')
        
        # Create FCR model
        data = {'name': 'New FCR Model'}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        fcr_model_id = response.data['model_id']
        
        # Get model with stage coverage info
        response = self.client.get(f"{url}{fcr_model_id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('stage_coverage', response.data)
        self.assertEqual(response.data['stage_coverage']['coverage_percent'], 0)
    
    def test_fcr_model_templates(self):
        """Test FCR model templates."""
        url = self.get_api_url('fcr-models') + 'templates/'
        
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, list)
        
        # Check template has stages
        template = response.data[0]
        self.assertIn('stages', template)
        self.assertIsInstance(template['stages'], list)
    
    def test_fcr_stage_summary(self):
        """Test FCR stage summary endpoint."""
        url = f"{self.get_api_url('fcr-models')}{self.fcr_model.model_id}/stage_summary/"
        
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('total_stages', response.data)
        self.assertIn('total_duration', response.data)
        self.assertIn('average_fcr', response.data)
        self.assertIn('stages', response.data)


class MortalityModelAPITests(BaseScenarioAPITestCase):
    """Test Mortality Model API endpoints."""
    
    def test_mortality_rate_validation(self):
        """Test mortality rate validation."""
        url = self.get_api_url('mortality-models')
        
        # Test rate out of range
        data = {
            'name': 'Invalid Mortality',
            'frequency': 'daily',
            'rate': 150  # > 100%
        }
        
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('rate', response.data)
        
        # Test high daily rate warning
        data['rate'] = 10  # Very high for daily
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('unusually high', str(response.data['rate']))
    
    def test_mortality_effective_annual_rate(self):
        """Test effective annual rate calculation."""
        url = f"{self.get_api_url('mortality-models')}{self.mortality_model.model_id}/"
        
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('effective_annual_rate', response.data)
        
        # Check calculation is reasonable
        annual_rate = response.data['effective_annual_rate']
        self.assertGreater(annual_rate, 0)
        self.assertLess(annual_rate, 100)


class ScenarioAPITests(BaseScenarioAPITestCase):
    """Test Scenario API endpoints."""
    
    def test_create_scenario_with_validation(self):
        """Test creating scenario with validation."""
        url = self.get_api_url('scenarios')
        
        # Valid scenario
        data = {
            'name': 'Test Scenario',
            'start_date': date.today().isoformat(),
            'duration_days': 600,
            'initial_count': 10000,
            'initial_weight': 50.0,
            'genotype': 'Atlantic Salmon',
            'supplier': 'Test Supplier',
            'tgc_model': self.tgc_model.model_id,
            'fcr_model': self.fcr_model.model_id,
            'mortality_model': self.mortality_model.model_id,
            'biological_constraints': self.bio_constraints.id
        }
        
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['name'], 'Test Scenario')
        self.assertIn('initial_stage', response.data)
        self.assertEqual(response.data['initial_stage']['stage'], 'parr')
    
    def test_scenario_validation_errors(self):
        """Test scenario validation errors."""
        url = self.get_api_url('scenarios')
        
        # Test duration validation
        data = {
            'name': 'Invalid Duration',
            'start_date': date.today().isoformat(),
            'duration_days': 1500,  # Too long
            'initial_count': 10000,
            'tgc_model': self.tgc_model.model_id,
            'fcr_model': self.fcr_model.model_id,
            'mortality_model': self.mortality_model.model_id
        }
        
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('duration_days', response.data)
        
        # Test initial count validation
        data['duration_days'] = 600
        data['initial_count'] = 0  # Too low
        
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('initial_count', response.data)
        
        # Test initial weight validation
        data['initial_count'] = 10000
        data['initial_weight'] = 20000  # Too high (20kg)
        
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('initial_weight', response.data)
    
    def test_scenario_name_uniqueness_per_user(self):
        """Test scenario name uniqueness is per user."""
        url = self.get_api_url('scenarios')
        
        # Create first scenario
        data = {
            'name': 'Unique Name',
            'start_date': date.today().isoformat(),
            'duration_days': 600,
            'initial_count': 10000,
            'initial_weight': 50.0,
            'genotype': 'Test',
            'supplier': 'Test',
            'tgc_model': self.tgc_model.model_id,
            'fcr_model': self.fcr_model.model_id,
            'mortality_model': self.mortality_model.model_id
        }
        
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Try to create with same name for same user
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('name', response.data)
        
        # Switch to other user
        self.client.force_authenticate(user=self.other_user)
        
        # Should be able to create with same name
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
    
    def test_scenario_duplicate(self):
        """Test scenario duplication."""
        # Create original scenario
        scenario = Scenario.objects.create(
            name='Original Scenario',
            start_date=date.today(),
            duration_days=600,
            initial_count=10000,
            initial_weight=50.0,
            genotype='Test',
            supplier='Test',
            tgc_model=self.tgc_model,
            fcr_model=self.fcr_model,
            mortality_model=self.mortality_model,
            created_by=self.user
        )
        
        url = f"{self.get_api_url('scenarios')}{scenario.scenario_id}/duplicate/"
        
        data = {
            'new_name': 'Duplicated Scenario',
            'include_projections': False,
            'include_model_changes': True
        }
        
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['name'], 'Duplicated Scenario')
        self.assertEqual(response.data['initial_count'], scenario.initial_count)
    
    def test_scenario_comparison(self):
        """Test scenario comparison endpoint."""
        # Create multiple scenarios
        scenarios = []
        for i in range(3):
            scenario = Scenario.objects.create(
                name=f'Scenario {i}',
                start_date=date.today(),
                duration_days=600,
                initial_count=10000,
                initial_weight=50.0 + i * 10,
                genotype='Test',
                supplier='Test',
                tgc_model=self.tgc_model,
                fcr_model=self.fcr_model,
                mortality_model=self.mortality_model,
                created_by=self.user
            )
            scenarios.append(scenario)
        
        url = self.get_api_url('scenarios') + 'compare/'
        
        data = {
            'scenario_ids': [s.scenario_id for s in scenarios],
            'comparison_metrics': ['final_weight', 'final_biomass']
        }
        
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('scenarios', response.data)
        self.assertIn('metrics', response.data)
        self.assertEqual(len(response.data['scenarios']), 3)
    
    def test_scenario_permissions(self):
        """Test scenario permissions."""
        # Create scenario as user
        scenario = Scenario.objects.create(
            name='User Scenario',
            start_date=date.today(),
            duration_days=600,
            initial_count=10000,
            initial_weight=50.0,
            genotype='Test',
            supplier='Test',
            tgc_model=self.tgc_model,
            fcr_model=self.fcr_model,
            mortality_model=self.mortality_model,
            created_by=self.user
        )
        
        # Switch to other user
        self.client.force_authenticate(user=self.other_user)
        
        # Should not see scenario in list by default
        url = self.get_api_url('scenarios')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 0)
        
        # Can see with all=true
        response = self.client.get(url + '?all=true')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreater(len(response.data['results']), 0)
        
        # Cannot run projection on other user's scenario
        url = f"{self.get_api_url('scenarios')}{scenario.scenario_id}/run_projection/"
        response = self.client.post(url)
        # Should get 404 since the scenario is not visible to this user
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class BiologicalConstraintsAPITests(BaseScenarioAPITestCase):
    """Test Biological Constraints API endpoints."""
    
    def test_list_active_constraints(self):
        """Test listing active constraints."""
        url = self.get_api_url('biological-constraints') + 'active/'
        
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreater(len(response.data), 0)
        
        # Check structure
        constraint = response.data[0]
        self.assertIn('stage_constraints', constraint)
        self.assertIsInstance(constraint['stage_constraints'], list)
    
    def test_constraint_serialization(self):
        """Test constraint serialization format."""
        url = f"{self.get_api_url('biological-constraints')}{self.bio_constraints.id}/"
        
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Check stage constraint format
        stage_constraints = response.data['stage_constraints']
        self.assertGreater(len(stage_constraints), 0)
        
        constraint = stage_constraints[0]
        self.assertIn('weight_range', constraint)
        self.assertIn('min', constraint['weight_range'])
        self.assertIn('max', constraint['weight_range'])
        self.assertIn('temperature_range', constraint)
        self.assertIn('freshwater_limit', constraint)


class DataEntryAPITests(BaseScenarioAPITestCase):
    """Test Data Entry API endpoints."""
    
    def test_csv_validation(self):
        """Test CSV validation endpoint."""
        url = self.get_api_url('data-entry') + 'validate_csv/'
        
        # Create CSV content
        csv_content = "date,temperature\n2024-01-01,10.5\n2024-01-02,11.0\n"
        csv_file = io.BytesIO(csv_content.encode('utf-8'))
        csv_file.name = 'test.csv'
        
        data = {
            'file': csv_file,
            'data_type': 'temperature',
            'profile_name': 'Test Profile'
        }
        
        response = self.client.post(url, data, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('success', response.data)
        self.assertIn('preview_data', response.data)
    
    def test_csv_template_download(self):
        """Test CSV template download."""
        url = self.get_api_url('data-entry') + 'csv_template/'
        
        # Test temperature template
        response = self.client.get(url + '?data_type=temperature')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response['Content-Type'], 'text/csv')
        
        # Test with sample data
        response = self.client.get(url + '?data_type=temperature&include_sample_data=true')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Check content
        content = response.content.decode('utf-8')
        self.assertIn('date', content)
        self.assertIn('temperature', content)


class ProjectionChartAPITests(BaseScenarioAPITestCase):
    """Test projection chart data formatting."""
    
    def test_chart_data_endpoint(self):
        """Test chart data endpoint."""
        # Create scenario with projections
        scenario = Scenario.objects.create(
            name='Chart Test Scenario',
            start_date=date.today(),
            duration_days=30,
            initial_count=10000,
            initial_weight=50.0,
            genotype='Test',
            supplier='Test',
            tgc_model=self.tgc_model,
            fcr_model=self.fcr_model,
            mortality_model=self.mortality_model,
            created_by=self.user
        )
        
        # Create some projections
        for i in range(30):
            ScenarioProjection.objects.create(
                scenario=scenario,
                projection_date=date.today() + timedelta(days=i),
                day_number=i,
                average_weight=50.0 + i * 2,
                population=10000 - i * 5,
                biomass=(50.0 + i * 2) * (10000 - i * 5) / 1000,
                daily_feed=10 + i * 0.5,
                cumulative_feed=(10 + i * 0.5) * (i + 1),
                temperature=10 + (i % 5) * 0.5,
                current_stage=LifeCycleStage.objects.get(name='parr')
            )
        
        url = f"{self.get_api_url('scenarios')}{scenario.scenario_id}/chart_data/"
        
        # Test default chart data
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('labels', response.data)
        self.assertIn('datasets', response.data)
        
        # Test with specific metrics
        response = self.client.get(url + '?metrics=weight&metrics=biomass&chart_type=line')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['datasets']), 2)
        
        # Check dataset structure
        dataset = response.data['datasets'][0]
        self.assertIn('label', dataset)
        self.assertIn('data', dataset)
        self.assertIn('borderColor', dataset)


class TemperatureProfileAPITests(BaseScenarioAPITestCase):
    """Test Temperature Profile API endpoints."""
    
    def test_temperature_statistics(self):
        """Test temperature statistics endpoint."""
        url = f"{self.get_api_url('temperature-profiles')}{self.temp_profile.profile_id}/statistics/"
        
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('statistics', response.data)
        
        stats = response.data['statistics']
        self.assertIn('min', stats)
        self.assertIn('max', stats)
        self.assertIn('avg', stats)
        self.assertIn('count', stats)
        self.assertIn('date_range', stats)
    
    def test_bulk_date_ranges(self):
        """Test bulk date range input."""
        url = self.get_api_url('temperature-profiles') + 'bulk_date_ranges/'
        
        data = {
            'profile_name': 'Bulk Range Profile',
            'ranges': [
                {
                    'start_date': '2024-01-01',
                    'end_date': '2024-01-31',
                    'value': 8.5
                },
                {
                    'start_date': '2024-02-01',
                    'end_date': '2024-02-28',
                    'value': 9.0
                }
            ],
            'merge_adjacent': True,
            'fill_gaps': True,
            'interpolation_method': 'linear'
        }
        
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['name'], 'Bulk Range Profile')
        
        # Test overlapping ranges validation
        data['ranges'][1]['start_date'] = '2024-01-15'  # Overlaps with first range
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('overlap', str(response.data).lower())


class SummaryStatsAPITests(BaseScenarioAPITestCase):
    """Test summary statistics endpoints."""
    
    def test_scenario_summary_stats(self):
        """Test scenario summary statistics."""
        # Create some scenarios
        for i in range(5):
            Scenario.objects.create(
                name=f'Stats Scenario {i}',
                start_date=date.today() - timedelta(days=i),
                duration_days=600 + i * 100,
                initial_count=10000,
                initial_weight=50.0,
                genotype='Test',
                supplier='Test',
                tgc_model=self.tgc_model,
                fcr_model=self.fcr_model,
                mortality_model=self.mortality_model,
                created_by=self.user
            )
        
        url = self.get_api_url('scenarios') + 'summary_stats/'
        
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Check stats structure
        self.assertIn('total_scenarios', response.data)
        self.assertIn('scenarios_with_projections', response.data)
        self.assertIn('average_duration', response.data)
        self.assertIn('location_distribution', response.data)
        self.assertIn('recent_scenarios', response.data)
        
        self.assertEqual(response.data['total_scenarios'], 5)
        self.assertIsInstance(response.data['recent_scenarios'], list) 