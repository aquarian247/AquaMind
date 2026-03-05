"""RBAC helpers for batch transfer operations."""

from apps.users.models import Role, Subsidiary


def can_execute_transport_actions(user) -> bool:
    """
    Return True when user can execute vessel/dynamic transport actions.

    Allowed:
    - superusers
    - role=ADMIN
    - role=SHIP_CREW
    - role=OPR with subsidiary=LG
    """
    if not user or not getattr(user, "is_authenticated", False):
        return False
    if getattr(user, "is_superuser", False):
        return True

    profile = getattr(user, "profile", None)
    if not profile:
        return False

    if profile.role == Role.ADMIN:
        return True
    if profile.role == Role.SHIP_CREW:
        return True
    return profile.role == Role.OPERATOR and profile.subsidiary == Subsidiary.LOGISTICS


def can_override_transport_compliance(user) -> bool:
    """
    Privileged compliance override gate for missing AVEVA mappings.

    Deliberately stricter than normal execution permissions.
    """
    if not user or not getattr(user, "is_authenticated", False):
        return False
    if getattr(user, "is_superuser", False):
        return True

    profile = getattr(user, "profile", None)
    if not profile:
        return False

    if profile.role == Role.ADMIN:
        return True
    return profile.role == Role.OPERATOR and profile.subsidiary == Subsidiary.LOGISTICS
