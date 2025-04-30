"""
Utility module for generating sequence-based IDs for sampling events.
"""

from django.db import connection

def generate_sampling_event_id():
    """
    Generates a unique sequence-based ID for sampling events.
    
    Returns:
        int: A unique BigInteger ID for the sampling event.
    """
    with connection.cursor() as cursor:
        # Check if the sequence exists, if not create it
        cursor.execute("""
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT FROM pg_class 
                    WHERE relname = 'sampling_event_id_seq' 
                    AND relkind = 'S'
                ) THEN
                    CREATE SEQUENCE sampling_event_id_seq 
                    START WITH 1000 
                    INCREMENT BY 1 
                    NO MINVALUE 
                    NO MAXVALUE 
                    CACHE 1;
                END IF;
            END
            $$;
        """)
        # Get the next value from the sequence
        cursor.execute("SELECT nextval('sampling_event_id_seq')")
        return cursor.fetchone()[0]
