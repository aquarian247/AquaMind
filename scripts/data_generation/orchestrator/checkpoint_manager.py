"""
Checkpoint Manager for Data Generation

Handles state persistence and recovery for long-running data generation processes.
"""

import json
import os
from datetime import datetime, date, timedelta
from typing import Dict, Any, Optional
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class DateTimeEncoder(json.JSONEncoder):
    """Custom JSON encoder for datetime objects"""
    def default(self, obj):
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        if isinstance(obj, timedelta):
            return obj.total_seconds()
        return super().default(obj)


class CheckpointManager:
    """
    Manages checkpoints for data generation sessions.
    
    Enables resuming from failure points and tracking progress across
    multiple execution sessions.
    """
    
    def __init__(self, checkpoint_dir: str = None):
        """
        Initialize checkpoint manager.
        
        Args:
            checkpoint_dir: Directory to store checkpoint files.
                          Defaults to scripts/data_generation/checkpoints/
        """
        if checkpoint_dir is None:
            checkpoint_dir = os.path.join(
                os.path.dirname(os.path.dirname(__file__)), 
                'checkpoints'
            )
        
        self.checkpoint_dir = Path(checkpoint_dir)
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        
        self.main_checkpoint_file = self.checkpoint_dir / 'main_checkpoint.json'
        self.session_checkpoints = {}
        
        # Load existing checkpoint if available
        self.load_main_checkpoint()
    
    def load_main_checkpoint(self) -> Dict[str, Any]:
        """Load the main checkpoint file."""
        if self.main_checkpoint_file.exists():
            try:
                with open(self.main_checkpoint_file, 'r') as f:
                    data = json.load(f)
                    logger.info(f"Loaded main checkpoint from {self.main_checkpoint_file}")
                    return data
            except Exception as e:
                logger.error(f"Error loading checkpoint: {e}")
                return self._create_empty_checkpoint()
        else:
            return self._create_empty_checkpoint()
    
    def _create_empty_checkpoint(self) -> Dict[str, Any]:
        """Create an empty checkpoint structure."""
        return {
            'created_at': datetime.now().isoformat(),
            'last_updated': datetime.now().isoformat(),
            'sessions': {
                'session_1': {'status': 'not_started', 'progress': {}},
                'session_2': {'status': 'not_started', 'progress': {}},
                'session_3': {'status': 'not_started', 'progress': {}},
                'session_4': {'status': 'not_started', 'progress': {}}
            },
            'global_state': {
                'total_batches_created': 0,
                'total_records_generated': 0,
                'current_active_batches': [],
                'last_processed_date': None
            },
            'statistics': {
                'total_runtime_seconds': 0,
                'peak_memory_mb': 0,
                'errors_encountered': []
            }
        }
    
    def save_checkpoint(self, session_id: str, checkpoint_data: Dict[str, Any]):
        """
        Save checkpoint for a specific session.
        
        Args:
            session_id: Identifier for the session (e.g., 'session_1')
            checkpoint_data: Data to checkpoint
        """
        # Load current main checkpoint
        main_checkpoint = self.load_main_checkpoint()
        
        # Update session-specific data
        if session_id:
            main_checkpoint['sessions'][session_id].update(checkpoint_data)
            
            # Save session-specific checkpoint
            session_file = self.checkpoint_dir / f'{session_id}_checkpoint.json'
            with open(session_file, 'w') as f:
                json.dump(checkpoint_data, f, indent=2, cls=DateTimeEncoder)
                logger.debug(f"Saved session checkpoint to {session_file}")
        
        # Update global state
        main_checkpoint['last_updated'] = datetime.now().isoformat()
        
        # Save main checkpoint
        with open(self.main_checkpoint_file, 'w') as f:
            json.dump(main_checkpoint, f, indent=2, cls=DateTimeEncoder)
            logger.info(f"Saved main checkpoint to {self.main_checkpoint_file}")
    
    def get_session_checkpoint(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get checkpoint data for a specific session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Checkpoint data if exists, None otherwise
        """
        session_file = self.checkpoint_dir / f'{session_id}_checkpoint.json'
        if session_file.exists():
            try:
                with open(session_file, 'r') as f:
                    data = json.load(f)
                    
                    # Convert ISO format strings back to datetime objects
                    if 'last_processed_date' in data and data['last_processed_date']:
                        data['last_processed_date'] = datetime.fromisoformat(
                            data['last_processed_date']
                        ).date()
                    
                    return data
            except Exception as e:
                logger.error(f"Error loading session checkpoint: {e}")
                return None
        return None
    
    def mark_session_complete(self, session_id: str, statistics: Dict[str, Any]):
        """
        Mark a session as complete and save statistics.
        
        Args:
            session_id: Session identifier
            statistics: Session execution statistics
        """
        checkpoint_data = {
            'status': 'completed',
            'completed_at': datetime.now().isoformat(),
            'statistics': statistics,
            'progress': {'percent': 100}
        }
        
        self.save_checkpoint(session_id, checkpoint_data)
        logger.info(f"Session {session_id} marked as complete")
    
    def get_resume_point(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the resume point for a partially completed session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Resume point data including date and batch states
        """
        checkpoint = self.get_session_checkpoint(session_id)
        if checkpoint and checkpoint.get('status') == 'in_progress':
            return {
                'last_date': checkpoint.get('last_processed_date'),
                'active_batches': checkpoint.get('active_batches', []),
                'completed_steps': checkpoint.get('completed_steps', []),
                'partial_data': checkpoint.get('partial_data', {})
            }
        return None
    
    def clear_session_checkpoint(self, session_id: str):
        """
        Clear checkpoint for a specific session.
        
        Args:
            session_id: Session identifier
        """
        session_file = self.checkpoint_dir / f'{session_id}_checkpoint.json'
        if session_file.exists():
            session_file.unlink()
            logger.info(f"Cleared checkpoint for {session_id}")
        
        # Update main checkpoint
        main_checkpoint = self.load_main_checkpoint()
        main_checkpoint['sessions'][session_id] = {
            'status': 'not_started',
            'progress': {}
        }
        
        with open(self.main_checkpoint_file, 'w') as f:
            json.dump(main_checkpoint, f, indent=2, cls=DateTimeEncoder)
    
    def clear_all_checkpoints(self):
        """Clear all checkpoint files."""
        for checkpoint_file in self.checkpoint_dir.glob('*.json'):
            checkpoint_file.unlink()
        
        # Recreate empty main checkpoint
        empty_checkpoint = self._create_empty_checkpoint()
        with open(self.main_checkpoint_file, 'w') as f:
            json.dump(empty_checkpoint, f, indent=2, cls=DateTimeEncoder)
        
        logger.info("Cleared all checkpoints")
    
    def get_global_state(self) -> Dict[str, Any]:
        """Get global state across all sessions."""
        main_checkpoint = self.load_main_checkpoint()
        return main_checkpoint.get('global_state', {})
    
    def update_global_state(self, updates: Dict[str, Any]):
        """
        Update global state values.
        
        Args:
            updates: Dictionary of state updates
        """
        main_checkpoint = self.load_main_checkpoint()
        main_checkpoint['global_state'].update(updates)
        
        with open(self.main_checkpoint_file, 'w') as f:
            json.dump(main_checkpoint, f, indent=2, cls=DateTimeEncoder)
    
    def log_error(self, session_id: str, error_message: str):
        """
        Log an error to the checkpoint.
        
        Args:
            session_id: Session where error occurred
            error_message: Error description
        """
        main_checkpoint = self.load_main_checkpoint()
        
        error_entry = {
            'session_id': session_id,
            'timestamp': datetime.now().isoformat(),
            'message': error_message
        }
        
        if 'errors_encountered' not in main_checkpoint['statistics']:
            main_checkpoint['statistics']['errors_encountered'] = []
        
        main_checkpoint['statistics']['errors_encountered'].append(error_entry)
        
        with open(self.main_checkpoint_file, 'w') as f:
            json.dump(main_checkpoint, f, indent=2, cls=DateTimeEncoder)

