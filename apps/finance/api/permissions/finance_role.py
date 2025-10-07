"""Permission ensuring finance read-only access."""

from rest_framework import permissions

from apps.users.models import Role


class IsFinanceUser(permissions.BasePermission):
    """Allows finance users and admins to access finance data."""

    message = "You do not have access to finance data."

    def has_permission(self, request, view):  # pylint: disable=unused-argument
        user = request.user
        if not user or not user.is_authenticated:
            return False

        if user.is_superuser:
            return True

        profile = getattr(user, "profile", None)
        if not profile:
            return False

        return profile.role in {Role.ADMIN, Role.FINANCE}
