"""
Test imports for the environmental app.
This ensures that all tests are properly discovered.
"""

from apps.environmental.tests.api import *
from apps.environmental.tests.models import *
from apps.environmental.tests.test_timescaledb import *
from apps.environmental.tests.test_timescaledb_features import *