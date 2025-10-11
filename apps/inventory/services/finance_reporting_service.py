"""
Finance Reporting Service for Feed Inventory.

Provides comprehensive aggregation and breakdown capabilities for finance reporting,
including multi-dimensional analysis by geography, feed type, container, and time periods.
"""
from decimal import Decimal
from typing import Dict, List, Any, Optional
from datetime import date, timedelta
from django.db.models import QuerySet, Sum, Count, Avg, Min, Max, Q, F
from django.db.models.functions import TruncDate, TruncWeek, TruncMonth

from apps.inventory.models import FeedingEvent


class FinanceReportingService:
    """
    Service for generating finance reports from feeding event data.
    
    Provides methods for calculating summaries, breakdowns by various dimensions,
    and time series analysis for feed usage and costs.
    """

    @classmethod
    def generate_finance_report(
        cls,
        queryset: QuerySet[FeedingEvent],
        include_breakdowns: bool = True,
        include_time_series: bool = False,
        group_by: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate comprehensive finance report from filtered queryset.
        
        Args:
            queryset: Pre-filtered FeedingEvent queryset
            include_breakdowns: Include dimensional breakdowns
            include_time_series: Include daily/weekly time series
            group_by: Primary grouping dimension ('feed_type', 'area', 'geography', 'container')
            
        Returns:
            Dict containing:
                - summary: Top-level totals and counts
                - by_feed_type: Breakdown by feed type (if include_breakdowns)
                - by_geography: Breakdown by geography (if include_breakdowns)
                - by_area: Breakdown by area (if include_breakdowns)
                - by_container: Breakdown by container (if include_breakdowns)
                - time_series: Daily/weekly breakdown (if include_time_series)
        """
        report = {}
        
        # Always include summary
        report['summary'] = cls.calculate_summary(queryset)
        
        # Include breakdowns if requested
        if include_breakdowns:
            report['by_feed_type'] = cls.breakdown_by_feed_type(queryset)
            report['by_geography'] = cls.breakdown_by_geography(queryset)
            report['by_area'] = cls.breakdown_by_area(queryset)
            report['by_container'] = cls.breakdown_by_container(queryset)
        
        # Include time series if requested
        if include_time_series:
            interval = cls._determine_time_series_interval(queryset, group_by)
            report['time_series'] = cls.generate_time_series(queryset, interval)
        
        return report

    @classmethod
    def calculate_summary(cls, queryset: QuerySet[FeedingEvent]) -> Dict[str, Any]:
        """
        Calculate top-level summary metrics.
        
        Args:
            queryset: FeedingEvent queryset to summarize
            
        Returns:
            Dict with total_feed_kg, total_feed_cost, events_count, date_range
        """
        aggregates = queryset.aggregate(
            total_feed_kg=Sum('amount_kg'),
            total_feed_cost=Sum('feed_cost'),
            events_count=Count('id')
        )
        
        # Get date range
        date_range = queryset.aggregate(
            start_date=Min('feeding_date'),
            end_date=Max('feeding_date')
        )
        
        return {
            'total_feed_kg': float(aggregates['total_feed_kg'] or 0),
            'total_feed_cost': float(aggregates['total_feed_cost'] or 0),
            'events_count': aggregates['events_count'] or 0,
            'date_range': {
                'start': date_range['start_date'].isoformat() if date_range['start_date'] else None,
                'end': date_range['end_date'].isoformat() if date_range['end_date'] else None
            }
        }

    @classmethod
    def breakdown_by_feed_type(cls, queryset: QuerySet[FeedingEvent]) -> List[Dict[str, Any]]:
        """
        Aggregate feeding events by feed type with nutritional information.
        
        Args:
            queryset: FeedingEvent queryset to analyze
            
        Returns:
            List of dicts with feed type details and aggregated metrics
        """
        breakdown = queryset.values(
            'feed__id',
            'feed__name',
            'feed__brand',
            'feed__protein_percentage',
            'feed__fat_percentage',
            'feed__carbohydrate_percentage',
            'feed__size_category'
        ).annotate(
            total_kg=Sum('amount_kg'),
            total_cost=Sum('feed_cost'),
            events_count=Count('id')
        ).order_by('-total_kg')
        
        results = []
        for item in breakdown:
            total_kg = float(item['total_kg'] or 0)
            total_cost = float(item['total_cost'] or 0)
            
            # Calculate weighted average cost per kg
            avg_cost_per_kg = (total_cost / total_kg) if total_kg > 0 else 0
            
            results.append({
                'feed_id': item['feed__id'],
                'feed_name': item['feed__name'],
                'brand': item['feed__brand'],
                'protein_percentage': float(item['feed__protein_percentage']) if item['feed__protein_percentage'] else None,
                'fat_percentage': float(item['feed__fat_percentage']) if item['feed__fat_percentage'] else None,
                'carbohydrate_percentage': float(item['feed__carbohydrate_percentage']) if item['feed__carbohydrate_percentage'] else None,
                'size_category': item['feed__size_category'],
                'total_kg': total_kg,
                'total_cost': total_cost,
                'events_count': item['events_count'] or 0,
                'avg_cost_per_kg': avg_cost_per_kg
            })
        
        return results

    @classmethod
    def breakdown_by_geography(cls, queryset: QuerySet[FeedingEvent]) -> List[Dict[str, Any]]:
        """
        Aggregate feeding events by geography with area counts.
        
        Args:
            queryset: FeedingEvent queryset to analyze
            
        Returns:
            List of dicts with geography details and aggregated metrics
        """
        breakdown = queryset.filter(
            container__area__isnull=False
        ).values(
            'container__area__geography__id',
            'container__area__geography__name'
        ).annotate(
            total_kg=Sum('amount_kg'),
            total_cost=Sum('feed_cost'),
            events_count=Count('id'),
            area_count=Count('container__area', distinct=True),
            container_count=Count('container', distinct=True)
        ).order_by('-total_kg')
        
        results = []
        for item in breakdown:
            results.append({
                'geography_id': item['container__area__geography__id'],
                'geography_name': item['container__area__geography__name'],
                'total_kg': float(item['total_kg'] or 0),
                'total_cost': float(item['total_cost'] or 0),
                'events_count': item['events_count'] or 0,
                'area_count': item['area_count'] or 0,
                'container_count': item['container_count'] or 0
            })
        
        return results

    @classmethod
    def breakdown_by_area(cls, queryset: QuerySet[FeedingEvent]) -> List[Dict[str, Any]]:
        """
        Aggregate feeding events by area with container counts.
        
        Args:
            queryset: FeedingEvent queryset to analyze
            
        Returns:
            List of dicts with area details and aggregated metrics
        """
        breakdown = queryset.filter(
            container__area__isnull=False
        ).values(
            'container__area__id',
            'container__area__name',
            'container__area__geography__name'
        ).annotate(
            total_kg=Sum('amount_kg'),
            total_cost=Sum('feed_cost'),
            events_count=Count('id'),
            container_count=Count('container', distinct=True)
        ).order_by('-total_kg')
        
        results = []
        for item in breakdown:
            results.append({
                'area_id': item['container__area__id'],
                'area_name': item['container__area__name'],
                'geography': item['container__area__geography__name'],
                'total_kg': float(item['total_kg'] or 0),
                'total_cost': float(item['total_cost'] or 0),
                'events_count': item['events_count'] or 0,
                'container_count': item['container_count'] or 0
            })
        
        return results

    @classmethod
    def breakdown_by_container(cls, queryset: QuerySet[FeedingEvent]) -> List[Dict[str, Any]]:
        """
        Aggregate feeding events by container with feed diversity.
        
        Args:
            queryset: FeedingEvent queryset to analyze
            
        Returns:
            List of dicts with container details and aggregated metrics
        """
        breakdown = queryset.values(
            'container__id',
            'container__name',
            'container__area__name',
            'container__hall__name'
        ).annotate(
            total_kg=Sum('amount_kg'),
            total_cost=Sum('feed_cost'),
            events_count=Count('id'),
            feed_type_count=Count('feed', distinct=True)
        ).order_by('-total_kg')
        
        results = []
        for item in breakdown:
            results.append({
                'container_id': item['container__id'],
                'container_name': item['container__name'],
                'area': item['container__area__name'],
                'hall': item['container__hall__name'],
                'total_kg': float(item['total_kg'] or 0),
                'total_cost': float(item['total_cost'] or 0),
                'events_count': item['events_count'] or 0,
                'feed_type_count': item['feed_type_count'] or 0
            })
        
        return results

    @classmethod
    def generate_time_series(
        cls,
        queryset: QuerySet[FeedingEvent],
        interval: str = 'day'
    ) -> List[Dict[str, Any]]:
        """
        Generate time series with specified interval.
        
        Args:
            queryset: FeedingEvent queryset to analyze
            interval: Time bucket interval ('day', 'week', 'month')
            
        Returns:
            List of dicts with date/period and aggregated metrics
            
        Raises:
            ValueError: If interval is not supported
        """
        if interval not in ['day', 'week', 'month']:
            raise ValueError(f"Unsupported interval: {interval}. Use 'day', 'week', or 'month'.")
        
        # For daily interval, use simple values grouping (SQLite compatible)
        if interval == 'day':
            time_series = queryset.values('feeding_date').annotate(
                total_kg=Sum('amount_kg'),
                total_cost=Sum('feed_cost'),
                events_count=Count('id')
            ).order_by('feeding_date')
            
            results = []
            for item in time_series:
                results.append({
                    'date': item['feeding_date'].isoformat() if item['feeding_date'] else None,
                    'total_kg': float(item['total_kg'] or 0),
                    'total_cost': float(item['total_cost'] or 0),
                    'events_count': item['events_count'] or 0
                })
            
            return results
        
        # For week/month, use Trunc functions (PostgreSQL optimal)
        # On SQLite, fall back to Python-side grouping
        try:
            trunc_func = {
                'week': TruncWeek,
                'month': TruncMonth
            }[interval]
            
            time_series = queryset.annotate(
                period=trunc_func('feeding_date')
            ).values('period').annotate(
                total_kg=Sum('amount_kg'),
                total_cost=Sum('feed_cost'),
                events_count=Count('id')
            ).order_by('period')
            
            results = []
            for item in time_series:
                results.append({
                    'period': item['period'].isoformat() if item['period'] else None,
                    'total_kg': float(item['total_kg'] or 0),
                    'total_cost': float(item['total_cost'] or 0),
                    'events_count': item['events_count'] or 0
                })
            
            return results
        except Exception:
            # Fallback to daily if week/month truncation fails (e.g., SQLite)
            return cls.generate_time_series(queryset, 'day')

    @classmethod
    def _determine_time_series_interval(
        cls,
        queryset: QuerySet[FeedingEvent],
        group_by: Optional[str]
    ) -> str:
        """
        Determine appropriate time series interval based on data range and grouping.
        
        Args:
            queryset: FeedingEvent queryset to analyze
            group_by: User-specified grouping preference
            
        Returns:
            'day', 'week', or 'month'
        """
        # If user specified week or month grouping, use that
        if group_by in ['week', 'month']:
            return group_by
        
        # Otherwise, determine based on date range
        date_range = queryset.aggregate(
            start_date=Min('feeding_date'),
            end_date=Max('feeding_date')
        )
        
        if not date_range['start_date'] or not date_range['end_date']:
            return 'day'
        
        days = (date_range['end_date'] - date_range['start_date']).days
        
        # Use day for <= 90 days, week for <= 365 days, month for > 365 days
        if days <= 90:
            return 'day'
        elif days <= 365:
            return 'week'
        else:
            return 'month'

