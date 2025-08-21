#!/usr/bin/env python
"""
Main entry point for AquaMind 10-year data generation.

This script orchestrates the generation of comprehensive aquaculture data
spanning 10 years through a multi-session approach.

Usage:
    # Run all sessions sequentially
    python scripts/data_generation/run_generation.py
    
    # Run specific session
    python scripts/data_generation/run_generation.py --session=1
    
    # Resume from checkpoint
    python scripts/data_generation/run_generation.py --resume
    
    # Validate generated data
    python scripts/data_generation/run_generation.py --validate
    
    # Generate report
    python scripts/data_generation/run_generation.py --report
"""

import os
import sys
import argparse
import logging
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Django setup
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'aquamind.settings')
import django
django.setup()

from orchestrator.session_manager import DataGenerationSessionManager
from orchestrator.progress_tracker import ProgressTracker

# Configure root logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Generate 10 years of AquaMind aquaculture data'
    )
    
    # Execution modes
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        '--session',
        type=int,
        choices=[1, 2, 3, 4],
        help='Run specific session (1-4)'
    )
    mode_group.add_argument(
        '--all',
        action='store_true',
        default=True,
        help='Run all sessions sequentially (default)'
    )
    mode_group.add_argument(
        '--validate',
        action='store_true',
        help='Validate generated data only'
    )
    mode_group.add_argument(
        '--report',
        action='store_true',
        help='Generate report only'
    )
    mode_group.add_argument(
        '--clear',
        action='store_true',
        help='Clear all data and checkpoints'
    )
    
    # Options
    parser.add_argument(
        '--resume',
        action='store_true',
        help='Resume from last checkpoint'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Simulate without creating data'
    )
    parser.add_argument(
        '--max-memory',
        type=float,
        default=75.0,
        help='Maximum memory usage percentage (default: 75)'
    )
    parser.add_argument(
        '--checkpoint-dir',
        type=str,
        help='Custom checkpoint directory'
    )
    
    args = parser.parse_args()
    
    # Print header
    print_header()
    
    # Initialize session manager
    manager = DataGenerationSessionManager(
        checkpoint_dir=args.checkpoint_dir,
        max_memory_percent=args.max_memory,
        dry_run=args.dry_run
    )
    
    try:
        if args.clear:
            # Clear all data and checkpoints
            logger.warning("Clearing all data and checkpoints...")
            manager.clear_all_data()
            
        elif args.validate:
            # Validate generated data
            logger.info("Running data validation...")
            manager.validate_data()
            
        elif args.report:
            # Generate report only
            logger.info("Generating report...")
            progress_tracker = ProgressTracker()
            progress_tracker.print_summary()
            manager.generate_final_report()
            
        elif args.session:
            # Run specific session
            session_id = f'session_{args.session}'
            logger.info(f"Running {session_id}")
            manager.run_session(session_id, resume=args.resume)
            
        else:
            # Run all sessions (default)
            logger.info("Running all sessions sequentially")
            manager.run_all_sessions(resume=args.resume)
        
        print_footer(success=True)
        
    except KeyboardInterrupt:
        logger.warning("Generation interrupted by user")
        print_footer(success=False, interrupted=True)
        sys.exit(1)
        
    except Exception as e:
        logger.error(f"Generation failed: {e}")
        print_footer(success=False)
        sys.exit(1)


def print_header():
    """Print script header."""
    print("\n" + "="*70)
    print(" "*20 + "AQUAMIND DATA GENERATION")
    print(" "*15 + "10 Years of Aquaculture Data")
    print("="*70)
    print()
    print("This process will generate comprehensive aquaculture data including:")
    print("  • Infrastructure (geographies, areas, stations, containers)")
    print("  • Batch lifecycles (40-50 concurrent batches)")
    print("  • Environmental readings (temperature, oxygen, pH, salinity)")
    print("  • Feed management (procurement, inventory, consumption)")
    print("  • Health records (diseases, treatments, mortality)")
    print("  • Growth tracking (TGC-based calculations)")
    print()
    print("The generation is split into 4 sessions:")
    print("  • Session 1: Years 1-3 (Infrastructure & Historical Setup)")
    print("  • Session 2: Years 4-6 (Early Production Cycles)")
    print("  • Session 3: Years 7-9 (Mature Operations)")
    print("  • Session 4: Year 10 (Recent History & Validation)")
    print()
    print("="*70)
    print()


def print_footer(success: bool = True, interrupted: bool = False):
    """Print script footer."""
    print()
    print("="*70)
    
    if interrupted:
        print(" "*20 + "GENERATION INTERRUPTED")
        print(" "*15 + "Progress has been saved to checkpoint")
        print(" "*15 + "Run with --resume to continue")
    elif success:
        print(" "*20 + "GENERATION COMPLETE")
        print(" "*15 + "Data successfully generated")
    else:
        print(" "*20 + "GENERATION FAILED")
        print(" "*15 + "Check logs for error details")
    
    print("="*70)
    print()


if __name__ == '__main__':
    main()
