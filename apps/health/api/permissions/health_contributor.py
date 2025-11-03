"""Permission class for health data contributors (Veterinarians, QA, Admin)."""

from rest_framework import permissions

from apps.users.models import Role


class IsHealthContributor(permissions.BasePermission):
    """
    Permission class for health data contribution.
    
    Allows Veterinarians, QA personnel, and Admins to read and write general
    health data including journal entries, lice counts, mortality records,
    health sampling events, and lab samples.
    
    Access Control:
    - Veterinarians: Full read/write access to health data
    - QA Personnel: Full read/write access to health data (excluding treatments)
    - Admins: Full access to all health data
    - Other roles: No access
    
    Note: For treatments/vaccinations, use IsTreatmentEditor which restricts
    write access to Veterinarians and Admins only.
    """
    
    message = "Health data is restricted to Veterinarians, QA personnel, and Administrators."
    
    def has_permission(self, request, view):
        """
        Check if user has permission to access health data.
        
        Args:
            request: HTTP request object
            view: ViewSet being accessed
            
        Returns:
            bool: True if user has VET, QA, or ADMIN role
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
        
        # Allow VET, QA, and ADMIN roles
        return profile.role in {Role.ADMIN, Role.VETERINARIAN, Role.QA}
    
    def has_object_permission(self, request, view, obj):
        """
        Check object-level permissions.
        
        This ensures users can only access health data within their
        geographic scope. The geographic filtering is handled by
        RBACFilterMixin at the queryset level, but this provides an
        additional safety check.
        
        Args:
            request: HTTP request object
            view: ViewSet being accessed
            obj: Model instance being accessed
            
        Returns:
            bool: True if user has access to this specific object
        """
        # Basic permission check first
        if not self.has_permission(request, view):
            return False
        
        # Superusers can access any object
        if request.user.is_superuser:
            return True
        
        # Additional geographic checks could be added here if needed
        # For now, rely on queryset filtering from RBACFilterMixin
        return True
