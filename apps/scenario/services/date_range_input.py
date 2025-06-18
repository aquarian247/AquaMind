"""
Date range input service for scenario planning.

Handles period-based data entry with range validation, overlap detection,
and data interpolation for gaps.
"""
from datetime import date, timedelta
from typing import List, Dict, Tuple, Optional, Any
from django.core.exceptions import ValidationError
from django.db import transaction

from ..models import TemperatureProfile, TemperatureReading


class DateRange:
    """Represents a date range with associated value."""
    
    def __init__(self, start_date: date, end_date: date, value: float):
        """Initialize date range."""
        if start_date > end_date:
            raise ValidationError("Start date must be before end date")
        
        self.start_date = start_date
        self.end_date = end_date
        self.value = value
    
    def overlaps_with(self, other: 'DateRange') -> bool:
        """Check if this range overlaps with another."""
        return not (self.end_date < other.start_date or 
                   self.start_date > other.end_date)
    
    def contains_date(self, check_date: date) -> bool:
        """Check if a date falls within this range."""
        return self.start_date <= check_date <= self.end_date
    
    def get_days(self) -> int:
        """Get number of days in range (inclusive)."""
        return (self.end_date - self.start_date).days + 1
    
    def __repr__(self):
        return f"DateRange({self.start_date} to {self.end_date}: {self.value})"


