"""
RBAC Filter Mixins for Django REST Framework

This module provides reusable mixins for applying Role-Based Access Control (RBAC)
filtering to DRF viewsets. These mixins ensure that users only see data relevant to
their geography, subsidiary, and role assignments.

Usage:
    class MyViewSet(RBACFilterMixin, viewsets.ModelViewSet):
        # Define how to filter by geography and subsidiary
        geography_filter_field = 'container__area__geography'
        subsidiary_filter_field = 'lifecycle_stage__name'
        
        # The mixin will automatically filter queryset based on user profile
"""

from django.db.models import Q
from rest_framework.exceptions import PermissionDenied

from apps.users.models import Geography, Subsidiary, Role


class RBACFilterMixin:
    """
    Mixin to apply RBAC filtering based on user's geography and subsidiary.
    
    This mixin provides automatic queryset filtering to ensure users only access
    data within their authorized geography and subsidiary scope. It also provides
    object-level validation for create/update operations.
    
    Attributes:
        geography_filter_field: ORM path to geography field (e.g., 'area__geography')
        subsidiary_filter_field: ORM path to subsidiary field (optional)
        enable_operator_location_filtering: Enable fine-grained operator location filtering
    """
    
    geography_filter_field = None
    subsidiary_filter_field = None
    enable_operator_location_filtering = False
    
    def get_queryset(self):
        """
        Override get_queryset to apply RBAC filters.
        
        Returns:
            QuerySet filtered by user's geography and subsidiary permissions
        """
        queryset = super().get_queryset()
        return self.apply_rbac_filters(queryset)
    
    def apply_rbac_filters(self, queryset):
        """
        Apply geography and subsidiary filters based on user profile.
        
        Args:
            queryset: Base queryset to filter
            
        Returns:
            Filtered queryset based on user's RBAC permissions
        """
        user = self.request.user
        
        # Superusers see everything
        if user.is_superuser:
            return queryset
        
        profile = getattr(user, 'profile', None)
        if not profile:
            # No profile = no access
            return queryset.none()
        
        # Apply geography filter
        if profile.geography != Geography.ALL and self.geography_filter_field:
            geography_filter = {
                f'{self.geography_filter_field}': profile.geography
            }
            queryset = queryset.filter(**geography_filter)
        
        # Apply subsidiary filter
        if profile.subsidiary != Subsidiary.ALL and self.subsidiary_filter_field:
            subsidiary_filter = {
                f'{self.subsidiary_filter_field}': profile.subsidiary
            }
            queryset = queryset.filter(**subsidiary_filter)
        
        # Apply operator location filtering if enabled
        if self.enable_operator_location_filtering and profile.role == Role.OPERATOR:
            queryset = self.apply_operator_location_filters(queryset, profile)
        
        return queryset
    
    def apply_operator_location_filters(self, queryset, profile):
        """
        Apply fine-grained location filtering for operators.
        
        Operators should only see data for their assigned areas, stations, or containers.
        Filters data based on M2M relationships: allowed_areas, allowed_stations, allowed_containers.
        
        Args:
            queryset: Base queryset to filter
            profile: UserProfile instance
            
        Returns:
            Filtered queryset for operator's assigned locations
        """
        # If no locations are assigned, operator sees nothing
        # (Managers and Admins bypass this through role check above)
        
        area_ids = list(profile.allowed_areas.values_list('id', flat=True))
        station_ids = list(profile.allowed_stations.values_list('id', flat=True))
        container_ids = list(profile.allowed_containers.values_list('id', flat=True))
        
        # If no assignments at all, return empty queryset
        if not area_ids and not station_ids and not container_ids:
            return queryset.none()
        
        # Build filter conditions based on the model's location relationships
        # This assumes the queryset model has relationships to containers, areas, or stations
        # Subclasses can override this method for custom location filtering logic
        
        filters = Q()
        
        # Filter by assigned areas
        if area_ids:
            # Common patterns:
            # - container__area_id__in (for models with direct container FK)
            # - batch__batchcontainerassignment__container__area_id__in (for batch-related)
            # - area_id__in (for models with direct area FK)
            
            if hasattr(queryset.model, 'container'):
                filters |= Q(container__area_id__in=area_ids)
            elif hasattr(queryset.model, 'area'):
                filters |= Q(area_id__in=area_ids)
            
            # Try batch relationships
            if hasattr(queryset.model, 'batch'):
                filters |= Q(batch__batchcontainerassignment__container__area_id__in=area_ids)
        
        # Filter by assigned stations
        if station_ids:
            if hasattr(queryset.model, 'container'):
                filters |= Q(container__hall__freshwater_station_id__in=station_ids)
            elif hasattr(queryset.model, 'hall'):
                filters |= Q(hall__freshwater_station_id__in=station_ids)
            elif hasattr(queryset.model, 'freshwater_station'):
                filters |= Q(freshwater_station_id__in=station_ids)
            
            # Try batch relationships
            if hasattr(queryset.model, 'batch'):
                filters |= Q(batch__batchcontainerassignment__container__hall__freshwater_station_id__in=station_ids)
        
        # Filter by assigned containers (most specific)
        if container_ids:
            if hasattr(queryset.model, 'container'):
                filters |= Q(container_id__in=container_ids)
            
            # Try batch relationships
            if hasattr(queryset.model, 'batch'):
                filters |= Q(batch__batchcontainerassignment__container_id__in=container_ids)
        
        # Apply the filters if any were built
        if filters:
            queryset = queryset.filter(filters).distinct()
        else:
            # No matching relationships found, return empty
            return queryset.none()
        
        return queryset
    
    def validate_object_geography(self, obj):
        """
        Validate that an object belongs to the user's geography.
        
        This should be called in perform_create and perform_update to prevent
        users from creating/updating objects in other geographies.
        
        Args:
            obj: Model instance to validate
            
        Raises:
            PermissionDenied: If object is outside user's geography scope
        """
        user = self.request.user
        
        # Superusers can access anything
        if user.is_superuser:
            return
        
        profile = getattr(user, 'profile', None)
        if not profile:
            raise PermissionDenied("User profile not found")
        
        # Skip check if user has ALL geography access
        if profile.geography == Geography.ALL:
            return
        
        # Get the geography from the object using the filter field
        if not self.geography_filter_field:
            # No geography filtering defined, skip validation
            return
        
        # Navigate through the field path to get the geography value
        obj_geography = self._get_nested_field_value(obj, self.geography_filter_field)
        
        if obj_geography != profile.geography:
            raise PermissionDenied(
                f"You do not have permission to access data in geography: {obj_geography}"
            )
    
    def validate_object_subsidiary(self, obj):
        """
        Validate that an object belongs to the user's subsidiary.
        
        Args:
            obj: Model instance to validate
            
        Raises:
            PermissionDenied: If object is outside user's subsidiary scope
        """
        user = self.request.user
        
        # Superusers can access anything
        if user.is_superuser:
            return
        
        profile = getattr(user, 'profile', None)
        if not profile:
            raise PermissionDenied("User profile not found")
        
        # Skip check if user has ALL subsidiary access
        if profile.subsidiary == Subsidiary.ALL:
            return
        
        if not self.subsidiary_filter_field:
            return
        
        obj_subsidiary = self._get_nested_field_value(obj, self.subsidiary_filter_field)
        
        if obj_subsidiary != profile.subsidiary:
            raise PermissionDenied(
                f"You do not have permission to access data in subsidiary: {obj_subsidiary}"
            )
    
    def _get_nested_field_value(self, obj, field_path):
        """
        Navigate through nested field path to get final value.
        
        Args:
            obj: Starting model instance
            field_path: Dot-separated field path (e.g., 'area__geography')
            
        Returns:
            Final field value or None if path is invalid
        """
        parts = field_path.split('__')
        value = obj
        
        for part in parts:
            if value is None:
                return None
            value = getattr(value, part, None)
        
        return value
    
    def perform_create(self, serializer):
        """
        Override perform_create to validate object-level permissions.
        
        Ensures that created objects belong to user's authorized geography/subsidiary.
        """
        # Save the instance first
        instance = serializer.save()
        
        # Validate geography and subsidiary
        try:
            self.validate_object_geography(instance)
            self.validate_object_subsidiary(instance)
        except PermissionDenied:
            # If validation fails, delete the instance and re-raise
            instance.delete()
            raise
        
        return instance
    
    def perform_update(self, serializer):
        """
        Override perform_update to validate object-level permissions.
        
        Ensures that updated objects remain within user's authorized scope.
        """
        # Save the instance first
        instance = serializer.save()
        
        # Validate geography and subsidiary
        self.validate_object_geography(instance)
        self.validate_object_subsidiary(instance)
        
        return instance


class GeographicFilterMixin(RBACFilterMixin):
    """
    Simplified mixin for geographic filtering only.
    
    Use this when you only need geography-based filtering without
    subsidiary or location restrictions.
    """
    
    def apply_rbac_filters(self, queryset):
        """Apply only geographic filtering."""
        user = self.request.user
        
        if user.is_superuser:
            return queryset
        
        profile = getattr(user, 'profile', None)
        if not profile:
            return queryset.none()
        
        if profile.geography != Geography.ALL and self.geography_filter_field:
            geography_filter = {
                f'{self.geography_filter_field}': profile.geography
            }
            queryset = queryset.filter(**geography_filter)
        
        return queryset
