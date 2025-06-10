# This file makes the services directory a Python package.

"""
Services package for the inventory app.

This package contains business logic services for inventory management.
"""

from .fifo_service import FIFOInventoryService
from .fcr_service import FCRCalculationService

__all__ = [
    'FIFOInventoryService',
    'FCRCalculationService',
]
