"""
Custom migration operations for TimescaleDB hypertables.
"""
from django.db.migrations.operations.base import Operation


class CreateHypertable(Operation):
    """
    Custom migration operation to create a TimescaleDB hypertable from an existing table.
    
    This operation should be run after the table has been created and before any
    data is inserted.
    """
    
    reversible = False
    
    def __init__(self, table_name, time_column='created_at', chunk_time_interval=None, 
                 if_not_exists=True, partitioning_column=None, number_partitions=None):
        """
        Initialize the hypertable creation operation.
        
        Args:
            table_name (str): Name of the table to convert to a hypertable
            time_column (str): Name of the timestamp column to use for partitioning
            chunk_time_interval (str, optional): Chunk time interval (e.g., '1 day')
            if_not_exists (bool): Whether to use IF NOT EXISTS when creating
            partitioning_column (str, optional): Additional column for space partitioning
            number_partitions (int, optional): Number of partitions to use if space partitioning
        """
        self.table_name = table_name
        self.time_column = time_column
        self.chunk_time_interval = chunk_time_interval
        self.if_not_exists = if_not_exists
        self.partitioning_column = partitioning_column
        self.number_partitions = number_partitions
        
    def state_forwards(self, app_label, state):
        """
        No state changes needed since we're just converting an existing table.
        """
        pass
        
    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        """
        Execute the SQL to create the hypertable.
        """
        # Build the SQL command
        sql = f"SELECT create_hypertable('{app_label}_{self.table_name}', '{self.time_column}'"
        
        # Add options
        if self.chunk_time_interval:
            sql += f", chunk_time_interval => interval '{self.chunk_time_interval}'"
        
        if self.if_not_exists:
            sql += f", if_not_exists => TRUE"
            
        if self.partitioning_column and self.number_partitions:
            sql += f", partitioning_column => '{self.partitioning_column}', number_partitions => {self.number_partitions}"
            
        sql += ");"
        
        # Execute the SQL
        schema_editor.execute(sql)
        
    def database_backwards(self, app_label, schema_editor, from_state, to_state):
        """
        Converting a hypertable back to a regular table is not supported in TimescaleDB.
        The table would need to be dropped and recreated.
        """
        pass
        
    def describe(self):
        """
        Return a description of this operation.
        """
        return f"Create hypertable for {self.table_name} using time column {self.time_column}"
