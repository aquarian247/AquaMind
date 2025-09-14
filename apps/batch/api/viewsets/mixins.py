"""
Mixins for batch viewsets.

These mixins contain complex business logic extracted from viewsets
to improve maintainability and reduce cyclomatic complexity.
"""
import math
from django.db.models import Sum, Count, Q
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.batch.models import GrowthSample, MortalityEvent, BatchContainerAssignment
from rest_framework.exceptions import ValidationError


class BatchAnalyticsMixin:
    """
    Mixin containing complex analytics methods for BatchViewSet.

    This mixin extracts high-complexity methods from BatchViewSet to improve
    maintainability and reduce cyclomatic complexity.
    """

    @action(detail=True, methods=['get'])
    def growth_analysis(self, request, pk=None):
        """
        Calculate and return growth analysis metrics for a batch over time.

        Returns metrics like:
        - Growth rate over time
        - Weight gain trends
        - SGR (Specific Growth Rate)
        - TGC (Thermal Growth Coefficient) if temperature data is available

        URL: /api/v1/batch/batches/{pk}/growth_analysis/
        """
        batch = self.get_object()

        # Get all growth samples for this batch, ordered by sample_date
        growth_samples = GrowthSample.objects.filter(assignment__batch=batch).order_by('sample_date')

        if not growth_samples.exists():
            return Response(
                {'detail': 'No growth samples available for this batch.'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Process growth samples to calculate metrics
        result = self._build_growth_analysis_response(batch, growth_samples)
        return Response(result)

    def _build_growth_analysis_response(self, batch, growth_samples):
        """Build the growth analysis response data structure."""
        # Initialize response data structure
        result = {
            'batch_number': batch.batch_number,
            'species': batch.species.name,
            'lifecycle_stage': batch.lifecycle_stage.name,
            'start_date': batch.start_date,
            'current_avg_weight': batch.calculated_avg_weight_g, # Updated to use calculated property
            'growth_metrics': [],
            'summary': {}
        }

        # Process growth samples to calculate metrics
        prev_sample = None
        sgr_values = []
        weight_data = []

        for sample in growth_samples:
            sample_data = self._process_growth_sample(sample, prev_sample, sgr_values)
            weight_data.append(float(sample.avg_weight_g))
            result['growth_metrics'].append(sample_data)
            prev_sample = sample

        # Calculate summary statistics
        if growth_samples.count() > 1:
            result['summary'] = self._calculate_growth_summary(growth_samples, weight_data, sgr_values)

        return result

    def _process_growth_sample(self, sample, prev_sample, sgr_values):
        """Process a single growth sample and calculate metrics."""
        sample_data = {
            'date': sample.sample_date,
            'avg_weight_g': float(sample.avg_weight_g),
            'avg_length_cm': float(sample.avg_length_cm) if sample.avg_length_cm else None,
            'condition_factor': float(sample.condition_factor) if sample.condition_factor else None,
        }

        # Add weight gain and SGR if we have a previous sample
        if prev_sample:
            days_diff = (sample.sample_date - prev_sample.sample_date).days
            if days_diff > 0:
                # Calculate weight gain
                weight_gain = sample.avg_weight_g - prev_sample.avg_weight_g
                sample_data['weight_gain_g'] = float(weight_gain)

                # Calculate daily growth rate
                daily_growth = weight_gain / days_diff
                sample_data['daily_growth_g'] = float(daily_growth)

                # Calculate SGR (Specific Growth Rate)
                if prev_sample.avg_weight_g > 0:
                    sgr = (math.log(float(sample.avg_weight_g)) -
                           math.log(float(prev_sample.avg_weight_g))) / days_diff * 100
                    sample_data['sgr'] = round(sgr, 2)
                    sgr_values.append(sgr)

        return sample_data

    def _calculate_growth_summary(self, growth_samples, weight_data, sgr_values):
        """Calculate summary statistics for growth analysis."""
        first_sample = growth_samples.first()
        last_sample = growth_samples.last()
        total_days = (last_sample.sample_date - first_sample.sample_date).days

        if total_days > 0:
            total_weight_gain = last_sample.avg_weight_g - first_sample.avg_weight_g

            return {
                'total_weight_gain_g': float(total_weight_gain),
                'avg_daily_growth_g': float(total_weight_gain / total_days),
                'samples_count': growth_samples.count(),
                'measurement_period_days': total_days,
                'avg_sgr': round(sum(sgr_values) / len(sgr_values), 2) if sgr_values else None,
                'min_weight_g': min(weight_data),
                'max_weight_g': max(weight_data)
            }

        return {}

    @action(detail=True, methods=['get'])
    def performance_metrics(self, request, pk=None):
        """
        Calculate and return performance metrics for a batch.

        Includes:
        - Mortality rates
        - Growth efficiency
        - Density metrics
        - Current status summary

        URL: /api/v1/batch/batches/{pk}/performance_metrics/
        """
        batch = self.get_object()

        # Initialize response data structure
        result = {
            'batch_number': batch.batch_number,
            'species': batch.species.name,
            'lifecycle_stage': batch.lifecycle_stage.name,
            'start_date': batch.start_date,
            'days_active': (timezone.now().date() - batch.start_date).days,
            'current_metrics': {
                'population_count': batch.population_count,
                'biomass_kg': float(batch.biomass_kg),
                'avg_weight_g': float(batch.avg_weight_g)
            },
        }

        # Calculate mortality metrics
        mortality_metrics = self._calculate_mortality_metrics(batch)
        result['mortality_metrics'] = mortality_metrics

        # Calculate container metrics
        container_metrics = self._calculate_container_metrics(batch)
        if container_metrics:
            result['container_metrics'] = container_metrics

        # Get growth metrics if available
        growth_samples = self._get_recent_growth_samples(batch)
        if growth_samples:
            result['recent_growth_samples'] = growth_samples

        return Response(result)

    def _calculate_mortality_metrics(self, batch):
        """Calculate mortality metrics for a batch."""
        total_mortality = batch.mortality_events.aggregate(
            total_count=Sum('count'),
            total_biomass=Sum('biomass_kg')
        )

        if total_mortality['total_count']:
            # Get initial population (current + mortality)
            initial_population = batch.population_count + total_mortality['total_count']
            mortality_rate = round((total_mortality['total_count'] / initial_population) * 100, 2)

            # Get mortality by cause
            mortality_by_cause = self._get_mortality_by_cause(batch.mortality_events.all())

            return {
                'total_count': total_mortality['total_count'],
                'total_biomass_kg': float(total_mortality['total_biomass'] or 0),
                'mortality_rate': mortality_rate,
                'by_cause': mortality_by_cause
            }

        return {
            'total_count': 0,
            'total_biomass_kg': 0,
            'mortality_rate': 0,
            'by_cause': []
        }

    def _get_mortality_by_cause(self, mortality_events):
        """Get mortality statistics grouped by cause."""
        mortality_by_cause = mortality_events.values('cause').annotate(
            count=Sum('count'),
            biomass=Sum('biomass_kg')
        ).order_by('-count')

        return [
            {
                'cause': item['cause'],
                'count': item['count'],
                'biomass_kg': float(item['biomass'] or 0),
                'percentage': round((item['count'] / mortality_by_cause.aggregate(total=Sum('count'))['total']) * 100, 2)
            }
            for item in mortality_by_cause
        ]

    def _calculate_container_metrics(self, batch):
        """Calculate container assignment metrics for a batch."""
        active_assignments = batch.container_assignments.filter(is_active=True)
        if not active_assignments.exists():
            return None

        containers_data = []
        for assignment in active_assignments:
            container_data = self._process_container_assignment(assignment)
            containers_data.append(container_data)

        return containers_data

    def _process_container_assignment(self, assignment):
        """Process a single container assignment."""
        # Calculate density
        if assignment.container.volume_m3:
            density = assignment.biomass_kg / assignment.container.volume_m3
        else:
            density = None

        return {
            'container_name': assignment.container.name,
            'population': assignment.population_count,
            'biomass_kg': float(assignment.biomass_kg),
            'density_kg_m3': round(float(density), 2) if density else None,
            'assignment_date': assignment.assignment_date
        }

    def _get_recent_growth_samples(self, batch):
        """Get recent growth samples for a batch."""
        latest_samples = GrowthSample.objects.filter(assignment__batch=batch).order_by('-sample_date')[:5]

        if not latest_samples.exists():
            return None

        return [
            {
                'date': sample.sample_date,
                'avg_weight_g': float(sample.avg_weight_g),
                'sample_size': sample.sample_size,
                'condition_factor': float(sample.condition_factor) if sample.condition_factor else None
            }
            for sample in latest_samples
        ]

    @action(detail=False, methods=['get'])
    def compare(self, request):
        """
        Compare metrics between multiple batches.

        Query parameters:
        - batch_ids: Comma-separated list of batch IDs to compare
        - metrics: Comma-separated list of metrics to include (default: all)
          Options: growth, mortality, biomass, all

        Example URL: /api/v1/batch/batches/compare/?batch_ids=1,2,3&metrics=growth,mortality
        """
        batch_ids = request.query_params.get('batch_ids', '')
        metrics = request.query_params.get('metrics', 'all').lower()

        if not batch_ids:
            return Response(
                {'detail': 'batch_ids parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            batch_id_list = [int(id.strip()) for id in batch_ids.split(',')]
        except ValueError:
            return Response(
                {'detail': 'Invalid batch_ids format. Use comma-separated integers.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        batches = self.get_queryset().filter(id__in=batch_id_list)
        if not batches.exists():
            return Response(
                {'detail': 'No batches found with the provided IDs.'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Process requested metrics
        include_growth = metrics in ('all', 'growth')
        include_mortality = metrics in ('all', 'mortality')
        include_biomass = metrics in ('all', 'biomass')

        # Initialize response with batch basic info
        result = {
            'batches': [
                {
                    'id': batch.id,
                    'batch_number': batch.batch_number,
                    'species': batch.species.name,
                    'lifecycle_stage': batch.lifecycle_stage.name,
                    'status': batch.status,
                    'start_date': batch.start_date,
                    'days_active': (timezone.now().date() - batch.start_date).days,
                }
                for batch in batches
            ],
        }

        # Add growth metrics if requested
        if include_growth:
            growth_metrics = self._get_growth_comparison_metrics(batches)
            result['growth_comparison'] = growth_metrics

        # Add mortality metrics if requested
        if include_mortality:
            mortality_metrics = self._get_mortality_comparison_metrics(batches)
            result['mortality_comparison'] = mortality_metrics

        # Add biomass metrics if requested
        if include_biomass:
            biomass_metrics = self._get_biomass_comparison_metrics(batches)
            result['biomass_comparison'] = biomass_metrics

        return Response(result)

    def _get_growth_comparison_metrics(self, batches):
        """Get growth comparison metrics for multiple batches."""
        growth_metrics = []

        for batch in batches:
            # Get first and last growth samples
            batch_growth_samples = GrowthSample.objects.filter(assignment__batch=batch).order_by('sample_date')
            first_sample = batch_growth_samples.first()
            last_sample = batch_growth_samples.last()

            batch_growth = {
                'batch_id': batch.id,
                'batch_number': batch.batch_number,
                'current_avg_weight_g': float(batch.calculated_avg_weight_g),
            }

            if first_sample and last_sample and first_sample != last_sample:
                days = (last_sample.sample_date - first_sample.sample_date).days
                if days > 0:
                    weight_gain = last_sample.avg_weight_g - first_sample.avg_weight_g
                    daily_growth = weight_gain / days

                    # Calculate SGR
                    sgr = (math.log(float(last_sample.avg_weight_g)) -
                          math.log(float(first_sample.avg_weight_g))) / days * 100

                    batch_growth.update({
                        'initial_weight_g': float(first_sample.avg_weight_g),
                        'final_weight_g': float(last_sample.avg_weight_g),
                        'weight_gain_g': float(weight_gain),
                        'days': days,
                        'daily_growth_g': float(daily_growth),
                        'sgr': round(sgr, 2)
                    })

            growth_metrics.append(batch_growth)

        return growth_metrics

    def _get_mortality_comparison_metrics(self, batches):
        """Get mortality comparison metrics for multiple batches."""
        mortality_metrics = []

        for batch in batches:
            mortality_data = batch.mortality_events.aggregate(
                total_count=Sum('count'),
                total_biomass=Sum('biomass_kg')
            )

            batch_mortality = {
                'batch_id': batch.id,
                'batch_number': batch.batch_number,
                'total_mortality': mortality_data['total_count'] or 0,
                'mortality_biomass_kg': float(mortality_data['total_biomass'] or 0),
            }

            # Calculate mortality rate
            if mortality_data['total_count']:
                initial_population = batch.calculated_population_count + mortality_data['total_count']
                batch_mortality['mortality_rate'] = round(
                    (mortality_data['total_count'] / initial_population) * 100, 2
                )
            else:
                batch_mortality['mortality_rate'] = 0.0

            mortality_metrics.append(batch_mortality)

        return mortality_metrics

    def _get_biomass_comparison_metrics(self, batches):
        """Get biomass comparison metrics for multiple batches."""
        biomass_metrics = []

        for batch in batches:
            # Get container assignments
            assignments = batch.batch_assignments.filter(is_active=True)

            # Calculate total volume if container has volume data
            total_volume = 0
            containers_with_volume = 0

            for assignment in assignments:
                if assignment.container.volume_m3:
                    total_volume += assignment.container.volume_m3
                    containers_with_volume += 1

            batch_biomass = {
                'batch_id': batch.id,
                'batch_number': batch.batch_number,
                'current_biomass_kg': float(batch.calculated_biomass_kg),
                'population_count': batch.calculated_population_count,
            }

            # Add density if we have container volume
            if containers_with_volume > 0:
                avg_density = batch.calculated_biomass_kg / total_volume
                batch_biomass['avg_density_kg_m3'] = round(float(avg_density), 2)

            biomass_metrics.append(batch_biomass)

        return biomass_metrics


class LocationFilterMixin:
    """
    Mixin containing location-based filtering logic for BatchContainerAssignmentViewSet.

    This mixin extracts complex location filtering logic to improve maintainability
    and reduce cyclomatic complexity.
    """

    def apply_location_filters(self, queryset, request):
        """
        Apply location-based filters to the BatchContainerAssignment queryset.

        Filters supported:
        - geography: Filter by Geography ID (through hall->station or area)
        - area: Filter by Area ID (direct container area)
        - station: Filter by FreshwaterStation ID (through hall)
        - hall: Filter by Hall ID (direct container hall)
        - container_type: Filter by ContainerType category slug (TANK, PEN, TRAY, OTHER)

        Returns filtered queryset or raises ValidationError for invalid IDs.
        """
        filters_applied = Q()

        # Geography filter (affects both hall and area containers)
        geography_id = request.query_params.get('geography')
        if geography_id:
            geography_filters = self._get_geography_filters(geography_id)
            filters_applied &= geography_filters

        # Area filter (only affects containers directly in areas)
        area_id = request.query_params.get('area')
        if area_id:
            area_filters = self._get_area_filters(area_id)
            filters_applied &= area_filters

        # Station filter (only affects containers in halls)
        station_id = request.query_params.get('station')
        if station_id:
            station_filters = self._get_station_filters(station_id)
            filters_applied &= station_filters

        # Hall filter (only affects containers in halls)
        hall_id = request.query_params.get('hall')
        if hall_id:
            hall_filters = self._get_hall_filters(hall_id)
            filters_applied &= hall_filters

        # Container type filter (by category)
        container_type = request.query_params.get('container_type')
        if container_type:
            container_type_filters = self._get_container_type_filters(container_type)
            filters_applied &= container_type_filters

        return queryset.filter(filters_applied) if filters_applied else queryset

    def _get_geography_filters(self, geography_id):
        """Get Q filters for geography-based filtering."""
        try:
            geography_id = int(geography_id)
            # Validate geography exists
            from apps.infrastructure.models import Geography
            if not Geography.objects.filter(id=geography_id).exists():
                raise ValidationError({'geography': 'Geography not found'})

            # Filter containers that are either in halls of stations in this geography
            # OR directly in areas in this geography
            return (
                Q(container__hall__freshwater_station__geography_id=geography_id) |
                Q(container__area__geography_id=geography_id)
            )
        except (ValueError, TypeError):
            raise ValidationError({'geography': 'Invalid geography ID'})

    def _get_area_filters(self, area_id):
        """Get Q filters for area-based filtering."""
        try:
            area_id = int(area_id)
            # Validate area exists
            from apps.infrastructure.models import Area
            if not Area.objects.filter(id=area_id).exists():
                raise ValidationError({'area': 'Area not found'})

            return Q(container__area_id=area_id)
        except (ValueError, TypeError):
            raise ValidationError({'area': 'Invalid area ID'})

    def _get_station_filters(self, station_id):
        """Get Q filters for station-based filtering."""
        try:
            station_id = int(station_id)
            # Validate station exists
            from apps.infrastructure.models import FreshwaterStation
            if not FreshwaterStation.objects.filter(id=station_id).exists():
                raise ValidationError({'station': 'Freshwater station not found'})

            return Q(container__hall__freshwater_station_id=station_id)
        except (ValueError, TypeError):
            raise ValidationError({'station': 'Invalid freshwater station ID'})

    def _get_hall_filters(self, hall_id):
        """Get Q filters for hall-based filtering."""
        try:
            hall_id = int(hall_id)
            # Validate hall exists
            from apps.infrastructure.models import Hall
            if not Hall.objects.filter(id=hall_id).exists():
                raise ValidationError({'hall': 'Hall not found'})

            return Q(container__hall_id=hall_id)
        except (ValueError, TypeError):
            raise ValidationError({'hall': 'Invalid hall ID'})

    def _get_container_type_filters(self, container_type):
        """Get Q filters for container type filtering."""
        # Validate that the category exists
        from apps.infrastructure.models import ContainerType
        if not ContainerType.objects.filter(category=container_type.upper()).exists():
            raise ValidationError({
                'container_type': f'Invalid container type. Must be one of: {[choice[0] for choice in ContainerType.CONTAINER_CATEGORIES]}'
            })

        return Q(container__container_type__category=container_type.upper())
