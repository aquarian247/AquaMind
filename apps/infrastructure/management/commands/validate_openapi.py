import os
import sys
import yaml
import tempfile
import subprocess
from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from django.core.management import call_command
from django.conf import settings
from drf_spectacular.settings import spectacular_settings
from drf_spectacular.validation import validate_schema


class Command(BaseCommand):
    help = 'Validates the OpenAPI specification is complete and properly configured'

    def add_arguments(self, parser):
        parser.add_argument(
            '--check',
            action='store_true',
            help='Run in non-interactive CI mode (exit with error code on failure)',
        )
        parser.add_argument(
            '--output',
            type=str,
            help='Path to save the generated OpenAPI spec for inspection',
        )
        parser.add_argument(
            '--schemathesis',
            action='store_true',
            help='Run schemathesis validation against the spec',
        )
        parser.add_argument(
            '--fix',
            action='store_true',
            help='Automatically fix issues by regenerating the spec',
        )

    def handle(self, *args, **options):
        self.check_mode = options['check']
        self.fix_mode = options['fix']
        # Use the settings module already configured via DJANGO_SETTINGS_MODULE
        # (falls back to the project default if the env var is missing).
        self.settings_module = os.getenv('DJANGO_SETTINGS_MODULE', 'aquamind.settings')
        self.run_schemathesis = options['schemathesis']
        
        # Set up colors for terminal output
        self.style.SUCCESS = self.style.SUCCESS
        self.style.ERROR = self.style.ERROR
        self.style.WARNING = self.style.WARNING
        self.style.NOTICE = self.style.NOTICE
        
        # Track validation status
        self.errors = []
        self.warnings = []
        
        # Generate fresh spec for validation
        self.stdout.write(self.style.NOTICE("Generating fresh OpenAPI specification..."))
        spec_file, spec_data = self.generate_spec()
        
        # Save output if requested
        if options['output']:
            output_path = Path(options['output'])
            with open(output_path, 'w') as f:
                yaml.dump(spec_data, f)
            self.stdout.write(self.style.SUCCESS(f"Saved OpenAPI spec to {output_path}"))
        
        # Run validations
        self.validate_schema_format(spec_data)
        self.validate_hooks_configured()
        self.validate_response_codes(spec_data)
        self.validate_sync_with_committed_spec(spec_file)
        
        if self.run_schemathesis:
            self.run_schemathesis_validation(spec_file)
        
        # Report results
        self.report_results()
        
        # Clean up temporary file
        if os.path.exists(spec_file):
            os.unlink(spec_file)
        
        # Exit with error code if issues found in check mode
        if self.check_mode and (self.errors or self.warnings):
            sys.exit(1)
    
    def generate_spec(self):
        """Generate a fresh OpenAPI spec and return the file path and loaded data."""
        temp_file = tempfile.NamedTemporaryFile(suffix='.yaml', delete=False)
        temp_file.close()
        
        try:
            call_command('spectacular', '--file', temp_file.name, '--settings', self.settings_module)
            
            with open(temp_file.name, 'r') as f:
                spec_data = yaml.safe_load(f)
            
            return temp_file.name, spec_data
        except Exception as e:
            self.errors.append(f"Failed to generate OpenAPI spec: {str(e)}")
            sys.exit(1)
    
    def validate_schema_format(self, spec_data):
        """Validate the schema format using drf-spectacular's validator."""
        self.stdout.write(self.style.NOTICE("Validating schema format..."))
        try:
            validate_schema(spec_data)
            self.stdout.write(self.style.SUCCESS("✓ Schema format is valid"))
        except Exception as e:
            self.errors.append(f"Schema validation failed: {str(e)}")
            self.stdout.write(self.style.ERROR(f"✗ Schema validation failed: {str(e)}"))
    
    def validate_hooks_configured(self):
        """Validate that all required hooks are configured."""
        self.stdout.write(self.style.NOTICE("Validating hook configuration..."))
        
        required_hooks = [
            'ensure_global_security',
            'add_standard_responses',
            'fix_action_response_types',
            'cleanup_duplicate_security',
            'add_validation_error_responses',
            'clamp_integer_schema_bounds'
        ]
        
        hooks = spectacular_settings.POSTPROCESSING_HOOKS
        hook_names = [h.__name__ if callable(h) else h.split('.')[-1] for h in hooks]
        
        missing_hooks = [hook for hook in required_hooks if hook not in hook_names]
        
        if missing_hooks:
            self.errors.append(f"Missing required hooks: {', '.join(missing_hooks)}")
            self.stdout.write(self.style.ERROR(f"✗ Missing required hooks: {', '.join(missing_hooks)}"))
        else:
            self.stdout.write(self.style.SUCCESS("✓ All required hooks are configured"))
    
    def validate_response_codes(self, spec_data):
        """Validate that all endpoints have proper response codes."""
        self.stdout.write(self.style.NOTICE("Validating response codes..."))
        
        missing_responses = []
        
        for path, path_item in spec_data.get('paths', {}).items():
            for method, operation in path_item.items():
                if method not in ['get', 'post', 'put', 'patch', 'delete']:
                    continue
                
                responses = operation.get('responses', {})
                
                # Check for 200 response
                if '200' not in responses:
                    missing_responses.append(f"Missing 200 response for {method.upper()} {path}")
                
                # Non-GET methods should have validation error responses
                if method != 'get' and '400' not in responses:
                    missing_responses.append(f"Missing 400 response for {method.upper()} {path}")
                
                # All authenticated endpoints should have auth error responses
                if not path.startswith('/api/v1/schema'):
                    if '401' not in responses:
                        missing_responses.append(f"Missing 401 response for {method.upper()} {path}")
                    
                    # Auth endpoints don't require 403 response
                    if not path.startswith('/api/v1/auth/') and '403' not in responses:
                        missing_responses.append(f"Missing 403 response for {method.upper()} {path}")
                
                # All endpoints should have server error response
                if '500' not in responses:
                    missing_responses.append(f"Missing 500 response for {method.upper()} {path}")
                
                # Detail endpoints should have not found response
                if ('{id}' in path or '{pk}' in path) and '404' not in responses:
                    missing_responses.append(f"Missing 404 response for {method.upper()} {path}")
        
        if missing_responses:
            # Limit to first 10 issues to avoid overwhelming output
            display_issues = missing_responses[:10]
            if len(missing_responses) > 10:
                display_issues.append(f"... and {len(missing_responses) - 10} more issues")
            
            self.errors.append(f"Found {len(missing_responses)} missing response codes")
            self.stdout.write(self.style.ERROR(f"✗ Found {len(missing_responses)} missing response codes:"))
            for issue in display_issues:
                self.stdout.write(self.style.ERROR(f"  - {issue}"))
        else:
            self.stdout.write(self.style.SUCCESS("✓ All endpoints have proper response codes"))
    
    def validate_sync_with_committed_spec(self, temp_spec_file):
        """Validate that the generated spec matches the committed one."""
        self.stdout.write(self.style.NOTICE("Checking if spec is in sync with code..."))
        
        committed_spec_path = 'api/openapi.yaml'
        
        if not os.path.exists(committed_spec_path):
            self.warnings.append(f"Committed spec not found at {committed_spec_path}")
            self.stdout.write(self.style.WARNING(f"! Committed spec not found at {committed_spec_path}"))
            return
        
        try:
            result = subprocess.run(
                ['diff', '-u', committed_spec_path, temp_spec_file],
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                diff_lines = result.stdout.count('\n')
                self.errors.append("OpenAPI spec is out of sync with code")
                self.stdout.write(self.style.ERROR(f"✗ OpenAPI spec is out of sync with code ({diff_lines} lines differ)"))
                
                # Show a sample of the diff
                diff_sample = '\n'.join(result.stdout.split('\n')[:20])
                if len(result.stdout.split('\n')) > 20:
                    diff_sample += "\n... (more differences omitted)"
                
                self.stdout.write(self.style.ERROR("Diff sample:"))
                self.stdout.write(diff_sample)
                
                if self.fix_mode:
                    self.fix_spec_sync()
            else:
                self.stdout.write(self.style.SUCCESS("✓ OpenAPI spec is in sync with code"))
        except Exception as e:
            self.warnings.append(f"Failed to check spec sync: {str(e)}")
            self.stdout.write(self.style.WARNING(f"! Failed to check spec sync: {str(e)}"))
    
    def fix_spec_sync(self):
        """Fix the spec sync by regenerating and updating the committed spec."""
        self.stdout.write(self.style.NOTICE("Fixing OpenAPI spec..."))
        
        try:
            call_command('spectacular', '--file', 'api/openapi.yaml', '--settings', self.settings_module)
            self.stdout.write(self.style.SUCCESS("✓ OpenAPI spec has been regenerated"))
            
            # If in check mode, still report this as an error
            if self.check_mode:
                self.stdout.write(self.style.WARNING(
                    "! Spec was fixed, but this is still an error in check mode"
                ))
        except Exception as e:
            self.errors.append(f"Failed to fix spec: {str(e)}")
            self.stdout.write(self.style.ERROR(f"✗ Failed to fix spec: {str(e)}"))
    
    def run_schemathesis_validation(self, spec_file):
        """Run schemathesis validation against the spec."""
        self.stdout.write(self.style.NOTICE("Running schemathesis validation..."))
        
        try:
            # Check if schemathesis is installed
            result = subprocess.run(
                ['schemathesis', '--version'],
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                self.warnings.append("Schemathesis not installed, skipping validation")
                self.stdout.write(self.style.WARNING("! Schemathesis not installed, skipping validation"))
                return
            
            # Run schemathesis validation
            self.stdout.write("Running schemathesis checks (this may take a while)...")
            
            # Set up environment for hooks
            env = os.environ.copy()
            env['SCHEMATHESIS_HOOKS'] = 'aquamind.utils.schemathesis_hooks'
            
            # Get auth token if available
            try:
                token_result = subprocess.run(
                    ['python', 'manage.py', 'get_ci_token', '--settings', self.settings_module],
                    capture_output=True,
                    text=True
                )
                if token_result.returncode == 0:
                    token = token_result.stdout.strip()
                    if token:
                        env['SCHEMATHESIS_AUTH_TOKEN'] = token
                        self.stdout.write("Using CI auth token for validation")
            except Exception:
                pass
            
            # Run validation
            result = subprocess.run(
                [
                    'schemathesis', 'run',
                    '--checks', 'all',
                    '--hypothesis-max-examples', '5',
                    '--hypothesis-suppress-health-check=filter_too_much,data_too_large',
                    '--hypothesis-derandomize',
                    spec_file
                ],
                capture_output=True,
                text=True,
                env=env
            )
            
            if result.returncode != 0:
                self.errors.append("Schemathesis validation failed")
                self.stdout.write(self.style.ERROR("✗ Schemathesis validation failed"))
                self.stdout.write(self.style.ERROR(result.stdout[:1000] + "..." if len(result.stdout) > 1000 else result.stdout))
            else:
                self.stdout.write(self.style.SUCCESS("✓ Schemathesis validation passed"))
        except Exception as e:
            self.warnings.append(f"Failed to run schemathesis: {str(e)}")
            self.stdout.write(self.style.WARNING(f"! Failed to run schemathesis: {str(e)}"))
    
    def report_results(self):
        """Report the final validation results."""
        self.stdout.write("\n" + "=" * 80)
        self.stdout.write(self.style.NOTICE("OpenAPI Validation Results"))
        self.stdout.write("=" * 80)
        
        if not self.errors and not self.warnings:
            self.stdout.write(self.style.SUCCESS("\n✓ All validations passed! OpenAPI spec is complete and properly configured."))
        else:
            if self.errors:
                self.stdout.write(self.style.ERROR(f"\n✗ Found {len(self.errors)} errors:"))
                for i, error in enumerate(self.errors, 1):
                    self.stdout.write(self.style.ERROR(f"  {i}. {error}"))
            
            if self.warnings:
                self.stdout.write(self.style.WARNING(f"\n! Found {len(self.warnings)} warnings:"))
                for i, warning in enumerate(self.warnings, 1):
                    self.stdout.write(self.style.WARNING(f"  {i}. {warning}"))
            
            self.stdout.write("\nRecommended actions:")
            if self.fix_mode:
                self.stdout.write("- Review the fixed spec and commit the changes")
            else:
                self.stdout.write("- Run with --fix to automatically regenerate the spec")
                self.stdout.write("- Or manually run: python manage.py spectacular --file api/openapi.yaml")
            
            self.stdout.write("- Ensure all required hooks are configured in settings")
            self.stdout.write("- Check that all endpoints have proper response documentation")
        
        self.stdout.write("\n" + "=" * 80 + "\n")
