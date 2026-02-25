"""Permission classes for batch API endpoints."""

from rest_framework.permissions import BasePermission

from apps.batch.access import can_execute_transport_actions


class IsShipCrewOrAdmin(BasePermission):
    """Allow only ship crew logistics operators/admins for transport execution."""

    message = (
        "You do not have permission to execute transport actions. "
        "Required role: SHIP_CREW or OPR with Logistics subsidiary."
    )

    def has_permission(self, request, view):
        return can_execute_transport_actions(request.user)
