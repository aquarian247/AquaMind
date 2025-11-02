"""General RBAC permission classes used across multiple apps."""

from rest_framework import permissions

from apps.users.models import Role


class IsOperator(permissions.BasePermission):
    """
    Permission class for operational data access.
    
    Allows Operators, Managers, and Admins to access operational data such as
    batches, feeding events, and container assignments. This permission is used
    in conjunction with geographic/subsidiary filtering to ensure operators only
    see data within their scope.
    
    Access Control:
    - Operators: Access to operational data within their geography/subsidiary/locations
    - Managers: Broader operational access within their geography/subsidiary
    - Admins: Full operational access
    - Other roles: No operational access (they may have other specialized access)
    """
    
    message = "Operational data access is restricted to Operators, Managers, and Administrators."
    
    def has_permission(self, request, view):
        """
        Check if user has permission to access operational data.
        
        Args:
            request: HTTP request object
            view: ViewSet being accessed
            
        Returns:
            bool: True if user has OPERATOR, MANAGER, or ADMIN role
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
        
        # Allow OPERATOR, MANAGER, and ADMIN roles
        return profile.role in {Role.ADMIN, Role.MANAGER, Role.OPERATOR}
    
    def has_object_permission(self, request, view, obj):
        """
        Check object-level permissions for operational data.
        
        Args:
            request: HTTP request object
            view: ViewSet being accessed
            obj: Model instance being accessed
            
        Returns:
            bool: True if user has access to this object
        """
        # Basic permission check first
        if not self.has_permission(request, view):
            return False
        
        # Superusers can access any object
        if request.user.is_superuser:
            return True
        
        # Object-level geographic filtering handled by RBACFilterMixin
        return True


class IsManager(permissions.BasePermission):
    """
    Permission class for management-level access.
    
    Restricts access to management functions to Managers and Admins only.
    """
    
    message = "This action is restricted to Managers and Administrators."
    
    def has_permission(self, request, view):
        """Check if user has manager-level access."""
        user = request.user
        
        if not user or not user.is_authenticated:
            return False
        
        if user.is_superuser:
            return True
        
        profile = getattr(user, 'profile', None)
        if not profile:
            return False
        
        return profile.role in {Role.ADMIN, Role.MANAGER}


class IsReadOnly(permissions.BasePermission):
    """
    Permission class that allows only read-only operations.
    
    Useful for roles that need to view data but not modify it.
    """
    
    message = "You have read-only access to this resource."
    
    def has_permission(self, request, view):
        """Allow only safe methods (GET, HEAD, OPTIONS)."""
        return request.method in permissions.SAFE_METHODS
