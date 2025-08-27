"""
Management command to set Schemathesis execution mode.

This command is used by CI workflows to explicitly mark when Schemathesis
is running, ensuring reliable separation between unit tests and contract testing.

Usage:
    python manage.py set_schemathesis_mode

This sets the SCHEMATHESIS_MODE environment variable and marks the current
thread context as running Schemathesis, ensuring proper authentication behavior.
"""

import os
import sys
from django.core.management.base import BaseCommand
from aquamind.utils.auth_isolation import schemathesis_context


class Command(BaseCommand):
    help = 'Set Schemathesis execution mode for reliable CI/CD authentication isolation'

    def add_arguments(self, parser):
        parser.add_argument(
            '--mode',
            choices=['on', 'off'],
            default='on',
            help='Set schemathesis mode on or off (default: on)'
        )

    def handle(self, *args, **options):
        mode = options['mode']

        if mode == 'on':
            # Set environment variable for process-wide visibility
            os.environ['SCHEMATHESIS_MODE'] = '1'

            # Set thread-local context
            with schemathesis_context():
                self.stdout.write(
                    self.style.SUCCESS(
                        '🔑 Schemathesis mode enabled - mock authentication will be provided'
                    )
                )

                # Keep the context alive until interrupted or command finishes
                try:
                    # If there are additional commands to run, execute them here
                    # For now, just keep the context alive
                    import time
                    self.stdout.write('Schemathesis mode active. Press Ctrl+C to exit.')
                    while True:
                        time.sleep(1)
                except KeyboardInterrupt:
                    self.stdout.write(
                        self.style.SUCCESS('Schemathesis mode disabled')
                    )

        else:  # mode == 'off'
            # Clear environment variable
            os.environ.pop('SCHEMATHESIS_MODE', None)

            self.stdout.write(
                self.style.SUCCESS(
                    '🔍 Schemathesis mode disabled - normal authentication will be used'
                )
            )
