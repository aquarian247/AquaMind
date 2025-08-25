"""
Memory Manager for Data Generation

Monitors and manages memory usage during data generation to prevent OOM errors.
"""

import gc
import psutil
import logging
from typing import Optional, Callable
from datetime import datetime
import warnings

logger = logging.getLogger(__name__)


class MemoryManager:
    """
    Manages memory usage during data generation.
    
    Provides monitoring, garbage collection, and emergency cleanup
    to prevent out-of-memory errors during long-running processes.
    """
    
    def __init__(self, 
                 max_memory_percent: float = 80.0,
                 warning_threshold_percent: float = 60.0,
                 check_interval_records: int = 10000):
        """
        Initialize memory manager.
        
        Args:
            max_memory_percent: Maximum memory usage before forcing cleanup (0-100)
            warning_threshold_percent: Memory usage to trigger warning (0-100)
            check_interval_records: Check memory every N records processed
        """
        self.max_memory_percent = max_memory_percent
        self.warning_threshold_percent = warning_threshold_percent
        self.check_interval_records = check_interval_records
        
        self.process = psutil.Process()
        self.total_memory = psutil.virtual_memory().total
        self.records_since_check = 0
        self.peak_memory_mb = 0
        self.cleanup_callbacks = []
        
        # Memory usage history for tracking trends
        self.memory_history = []
        self.max_history_size = 100
        
        logger.info(f"Memory Manager initialized. Total system memory: "
                   f"{self.total_memory / (1024**3):.2f} GB")
    
    def get_memory_usage(self) -> dict:
        """
        Get current memory usage statistics.
        
        Returns:
            Dictionary with memory statistics
        """
        memory_info = self.process.memory_info()
        system_memory = psutil.virtual_memory()
        
        current_mb = memory_info.rss / (1024 * 1024)
        self.peak_memory_mb = max(self.peak_memory_mb, current_mb)
        
        return {
            'current_mb': current_mb,
            'peak_mb': self.peak_memory_mb,
            'percent_used': system_memory.percent,
            'available_mb': system_memory.available / (1024 * 1024),
            'process_percent': (memory_info.rss / self.total_memory) * 100
        }
    
    def check_memory(self, force: bool = False) -> bool:
        """
        Check memory usage and trigger cleanup if needed.
        
        Args:
            force: Force memory check regardless of interval
            
        Returns:
            True if memory is within safe limits, False if cleanup was triggered
        """
        self.records_since_check += 1
        
        if not force and self.records_since_check < self.check_interval_records:
            return True
        
        self.records_since_check = 0
        memory_stats = self.get_memory_usage()
        
        # Track memory history
        self.memory_history.append({
            'timestamp': datetime.now(),
            'memory_mb': memory_stats['current_mb'],
            'percent': memory_stats['process_percent']
        })
        
        if len(self.memory_history) > self.max_history_size:
            self.memory_history.pop(0)
        
        # Check if we're approaching limits
        if memory_stats['process_percent'] >= self.max_memory_percent:
            logger.warning(f"Memory usage critical: {memory_stats['process_percent']:.1f}%")
            self.emergency_cleanup()
            return False
        
        elif memory_stats['process_percent'] >= self.warning_threshold_percent:
            logger.warning(f"Memory usage high: {memory_stats['process_percent']:.1f}%")
            self.standard_cleanup()
        
        return True
    
    def standard_cleanup(self):
        """Perform standard memory cleanup."""
        logger.info("Performing standard memory cleanup...")
        
        # Clear Django query cache
        try:
            from django.db import reset_queries
            reset_queries()
        except ImportError:
            pass
        
        # Force garbage collection
        gc.collect()
        
        # Call registered cleanup callbacks
        for callback in self.cleanup_callbacks:
            try:
                callback()
            except Exception as e:
                logger.error(f"Error in cleanup callback: {e}")
        
        # Log memory after cleanup
        memory_after = self.get_memory_usage()
        logger.info(f"Memory after cleanup: {memory_after['current_mb']:.1f} MB")
    
    def emergency_cleanup(self):
        """
        Perform emergency memory cleanup.
        
        More aggressive than standard cleanup, may impact performance.
        """
        logger.warning("Performing emergency memory cleanup...")
        
        # Standard cleanup first
        self.standard_cleanup()
        
        # Clear Django ORM cache more aggressively
        try:
            from django.core.cache import cache
            cache.clear()
        except ImportError:
            pass
        
        # Force multiple garbage collection passes
        for _ in range(3):
            gc.collect()
        
        # Clear module-level caches if they exist
        try:
            import sys
            sys.modules.clear()
        except:
            pass
        
        memory_after = self.get_memory_usage()
        logger.warning(f"Memory after emergency cleanup: {memory_after['current_mb']:.1f} MB")
        
        # If still above threshold, raise warning
        if memory_after['process_percent'] >= self.max_memory_percent:
            warnings.warn(
                f"Memory still critical after cleanup: {memory_after['process_percent']:.1f}%. "
                "Consider reducing batch size or splitting into smaller sessions.",
                ResourceWarning
            )
    
    def register_cleanup_callback(self, callback: Callable):
        """
        Register a callback to be called during cleanup.
        
        Args:
            callback: Function to call during cleanup
        """
        self.cleanup_callbacks.append(callback)
        logger.debug(f"Registered cleanup callback: {callback.__name__}")
    
    def get_memory_trend(self) -> str:
        """
        Analyze memory usage trend.
        
        Returns:
            String describing trend (increasing, stable, decreasing)
        """
        if len(self.memory_history) < 10:
            return "insufficient_data"
        
        recent = self.memory_history[-10:]
        first_avg = sum(h['memory_mb'] for h in recent[:5]) / 5
        last_avg = sum(h['memory_mb'] for h in recent[-5:]) / 5
        
        diff_percent = ((last_avg - first_avg) / first_avg) * 100
        
        if diff_percent > 10:
            return "increasing"
        elif diff_percent < -10:
            return "decreasing"
        else:
            return "stable"
    
    def estimate_remaining_capacity(self, avg_record_size_mb: float) -> int:
        """
        Estimate how many more records can be processed.
        
        Args:
            avg_record_size_mb: Average size of a record in MB
            
        Returns:
            Estimated number of records that can be processed
        """
        memory_stats = self.get_memory_usage()
        available_mb = memory_stats['available_mb']
        
        # Reserve 20% as safety buffer
        usable_mb = available_mb * 0.8
        
        if avg_record_size_mb > 0:
            return int(usable_mb / avg_record_size_mb)
        return 0
    
    def create_memory_report(self) -> dict:
        """
        Create a comprehensive memory usage report.
        
        Returns:
            Dictionary with memory statistics and analysis
        """
        current_stats = self.get_memory_usage()
        
        report = {
            'current_usage': current_stats,
            'peak_memory_mb': self.peak_memory_mb,
            'trend': self.get_memory_trend(),
            'cleanup_count': len([h for h in self.memory_history 
                                 if h.get('cleanup', False)]),
            'history_summary': {
                'samples': len(self.memory_history),
                'avg_mb': sum(h['memory_mb'] for h in self.memory_history) / len(self.memory_history)
                         if self.memory_history else 0,
                'max_mb': max(h['memory_mb'] for h in self.memory_history)
                         if self.memory_history else 0
            }
        }
        
        return report
    
    def __enter__(self):
        """Context manager entry."""
        self.check_memory(force=True)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit with cleanup."""
        self.standard_cleanup()
        
        # Log final memory statistics
        report = self.create_memory_report()
        logger.info(f"Memory Manager Report: Peak usage {report['peak_memory_mb']:.1f} MB")
        
        return False

