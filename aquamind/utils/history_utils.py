"""
History API Utilities for AquaMind

This module provides reusable classes for implementing history API endpoints
across all apps in the AquaMind project. These utilities ensure consistent
filtering, pagination, and serialization for historical data access.

Classes:
    - HistoryFilter: Base filter class for history endpoints
    - HistoryPagination: Pagination class optimized for history data
    - HistorySerializer: Base serializer for history records
    - HistoryViewSetMixin: Mixin for history viewsets
"""

from rest_framework import serializers
import django_filters as filters
from django_filters import rest_framework as rest_filters


class HistoryFilter(filters.FilterSet):
    """
    Base filter class for history endpoints.

    Provides common filters for all history viewsets:
    - date_from: Filter by history_date >= date_from
    - date_to: Filter by history_date <= date_to
    - history_user: Filter by history_user username
    - history_type: Filter by history_type (+, ~, -)

    Usage:
        class MyModelHistoryFilter(HistoryFilter):
            class Meta:
                model = MyModel.history.model
                fields = '__all__'
    """

    date_from = filters.DateTimeFilter(
        field_name='history_date',
        lookup_expr='gte',
        help_text="Filter records from this date onwards (inclusive)"
    )
    date_to = filters.DateTimeFilter(
        field_name='history_date',
        lookup_expr='lte',
        help_text="Filter records up to this date (inclusive)"
    )
    history_user = filters.CharFilter(
        field_name='history_user__username',
        lookup_expr='icontains',
        help_text="Filter by username of the user who made the change"
    )
    history_type = filters.ChoiceFilter(
        choices=[
            ('+', 'Created'),
            ('~', 'Updated'),
            ('-', 'Deleted')
        ],
        field_name='history_type',
        help_text="Filter by type of change: + (Created), ~ (Updated), - (Deleted)"
    )


class HistoryPagination:
    """
    Pagination class optimized for history data.

    Uses a default page size of 25 items, which is suitable for
    most history browsing use cases. Allows customization via
    query parameters.
    """

    page_size = 25
    page_size_query_param = 'page_size'
    max_page_size = 100

    def __init__(self):
        # Import here to avoid Django settings requirement at module level
        from rest_framework.pagination import PageNumberPagination
        self._pagination_class = PageNumberPagination
        self._pagination_class.page_size = self.page_size
        self._pagination_class.page_size_query_param = self.page_size_query_param
        self._pagination_class.max_page_size = self.max_page_size

    def __getattr__(self, name):
        return getattr(self._pagination_class, name)

    def __setattr__(self, name, value):
        if name.startswith('_'):
            super().__setattr__(name, value)
        else:
            setattr(self._pagination_class, name, value)


class HistorySerializer(serializers.ModelSerializer):
    """
    Base serializer for history records.

    Provides common fields that should be exposed for all history endpoints:
    - history_user: String representation of the user who made the change
    - history_date: When the change was made
    - history_type: Type of change (+, ~, -)
    - history_change_reason: Reason for the change (if provided)

    Usage:
        class MyModelHistorySerializer(HistorySerializer):
            class Meta:
                model = MyModel.history.model
                fields = '__all__'
    """

    # Explicitly define history fields for Spectacular compatibility
    history_user = serializers.StringRelatedField(read_only=True, help_text="User who made the change")
    history_date = serializers.DateTimeField(read_only=True, help_text="When the change was made")
    history_type = serializers.CharField(read_only=True, help_text="Type of change: + (Created), ~ (Updated), - (Deleted)")
    history_change_reason = serializers.CharField(read_only=True, required=False, help_text="Reason for the change")

    class Meta:
        fields = [
            'history_user',
            'history_date',
            'history_type',
            'history_change_reason'
        ]


