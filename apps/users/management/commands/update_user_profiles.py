from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from apps.users.models import UserProfile, Geography, Subsidiary, Role


class Command(BaseCommand):
    help = 'Update existing user profiles with RBAC fields'

    def add_arguments(self, parser):
        parser.add_argument(
            '--role',
            type=str,
            choices=['ADMIN', 'MGR', 'OPR', 'VET', 'QA', 'FIN', 'VIEW'],
            default='ADMIN',
            help='Role to assign to users (default: ADMIN)',
        )
        parser.add_argument(
            '--geography',
            type=str,
            choices=['FO', 'SC', 'ALL'],
            default='ALL',
            help='Geography to assign to users (default: ALL)',
        )
        parser.add_argument(
            '--subsidiary',
            type=str,
            choices=['BS', 'FW', 'FM', 'LG', 'ALL'],
            default='ALL',
            help='Subsidiary to assign to users (default: ALL)',
        )
        parser.add_argument(
            '--username',
            type=str,
            help='Update only specific username',
        )

    def handle(self, *args, **options):
        # Get role choices
        role_choices = {
            'ADMIN': Role.ADMIN,
            'MGR': Role.MANAGER,
            'OPR': Role.OPERATOR,
            'VET': Role.VETERINARIAN,
            'QA': Role.QA,
            'FIN': Role.FINANCE,
            'VIEW': Role.VIEWER,
        }

        geography_choices = {
            'FO': Geography.FAROE_ISLANDS,
            'SC': Geography.SCOTLAND,
            'ALL': Geography.ALL,
        }

        subsidiary_choices = {
            'BS': Subsidiary.BROODSTOCK,
            'FW': Subsidiary.FRESHWATER,
            'FM': Subsidiary.FARMING,
            'LG': Subsidiary.LOGISTICS,
            'ALL': Subsidiary.ALL,
        }

        role = role_choices[options['role']]
        geography = geography_choices[options['geography']]
        subsidiary = subsidiary_choices[options['subsidiary']]

        # Get users to update
        if options['username']:
            users = User.objects.filter(username=options['username'])
            if not users.exists():
                self.stderr.write(f"User '{options['username']}' not found")
                return
        else:
            users = User.objects.all()

        updated_count = 0
        for user in users:
            # Create profile if it doesn't exist
            profile, created = UserProfile.objects.get_or_create(
                user=user,
                defaults={
                    'role': role,
                    'geography': geography,
                    'subsidiary': subsidiary,
                }
            )

            # Update existing profile
            if not created:
                profile.role = role
                profile.geography = geography
                profile.subsidiary = subsidiary
                profile.save()

            self.stdout.write(
                f"{'Created' if created else 'Updated'} profile for user '{user.username}': "
                f"role={profile.role}, geography={profile.geography}, subsidiary={profile.subsidiary}"
            )
            updated_count += 1

        self.stdout.write(
            self.style.SUCCESS(f"Successfully updated {updated_count} user profile(s)")
        )






