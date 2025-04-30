# apps/health/migrations/0007_create_sampling_event_sequence.py
# Generated manually 2025-04-29

from django.db import migrations
from django.conf import settings


# SQL to create the sequence (PostgreSQL specific)
CREATE_SEQUENCE_SQL = """
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_sequences WHERE sequencename = 'sampling_event_id_seq') THEN
        CREATE SEQUENCE sampling_event_id_seq START 1 INCREMENT 1;
    END IF;
END $$;
"""

# SQL to drop the sequence (PostgreSQL specific)
DROP_SEQUENCE_SQL = """
DROP SEQUENCE IF EXISTS sampling_event_id_seq;
"""


class Migration(migrations.Migration):

    dependencies = [
        ('health', '0006_journalentry_sampling_event_id'),
    ]

    operations = [
        # Only run this operation if the database is PostgreSQL
        # This adheres to the rule of making migrations SQLite compatible for CI
        migrations.RunSQL(
            sql=CREATE_SEQUENCE_SQL,
            reverse_sql=DROP_SEQUENCE_SQL,
        ) if settings.DATABASES['default']['ENGINE'] == 'django.db.backends.postgresql' else migrations.RunSQL.noop,
    ]