class HistoryViewSetMixin:
    """
    Mixin for history viewsets.

    Provides common configuration for all history viewsets:
    - ReadOnlyModelViewSet base
    - HistoryPagination
    - Standard queryset ordering by history_date descending
    - OpenAPI documentation enhancements
    - Custom operation ID methods to resolve Spectacular collisions

    Usage:
        class MyModelHistoryViewSet(HistoryViewSetMixin, ReadOnlyModelViewSet):
            queryset = MyModel.history.all()
            serializer_class = MyModelHistorySerializer
            filterset_class = MyModelHistoryFilter
    """

    def get_queryset(self):
        """Order history records by date descending (most recent first)."""
        return super().get_queryset().order_by('-history_date')

    def list(self, request, *args, **kwargs):
        """List historical records with enhanced OpenAPI documentation."""
        return super().list(request, *args, **kwargs)

    def get_operation_id(self, request=None, action=None):
        """
        Generate unique operation IDs to resolve DRF Spectacular collisions.

        Returns unique operation IDs for list vs retrieve operations:
        - list{AppName}{ModelName}History for list operations
        - retrieve{AppName}{ModelName}History for retrieve operations
        """
        if action is None:
            # Get action from the current request
            action = getattr(self, 'action', None) or self.get_view_action()

        if action is None:
            return None

        # Get the viewset class name (e.g., 'BatchHistoryViewSet')
        viewset_name = self.__class__.__name__

        # Extract app and model names from viewset name
        # Remove 'HistoryViewSet' suffix and parse app/model
        if viewset_name.endswith('HistoryViewSet'):
            model_part = viewset_name[:-14]  # Remove 'HistoryViewSet'

            # Handle special cases for multi-word model names
            if 'ContainerAssignment' in model_part:
                app_name = 'Batch'
                model_name = 'ContainerAssignment'
            elif 'FeedContainer' in model_part:
                app_name = 'Infrastructure'
                model_name = 'FeedContainer'
            elif 'FreshwaterStation' in model_part:
                app_name = 'Infrastructure'
                model_name = 'FreshwaterStation'
            elif 'ContainerType' in model_part:
                app_name = 'Infrastructure'
                model_name = 'ContainerType'
            elif 'HealthLabSample' in model_part:
                app_name = 'Health'
                model_name = 'HealthLabSample'
            elif 'JournalEntry' in model_part:
                app_name = 'Health'
                model_name = 'JournalEntry'
            elif 'MortalityRecord' in model_part:
                app_name = 'Health'
                model_name = 'MortalityRecord'
            elif 'BatchParentage' in model_part:
                app_name = 'Broodstock'
                model_name = 'BatchParentage'
            elif 'FishMovement' in model_part:
                app_name = 'Broodstock'
                model_name = 'FishMovement'
            elif 'BreedingPair' in model_part:
                app_name = 'Broodstock'
                model_name = 'BreedingPair'
            elif 'EggProduction' in model_part:
                app_name = 'Broodstock'
                model_name = 'EggProduction'
            elif 'BroodstockFish' in model_part:
                app_name = 'Broodstock'
                model_name = 'BroodstockFish'
            elif 'FeedStock' in model_part:
                app_name = 'Inventory'
                model_name = 'FeedStock'
            elif 'FeedingEvent' in model_part:
                app_name = 'Inventory'
                model_name = 'FeedingEvent'
            elif 'FCRModel' in model_part:
                app_name = 'Scenario'
                model_name = 'FCRModel'
            elif 'MortalityModel' in model_part:
                app_name = 'Scenario'
                model_name = 'MortalityModel'
            elif 'TGCModel' in model_part:
                app_name = 'Scenario'
                model_name = 'TGCModel'
            elif 'ScenarioModelChange' in model_part:
                app_name = 'Scenario'
                model_name = 'ScenarioModelChange'
            elif 'UserProfile' in model_part:
                app_name = 'Users'
                model_name = 'UserProfile'
            else:
                # Default parsing for simpler cases
                if model_part.startswith('Batch'):
                    app_name = 'Batch'
                    model_name = model_part[5:]  # Remove 'Batch' prefix
                elif model_part.startswith('Growth'):
                    app_name = 'Batch'
                    model_name = model_part[6:]  # Remove 'Growth' prefix
                elif model_part.startswith('Mortality'):
                    app_name = 'Batch'
                    model_name = model_part[8:]  # Remove 'Mortality' prefix
                else:
                    # Fallback - assume Batch app for unrecognized patterns
                    app_name = 'Batch'
                    model_name = model_part

            # Generate unique operation ID
            if action == 'list':
                return f'list{app_name}{model_name}History'
            elif action == 'retrieve':
                return f'retrieve{app_name}{model_name}History'

        # Fallback to default behavior if parsing fails
        return None

    def get_view_action(self):
        """Helper method to determine the current view action."""
        if hasattr(self, 'request') and self.request:
            return getattr(self.request, 'action', None)
        return None


