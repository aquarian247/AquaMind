"""
Bulk data import service for scenario planning.

Handles CSV upload processing for temperature, FCR, and mortality data
with validation, error handling, and preview generation.
"""
import csv
import io
from datetime import datetime, date
from typing import Dict, List, Tuple, Any, Optional
from django.core.exceptions import ValidationError
from django.db import transaction

from ..models import TemperatureProfile, TemperatureReading


class BulkDataImportService:
    """
    Service for importing bulk data from CSV files.
    
    Supports importing temperature profiles, FCR data, and mortality rates
    with comprehensive validation and error handling.
    """
    
    # CSV column headers
    TEMP_HEADERS = ['date', 'temperature']
    FCR_HEADERS = ['stage', 'fcr_value', 'duration_days']
    MORTALITY_HEADERS = ['date', 'rate']
    
    def __init__(self):
        """Initialize the bulk import service."""
        self.errors = []
        self.warnings = []
        self.preview_data = []
    
    def import_temperature_data(
        self, 
        csv_file: io.StringIO, 
        profile_name: str,
        validate_only: bool = False
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Import temperature data from CSV file.
        
        Args:
            csv_file: CSV file content as StringIO
            profile_name: Name for the temperature profile
            validate_only: If True, only validate without saving
            
        Returns:
            Tuple of (success, result_dict) where result_dict contains
            errors, warnings, preview_data, and created objects
        """
        self._reset_state()

        try:
            reader = csv.DictReader(csv_file)
            if not self._validate_headers(reader.fieldnames, self.TEMP_HEADERS):
                return False, self._get_result()

            temperature_data = self._collect_temperature_rows(reader)
            self._finalize_temperature_data(temperature_data)

            if validate_only or self.errors:
                return len(self.errors) == 0, self._get_result()

            created_objects = self._save_temperature_data(profile_name, temperature_data)
            return True, {**self._get_result(), 'created_objects': created_objects}

        except Exception as e:  # pragma: no cover - defensive outer guard
            self.errors.append(f"Import failed: {str(e)}")
            return False, self._get_result()
    
    def validate_csv_structure(
        self, 
        csv_file: io.StringIO, 
        expected_headers: List[str]
    ) -> Tuple[bool, List[str]]:
        """
        Validate CSV file structure.
        
        Args:
            csv_file: CSV file content
            expected_headers: Expected column headers
            
        Returns:
            Tuple of (is_valid, actual_headers)
        """
        try:
            reader = csv.reader(csv_file)
            headers = next(reader, None)
            
            if not headers:
                self.errors.append("CSV file is empty")
                return False, []
            
            # Normalize headers (lowercase, strip whitespace)
            headers = [h.lower().strip() for h in headers]
            expected = [h.lower() for h in expected_headers]
            
            if headers != expected:
                self.errors.append(
                    f"Invalid headers. Expected: {expected_headers}, "
                    f"Got: {headers}"
                )
                return False, headers
            
            return True, headers
            
        except Exception as e:
            self.errors.append(f"Failed to read CSV: {str(e)}")
            return False, []
    
    def generate_csv_template(self, data_type: str) -> str:
        """
        Generate a CSV template for the specified data type.
        
        Args:
            data_type: Type of data ('temperature', 'fcr', 'mortality')
            
        Returns:
            CSV template as string
        """
        templates = {
            'temperature': {
                'headers': self.TEMP_HEADERS,
                'sample_rows': [
                    ['2024-01-01', '8.5'],
                    ['2024-01-02', '8.7'],
                    ['2024-01-03', '8.6']
                ]
            },
            'fcr': {
                'headers': self.FCR_HEADERS,
                'sample_rows': [
                    ['Egg', '0', '50'],
                    ['Fry', '1.0', '90'],
                    ['Parr', '1.1', '90']
                ]
            },
            'mortality': {
                'headers': self.MORTALITY_HEADERS,
                'sample_rows': [
                    ['2024-01-01', '0.1'],
                    ['2024-01-08', '0.1'],
                    ['2024-01-15', '0.15']
                ]
            }
        }
        
        template_info = templates.get(data_type)
        if not template_info:
            raise ValueError(f"Unknown data type: {data_type}")
        
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(template_info['headers'])
        writer.writerows(template_info['sample_rows'])
        
        return output.getvalue()
    
    # Private helper methods
    def _validate_headers(
        self, 
        actual_headers: Optional[List[str]], 
        expected_headers: List[str]
    ) -> bool:
        """Validate CSV headers match expected format."""
        if not actual_headers:
            self.errors.append("No headers found in CSV file")
            return False
        
        # Normalize for comparison
        actual = [h.lower().strip() for h in actual_headers]
        expected = [h.lower() for h in expected_headers]
        
        if actual != expected:
            self.errors.append(
                f"Invalid headers. Expected: {expected_headers}, "
                f"Got: {actual_headers}"
            )
            return False
        
        return True

    def _reset_state(self) -> None:
        self.errors = []
        self.warnings = []
        self.preview_data = []

    def _collect_temperature_rows(self, reader: csv.DictReader) -> List[Dict[str, Any]]:
        temperature_data: List[Dict[str, Any]] = []
        row_num = 1
        for row in reader:
            row_num += 1
            parsed = self._parse_temperature_row(row, row_num)
            if parsed:
                temperature_data.append(parsed)
        return temperature_data

    def _parse_temperature_row(self, row: Dict[str, Any], row_num: int) -> Optional[Dict[str, Any]]:
        date_str = row.get('date', '').strip()
        reading_date = self._parse_date(date_str)
        if not reading_date:
            self.errors.append(f"Row {row_num}: Invalid date format")
            return None

        temp_str = row.get('temperature', '').strip()
        try:
            temperature = float(temp_str)
        except ValueError:
            self.errors.append(f"Row {row_num}: Invalid temperature value '{temp_str}'")
            return None

        if temperature < -50 or temperature > 50:
            self.warnings.append(f"Row {row_num}: Unusual temperature {temperature}°C")

        return {'date': reading_date, 'temperature': temperature}

    def _finalize_temperature_data(self, temperature_data: List[Dict[str, Any]]) -> None:
        dates = [entry['date'] for entry in temperature_data]
        if len(dates) != len(set(dates)):
            self.errors.append("Duplicate dates found in CSV")

        temperature_data.sort(key=lambda item: item['date'])
        self.preview_data = temperature_data[:10]
    
    def _parse_date(self, date_str: str) -> Optional[date]:
        """Parse date string in various formats."""
        if not date_str:
            return None
        
        # Try common date formats
        formats = [
            '%Y-%m-%d',
            '%d/%m/%Y',
            '%m/%d/%Y',
            '%Y/%m/%d',
            '%d-%m-%Y',
            '%m-%d-%Y'
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt).date()
            except ValueError:
                continue
        
        return None
    
    @transaction.atomic
    def _save_temperature_data(
        self, 
        profile_name: str, 
        temperature_data: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Save temperature data to database."""
        # Create or get profile
        profile, created = TemperatureProfile.objects.get_or_create(
            name=profile_name
        )
        
        if not created:
            # Delete existing readings if updating
            profile.readings.all().delete()
            self.warnings.append(
                f"Updated existing profile '{profile_name}' - old data replaced"
            )
        
        # Create temperature readings
        readings = []
        for data in temperature_data:
            reading = TemperatureReading(
                profile=profile,
                reading_date=data['date'],
                temperature=data['temperature']
            )
            readings.append(reading)
        
        # Bulk create for efficiency
        TemperatureReading.objects.bulk_create(readings)
        
        return {
            'profile': profile,
            'readings_count': len(readings),
            'date_range': {
                'start': temperature_data[0]['date'],
                'end': temperature_data[-1]['date']
            }
        }
    
    def _get_result(self) -> Dict[str, Any]:
        """Get standard result dictionary."""
        return {
            'errors': self.errors,
            'warnings': self.warnings,
            'preview_data': self.preview_data,
            'success': len(self.errors) == 0
        } 