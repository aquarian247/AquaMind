import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from apps.users.models import Geography, Role, Subsidiary, UserProfile


class Command(BaseCommand):
    help = (
        "Create or update an admin user from CLI args "
        "or environment variables."
    )

    def add_arguments(self, parser):
        parser.add_argument("--username", help="Admin username")
        parser.add_argument("--email", help="Admin email")
        parser.add_argument("--password", help="Admin password")

    @staticmethod
    def _resolve_value(options, option_name, env_name):
        return options.get(option_name) or os.environ.get(env_name)

    @staticmethod
    def _update_user(user, email):
        updated = False
        desired_values = {
            "email": email,
            "is_staff": True,
            "is_superuser": True,
            "is_active": True,
        }
        for field, expected in desired_values.items():
            if getattr(user, field) != expected:
                setattr(user, field, expected)
                updated = True
        return updated

    @staticmethod
    def _update_profile(profile):
        updated = False
        desired_values = {
            "role": Role.ADMIN,
            "geography": Geography.ALL,
            "subsidiary": Subsidiary.ALL,
        }
        for field, expected in desired_values.items():
            if getattr(profile, field) != expected:
                setattr(profile, field, expected)
                updated = True
        return updated

    def handle(self, *args, **options):
        username = self._resolve_value(
            options, "username", "DJANGO_SUPERUSER_USERNAME"
        )
        email = self._resolve_value(
            options, "email", "DJANGO_SUPERUSER_EMAIL"
        )
        password = self._resolve_value(
            options, "password", "DJANGO_SUPERUSER_PASSWORD"
        )

        missing = [
            name
            for name, value in (
                ("DJANGO_SUPERUSER_USERNAME", username),
                ("DJANGO_SUPERUSER_EMAIL", email),
                ("DJANGO_SUPERUSER_PASSWORD", password),
            )
            if not value
        ]
        if missing:
            raise CommandError(
                f"Missing admin bootstrap value(s): {', '.join(missing)}"
            )

        User = get_user_model()
        user, created = User.objects.get_or_create(
            username=username,
            defaults={
                "email": email,
                "is_staff": True,
                "is_superuser": True,
                "is_active": True,
            },
        )

        updated = self._update_user(user, email)

        user.set_password(password)
        user.save()

        profile, _ = UserProfile.objects.get_or_create(user=user)
        updated = self._update_profile(profile) or updated
        profile.save()

        verb = "Created" if created else "Updated"
        state = (
            "with profile updates" if updated else "without profile changes"
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"{verb} admin user '{username}' {state}."
            )
        )
