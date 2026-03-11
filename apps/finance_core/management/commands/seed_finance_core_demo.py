"""Seed finance-core demo data for the feature dev environment."""

from django.core.management.base import BaseCommand, CommandError

from apps.finance_core.services.demo_seed import seed_finance_core_demo


class Command(BaseCommand):
    help = (
        "Seed an idempotent finance-core demo slice for the feature dev "
        "environment. Refuses migration-preview style databases unless forced."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--prefix",
            type=str,
            default="FC-DEMO",
            help="Prefix used for demo data labels (default: FC-DEMO).",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Allow seeding even when the database name looks like a migration-preview environment.",
        )

    def handle(self, *args, **options):
        try:
            result = seed_finance_core_demo(
                prefix=options["prefix"],
                force=options["force"],
            )
        except CommandError:
            raise
        except Exception as exc:  # pragma: no cover - command wrapper
            raise CommandError(f"Failed to seed finance-core demo data: {exc}") from exc

        self.stdout.write(self.style.SUCCESS("Finance-core demo data seeded successfully."))
        for key, value in result.items():
            self.stdout.write(f"- {key}: {value}")
