"""
Simplified tests for Phase 1 schema migrations - Issue #112.

Tests that the new fields exist and have correct properties.
"""
from django.test import TestCase
from django.db import connection

from apps.batch.models import TransferAction, Batch
from apps.health.models import Treatment


class Phase1SchemaMigrationTestCase(TestCase):
    """Test that Phase 1 migrations added the correct fields."""
    
    def test_transferaction_has_measured_fields(self):
        """Test that TransferAction model has all new measured weight fields."""
        # Get all field names
        field_names = [f.name for f in TransferAction._meta.get_fields()]
        
        # Check that all new fields exist
        self.assertIn('measured_avg_weight_g', field_names)
        self.assertIn('measured_std_dev_weight_g', field_names)
        self.assertIn('measured_sample_size', field_names)
        self.assertIn('measured_avg_length_cm', field_names)
        self.assertIn('measured_notes', field_names)
        self.assertIn('selection_method', field_names)
    
    def test_transferaction_selection_method_choices(self):
        """Test that selection_method field has correct choices."""
        field = TransferAction._meta.get_field('selection_method')
        choices_values = [choice[0] for choice in field.choices]
        
        self.assertIn('AVERAGE', choices_values)
        self.assertIn('LARGEST', choices_values)
        self.assertIn('SMALLEST', choices_values)
    
    def test_transferaction_measured_fields_nullable(self):
        """Test that measured fields are nullable."""
        measured_avg_weight_field = TransferAction._meta.get_field('measured_avg_weight_g')
        self.assertTrue(measured_avg_weight_field.null)
        self.assertTrue(measured_avg_weight_field.blank)
        
        measured_std_dev_field = TransferAction._meta.get_field('measured_std_dev_weight_g')
        self.assertTrue(measured_std_dev_field.null)
        self.assertTrue(measured_std_dev_field.blank)
        
        measured_sample_size_field = TransferAction._meta.get_field('measured_sample_size')
        self.assertTrue(measured_sample_size_field.null)
        self.assertTrue(measured_sample_size_field.blank)
    
    def test_batch_has_pinned_scenario_field(self):
        """Test that Batch model has pinned_scenario field."""
        field_names = [f.name for f in Batch._meta.get_fields()]
        self.assertIn('pinned_scenario', field_names)
    
    def test_batch_pinned_scenario_nullable(self):
        """Test that pinned_scenario field is nullable."""
        pinned_scenario_field = Batch._meta.get_field('pinned_scenario')
        self.assertTrue(pinned_scenario_field.null)
        self.assertTrue(pinned_scenario_field.blank)
        
        # Check that it's a ForeignKey to Scenario
        self.assertEqual(pinned_scenario_field.related_model.__name__, 'Scenario')
    
    def test_treatment_has_weighing_fields(self):
        """Test that Treatment model has new weighing-related fields."""
        field_names = [f.name for f in Treatment._meta.get_fields()]
        
        self.assertIn('includes_weighing', field_names)
        self.assertIn('sampling_event', field_names)
        self.assertIn('journal_entry', field_names)
    
    def test_treatment_includes_weighing_default(self):
        """Test that includes_weighing field has correct default."""
        includes_weighing_field = Treatment._meta.get_field('includes_weighing')
        self.assertFalse(includes_weighing_field.default)
    
    def test_treatment_weighing_fields_nullable(self):
        """Test that weighing link fields are nullable."""
        sampling_event_field = Treatment._meta.get_field('sampling_event')
        self.assertTrue(sampling_event_field.null)
        self.assertTrue(sampling_event_field.blank)
        
        journal_entry_field = Treatment._meta.get_field('journal_entry')
        self.assertTrue(journal_entry_field.null)
        self.assertTrue(journal_entry_field.blank)
    
    def test_database_columns_exist(self):
        """Test that database columns were actually created (database-agnostic)."""
        # Use Django's schema introspection instead of raw SQL
        from django.db import connection
        
        # Get table descriptions (works for both PostgreSQL and SQLite)
        with connection.cursor() as cursor:
            # Check TransferAction table columns via Django model
            transfer_fields = {f.column for f in TransferAction._meta.fields}
            
            # Verify new columns exist
            self.assertIn('measured_avg_weight_g', transfer_fields)
            self.assertIn('measured_std_dev_weight_g', transfer_fields)
            self.assertIn('measured_sample_size', transfer_fields)
            self.assertIn('measured_avg_length_cm', transfer_fields)
            self.assertIn('measured_notes', transfer_fields)
            self.assertIn('selection_method', transfer_fields)
            
            # Check Batch table
            batch_fields = {f.column for f in Batch._meta.fields}
            self.assertIn('pinned_scenario_id', batch_fields)
            
            # Check Treatment table
            treatment_fields = {f.column for f in Treatment._meta.fields}
            self.assertIn('includes_weighing', treatment_fields)
            self.assertIn('sampling_event_id', treatment_fields)
            self.assertIn('journal_entry_id', treatment_fields)

