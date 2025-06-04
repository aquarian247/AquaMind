"""
API test imports for the environmental app.
This ensures that all API tests are properly discovered.
"""

from apps.environmental.tests.api.test_parameter_api import *
from apps.environmental.tests.api.test_reading_api import *
from apps.environmental.tests.api.test_stage_transition_api import *
from apps.environmental.tests.api.test_weather_api import *
