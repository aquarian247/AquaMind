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


class Command(BaseCommand):
    help = "Creates or gets a test user and returns its authentication token for CI testing"

    def add_arguments(self, parser):
        # No additional arguments needed
        pass

    def handle(self, *args, **options):
        # CI test user credentials
        username = "schemathesis_ci"
        password = "testpass123"
        
        # Get or create the test user
        user, created = User.objects.get_or_create(
            username=username,
            defaults={
                "email": "ci@example.com",
                "is_active": True
            }
        )
        
        # Always reset password to ensure it's correct
        user.set_password(password)
        user.save()
        
        # Get or create token
        token, _ = Token.objects.get_or_create(user=user)
        
        # Print only the token key (for capture in CI)
        # No additional text/formatting to make it easy to capture in shell
        self.stdout.write(token.key, ending='')
