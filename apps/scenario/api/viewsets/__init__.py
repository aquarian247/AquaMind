"""
Scenario API viewsets package.

This package contains viewsets for the scenario app, organized into separate modules.
"""

# Import all viewsets from the main viewsets.py file
from apps.scenario.api.viewsets import *

# Import history viewsets
from .history import *
