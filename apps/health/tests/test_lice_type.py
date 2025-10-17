"""
Tests for the LiceType model.

This module contains unit tests for the LiceType model, including
validation, uniqueness constraints, and string representations.
"""

from django.test import TestCase
from django.core.exceptions import ValidationError

from apps.health.models import LiceType


class LiceTypeModelTest(TestCase):
    """Test cases for the LiceType model."""

    def setUp(self):
        """Set up test data."""
        # Use unique combination not in migration
        self.lice_type_data = {
            'species': 'Test species',
            'gender': 'female',
            'development_stage': 'test_stage',
            'description': 'Test lice type',
        }

    def test_create_lice_type(self):
        """Test creating a lice type."""
        lice_type = LiceType.objects.create(**self.lice_type_data)

        self.assertEqual(lice_type.species, 'Test species')
        self.assertEqual(lice_type.gender, 'female')
        self.assertEqual(lice_type.development_stage, 'test_stage')
        self.assertTrue(lice_type.is_active)

    def test_unique_together_constraint(self):
        """Test unique_together constraint on species/gender/stage."""
        LiceType.objects.create(**self.lice_type_data)

        # Attempt to create duplicate
        with self.assertRaises(Exception):
            LiceType.objects.create(**self.lice_type_data)

    def test_string_representation(self):
        """Test the __str__ method."""
        lice_type = LiceType.objects.create(**self.lice_type_data)
        expected = "T. species - Female - Test_stage"
        self.assertEqual(str(lice_type), expected)

    def test_string_representation_single_word_species(self):
        """Test __str__ with single-word species name."""
        lice_type = LiceType.objects.create(
            species='Testicus',
            gender='unknown',
            development_stage='test_juv2'
        )
        expected = "Testicus - Unknown - Test_juv2"
        self.assertEqual(str(lice_type), expected)

    def test_clean_validates_species(self):
        """Test that clean() validates species is not empty."""
        lice_type = LiceType(
            species='  ',  # Empty/whitespace only
            gender='female',
            development_stage='test_dev_stage'
        )
        with self.assertRaises(ValidationError) as cm:
            lice_type.full_clean()
        self.assertIn('species', cm.exception.message_dict)

    def test_clean_validates_development_stage(self):
        """Test validation for empty development_stage."""
        lice_type = LiceType(
            species='Test unique species 2',
            gender='female',
            development_stage='  '  # Empty/whitespace only
        )
        with self.assertRaises(ValidationError) as cm:
            lice_type.full_clean()
        self.assertIn('development_stage', cm.exception.message_dict)

    def test_is_active_default(self):
        """Test that is_active defaults to True."""
        lice_type = LiceType.objects.create(
            species='Test species 2',
            gender='male',
            development_stage='test_stage_2'
        )
        self.assertTrue(lice_type.is_active)

    def test_description_optional(self):
        """Test that description is optional."""
        lice_type = LiceType.objects.create(
            species='Test species 3',
            gender='male',
            development_stage='test_juvenile'
            # No description provided
        )
        self.assertEqual(lice_type.description, '')

    def test_ordering(self):
        """Test that lice types are ordered correctly."""
        LiceType.objects.create(
            species='Species B',
            gender='male',
            development_stage='stage1'
        )
        LiceType.objects.create(
            species='Species A',
            gender='female',
            development_stage='stage2'
        )
        LiceType.objects.create(
            species='Species A',
            gender='female',
            development_stage='stage1'
        )

        types = list(
            LiceType.objects.filter(
                species__startswith='Species '
            )
        )

        # Should be ordered by species, then dev stage, then gender
        self.assertEqual(types[0].species, 'Species A')
        self.assertEqual(types[1].species, 'Species A')
        self.assertEqual(types[2].species, 'Species B')

