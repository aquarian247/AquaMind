"""Health-related permission classes for RBAC enforcement."""

from .health_contributor import IsHealthContributor
from .treatment_editor import IsTreatmentEditor

__all__ = ['IsHealthContributor', 'IsTreatmentEditor']
