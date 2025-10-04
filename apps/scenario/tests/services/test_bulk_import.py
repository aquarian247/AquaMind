"""
Tests for bulk data import service.

Tests cover CSV import for temperature, FCR, and mortality data
with comprehensive validation and error handling scenarios.
"""
import io
from django.test import TestCase

from apps.scenario.services.bulk_import import BulkDataImportService
from apps.scenario.models import (
    TemperatureProfile,
    FCRModel,
    MortalityModel
)
from apps.batch.models import Species, LifeCycleStage


class BulkImportTemperatureTestCase(TestCase):
    """Test temperature data import functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.service = BulkDataImportService()

    def test_import_temperature_success(self):
        """Test successful temperature data import."""
        csv_content = (
            "date,temperature\n"
            "2024-01-01,10.5\n"
            "2024-01-02,11.0\n"
            "2024-01-03,10.8\n"
        )
        csv_file = io.StringIO(csv_content)

        success, result = self.service.import_temperature_data(
            csv_file, "Test Profile"
        )

        self.assertTrue(success)
        self.assertEqual(len(result['errors']), 0)
        self.assertEqual(result['created_objects']['readings_count'], 3)

        # Verify data was saved
        profile = TemperatureProfile.objects.get(name="Test Profile")
        self.assertEqual(profile.readings.count(), 3)

    def test_import_temperature_invalid_headers(self):
        """Test temperature import with invalid headers."""
        csv_content = (
            "date,temp\n"
            "2024-01-01,10.5\n"
        )
        csv_file = io.StringIO(csv_content)

        success, result = self.service.import_temperature_data(
            csv_file, "Test Profile"
        )

        self.assertFalse(success)
        self.assertIn("Invalid headers", result['errors'][0])

    def test_import_temperature_invalid_date(self):
        """Test temperature import with invalid date format."""
        csv_content = (
            "date,temperature\n"
            "not-a-date,10.5\n"
        )
        csv_file = io.StringIO(csv_content)

        success, result = self.service.import_temperature_data(
            csv_file, "Test Profile"
        )

        self.assertFalse(success)
        self.assertIn("Invalid date format", result['errors'][0])

    def test_import_temperature_invalid_value(self):
        """Test temperature import with invalid temperature value."""
        csv_content = (
            "date,temperature\n"
            "2024-01-01,not-a-number\n"
        )
        csv_file = io.StringIO(csv_content)

        success, result = self.service.import_temperature_data(
            csv_file, "Test Profile"
        )

        self.assertFalse(success)
        self.assertIn("Invalid temperature value", result['errors'][0])

    def test_import_temperature_unusual_value_warning(self):
        """Test warning for unusual temperature values."""
        csv_content = (
            "date,temperature\n"
            "2024-01-01,55.0\n"
        )
        csv_file = io.StringIO(csv_content)

        success, result = self.service.import_temperature_data(
            csv_file, "Test Profile"
        )

        self.assertTrue(success)
        self.assertIn("Unusual temperature", result['warnings'][0])

    def test_import_temperature_duplicate_dates(self):
        """Test temperature import with duplicate dates."""
        csv_content = (
            "date,temperature\n"
            "2024-01-01,10.5\n"
            "2024-01-01,11.0\n"
        )
        csv_file = io.StringIO(csv_content)

        success, result = self.service.import_temperature_data(
            csv_file, "Test Profile"
        )

        self.assertFalse(success)
        self.assertIn("Duplicate dates", result['errors'][0])

    def test_import_temperature_update_existing(self):
        """Test updating existing temperature profile."""
        # Create initial profile
        csv_content = (
            "date,temperature\n"
            "2024-01-01,10.5\n"
        )
        csv_file = io.StringIO(csv_content)
        self.service.import_temperature_data(csv_file, "Test Profile")

        # Update with new data
        csv_content = (
            "date,temperature\n"
            "2024-01-02,11.0\n"
        )
        csv_file = io.StringIO(csv_content)
        success, result = self.service.import_temperature_data(
            csv_file, "Test Profile"
        )

        self.assertTrue(success)
        self.assertIn("Updated existing profile", result['warnings'][0])

        # Verify old data was replaced
        profile = TemperatureProfile.objects.get(name="Test Profile")
        self.assertEqual(profile.readings.count(), 1)

    def test_import_temperature_validate_only(self):
        """Test temperature import in validation-only mode."""
        csv_content = (
            "date,temperature\n"
            "2024-01-01,10.5\n"
        )
        csv_file = io.StringIO(csv_content)

        success, result = self.service.import_temperature_data(
            csv_file, "Test Profile", validate_only=True
        )

        self.assertTrue(success)
        # Verify no data was saved
        self.assertEqual(TemperatureProfile.objects.count(), 0)

    def test_import_temperature_various_date_formats(self):
        """Test temperature import with various date formats."""
        csv_content = (
            "date,temperature\n"
            "2024-01-01,10.5\n"
            "01/02/2024,11.0\n"
            "03-01-2024,10.8\n"
        )
        csv_file = io.StringIO(csv_content)

        success, result = self.service.import_temperature_data(
            csv_file, "Test Profile"
        )

        self.assertTrue(success)
        self.assertEqual(result['created_objects']['readings_count'], 3)


class BulkImportFCRTestCase(TestCase):
    """Test FCR data import functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.service = BulkDataImportService()

        # Create test species and lifecycle stages
        self.species = Species.objects.create(
            name="Atlantic Salmon",
            scientific_name="Salmo salar"
        )
        self.egg_stage = LifeCycleStage.objects.create(
            name="Egg",
            species=self.species,
            order=1
        )
        self.fry_stage = LifeCycleStage.objects.create(
            name="Fry",
            species=self.species,
            order=2
        )
        self.parr_stage = LifeCycleStage.objects.create(
            name="Parr",
            species=self.species,
            order=3
        )

    def test_import_fcr_success(self):
        """Test successful FCR data import."""
        csv_content = (
            "stage,fcr_value,duration_days\n"
            "Egg,0.0,50\n"
            "Fry,1.0,90\n"
            "Parr,1.1,90\n"
        )
        csv_file = io.StringIO(csv_content)

        success, result = self.service.import_fcr_data(
            csv_file, "Standard FCR"
        )

        self.assertTrue(success)
        self.assertEqual(len(result['errors']), 0)
        self.assertEqual(result['created_objects']['stages_count'], 3)

        # Verify data was saved
        fcr_model = FCRModel.objects.get(name="Standard FCR")
        self.assertEqual(fcr_model.stages.count(), 3)

    def test_import_fcr_invalid_headers(self):
        """Test FCR import with invalid headers."""
        csv_content = (
            "stage,fcr,days\n"
            "Egg,0.0,50\n"
        )
        csv_file = io.StringIO(csv_content)

        success, result = self.service.import_fcr_data(
            csv_file, "Standard FCR"
        )

        self.assertFalse(success)
        self.assertIn("Invalid headers", result['errors'][0])

    def test_import_fcr_missing_stage(self):
        """Test FCR import with missing stage name."""
        csv_content = (
            "stage,fcr_value,duration_days\n"
            ",1.0,90\n"
        )
        csv_file = io.StringIO(csv_content)

        success, result = self.service.import_fcr_data(
            csv_file, "Standard FCR"
        )

        self.assertFalse(success)
        self.assertIn("Missing stage name", result['errors'][0])

    def test_import_fcr_invalid_fcr_value(self):
        """Test FCR import with invalid FCR value."""
        csv_content = (
            "stage,fcr_value,duration_days\n"
            "Egg,not-a-number,50\n"
        )
        csv_file = io.StringIO(csv_content)

        success, result = self.service.import_fcr_data(
            csv_file, "Standard FCR"
        )

        self.assertFalse(success)
        self.assertIn("Invalid FCR value", result['errors'][0])

    def test_import_fcr_negative_value(self):
        """Test FCR import with negative FCR value."""
        csv_content = (
            "stage,fcr_value,duration_days\n"
            "Egg,-1.0,50\n"
        )
        csv_file = io.StringIO(csv_content)

        success, result = self.service.import_fcr_data(
            csv_file, "Standard FCR"
        )

        self.assertFalse(success)
        self.assertIn("must be non-negative", result['errors'][0])

    def test_import_fcr_high_value_warning(self):
        """Test warning for unusually high FCR values."""
        csv_content = (
            "stage,fcr_value,duration_days\n"
            "Egg,15.0,50\n"
        )
        csv_file = io.StringIO(csv_content)

        success, result = self.service.import_fcr_data(
            csv_file, "Standard FCR"
        )

        self.assertTrue(success)
        self.assertIn("Unusually high FCR value", result['warnings'][0])

    def test_import_fcr_invalid_duration(self):
        """Test FCR import with invalid duration."""
        csv_content = (
            "stage,fcr_value,duration_days\n"
            "Egg,1.0,not-a-number\n"
        )
        csv_file = io.StringIO(csv_content)

        success, result = self.service.import_fcr_data(
            csv_file, "Standard FCR"
        )

        self.assertFalse(success)
        self.assertIn("Invalid duration_days", result['errors'][0])

    def test_import_fcr_zero_duration(self):
        """Test FCR import with zero duration."""
        csv_content = (
            "stage,fcr_value,duration_days\n"
            "Egg,1.0,0\n"
        )
        csv_file = io.StringIO(csv_content)

        success, result = self.service.import_fcr_data(
            csv_file, "Standard FCR"
        )

        self.assertFalse(success)
        self.assertIn("at least 1 day", result['errors'][0])

    def test_import_fcr_duplicate_stages(self):
        """Test FCR import with duplicate stage names."""
        csv_content = (
            "stage,fcr_value,duration_days\n"
            "Egg,0.0,50\n"
            "Egg,1.0,60\n"
        )
        csv_file = io.StringIO(csv_content)

        success, result = self.service.import_fcr_data(
            csv_file, "Standard FCR"
        )

        self.assertFalse(success)
        self.assertIn("Duplicate stage names", result['errors'][0])

    def test_import_fcr_nonexistent_stage(self):
        """Test FCR import with non-existent lifecycle stage."""
        csv_content = (
            "stage,fcr_value,duration_days\n"
            "NonExistent,1.0,50\n"
        )
        csv_file = io.StringIO(csv_content)

        success, result = self.service.import_fcr_data(
            csv_file, "Standard FCR"
        )

        self.assertFalse(success)
        self.assertIn("not found in system", result['errors'][0])

    def test_import_fcr_case_insensitive_stage(self):
        """Test FCR import with case-insensitive stage matching."""
        csv_content = (
            "stage,fcr_value,duration_days\n"
            "egg,0.0,50\n"
            "FRY,1.0,90\n"
        )
        csv_file = io.StringIO(csv_content)

        success, result = self.service.import_fcr_data(
            csv_file, "Standard FCR"
        )

        self.assertTrue(success)
        self.assertEqual(result['created_objects']['stages_count'], 2)

    def test_import_fcr_update_existing(self):
        """Test updating existing FCR model."""
        # Create initial model
        csv_content = (
            "stage,fcr_value,duration_days\n"
            "Egg,0.0,50\n"
        )
        csv_file = io.StringIO(csv_content)
        self.service.import_fcr_data(csv_file, "Standard FCR")

        # Update with new data
        csv_content = (
            "stage,fcr_value,duration_days\n"
            "Fry,1.0,90\n"
        )
        csv_file = io.StringIO(csv_content)
        success, result = self.service.import_fcr_data(
            csv_file, "Standard FCR"
        )

        self.assertTrue(success)
        self.assertIn("old stages replaced", result['warnings'][0])

        # Verify old stages were replaced
        fcr_model = FCRModel.objects.get(name="Standard FCR")
        self.assertEqual(fcr_model.stages.count(), 1)

    def test_import_fcr_validate_only(self):
        """Test FCR import in validation-only mode."""
        csv_content = (
            "stage,fcr_value,duration_days\n"
            "Egg,0.0,50\n"
        )
        csv_file = io.StringIO(csv_content)

        success, result = self.service.import_fcr_data(
            csv_file, "Standard FCR", validate_only=True
        )

        self.assertTrue(success)
        # Verify no data was saved
        self.assertEqual(FCRModel.objects.count(), 0)


