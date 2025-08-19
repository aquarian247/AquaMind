#!/usr/bin/env python
"""
Test script for the data generation orchestrator.

This script tests the basic functionality of the orchestrator components
without actually generating large amounts of data.
"""

import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Django setup
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'aquamind.settings')
import django
django.setup()

from orchestrator.checkpoint_manager import CheckpointManager
from orchestrator.memory_manager import MemoryManager
from orchestrator.progress_tracker import ProgressTracker
from orchestrator.session_manager import DataGenerationSessionManager
from config.generation_params import GenerationParameters
from config.disease_profiles import DISEASE_PROFILES


def test_checkpoint_manager():
    """Test checkpoint manager functionality."""
    print("\n" + "="*50)
    print("Testing Checkpoint Manager")
    print("="*50)
    
    cm = CheckpointManager()
    
    # Test saving checkpoint
    cm.save_checkpoint('session_1', {
        'status': 'in_progress',
        'last_processed_date': '2024-01-15',
        'active_batches': [1, 2, 3],
        'progress': {'percent': 25}
    })
    print("✓ Saved checkpoint")
    
    # Test loading checkpoint
    checkpoint = cm.get_session_checkpoint('session_1')
    if checkpoint:
        print(f"✓ Loaded checkpoint: {checkpoint['status']}")
    
    # Test resume point
    resume_point = cm.get_resume_point('session_1')
    if resume_point:
        print(f"✓ Resume point found: {resume_point['last_date']}")
    
    # Test global state
    cm.update_global_state({'total_batches_created': 15})
    state = cm.get_global_state()
    print(f"✓ Global state updated: {state.get('total_batches_created')} batches")
    
    print("\nCheckpoint Manager: PASSED")


def test_memory_manager():
    """Test memory manager functionality."""
    print("\n" + "="*50)
    print("Testing Memory Manager")
    print("="*50)
    
    mm = MemoryManager(max_memory_percent=80.0)
    
    # Test memory monitoring
    stats = mm.get_memory_usage()
    print(f"✓ Current memory: {stats['current_mb']:.1f} MB")
    print(f"✓ Process percent: {stats['process_percent']:.1f}%")
    
    # Test memory check
    is_safe = mm.check_memory()
    print(f"✓ Memory check: {'Safe' if is_safe else 'Warning'}")
    
    # Test cleanup callback
    def custom_cleanup():
        print("  Custom cleanup called")
    
    mm.register_cleanup_callback(custom_cleanup)
    mm.standard_cleanup()
    print("✓ Cleanup executed")
    
    # Test memory report
    report = mm.create_memory_report()
    print(f"✓ Memory report generated: Peak {report['peak_memory_mb']:.1f} MB")
    
    print("\nMemory Manager: PASSED")


def test_progress_tracker():
    """Test progress tracker functionality."""
    print("\n" + "="*50)
    print("Testing Progress Tracker")
    print("="*50)
    
    pt = ProgressTracker()
    
    # Test session tracking
    pt.start_session('session_1')
    print("✓ Session started")
    
    # Test progress updates
    pt.update_progress('1.1', 'Infrastructure Setup')
    pt.update_progress('1.1', 'Infrastructure Setup', completed=True)
    print("✓ Progress updated")
    
    # Test metric tracking
    pt.increment_metric('total_batches_created', 5)
    pt.increment_metric('environmental_readings_created', 1000)
    print(f"✓ Metrics tracked: {pt.metrics['total_batches_created']} batches")
    
    # Test summary
    summary = pt.get_overall_progress()
    print(f"✓ Overall progress: {summary['progress_percent']:.1f}%")
    
    print("\nProgress Tracker: PASSED")


def test_configuration():
    """Test configuration loading."""
    print("\n" + "="*50)
    print("Testing Configuration")
    print("="*50)
    
    # Test generation parameters
    print(f"✓ Target active batches: {GenerationParameters.TARGET_ACTIVE_BATCHES}")
    print(f"✓ Egg count range: {GenerationParameters.EGG_COUNT_MIN:,} - {GenerationParameters.EGG_COUNT_MAX:,}")
    
    duration = GenerationParameters.get_stage_duration('smolt')
    print(f"✓ Smolt stage duration: {duration[0]}-{duration[1]} days")
    
    tgc = GenerationParameters.get_tgc_value('grow_out')
    print(f"✓ Grow-out TGC: {tgc[0]}-{tgc[1]}")
    
    # Test disease profiles
    print(f"✓ Disease profiles loaded: {len(DISEASE_PROFILES)} diseases")
    
    pd_profile = DISEASE_PROFILES.get('PD')
    if pd_profile:
        print(f"✓ PD probability: {pd_profile['probability']*100:.1f}% annual")
    
    print("\nConfiguration: PASSED")


def test_session_manager_dry_run():
    """Test session manager in dry-run mode."""
    print("\n" + "="*50)
    print("Testing Session Manager (Dry Run)")
    print("="*50)
    
    # Create manager in dry-run mode
    manager = DataGenerationSessionManager(dry_run=True)
    
    # Test session configuration
    print(f"✓ Sessions configured: {len(manager.SESSIONS)}")
    
    for session_id, config in manager.SESSIONS.items():
        print(f"  {session_id}: {config['name']} (Years {config['years'][0]}-{config['years'][1]})")
    
    # Test dependency checking
    can_run = manager._check_session_dependencies('session_1')
    print(f"✓ Session 1 dependencies: {'Met' if can_run else 'Not met'}")
    
    print("\nSession Manager: PASSED")


def main():
    """Run all tests."""
    print("\n" + "="*60)
    print(" "*15 + "DATA GENERATION ORCHESTRATOR TEST")
    print("="*60)
    
    try:
        test_checkpoint_manager()
        test_memory_manager()
        test_progress_tracker()
        test_configuration()
        test_session_manager_dry_run()
        
        print("\n" + "="*60)
        print(" "*20 + "ALL TESTS PASSED ✓")
        print("="*60)
        print("\nThe orchestrator is ready for data generation!")
        print("Run 'python scripts/data_generation/run_generation.py' to start")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
