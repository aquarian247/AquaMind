#!/usr/bin/env python
"""
CI Test Token Generator Management Command

This Django management command creates a test user and generates an authentication token
for use in CI environments, particularly for Schemathesis API contract testing
that requires authenticated requests.

Usage:
    python manage.py get_ci_token [--settings=aquamind.settings_ci]

The command will print only the token key to stdout, allowing it to be captured in CI:
    TOKEN=$(python manage.py get_ci_token)
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from rest_framework.authtoken.models import Token
import sys
import traceback


class Command(BaseCommand):
    help = "Creates or gets a test user and returns its authentication token for CI testing"

    def add_arguments(self, parser):
        parser.add_argument(
            "--debug",
            action="store_true",
            help="Print diagnostic information to stderr if something goes wrong.",
        )

    def handle(self, *args, **options):
        debug: bool = options.get("debug", False)

        try:
            # CI test user credentials
            username = "schemathesis_ci"
            password = "testpass123"

            # Get or create the test user
            user, _ = User.objects.get_or_create(
                username=username,
                defaults={
                    "email": "ci@example.com",
                    "is_active": True,
                },
            )

            # Always reset password to ensure it's correct
            user.set_password(password)
            user.save()

            # Get or create token
            token, _ = Token.objects.get_or_create(user=user)

            # Print only the token key (for capture in CI)
            self.stdout.write(token.key, ending="")
            # Return normally so outer shells can capture stdout without the
            # process terminating prematurely via sys.exit().
            return

        except Exception as exc:  # pylint: disable=broad-except
            if debug:
                traceback.print_exc(file=sys.stderr)
            else:
                self.stderr.write(f"Error generating CI auth token: {exc}")
            # Ensure non-zero exit status so CI fails clearly
            sys.exit(1)
