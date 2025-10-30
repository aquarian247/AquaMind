"""
Tests for ParameterScoreDefinition API serializers and viewsets.

This module tests the normalized parameter scoring system with flexible score ranges.
"""

from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from rest_framework.test import APITestCase

from apps.health.models import HealthParameter, ParameterScoreDefinition
from apps.health.api.serializers import ParameterScoreDefinitionSerializer

User = get_user_model()


class ParameterScoreDefinitionSerializerTestCase(TestCase):
    """Test cases for the ParameterScoreDefinitionSerializer."""

    @classmethod
    def setUpTestData(cls):
        # Create a parameter with 0-3 range (unique name to avoid conflict with migration data)
        cls.parameter = HealthParameter.objects.create(
            name='Test Gill Condition Serializer',
            description='Assessment of gill health',
            min_score=0,
            max_score=3,
            is_active=True
        )
        
        # Create sample score definitions
        cls.score_def_0 = ParameterScoreDefinition.objects.create(
            parameter=cls.parameter,
            score_value=0,
            label='Excellent',
            description='Healthy gills, pink color',
            display_order=0
        )
        cls.score_def_1 = ParameterScoreDefinition.objects.create(
            parameter=cls.parameter,
            score_value=1,
            label='Good',
            description='Slight mucus buildup',
            display_order=1
        )

    def test_serialize_score_definition(self):
        """Test serialization of a score definition."""
        serializer = ParameterScoreDefinitionSerializer(instance=self.score_def_0)
        data = serializer.data
        
        self.assertEqual(data['parameter'], self.parameter.id)
        self.assertEqual(data['score_value'], 0)
        self.assertEqual(data['label'], 'Excellent')
        self.assertEqual(data['description'], 'Healthy gills, pink color')
        self.assertEqual(data['display_order'], 0)

    def test_create_score_definition(self):
        """Test creating a new score definition."""
        data = {
            'parameter': self.parameter.id,
            'score_value': 2,
            'label': 'Fair',
            'description': 'Moderate inflammation',
            'display_order': 2
        }
        serializer = ParameterScoreDefinitionSerializer(data=data)
        self.assertTrue(serializer.is_valid(), msg=serializer.errors)
        score_def = serializer.save()
        
        self.assertEqual(score_def.parameter, self.parameter)
        self.assertEqual(score_def.score_value, 2)
        self.assertEqual(score_def.label, 'Fair')

    def test_unique_constraint(self):
        """Test that duplicate parameter+score_value combinations are rejected."""
        # Try to create a duplicate score_value for the same parameter
        data = {
            'parameter': self.parameter.id,
            'score_value': 0,  # Already exists
            'label': 'Duplicate',
            'description': 'This should fail',
            'display_order': 0
        }
        serializer = ParameterScoreDefinitionSerializer(data=data)
        
        # Serializer should catch the unique_together constraint
        self.assertFalse(serializer.is_valid())
        self.assertIn('non_field_errors', serializer.errors)
        self.assertIn('must make a unique set', str(serializer.errors['non_field_errors']))

    def test_update_score_definition(self):
        """Test updating an existing score definition."""
        new_data = {
            'parameter': self.parameter.id,
            'score_value': 1,
            'label': 'Very Good',  # Updated label
            'description': 'Minimal mucus buildup',  # Updated description
            'display_order': 1
        }
        serializer = ParameterScoreDefinitionSerializer(
            instance=self.score_def_1,
            data=new_data
        )
        self.assertTrue(serializer.is_valid(), msg=serializer.errors)
        updated = serializer.save()
        
        self.assertEqual(updated.label, 'Very Good')
        self.assertEqual(updated.description, 'Minimal mucus buildup')


class ParameterScoreDefinitionModelTestCase(TestCase):
    """Test cases for ParameterScoreDefinition model validation."""

    @classmethod
    def setUpTestData(cls):
        cls.parameter = HealthParameter.objects.create(
            name='Test Eye Condition Model',
            description='Assessment of eye clarity',
            min_score=0,
            max_score=3
        )

    def test_score_within_range(self):
        """Test that scores within parameter range are valid."""
        # Score 0 (min)
        score_def = ParameterScoreDefinition(
            parameter=self.parameter,
            score_value=0,
            label='Excellent',
            description='Clear eyes'
        )
        score_def.full_clean()  # Should not raise
        score_def.save()
        
        # Score 3 (max)
        score_def2 = ParameterScoreDefinition(
            parameter=self.parameter,
            score_value=3,
            label='Poor',
            description='Severe cloudiness'
        )
        score_def2.full_clean()  # Should not raise
        score_def2.save()

    def test_score_below_range(self):
        """Test that scores below parameter min_score are rejected."""
        score_def = ParameterScoreDefinition(
            parameter=self.parameter,
            score_value=-1,  # Below min_score=0
            label='Invalid',
            description='Should fail'
        )
        
        with self.assertRaises(ValidationError) as context:
            score_def.full_clean()
        
        self.assertIn('Score value must be between', str(context.exception))

    def test_score_above_range(self):
        """Test that scores above parameter max_score are rejected."""
        score_def = ParameterScoreDefinition(
            parameter=self.parameter,
            score_value=4,  # Above max_score=3
            label='Invalid',
            description='Should fail'
        )
        
        with self.assertRaises(ValidationError) as context:
            score_def.full_clean()
        
        self.assertIn('Score value must be between', str(context.exception))

    def test_different_score_ranges(self):
        """Test parameters with different score ranges."""
        # Create parameter with 1-5 range
        param_1_5 = HealthParameter.objects.create(
            name='Custom Parameter',
            description='Uses 1-5 scale',
            min_score=1,
            max_score=5
        )
        
        # Score 1 should be valid
        score_def = ParameterScoreDefinition(
            parameter=param_1_5,
            score_value=1,
            label='Best',
            description='Excellent condition'
        )
        score_def.full_clean()  # Should not raise
        score_def.save()
        
        # Score 0 should be invalid (below min)
        score_def_invalid = ParameterScoreDefinition(
            parameter=param_1_5,
            score_value=0,
            label='Invalid',
            description='Should fail'
        )
        
        with self.assertRaises(ValidationError):
            score_def_invalid.full_clean()


class HealthParameterModelTestCase(TestCase):
    """Test cases for HealthParameter model validation."""

    def test_min_score_less_than_max_score(self):
        """Test that min_score must be less than max_score."""
        param = HealthParameter(
            name='Invalid Parameter',
            description='Test',
            min_score=5,  # Invalid: min >= max
            max_score=3
        )
        
        with self.assertRaises(ValidationError) as context:
            param.full_clean()
        
        self.assertIn('min_score must be less than max_score', str(context.exception))

    def test_valid_score_ranges(self):
        """Test various valid score ranges."""
        # 0-3 range
        param1 = HealthParameter(
            name='Standard 0-3',
            min_score=0,
            max_score=3
        )
        param1.full_clean()  # Should not raise
        param1.save()
        
        # 1-5 range
        param2 = HealthParameter(
            name='Classic 1-5',
            min_score=1,
            max_score=5
        )
        param2.full_clean()  # Should not raise
        param2.save()
        
        # 0-10 range
        param3 = HealthParameter(
            name='Extended 0-10',
            min_score=0,
            max_score=10
        )
        param3.full_clean()  # Should not raise
        param3.save()

