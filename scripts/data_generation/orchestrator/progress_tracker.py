"""
Progress Tracker for Data Generation

Tracks and reports progress of data generation sessions.
"""

import time
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from pathlib import Path
import json

logger = logging.getLogger(__name__)


class ProgressTracker:
    """
    Tracks progress of data generation sessions and updates the implementation plan.
    """
    
    def __init__(self, plan_file: str = None):
        """
        Initialize progress tracker.
        
        Args:
            plan_file: Path to implementation plan markdown file
        """
        if plan_file is None:
            plan_file = Path(__file__).parent.parent / 'IMPLEMENTATION_PLAN.md'
        
        self.plan_file = Path(plan_file)
        self.session_start_times = {}
        self.session_metrics = {}
        
        # Current session tracking
        self.current_session = None
        self.current_phase = None
        self.current_step = None
        self.steps_completed = []
        
        # Metrics tracking
        self.metrics = {
            'total_batches_created': 0,
            'total_records_generated': 0,
            'environmental_readings_created': 0,
            'feed_events_processed': 0,
            'mortality_events_recorded': 0,
            'treatments_applied': 0
        }
    
    def start_session(self, session_id: str):
        """
        Mark the start of a session.
        
        Args:
            session_id: Session identifier (e.g., 'session_1')
        """
        self.current_session = session_id
        self.session_start_times[session_id] = time.time()
        self.session_metrics[session_id] = {
            'start_time': datetime.now().isoformat(),
            'status': 'in_progress',
            'metrics': {}
        }
        
        logger.info(f"Started {session_id}")
    
    def end_session(self, session_id: str, memory_peak_mb: float = 0):
        """
        Mark the end of a session.
        
        Args:
            session_id: Session identifier
            memory_peak_mb: Peak memory usage in MB
        """
        if session_id not in self.session_start_times:
            logger.warning(f"Session {session_id} was not properly started")
            return
        
        elapsed_time = time.time() - self.session_start_times[session_id]
        
        self.session_metrics[session_id].update({
            'end_time': datetime.now().isoformat(),
            'status': 'completed',
            'runtime_seconds': elapsed_time,
            'runtime_formatted': self._format_duration(elapsed_time),
            'memory_peak_mb': memory_peak_mb,
            'metrics': self.metrics.copy()
        })
        
        logger.info(f"Completed {session_id} in {self._format_duration(elapsed_time)}")
        
        # Save session report
        self._save_session_report(session_id)
    
    def update_progress(self, phase: str, step: str, completed: bool = False):
        """
        Update progress for a specific phase and step.
        
        Args:
            phase: Phase identifier (e.g., '1.1')
            step: Step description
            completed: Whether the step is completed
        """
        self.current_phase = phase
        self.current_step = step
        
        if completed:
            step_id = f"{phase}:{step}"
            if step_id not in self.steps_completed:
                self.steps_completed.append(step_id)
                logger.debug(f"Completed step: {step_id}")
    
    def increment_metric(self, metric_name: str, value: int = 1):
        """
        Increment a tracked metric.
        
        Args:
            metric_name: Name of the metric to increment
            value: Amount to increment by
        """
        if metric_name in self.metrics:
            self.metrics[metric_name] += value
        else:
            self.metrics[metric_name] = value
    
    def log_progress(self, message: str, level: str = 'info'):
        """
        Log a progress message.
        
        Args:
            message: Message to log
            level: Log level (info, warning, error)
        """
        log_func = getattr(logger, level, logger.info)
        
        if self.current_session and self.current_phase:
            message = f"[{self.current_session}:{self.current_phase}] {message}"
        elif self.current_session:
            message = f"[{self.current_session}] {message}"
        
        log_func(message)
    
    def get_session_summary(self, session_id: str) -> Dict[str, Any]:
        """
        Get summary for a specific session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Session summary dictionary
        """
        if session_id in self.session_metrics:
            return self.session_metrics[session_id]
        return {}
    
    def get_overall_progress(self) -> Dict[str, Any]:
        """
        Get overall progress across all sessions.
        
        Returns:
            Overall progress summary
        """
        completed_sessions = [
            sid for sid, metrics in self.session_metrics.items()
            if metrics.get('status') == 'completed'
        ]
        
        total_runtime = sum(
            metrics.get('runtime_seconds', 0)
            for metrics in self.session_metrics.values()
        )
        
        return {
            'total_sessions': 4,
            'completed_sessions': len(completed_sessions),
            'progress_percent': (len(completed_sessions) / 4) * 100,
            'total_runtime_seconds': total_runtime,
            'total_runtime_formatted': self._format_duration(total_runtime),
            'cumulative_metrics': self.metrics
        }
    
    def estimate_remaining_time(self) -> Optional[timedelta]:
        """
        Estimate remaining time based on completed sessions.
        
        Returns:
            Estimated time remaining or None if cannot estimate
        """
        completed = [
            sid for sid, metrics in self.session_metrics.items()
            if metrics.get('status') == 'completed'
        ]
        
        if not completed:
            return None
        
        avg_session_time = sum(
            self.session_metrics[sid].get('runtime_seconds', 0)
            for sid in completed
        ) / len(completed)
        
        remaining_sessions = 4 - len(completed)
        estimated_seconds = avg_session_time * remaining_sessions
        
        return timedelta(seconds=estimated_seconds)
    
    def _format_duration(self, seconds: float) -> str:
        """Format duration in seconds to human-readable string."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        
        if hours > 0:
            return f"{hours}h {minutes}m {secs}s"
        elif minutes > 0:
            return f"{minutes}m {secs}s"
        else:
            return f"{secs}s"
    
    def _save_session_report(self, session_id: str):
        """
        Save detailed session report to file.
        
        Args:
            session_id: Session identifier
        """
        try:
            report_dir = Path(__file__).parent.parent / 'reports'
            report_dir.mkdir(exist_ok=True)
            
            report_file = report_dir / f"{session_id}_report.json"
            
            report = {
                'session_id': session_id,
                'metrics': self.session_metrics.get(session_id, {}),
                'steps_completed': self.steps_completed,
                'timestamp': datetime.now().isoformat()
            }
            
            with open(report_file, 'w') as f:
                json.dump(report, f, indent=2)
            
            logger.info(f"Session report saved to {report_file}")
            
        except Exception as e:
            logger.error(f"Error saving session report: {e}")
    
    def print_summary(self):
        """Print a formatted summary of progress."""
        overall = self.get_overall_progress()
        
        print("\n" + "="*60)
        print("DATA GENERATION PROGRESS SUMMARY")
        print("="*60)
        
        print(f"\nSessions Completed: {overall['completed_sessions']}/{overall['total_sessions']} "
              f"({overall['progress_percent']:.1f}%)")
        print(f"Total Runtime: {overall['total_runtime_formatted']}")
        
        if self.session_metrics:
            print("\nSession Details:")
            for sid, metrics in self.session_metrics.items():
                status = metrics.get('status', 'unknown')
                runtime = metrics.get('runtime_formatted', 'N/A')
                memory = metrics.get('memory_peak_mb', 0)
                
                print(f"  {sid}: {status} - Runtime: {runtime}, Peak Memory: {memory:.1f} MB")
        
        print("\nCumulative Metrics:")
        for metric, value in overall['cumulative_metrics'].items():
            print(f"  {metric}: {value:,}")
        
        remaining = self.estimate_remaining_time()
        if remaining:
            print(f"\nEstimated Time Remaining: {remaining}")
        
        print("="*60 + "\n")

