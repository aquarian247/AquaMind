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


def conditionally_create_or_drop_sequence(apps, schema_editor, forward=True):
    if schema_editor.connection.vendor == 'postgresql':
        if forward:
            schema_editor.execute(CREATE_SEQUENCE_SQL)
        else:
            schema_editor.execute(DROP_SEQUENCE_SQL)
    # If not postgresql, do nothing (noop)


class Migration(migrations.Migration):

    dependencies = [
        ('health', '0006_journalentry_sampling_event_id'),
    ]

    operations = [
        migrations.RunPython(
            lambda apps, schema_editor: conditionally_create_or_drop_sequence(apps, schema_editor, forward=True),
            lambda apps, schema_editor: conditionally_create_or_drop_sequence(apps, schema_editor, forward=False),
        ),
    ]
