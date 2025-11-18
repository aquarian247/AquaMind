"""
Simplified tests for Phase 2 - ActualDailyAssignmentState schema - Issue #112.

Tests model structure without complex test fixtures.
"""
from django.test import TestCase

from apps.batch.models import ActualDailyAssignmentState


class ActualDailyAssignmentStateSchemaTestCase(TestCase):
    """Test that ActualDailyAssignmentState model has correct schema."""
    
    def test_model_exists(self):
        """Test that ActualDailyAssignmentState model exists."""
        self.assertEqual(ActualDailyAssignmentState._meta.db_table, 'batch_actualdailyassignmentstate')
    
    def test_model_has_required_fields(self):
        """Test that model has all required fields."""
        field_names = [f.name for f in ActualDailyAssignmentState._meta.fields]
        
        # Core relationships
        self.assertIn('assignment', field_names)
        self.assertIn('batch', field_names)
        self.assertIn('container', field_names)
        self.assertIn('lifecycle_stage', field_names)
        
        # Time dimension
        self.assertIn('date', field_names)
        self.assertIn('day_number', field_names)
        
        # Computed metrics
        self.assertIn('avg_weight_g', field_names)
        self.assertIn('population', field_names)
        self.assertIn('biomass_kg', field_names)
        
        # Environmental/operational
        self.assertIn('temp_c', field_names)
        self.assertIn('mortality_count', field_names)
        self.assertIn('feed_kg', field_names)
        self.assertIn('observed_fcr', field_names)
        
        # Provenance
        self.assertIn('anchor_type', field_names)
        self.assertIn('sources', field_names)
        self.assertIn('confidence_scores', field_names)
        
        # Metadata
        self.assertIn('last_computed_at', field_names)
    
    def test_anchor_type_choices(self):
        """Test that anchor_type has correct choices."""
        field = ActualDailyAssignmentState._meta.get_field('anchor_type')
        choices_values = [choice[0] for choice in field.choices]
        
        self.assertIn('growth_sample', choices_values)
        self.assertIn('transfer', choices_values)
        self.assertIn('vaccination', choices_values)
        self.assertIn('manual', choices_values)
    
    def test_json_fields(self):
        """Test that JSON fields are configured."""
        sources_field = ActualDailyAssignmentState._meta.get_field('sources')
        self.assertEqual(sources_field.get_internal_type(), 'JSONField')
        self.assertEqual(sources_field.default, dict)
        
        confidence_field = ActualDailyAssignmentState._meta.get_field('confidence_scores')
        self.assertEqual(confidence_field.get_internal_type(), 'JSONField')
        self.assertEqual(confidence_field.default, dict)
    
    def test_nullable_fields(self):
        """Test that appropriate fields are nullable."""
        temp_field = ActualDailyAssignmentState._meta.get_field('temp_c')
        self.assertTrue(temp_field.null)
        
        fcr_field = ActualDailyAssignmentState._meta.get_field('observed_fcr')
        self.assertTrue(fcr_field.null)
        
        anchor_type_field = ActualDailyAssignmentState._meta.get_field('anchor_type')
        self.assertTrue(anchor_type_field.null)
    
    def test_unique_constraint(self):
        """Test that unique constraint exists on (assignment, date)."""
        constraints = ActualDailyAssignmentState._meta.constraints
        
        # Find the unique constraint
        unique_constraints = [c for c in constraints if hasattr(c, 'fields')]
        self.assertTrue(len(unique_constraints) > 0, "No unique constraints found")
        
        # Check that it includes assignment and date
        found = False
        for constraint in unique_constraints:
            if hasattr(constraint, 'fields') and set(constraint.fields) == {'assignment', 'date'}:
                found = True
                break
        
        self.assertTrue(found, "Unique constraint on (assignment, date) not found")
    
    def test_indexes_defined(self):
        """Test that indexes are defined in model Meta."""
        indexes = ActualDailyAssignmentState._meta.indexes
        self.assertGreaterEqual(len(indexes), 4, "Expected at least 4 indexes")
        
        # Check that we have indexes on key fields
        index_fields = []
        for idx in indexes:
            index_fields.extend(idx.fields)
        
        # Should have indexes involving these fields
        self.assertIn('date', index_fields)
    
    def test_database_table_exists(self):
        """Test that database table was created."""
        from django.db import connection
        
        with connection.cursor() as cursor:
            if connection.vendor == 'postgresql':
                cursor.execute("""
                    SELECT table_name FROM information_schema.tables 
                    WHERE table_name = 'batch_actualdailyassignmentstate' 
                    AND table_schema = 'public';
                """)
            else:  # SQLite
                cursor.execute("""
                    SELECT name FROM sqlite_master 
                    WHERE type='table' AND name='batch_actualdailyassignmentstate';
                """)
            
            result = cursor.fetchone()
            self.assertIsNotNone(result, "Table batch_actualdailyassignmentstate not found in database")



