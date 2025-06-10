"""
Custom exceptions for AquaMind.
"""


class InsufficientStockError(Exception):
    """Raised when there is insufficient feed stock for an operation."""
    pass


class FIFOCalculationError(Exception):
    """Raised when FIFO cost calculation fails."""
    pass


class FCRCalculationError(Exception):
    """Raised when FCR calculation fails."""
    pass 