def get_operation_id_for_view(view, action, request=None):
    """
    Spectacular-compatible operation ID generator for history viewsets.

    This function is called by drf-spectacular to generate unique operation IDs
    and resolve collisions between list and retrieve operations on the same resource.

    Args:
        view: The viewset instance
        action: The action being performed (list, retrieve, etc.)
        request: The current request (optional)

    Returns:
        str: Unique operation ID or None to use default behavior
    """
    if not hasattr(view, '__class__'):
        return None

    viewset_name = view.__class__.__name__

    # Only process history viewsets
    if not viewset_name.endswith('HistoryViewSet'):
        return None

    # Extract app and model names from viewset name
    if viewset_name.endswith('HistoryViewSet'):
        model_part = viewset_name[:-14]  # Remove 'HistoryViewSet'

        # Handle special cases for multi-word model names
        if 'ContainerAssignment' in model_part:
            app_name = 'Batch'
            model_name = 'ContainerAssignment'
        elif 'FeedContainer' in model_part:
            app_name = 'Infrastructure'
            model_name = 'FeedContainer'
        elif 'FreshwaterStation' in model_part:
            app_name = 'Infrastructure'
            model_name = 'FreshwaterStation'
        elif 'ContainerType' in model_part:
            app_name = 'Infrastructure'
            model_name = 'ContainerType'
        elif 'HealthLabSample' in model_part:
            app_name = 'Health'
            model_name = 'HealthLabSample'
        elif 'JournalEntry' in model_part:
            app_name = 'Health'
            model_name = 'JournalEntry'
        elif 'MortalityRecord' in model_part:
            app_name = 'Health'
            model_name = 'MortalityRecord'
        elif 'BatchParentage' in model_part:
            app_name = 'Broodstock'
            model_name = 'BatchParentage'
        elif 'FishMovement' in model_part:
            app_name = 'Broodstock'
            model_name = 'FishMovement'
        elif 'BreedingPair' in model_part:
            app_name = 'Broodstock'
            model_name = 'BreedingPair'
        elif 'EggProduction' in model_part:
            app_name = 'Broodstock'
            model_name = 'EggProduction'
        elif 'BroodstockFish' in model_part:
            app_name = 'Broodstock'
            model_name = 'BroodstockFish'
        elif 'FeedStock' in model_part:
            app_name = 'Inventory'
            model_name = 'FeedStock'
        elif 'FeedingEvent' in model_part:
            app_name = 'Inventory'
            model_name = 'FeedingEvent'
        elif 'FCRModel' in model_part:
            app_name = 'Scenario'
            model_name = 'FCRModel'
        elif 'MortalityModel' in model_part:
            app_name = 'Scenario'
            model_name = 'MortalityModel'
        elif 'TGCModel' in model_part:
            app_name = 'Scenario'
            model_name = 'TGCModel'
        elif 'ScenarioModelChange' in model_part:
            app_name = 'Scenario'
            model_name = 'ScenarioModelChange'
        elif 'UserProfile' in model_part:
            app_name = 'Users'
            model_name = 'UserProfile'
        else:
            # Default parsing for simpler cases
            if model_part.startswith('Batch'):
                app_name = 'Batch'
                model_name = model_part[5:]  # Remove 'Batch' prefix
            elif model_part.startswith('Growth'):
                app_name = 'Batch'
                model_name = model_part[6:]  # Remove 'Growth' prefix
            elif model_part.startswith('Mortality'):
                app_name = 'Batch'
                model_name = model_part[8:]  # Remove 'Mortality' prefix
            else:
                # Fallback - assume Batch app for unrecognized patterns
                app_name = 'Batch'
                model_name = model_part

        # Generate unique operation ID
        if action == 'list':
            return f'list{app_name}{model_name}History'
        elif action == 'retrieve':
            return f'retrieve{app_name}{model_name}History'

    # Return None to use default behavior for non-history viewsets
    return None


