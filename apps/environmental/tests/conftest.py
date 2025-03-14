"""
Test configuration for the environmental app.
This file helps manage test execution by skipping TimescaleDB-specific tests.
"""
import unittest
from django.test import TestCase

# Create a decorator for marking tests that depend on TimescaleDB
timescaledb_test = unittest.skip("TimescaleDB tests are skipped for automated testing - will be tested manually")