class BulkImportMortalityTestCase(TestCase):
    """Test mortality data import functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.service = BulkDataImportService()

    def test_import_mortality_success(self):
        """Test successful mortality data import."""
        csv_content = (
            "date,rate\n"
            "2024-01-01,0.1\n"
            "2024-01-08,0.1\n"
            "2024-01-15,0.15\n"
        )
        csv_file = io.StringIO(csv_content)

        success, result = self.service.import_mortality_data(
            csv_file, "Low Mortality"
        )

        self.assertTrue(success)
        self.assertEqual(len(result['errors']), 0)
        self.assertEqual(result['created_objects']['data_points_count'], 3)

        # Verify average rate was calculated
        expected_avg = (0.1 + 0.1 + 0.15) / 3
        self.assertAlmostEqual(
            result['created_objects']['average_rate'],
            expected_avg,
            places=2
        )

        # Verify data was saved
        model = MortalityModel.objects.get(name="Low Mortality")
        self.assertAlmostEqual(model.rate, expected_avg, places=2)
        self.assertEqual(model.frequency, 'daily')

    def test_import_mortality_invalid_headers(self):
        """Test mortality import with invalid headers."""
        csv_content = (
            "date,mortality\n"
            "2024-01-01,0.1\n"
        )
        csv_file = io.StringIO(csv_content)

        success, result = self.service.import_mortality_data(
            csv_file, "Low Mortality"
        )

        self.assertFalse(success)
        self.assertIn("Invalid headers", result['errors'][0])

    def test_import_mortality_invalid_date(self):
        """Test mortality import with invalid date format."""
        csv_content = (
            "date,rate\n"
            "not-a-date,0.1\n"
        )
        csv_file = io.StringIO(csv_content)

        success, result = self.service.import_mortality_data(
            csv_file, "Low Mortality"
        )

        self.assertFalse(success)
        self.assertIn("Invalid date format", result['errors'][0])

    def test_import_mortality_invalid_rate(self):
        """Test mortality import with invalid rate value."""
        csv_content = (
            "date,rate\n"
            "2024-01-01,not-a-number\n"
        )
        csv_file = io.StringIO(csv_content)

        success, result = self.service.import_mortality_data(
            csv_file, "Low Mortality"
        )

        self.assertFalse(success)
        self.assertIn("Invalid mortality rate", result['errors'][0])

    def test_import_mortality_negative_rate(self):
        """Test mortality import with negative rate."""
        csv_content = (
            "date,rate\n"
            "2024-01-01,-1.0\n"
        )
        csv_file = io.StringIO(csv_content)

        success, result = self.service.import_mortality_data(
            csv_file, "Low Mortality"
        )

        self.assertFalse(success)
        self.assertIn("between 0 and 100", result['errors'][0])

    def test_import_mortality_rate_over_100(self):
        """Test mortality import with rate over 100%."""
        csv_content = (
            "date,rate\n"
            "2024-01-01,150.0\n"
        )
        csv_file = io.StringIO(csv_content)

        success, result = self.service.import_mortality_data(
            csv_file, "Low Mortality"
        )

        self.assertFalse(success)
        self.assertIn("between 0 and 100", result['errors'][0])

    def test_import_mortality_high_rate_warning(self):
        """Test warning for high mortality rates."""
        csv_content = (
            "date,rate\n"
            "2024-01-01,15.0\n"
        )
        csv_file = io.StringIO(csv_content)

        success, result = self.service.import_mortality_data(
            csv_file, "High Mortality"
        )

        self.assertTrue(success)
        self.assertIn("High mortality rate", result['warnings'][0])

    def test_import_mortality_duplicate_dates(self):
        """Test mortality import with duplicate dates."""
        csv_content = (
            "date,rate\n"
            "2024-01-01,0.1\n"
            "2024-01-01,0.2\n"
        )
        csv_file = io.StringIO(csv_content)

        success, result = self.service.import_mortality_data(
            csv_file, "Low Mortality"
        )

        self.assertFalse(success)
        self.assertIn("Duplicate dates", result['errors'][0])

    def test_import_mortality_update_existing(self):
        """Test updating existing mortality model."""
        # Create initial model
        csv_content = (
            "date,rate\n"
            "2024-01-01,0.1\n"
        )
        csv_file = io.StringIO(csv_content)
        self.service.import_mortality_data(csv_file, "Low Mortality")

        # Update with new data
        csv_content = (
            "date,rate\n"
            "2024-01-02,0.2\n"
        )
        csv_file = io.StringIO(csv_content)
        success, result = self.service.import_mortality_data(
            csv_file, "Low Mortality"
        )

        self.assertTrue(success)
        self.assertIn(
            "Updated existing mortality model",
            result['warnings'][0]
        )

        # Verify rate was updated
        model = MortalityModel.objects.get(name="Low Mortality")
        self.assertAlmostEqual(model.rate, 0.2, places=2)

    def test_import_mortality_validate_only(self):
        """Test mortality import in validation-only mode."""
        csv_content = (
            "date,rate\n"
            "2024-01-01,0.1\n"
        )
        csv_file = io.StringIO(csv_content)

        success, result = self.service.import_mortality_data(
            csv_file, "Low Mortality", validate_only=True
        )

        self.assertTrue(success)
        # Verify no data was saved
        self.assertEqual(MortalityModel.objects.count(), 0)

    def test_import_mortality_average_calculation(self):
        """Test correct average calculation with multiple data points."""
        csv_content = (
            "date,rate\n"
            "2024-01-01,0.1\n"
            "2024-01-02,0.2\n"
            "2024-01-03,0.3\n"
            "2024-01-04,0.4\n"
        )
        csv_file = io.StringIO(csv_content)

        success, result = self.service.import_mortality_data(
            csv_file, "Test Mortality"
        )

        self.assertTrue(success)
        # Average of 0.1, 0.2, 0.3, 0.4 = 0.25
        self.assertAlmostEqual(
            result['created_objects']['average_rate'],
            0.25,
            places=2
        )


class CSVTemplateGenerationTestCase(TestCase):
    """Test CSV template generation functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.service = BulkDataImportService()

    def test_generate_temperature_template(self):
        """Test temperature CSV template generation."""
        template = self.service.generate_csv_template('temperature')

        self.assertIn('date,temperature', template)
        self.assertIn('2024-01-01,8.5', template)

    def test_generate_fcr_template(self):
        """Test FCR CSV template generation."""
        template = self.service.generate_csv_template('fcr')

        self.assertIn('stage,fcr_value,duration_days', template)
        self.assertIn('Egg,0,50', template)

    def test_generate_mortality_template(self):
        """Test mortality CSV template generation."""
        template = self.service.generate_csv_template('mortality')

        self.assertIn('date,rate', template)
        self.assertIn('2024-01-01,0.1', template)

    def test_generate_template_unknown_type(self):
        """Test template generation with unknown type."""
        with self.assertRaises(ValueError):
            self.service.generate_csv_template('unknown_type')