class DateRangeInputService:
    """
    Service for managing date range-based data input.
    
    Supports adding ranges, detecting overlaps, merging ranges,
    and interpolating values for gaps.
    """
    
    def __init__(self):
        """Initialize the service."""
        self.ranges: List[DateRange] = []
        self.errors: List[str] = []
        self.warnings: List[str] = []
    
    def add_range(
        self, 
        start_date: date, 
        end_date: date, 
        value: float,
        allow_overlap: bool = False
    ) -> bool:
        """
        Add a new date range.
        
        Args:
            start_date: Start date of range
            end_date: End date of range
            value: Value for this range
            allow_overlap: If True, overlapping ranges are allowed
            
        Returns:
            True if range was added successfully
        """
        try:
            new_range = DateRange(start_date, end_date, value)
            
            # Check for overlaps
            if not allow_overlap:
                overlaps = self._find_overlapping_ranges(new_range)
                if overlaps:
                    self.errors.append(
                        f"Range {new_range} overlaps with existing ranges: "
                        f"{', '.join(str(r) for r in overlaps)}"
                    )
                    return False
            
            self.ranges.append(new_range)
            self._sort_ranges()
            return True
            
        except ValidationError as e:
            self.errors.append(str(e))
            return False
    
    def add_multiple_ranges(
        self, 
        range_data: List[Dict[str, Any]],
        allow_overlap: bool = False
    ) -> Tuple[int, int]:
        """
        Add multiple date ranges.
        
        Args:
            range_data: List of dicts with 'start_date', 'end_date', 'value'
            allow_overlap: If True, overlapping ranges are allowed
            
        Returns:
            Tuple of (successful_count, failed_count)
        """
        successful = 0
        failed = 0
        
        for data in range_data:
            if self.add_range(
                data['start_date'],
                data['end_date'],
                data['value'],
                allow_overlap
            ):
                successful += 1
            else:
                failed += 1
        
        return successful, failed
    
    def merge_adjacent_ranges(self, tolerance: float = 0.0) -> int:
        """
        Merge adjacent ranges with same or similar values.
        
        Args:
            tolerance: Maximum difference in values to consider for merging
            
        Returns:
            Number of ranges merged
        """
        if len(self.ranges) < 2:
            return 0
        
        merged_count = 0
        merged_ranges = [self.ranges[0]]
        
        for current in self.ranges[1:]:
            last = merged_ranges[-1]
            
            # Check if adjacent and values are within tolerance
            if (last.end_date + timedelta(days=1) == current.start_date and
                abs(last.value - current.value) <= tolerance):
                # Merge ranges
                last.end_date = current.end_date
                if tolerance == 0:
                    # Keep exact value if no tolerance
                    last.value = current.value
                else:
                    # Average values if within tolerance
                    last.value = (last.value + current.value) / 2
                merged_count += 1
            else:
                merged_ranges.append(current)
        
        self.ranges = merged_ranges
        return merged_count
    
    def fill_gaps(
        self, 
        start_date: date, 
        end_date: date,
        interpolation_method: str = 'linear',
        default_value: Optional[float] = None
    ) -> int:
        """
        Fill gaps in date ranges with interpolated values.
        
        Args:
            start_date: Start of period to fill
            end_date: End of period to fill
            interpolation_method: 'linear', 'previous', 'next', or 'default'
            default_value: Value to use for 'default' method
            
        Returns:
            Number of gaps filled
        """
        gaps = self._find_gaps(start_date, end_date)
        
        if not gaps:
            return 0
        
        for gap_start, gap_end in gaps:
            if interpolation_method == 'linear':
                value = self._interpolate_linear(gap_start, gap_end)
            elif interpolation_method == 'previous':
                value = self._get_previous_value(gap_start)
            elif interpolation_method == 'next':
                value = self._get_next_value(gap_end)
            elif interpolation_method == 'default':
                value = default_value
            else:
                raise ValueError(f"Unknown interpolation method: {interpolation_method}")
            
            if value is not None:
                self.add_range(gap_start, gap_end, value, allow_overlap=True)
        
        return len(gaps)
    
    def generate_daily_values(
        self, 
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> List[Dict[str, Any]]:
        """
        Generate daily values from ranges.
        
        Args:
            start_date: Start date (uses earliest range if None)
            end_date: End date (uses latest range if None)
            
        Returns:
            List of dicts with 'date' and 'value' keys
        """
        if not self.ranges:
            return []
        
        if start_date is None:
            start_date = min(r.start_date for r in self.ranges)
        if end_date is None:
            end_date = max(r.end_date for r in self.ranges)
        
        daily_values = []
        current_date = start_date
        
        while current_date <= end_date:
            # Find range containing this date
            value = None
            for range_obj in self.ranges:
                if range_obj.contains_date(current_date):
                    value = range_obj.value
                    break
            
            if value is not None:
                daily_values.append({
                    'date': current_date,
                    'value': value
                })
            
            current_date += timedelta(days=1)
        
        return daily_values
    
    @transaction.atomic
    def save_as_temperature_profile(
        self, 
        profile_name: str,
        fill_gaps: bool = True,
        interpolation_method: str = 'linear'
    ) -> Optional[TemperatureProfile]:
        """
        Save ranges as temperature profile.
        
        Args:
            profile_name: Name for the temperature profile
            fill_gaps: Whether to fill gaps before saving
            interpolation_method: Method for filling gaps
            
        Returns:
            Created TemperatureProfile or None if failed
        """
        if not self.ranges:
            self.errors.append("No ranges to save")
            return None
        
        # Fill gaps if requested
        if fill_gaps:
            start = min(r.start_date for r in self.ranges)
            end = max(r.end_date for r in self.ranges)
            self.fill_gaps(start, end, interpolation_method)
        
        # Generate daily values
        daily_values = self.generate_daily_values()
        
        if not daily_values:
            self.errors.append("No daily values generated")
            return None
        
        # Create profile
        profile = TemperatureProfile.objects.create(name=profile_name)
        
        # Create readings
        readings = []
        for data in daily_values:
            reading = TemperatureReading(
                profile=profile,
                reading_date=data['date'],
                temperature=data['value']
            )
            readings.append(reading)
        
        TemperatureReading.objects.bulk_create(readings)
        
        return profile
    
    def validate_ranges(self) -> bool:
        """
        Validate all ranges for consistency.
        
        Returns:
            True if all ranges are valid
        """
        self.errors = []
        self.warnings = []
        
        if not self.ranges:
            self.warnings.append("No ranges defined")
            return True
        
        # Check for gaps
        gaps = self._find_gaps(
            min(r.start_date for r in self.ranges),
            max(r.end_date for r in self.ranges)
        )
        
        if gaps:
            self.warnings.append(
                f"Found {len(gaps)} gaps in date ranges"
            )
        
        # Check for extreme values
        for range_obj in self.ranges:
            if range_obj.value < -50 or range_obj.value > 50:
                self.warnings.append(
                    f"Unusual value {range_obj.value} in range "
                    f"{range_obj.start_date} to {range_obj.end_date}"
                )
        
        return len(self.errors) == 0
    
    # Private helper methods
    def _sort_ranges(self):
        """Sort ranges by start date."""
        self.ranges.sort(key=lambda r: r.start_date)
    
    def _find_overlapping_ranges(self, new_range: DateRange) -> List[DateRange]:
        """Find ranges that overlap with the given range."""
        return [r for r in self.ranges if r.overlaps_with(new_range)]
    
    def _find_gaps(self, start_date: date, end_date: date) -> List[Tuple[date, date]]:
        """Find gaps in coverage between start and end dates."""
        if not self.ranges:
            return [(start_date, end_date)]
        
        gaps = []
        current_date = start_date
        
        for range_obj in self.ranges:
            if range_obj.start_date > current_date and range_obj.start_date <= end_date:
                # Found a gap
                gap_end = min(range_obj.start_date - timedelta(days=1), end_date)
                gaps.append((current_date, gap_end))
            
            if range_obj.end_date >= current_date:
                current_date = max(current_date, range_obj.end_date + timedelta(days=1))
        
        # Check for gap at the end
        if current_date <= end_date:
            gaps.append((current_date, end_date))
        
        return gaps
    
    def _interpolate_linear(self, gap_start: date, gap_end: date) -> Optional[float]:
        """Linear interpolation between surrounding values."""
        prev_value = self._get_previous_value(gap_start)
        next_value = self._get_next_value(gap_end)
        
        if prev_value is None or next_value is None:
            return prev_value or next_value
        
        # Simple average for now (could do weighted by distance)
        return (prev_value + next_value) / 2
    
    def _get_previous_value(self, ref_date: date) -> Optional[float]:
        """Get value from the range before the reference date."""
        for range_obj in reversed(self.ranges):
            if range_obj.end_date < ref_date:
                return range_obj.value
        return None
    
    def _get_next_value(self, ref_date: date) -> Optional[float]:
        """Get value from the range after the reference date."""
        for range_obj in self.ranges:
            if range_obj.start_date > ref_date:
                return range_obj.value
        return None 