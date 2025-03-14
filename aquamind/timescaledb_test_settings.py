"""
TimescaleDB test settings for AquaMind project.

This module contains Django settings specifically for manual testing of TimescaleDB features.
It inherits from the main settings and maintains the PostgreSQL/TimescaleDB database.
This configuration is for manual testing only and should not be used for automated CI/CD.
"""

from .settings import *  # noqa

# Explicitly enable TimescaleDB for testing
USE_TIMESCALEDB = True

# Use our custom test runner that handles TimescaleDB setup properly
TEST_RUNNER = 'apps.core.test_runner.TimescaleDBTestRunner'
