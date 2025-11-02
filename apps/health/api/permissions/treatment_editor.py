"""Permission class for treatment and vaccination editing (Veterinarians and Admin only)."""

from rest_framework import permissions

from apps.users.models import Role


class IsTreatmentEditor(permissions.BasePermission):
    """
    Permission class for treatment and vaccination editing.
    
    Restricts treatment and vaccination modifications to Veterinarians and
    Administrators only. QA personnel have read-only access.
    
    Access Control:
    - Veterinarians: Full read/write access to treatments
    - Admins: Full read/write access to treatments
    - QA Personnel: Read-only access to treatments
    - Other roles: No access
    
    This separation ensures that only qualified veterinary professionals can
    prescribe and record treatments, while QA can review treatment records.
    """
    
    message = "Only Veterinarians and Administrators may modify treatment records."
    
    def has_permission(self, request, view):
        """
        Check if user has permission to access treatment data.
        
        Args:
            request: HTTP request object
            view: ViewSet being accessed
            
        Returns:
            bool: True if user has appropriate access level
        """
        user = request.user
        
        # Must be authenticated
        if not user or not user.is_authenticated:
            return False
        
        # Superusers always have access
        if user.is_superuser:
            return True
        
        # Check user profile and role
        profile = getattr(user, 'profile', None)
        if not profile:
            return False
        
        # For read-only operations (GET, HEAD, OPTIONS)
        if request.method in permissions.SAFE_METHODS:
            # VET, QA, and ADMIN can read treatments
            return profile.role in {Role.ADMIN, Role.VETERINARIAN, Role.QA}
        
        # For write operations (POST, PUT, PATCH, DELETE)
        # Only VET and ADMIN can modify treatments
        return profile.role in {Role.ADMIN, Role.VETERINARIAN}
    
    def has_object_permission(self, request, view, obj):
        """
        Check object-level permissions for treatments.
        
        Args:
            request: HTTP request object
            view: ViewSet being accessed
            obj: Treatment instance being accessed
            
        Returns:
            bool: True if user has access to this treatment
        """
        # Use the same logic as has_permission
        return self.has_permission(request, view)
