from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from rest_framework.authtoken.models import Token
import sys


class Command(BaseCommand):
    help = 'Gets or creates CI test user token'

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
                }
            )

            if debug:
                self.stderr.write(f'User exists: {not created}')
                self.stderr.write(f'User id: {user.id}')

            # Reset password to ensure consistency
            user.set_password('testpass123')
            user.is_active = True
            user.save()

            # Get or create token
            token, token_created = Token.objects.get_or_create(user=user)

            if debug:
                self.stderr.write(f'Token created: {token_created}')
                self.stderr.write(f'Token key: {token.key}')

            # ------------------------------------------------------------------
            # Some edge cases (observed on CI) resulted in a Token row with an
            # *empty* key string. That breaks authentication because DRF expects
            # a 40-char key. Guard against that by recreating the token when
            # its key is falsy or empty.
            # ------------------------------------------------------------------
            if not token.key:
                if debug:
                    self.stderr.write('Empty token key detected – recreating token')
                token.delete()
                token = Token.objects.create(user=user)

            # Print token using print() for better CI compatibility
            # This ensures the output is properly captured in bash
            print(token.key, flush=True)
            
            # Also flush stdout to ensure output is captured
            sys.stdout.flush()

        except Exception as e:
            if debug:
                self.stderr.write(f'Error: {e}')
                import traceback
                traceback.print_exc(file=self.stderr)
            # Re-raise the exception to signal failure
            raise