def fix_history_operation_ids(result, generator, request, public):
    """
    Post-processing hook to fix operation ID collisions in history endpoints.

    This function modifies the generated OpenAPI schema to resolve operation ID
    collisions between list and retrieve operations on history endpoints.

    Args:
        result: The generated OpenAPI schema dictionary
        generator: The Spectacular generator instance
        request: The current request (if any)
        public: Whether this is a public schema generation

    Returns:
        The modified OpenAPI schema with fixed operation IDs
    """
    import logging
    logger = logging.getLogger(__name__)

    if 'paths' not in result:
        return result

    # Mapping of current Spectacular-generated operation IDs to correct ones
    # Need to differentiate between list and retrieve operations to avoid collisions
    operation_id_mapping = {
        # Batch app - LIST operations (collection endpoints)
        'api_v1_batch_history_batches_list': 'listBatchBatchHistory',
        'api_v1_batch_history_container_assignments_list': 'listBatchContainerAssignmentHistory',
        'api_v1_batch_history_growth_samples_list': 'listBatchGrowthSampleHistory',
        'api_v1_batch_history_mortality_events_list': 'listBatchMortalityEventHistory',
        'api_v1_batch_history_transfers_list': 'listBatchBatchTransferHistory',

        # Batch app - RETRIEVE operations (detail endpoints) - Fixed collision issue
        'api_v1_batch_history_batches_retrieve': 'retrieveBatchBatchHistoryDetail',
        'api_v1_batch_history_container_assignments_retrieve': 'retrieveBatchContainerAssignmentHistoryDetail',
        'api_v1_batch_history_growth_samples_retrieve': 'retrieveBatchGrowthSampleHistoryDetail',
        'api_v1_batch_history_mortality_events_retrieve': 'retrieveBatchMortalityEventHistoryDetail',
        'api_v1_batch_history_transfers_retrieve': 'retrieveBatchBatchTransferHistoryDetail',

        # Broodstock app - LIST operations
        'api_v1_broodstock_history_batch_parentages_list': 'listBroodstockBatchParentageHistory',
        'api_v1_broodstock_history_breeding_pairs_list': 'listBroodstockBreedingPairHistory',
        'api_v1_broodstock_history_egg_productions_list': 'listBroodstockEggProductionHistory',
        'api_v1_broodstock_history_fish_movements_list': 'listBroodstockFishMovementHistory',
        'api_v1_broodstock_history_fish_list': 'listBroodstockBroodstockFishHistory',

        # Broodstock app - RETRIEVE operations
        'api_v1_broodstock_history_batch_parentages_retrieve': 'retrieveBroodstockBatchParentageHistoryDetail',
        'api_v1_broodstock_history_breeding_pairs_retrieve': 'retrieveBroodstockBreedingPairHistoryDetail',
        'api_v1_broodstock_history_egg_productions_retrieve': 'retrieveBroodstockEggProductionHistoryDetail',
        'api_v1_broodstock_history_fish_movements_retrieve': 'retrieveBroodstockFishMovementHistoryDetail',
        'api_v1_broodstock_history_fish_retrieve': 'retrieveBroodstockBroodstockFishHistoryDetail',

        # Health app - LIST operations
        'api_v1_health_history_health_lab_samples_list': 'listHealthHealthLabSampleHistory',
        'api_v1_health_history_journal_entries_list': 'listHealthJournalEntryHistory',
        'api_v1_health_history_lice_counts_list': 'listHealthLiceCountHistory',
        'api_v1_health_history_mortality_records_list': 'listHealthMortalityRecordHistory',
        'api_v1_health_history_treatments_list': 'listHealthTreatmentHistory',

        # Health app - RETRIEVE operations
        'api_v1_health_history_health_lab_samples_retrieve': 'retrieveHealthHealthLabSampleHistoryDetail',
        'api_v1_health_history_journal_entries_retrieve': 'retrieveHealthJournalEntryHistoryDetail',
        'api_v1_health_history_lice_counts_retrieve': 'retrieveHealthLiceCountHistoryDetail',
        'api_v1_health_history_mortality_records_retrieve': 'retrieveHealthMortalityRecordHistoryDetail',
        'api_v1_health_history_treatments_retrieve': 'retrieveHealthTreatmentHistoryDetail',

        # Infrastructure app - LIST operations
        'api_v1_infrastructure_history_areas_list': 'listInfrastructureAreaHistory',
        'api_v1_infrastructure_history_container_types_list': 'listInfrastructureContainerTypeHistory',
        'api_v1_infrastructure_history_containers_list': 'listInfrastructureContainerHistory',
        'api_v1_infrastructure_history_feed_containers_list': 'listInfrastructureFeedContainerHistory',
        'api_v1_infrastructure_history_freshwater_stations_list': 'listInfrastructureFreshwaterStationHistory',
        'api_v1_infrastructure_history_geographies_list': 'listInfrastructureGeographyHistory',
        'api_v1_infrastructure_history_halls_list': 'listInfrastructureHallHistory',
        'api_v1_infrastructure_history_sensors_list': 'listInfrastructureSensorHistory',

        # Infrastructure app - RETRIEVE operations
        'api_v1_infrastructure_history_areas_retrieve': 'retrieveInfrastructureAreaHistoryDetail',
        'api_v1_infrastructure_history_container_types_retrieve': 'retrieveInfrastructureContainerTypeHistoryDetail',
        'api_v1_infrastructure_history_containers_retrieve': 'retrieveInfrastructureContainerHistoryDetail',
        'api_v1_infrastructure_history_feed_containers_retrieve': 'retrieveInfrastructureFeedContainerHistoryDetail',
        'api_v1_infrastructure_history_freshwater_stations_retrieve': 'retrieveInfrastructureFreshwaterStationHistoryDetail',
        'api_v1_infrastructure_history_geographies_retrieve': 'retrieveInfrastructureGeographyHistoryDetail',
        'api_v1_infrastructure_history_halls_retrieve': 'retrieveInfrastructureHallHistoryDetail',
        'api_v1_infrastructure_history_sensors_retrieve': 'retrieveInfrastructureSensorHistoryDetail',

        # Inventory app - LIST operations
        'api_v1_inventory_history_feed_stocks_list': 'listInventoryFeedStockHistory',
        'api_v1_inventory_history_feeding_events_list': 'listInventoryFeedingEventHistory',

        # Inventory app - RETRIEVE operations
        'api_v1_inventory_history_feed_stocks_retrieve': 'retrieveInventoryFeedStockHistoryDetail',
        'api_v1_inventory_history_feeding_events_retrieve': 'retrieveInventoryFeedingEventHistoryDetail',

        # Scenario app - LIST operations
        'api_v1_scenario_history_fcr_models_list': 'listScenarioFCRModelHistory',
        'api_v1_scenario_history_mortality_models_list': 'listScenarioMortalityModelHistory',
        'api_v1_scenario_history_scenario_model_changes_list': 'listScenarioScenarioModelChangeHistory',
        'api_v1_scenario_history_scenarios_list': 'listScenarioScenarioHistory',
        'api_v1_scenario_history_tgc_models_list': 'listScenarioTGCModelHistory',

        # Scenario app - RETRIEVE operations
        'api_v1_scenario_history_fcr_models_retrieve': 'retrieveScenarioFCRModelHistoryDetail',
        'api_v1_scenario_history_mortality_models_retrieve': 'retrieveScenarioMortalityModelHistoryDetail',
        'api_v1_scenario_history_scenario_model_changes_retrieve': 'retrieveScenarioScenarioModelChangeHistoryDetail',
        'api_v1_scenario_history_scenarios_retrieve': 'retrieveScenarioScenarioHistoryDetail',
        'api_v1_scenario_history_tgc_models_retrieve': 'retrieveScenarioTGCModelHistoryDetail',

        # Users app - LIST operations
        'api_v1_users_history_user_profiles_list': 'listUsersUserProfileHistory',

        # Users app - RETRIEVE operations
        'api_v1_users_history_user_profiles_retrieve': 'retrieveUsersUserProfileHistoryDetail',
    }

    # Count changes made
    changes_made = 0

    # Update operation IDs in the paths
    for path, path_item in result['paths'].items():
        for method, operation in path_item.items():
            if isinstance(operation, dict) and 'operationId' in operation:
                old_operation_id = operation['operationId']
                if old_operation_id in operation_id_mapping:
                    new_operation_id = operation_id_mapping[old_operation_id]
                    operation['operationId'] = new_operation_id
                    changes_made += 1
                    logger.debug(
                        f"Fixed operationId: {old_operation_id} → {new_operation_id}"
                    )

    if changes_made > 0:
        logger.debug(f"Total history operation ID fixes: {changes_made}")
    return result


class HistoryViewSet(HistoryViewSetMixin):
    """
    Base viewset for history endpoints.

    Provides a base class for history viewsets that can be combined
    with ReadOnlyModelViewSet.

    Usage:
        class MyModelHistoryViewSet(HistoryViewSet, ReadOnlyModelViewSet):
            queryset = MyModel.history.all()
            serializer_class = MyModelHistorySerializer
            filterset_class = MyModelHistoryFilter
    """
    pass
