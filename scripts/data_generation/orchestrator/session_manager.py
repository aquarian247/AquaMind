"""
Session Manager for Data Generation

Main orchestrator for multi-session data generation with 10 years of aquaculture data.
"""

import os
import sys
import logging
from datetime import datetime, date, timedelta
from typing import Dict, Any, Optional, List
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

# Django setup
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'aquamind.settings')
import django
django.setup()

from .checkpoint_manager import CheckpointManager
from .memory_manager import MemoryManager
from .progress_tracker import ProgressTracker

logger = logging.getLogger(__name__)


class DataGenerationSessionManager:
    """
    Manages multi-session data generation for 10 years of aquaculture data.
    
    Coordinates between different sessions, manages checkpoints, monitors memory,
    and tracks progress across the entire data generation process.
    """
    
    # Session configuration
    SESSIONS = {
        'session_1': {
            'name': 'Infrastructure & Historical Setup',
            'years': (1, 3),
            'start_date': date(2015, 1, 1),
            'end_date': date(2017, 12, 31),
            'focus': [
                'infrastructure_setup',
                'initial_batches',
                'environmental_baseline',
                'early_operations'
            ]
        },
        'session_2': {
            'name': 'Early Production Cycles',
            'years': (4, 6),
            'start_date': date(2018, 1, 1),
            'end_date': date(2020, 12, 31),
            'focus': [
                'batch_staggering',
                'disease_events',
                'feed_management',
                'health_monitoring'
            ]
        },
        'session_3': {
            'name': 'Mature Operations',
            'years': (7, 9),
            'start_date': date(2021, 1, 1),
            'end_date': date(2023, 12, 31),
            'focus': [
                'steady_state_operations',
                'advanced_health_management',
                'performance_optimization',
                'environmental_adaptation'
            ]
        },
        'session_4': {
            'name': 'Recent History & Validation',
            'years': (10, 10),
            'start_date': date(2024, 1, 1),
            'end_date': date(2024, 12, 31),
            'focus': [
                'current_operations',
                'data_validation',
                'statistical_validation',
                'summary_generation'
            ]
        }
    }
    
    def __init__(self, 
                 checkpoint_dir: str = None,
                 max_memory_percent: float = 75.0,
                 dry_run: bool = False):
        """
        Initialize session manager.
        
        Args:
            checkpoint_dir: Directory for checkpoints
            max_memory_percent: Maximum memory usage before cleanup
            dry_run: If True, simulate without creating data
        """
        self.dry_run = dry_run
        
        # Initialize managers
        self.checkpoint_manager = CheckpointManager(checkpoint_dir)
        self.memory_manager = MemoryManager(max_memory_percent=max_memory_percent)
        self.progress_tracker = ProgressTracker()
        
        # Session state
        self.current_session = None
        self.session_generators = {}
        
        # Load generators dynamically
        self._load_generators()
        
        # Configure logging
        self._setup_logging()
    
    def _setup_logging(self):
        """Configure logging for data generation."""
        log_dir = Path(__file__).parent.parent / 'logs'
        log_dir.mkdir(exist_ok=True)
        
        # Create file handler
        log_file = log_dir / f"data_generation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)
        
        # Create console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        # Add handlers to logger
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        
        logger.info(f"Logging initialized. Log file: {log_file}")
    
    def _load_generators(self):
        """Load session-specific generators."""
        try:
            # Import generators when they're implemented
            # For now, create placeholder
            for session_id in self.SESSIONS:
                self.session_generators[session_id] = None
                
            logger.info("Generators loaded successfully")
        except Exception as e:
            logger.error(f"Error loading generators: {e}")
    
    def run_all_sessions(self, resume: bool = False):
        """
        Run all sessions sequentially.
        
        Args:
            resume: Resume from last checkpoint if True
        """
        logger.info("Starting sequential data generation for all sessions")
        
        for session_id in self.SESSIONS:
            if resume:
                # Check if session already completed
                checkpoint = self.checkpoint_manager.get_session_checkpoint(session_id)
                if checkpoint and checkpoint.get('status') == 'completed':
                    logger.info(f"Skipping {session_id} - already completed")
                    continue
            
            try:
                self.run_session(session_id, resume=resume)
            except Exception as e:
                logger.error(f"Error in {session_id}: {e}")
                self.checkpoint_manager.log_error(session_id, str(e))
                
                # Ask user if they want to continue
                if not self._should_continue_after_error(session_id):
                    break
        
        # Generate final report
        self.generate_final_report()
    
    def run_session(self, session_id: str, resume: bool = False):
        """
        Run a specific session.
        
        Args:
            session_id: Session identifier (e.g., 'session_1')
            resume: Resume from checkpoint if True
        """
        if session_id not in self.SESSIONS:
            raise ValueError(f"Invalid session ID: {session_id}")
        
        session_config = self.SESSIONS[session_id]
        logger.info(f"Starting {session_id}: {session_config['name']}")
        
        # Check dependencies
        if not self._check_session_dependencies(session_id):
            raise RuntimeError(f"Dependencies not met for {session_id}")
        
        # Start tracking
        self.current_session = session_id
        self.progress_tracker.start_session(session_id)
        
        try:
            # Get resume point if applicable
            resume_point = None
            if resume:
                resume_point = self.checkpoint_manager.get_resume_point(session_id)
                if resume_point:
                    logger.info(f"Resuming from: {resume_point['last_date']}")
            
            # Run session-specific generation
            with self.memory_manager:
                self._execute_session(session_id, session_config, resume_point)
            
            # Mark session complete
            memory_report = self.memory_manager.create_memory_report()
            self.checkpoint_manager.mark_session_complete(
                session_id,
                {
                    'peak_memory_mb': memory_report['peak_memory_mb'],
                    'metrics': self.progress_tracker.metrics
                }
            )
            
            self.progress_tracker.end_session(
                session_id,
                memory_report['peak_memory_mb']
            )
            
            logger.info(f"Successfully completed {session_id}")
            
        except Exception as e:
            logger.error(f"Error in session {session_id}: {e}")
            
            # Save checkpoint for resume
            self._save_session_checkpoint(session_id, 'failed', str(e))
            raise
        
        finally:
            self.current_session = None
    
    def _execute_session(self, session_id: str, config: Dict[str, Any], 
                        resume_point: Optional[Dict] = None):
        """
        Execute the actual data generation for a session.
        
        Args:
            session_id: Session identifier
            config: Session configuration
            resume_point: Resume point data if resuming
        """
        start_date = config['start_date']
        end_date = config['end_date']
        
        if resume_point and resume_point['last_date']:
            start_date = resume_point['last_date'] + timedelta(days=1)
            logger.info(f"Resuming from {start_date}")
        
        # Session-specific logic
        if session_id == 'session_1':
            self._run_session_1(start_date, end_date, resume_point)
        elif session_id == 'session_2':
            self._run_session_2(start_date, end_date, resume_point)
        elif session_id == 'session_3':
            self._run_session_3(start_date, end_date, resume_point)
        elif session_id == 'session_4':
            self._run_session_4(start_date, end_date, resume_point)
    
    def _run_session_1(self, start_date: date, end_date: date, 
                      resume_point: Optional[Dict] = None):
        """
        Session 1: Infrastructure & Historical Setup (Years 1-3)
        """
        logger.info("Executing Session 1: Infrastructure & Historical Setup")
        
        # Phase 1.1: Infrastructure Initialization
        if not resume_point or '1.1' not in resume_point.get('completed_steps', []):
            self.progress_tracker.update_progress('1.1', 'Infrastructure Initialization')
            
            # This is a placeholder - actual implementation will come from generators
            logger.info("Setting up geography hierarchy...")
            if not self.dry_run:
                # TODO: Call infrastructure generator
                pass
            
            self.progress_tracker.update_progress('1.1', 'Infrastructure Initialization', completed=True)
            self._save_checkpoint()
        
        # Phase 1.2: Initial Batch Creation
        if not resume_point or '1.2' not in resume_point.get('completed_steps', []):
            self.progress_tracker.update_progress('1.2', 'Initial Batch Creation')
            
            logger.info("Creating initial batches...")
            if not self.dry_run:
                # TODO: Call batch generator
                pass
            
            self.progress_tracker.update_progress('1.2', 'Initial Batch Creation', completed=True)
            self._save_checkpoint()
        
        # Continue with other phases...
        logger.info("Session 1 implementation in progress...")
    
    def _run_session_2(self, start_date: date, end_date: date,
                      resume_point: Optional[Dict] = None):
        """Session 2: Early Production Cycles (Years 4-6)"""
        logger.info("Session 2 implementation pending...")
    
    def _run_session_3(self, start_date: date, end_date: date,
                      resume_point: Optional[Dict] = None):
        """Session 3: Mature Operations (Years 7-9)"""
        logger.info("Session 3 implementation pending...")
    
    def _run_session_4(self, start_date: date, end_date: date,
                      resume_point: Optional[Dict] = None):
        """Session 4: Recent History & Validation (Year 10)"""
        logger.info("Session 4 implementation pending...")
    
    def _check_session_dependencies(self, session_id: str) -> bool:
        """
        Check if dependencies for a session are met.
        
        Args:
            session_id: Session identifier
            
        Returns:
            True if dependencies are met
        """
        # Session 1 has no dependencies
        if session_id == 'session_1':
            return True
        
        # Other sessions depend on previous sessions
        session_num = int(session_id.split('_')[1])
        
        for i in range(1, session_num):
            prev_session = f'session_{i}'
            checkpoint = self.checkpoint_manager.get_session_checkpoint(prev_session)
            
            if not checkpoint or checkpoint.get('status') != 'completed':
                logger.warning(f"Dependency not met: {prev_session} not completed")
                return False
        
        return True
    
    def _save_checkpoint(self):
        """Save current session checkpoint."""
        if self.current_session:
            checkpoint_data = {
                'status': 'in_progress',
                'last_processed_date': datetime.now().date().isoformat(),
                'completed_steps': self.progress_tracker.steps_completed,
                'metrics': self.progress_tracker.metrics
            }
            
            self.checkpoint_manager.save_checkpoint(
                self.current_session,
                checkpoint_data
            )
    
    def _save_session_checkpoint(self, session_id: str, status: str, error: str = None):
        """Save checkpoint for a specific session."""
        checkpoint_data = {
            'status': status,
            'timestamp': datetime.now().isoformat(),
            'error': error
        }
        
        self.checkpoint_manager.save_checkpoint(session_id, checkpoint_data)
    
    def _should_continue_after_error(self, session_id: str) -> bool:
        """
        Ask user if they want to continue after an error.
        
        Args:
            session_id: Session that failed
            
        Returns:
            True if should continue
        """
        if self.dry_run:
            return False
        
        response = input(f"\nError in {session_id}. Continue with next session? (y/n): ")
        return response.lower() == 'y'
    
    def generate_final_report(self):
        """Generate final report after all sessions."""
        logger.info("Generating final report...")
        
        self.progress_tracker.print_summary()
        
        # Create detailed report
        report = {
            'generation_complete': datetime.now().isoformat(),
            'overall_progress': self.progress_tracker.get_overall_progress(),
            'session_details': {},
            'global_state': self.checkpoint_manager.get_global_state()
        }
        
        for session_id in self.SESSIONS:
            report['session_details'][session_id] = self.progress_tracker.get_session_summary(session_id)
        
        # Save report
        report_file = Path(__file__).parent.parent / 'reports' / 'final_report.json'
        report_file.parent.mkdir(exist_ok=True)
        
        import json
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        logger.info(f"Final report saved to {report_file}")
    
    def validate_data(self):
        """Run validation on generated data."""
        logger.info("Running data validation...")
        # TODO: Implement validation logic
        pass
    
    def clear_all_data(self):
        """Clear all generated data and checkpoints."""
        logger.warning("Clearing all generated data and checkpoints...")
        
        if not self.dry_run:
            response = input("Are you sure you want to clear all data? (yes/no): ")
            if response.lower() != 'yes':
                logger.info("Clear operation cancelled")
                return
        
        self.checkpoint_manager.clear_all_checkpoints()
        logger.info("All checkpoints cleared")
