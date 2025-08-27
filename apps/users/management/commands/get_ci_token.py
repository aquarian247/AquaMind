from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from rest_framework_simplejwt.tokens import RefreshToken
import sys
import json


class Command(BaseCommand):
    help = 'Gets or creates CI test JWT tokens'

    def add_arguments(self, parser):
        parser.add_argument(
            '--debug',
            action='store_true',
            help='Enable debug output to stderr'
        )

    def handle(self, *args, **options):
        debug = options.get('debug', False)

        try:
            # Get or create user (matches the migration)
            user, created = User.objects.get_or_create(
                username='schemathesis_ci',
                defaults={
                    'email': 'ci@example.com',
                    'is_active': True,
                    # Give the CI account blanket permissions so that
                    # Schemathesis can hit *any* endpoint without running
                    # into object-level permission checks.
                    'is_staff': True,
                    'is_superuser': True,
                }
            )

            if debug:
                self.stderr.write(f'User exists: {not created}')
                self.stderr.write(f'User id: {user.id}')

            # Reset password to ensure consistency
            user.set_password('testpass123')
            user.is_active = True
            # Ensure the flag fields are set even if the user pre-existed
            user.is_staff = True
            user.is_superuser = True
            user.save()

            # Generate JWT refresh token
            refresh = RefreshToken.for_user(user)
            access_token = str(refresh.access_token)
            refresh_token = str(refresh)

            if debug:
                self.stderr.write(f'JWT Access token length: {len(access_token)}')
                self.stderr.write(f'JWT Refresh token length: {len(refresh_token)}')

            # Output both tokens as JSON for the CI environment
            tokens = {
                'access': access_token,
                'refresh': refresh_token
            }

            # Print tokens as JSON for better CI compatibility
            print(json.dumps(tokens), flush=True)

            # Also flush stdout to ensure output is captured
            sys.stdout.flush()

        except Exception as e:
            if debug:
                self.stderr.write(f'Error: {e}')
                import traceback
                traceback.print_exc(file=self.stderr)
            # Re-raise the exception to signal failure
            raise
