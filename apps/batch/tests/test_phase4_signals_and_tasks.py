"""
Tests for Phase 4 - Event-Driven Recompute (Celery + Signals).

This test suite validates:
1. Celery tasks execute correctly (unit tests)
2. Deduplication logic (unit tests)
3. Signal handlers for simple events (integration tests)
4. Management command (integration tests)

Complex event tests (TransferAction, Treatment) deferred to Phase 9
with real Faroe Islands data per handover recommendation.

Issue: #112 - Phase 4
"""
import logging
from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import patch, MagicMock

from django.test import TestCase
from django.core.management import call_command
from django.core.cache import cache
from django.contrib.auth import get_user_model

from apps.batch.models import (
    Batch,
    BatchContainerAssignment,
    GrowthSample,
    MortalityEvent,
    ActualDailyAssignmentState,
)
from apps.batch.tasks import (
    recompute_assignment_window,
    recompute_batch_window,
    enqueue_recompute_with_deduplication,
    enqueue_batch_recompute,
    should_enqueue_task,
    get_dedup_key,
)

# Reuse existing test helpers (per handover recommendation)
from apps.batch.tests.models.test_utils import (
    create_test_batch,
    create_test_container,
    create_test_batch_container_assignment,
    create_test_species,
    create_test_lifecycle_stage
)
from apps.scenario.tests.test_helpers import create_test_scenario

User = get_user_model()
logger = logging.getLogger(__name__)


class CeleryTaskTestCase(TestCase):
    """Test Celery tasks for growth assimilation recomputation."""
    
    def setUp(self):
        """Set up test data."""
        # Create user for scenario
        self.user = User.objects.create_user(username='testuser1', password='testpass')
        
        # Use test helpers (per handover: "Use existing test helpers")
        self.container = create_test_container(name="Tank-001")
        
        # Create batch + assignment using helpers
        species = create_test_species(name="Atlantic Salmon")
        stage = create_test_lifecycle_stage(species=species, name="Fry", order=1)
        self.batch = create_test_batch(
            species=species,
            lifecycle_stage=stage,
            batch_number="TEST-001"
        )
        
        self.assignment = create_test_batch_container_assignment(
            batch=self.batch,
            container=self.container,
            lifecycle_stage=stage,
            population_count=5000,
            avg_weight_g=Decimal('50.0')
        )
        
        # Create and pin scenario
        self.scenario = create_test_scenario(user=self.user)
        self.batch.pinned_scenario = self.scenario
        self.batch.save()
    
    def test_recompute_assignment_window_task(self):
        """Test assignment-level recompute task executes successfully."""
        start_date = date(2024, 1, 1)
        end_date = date(2024, 1, 5)
        
        # Execute task (synchronously for testing)
        result = recompute_assignment_window(
            assignment_id=self.assignment.id,
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat()
        )
        
        # Verify result structure
        self.assertTrue(result['success'])
        self.assertEqual(result['assignment_id'], self.assignment.id)
        self.assertIn('rows_created', result)
        self.assertIn('rows_updated', result)
        
        # Note: Engine may create 0 states if no temperature data exists
        # This is expected - engine needs temperature to compute
        # Full validation with real data deferred to Phase 9
    
    def test_recompute_assignment_window_task_nonexistent_assignment(self):
        """Test task handles nonexistent assignment gracefully."""
        result = recompute_assignment_window(
            assignment_id=999999,
            start_date='2024-01-01',
            end_date='2024-01-05'
        )
        
        self.assertFalse(result['success'])
        self.assertIn('error', result)
    
    def test_recompute_batch_window_task(self):
        """Test batch-level recompute task executes successfully."""
        # Use batch's actual start date for valid test
        start_date = self.batch.start_date
        end_date = self.batch.start_date + timedelta(days=4)
        
        # Execute task
        result = recompute_batch_window(
            batch_id=self.batch.id,
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat()
        )
        
        # Verify result structure
        self.assertTrue(result['success'])
        self.assertEqual(result['batch_id'], self.batch.id)
        self.assertEqual(result['assignments_processed'], 1)
        
        # Note: Engine may create 0 states if no temperature data exists
        # Full validation with real data deferred to Phase 9
    
    def test_recompute_batch_window_task_nonexistent_batch(self):
        """Test task handles nonexistent batch gracefully."""
        result = recompute_batch_window(
            batch_id=999999,
            start_date='2024-01-01',
            end_date='2024-01-05'
        )
        
        self.assertFalse(result['success'])
        self.assertIn('error', result)


class DeduplicationTestCase(TestCase):
    """Test task deduplication logic."""
    
    def tearDown(self):
        """Clear cache after each test."""
        cache.clear()
    
    def test_dedup_key_generation(self):
        """Test deduplication key format."""
        assignment_id = 123
        trigger_date = date(2024, 1, 15)
        
        key = get_dedup_key(assignment_id, trigger_date)
        
        self.assertEqual(key, "growth_assimilation:dedup:123:2024-01-15")
    
    def test_should_enqueue_task_first_call(self):
        """Test first call returns True (task should be enqueued)."""
        assignment_id = 123
        trigger_date = date(2024, 1, 15)
        
        result = should_enqueue_task(assignment_id, trigger_date)
        
        self.assertTrue(result)
    
    def test_should_enqueue_task_duplicate_call(self):
        """Test duplicate call returns False (task already queued)."""
        assignment_id = 123
        trigger_date = date(2024, 1, 15)
        
        # First call - should enqueue
        first = should_enqueue_task(assignment_id, trigger_date)
        self.assertTrue(first)
        
        # Second call - should skip (duplicate)
        second = should_enqueue_task(assignment_id, trigger_date)
        self.assertFalse(second)
    
    def test_should_enqueue_task_different_dates(self):
        """Test different dates can both be enqueued."""
        assignment_id = 123
        date1 = date(2024, 1, 15)
        date2 = date(2024, 1, 16)
        
        result1 = should_enqueue_task(assignment_id, date1)
        result2 = should_enqueue_task(assignment_id, date2)
        
        self.assertTrue(result1)
        self.assertTrue(result2)


class SignalHandlerTestCase(TestCase):
    """Test signal handlers enqueue tasks correctly."""
    
    def setUp(self):
        """Set up test data."""
        # Create user for scenario
        self.user = User.objects.create_user(username='testuser2', password='testpass')
        
        # Use test helpers (per handover: "Use existing test helpers")
        self.container = create_test_container(name="Tank-002")
        
        # Create batch + assignment using helpers
        species = create_test_species(name="Atlantic Salmon 2")
        stage = create_test_lifecycle_stage(species=species, name="Fry 2", order=1)
        self.batch = create_test_batch(
            species=species,
            lifecycle_stage=stage,
            batch_number="TEST-002"
        )
        
        self.assignment = create_test_batch_container_assignment(
            batch=self.batch,
            container=self.container,
            lifecycle_stage=stage,
            population_count=5000,
            avg_weight_g=Decimal('50.0')
        )
        
        # Create and pin scenario
        self.scenario = create_test_scenario(user=self.user)
        self.batch.pinned_scenario = self.scenario
        self.batch.save()
    
    def tearDown(self):
        """Clear cache after each test."""
        cache.clear()
    
    @patch('apps.batch.tasks.recompute_assignment_window.delay')
    def test_growth_sample_signal_enqueues_task(self, mock_delay):
        """Test GrowthSample creation enqueues recompute task."""
        sample_date = date(2024, 1, 10)
        
        # Create growth sample (should trigger signal)
        sample = GrowthSample.objects.create(
            assignment=self.assignment,
            sample_date=sample_date,
            sample_size=100,
            avg_weight_g=150.0
        )
        
        # Verify task was enqueued
        mock_delay.assert_called_once()
        args = mock_delay.call_args[0]
        self.assertEqual(args[0], self.assignment.id)
        # Window should be [sample_date - 2, sample_date + 2]
        self.assertEqual(args[1], '2024-01-08')  # start_date
        self.assertEqual(args[2], '2024-01-12')  # end_date
    
    @patch('apps.batch.tasks.recompute_assignment_window.delay')
    def test_growth_sample_update_does_not_enqueue(self, mock_delay):
        """Test GrowthSample update does NOT enqueue task."""
        # Create sample
        sample = GrowthSample.objects.create(
            assignment=self.assignment,
            sample_date=date(2024, 1, 10),
            sample_size=100,
            avg_weight_g=150.0
        )
        
        # Clear mock
        mock_delay.reset_mock()
        
        # Update sample (should NOT trigger signal)
        sample.avg_weight_g = 160.0
        sample.save()
        
        # Verify task was NOT enqueued
        mock_delay.assert_not_called()
    
    @patch('apps.batch.tasks.recompute_batch_window.delay')
    def test_mortality_event_enqueues_batch_task(self, mock_delay):
        """Test MortalityEvent enqueues batch-level recompute."""
        event_date = date(2024, 1, 20)
        
        # Create mortality event
        mortality = MortalityEvent.objects.create(
            batch=self.batch,
            event_date=event_date,
            count=50,
            biomass_kg=Decimal('5.0')
        )
        
        # Verify batch task was enqueued
        mock_delay.assert_called_once()
        args = mock_delay.call_args[0]
        self.assertEqual(args[0], self.batch.id)
        self.assertEqual(args[1], '2024-01-19')  # event_date - 1
        self.assertEqual(args[2], '2024-01-21')  # event_date + 1


class ManagementCommandTestCase(TestCase):
    """Test nightly catch-up management command."""
    
    def setUp(self):
        """Set up test data."""
        # Create user for scenario
        self.user = User.objects.create_user(username='testuser3', password='testpass')
        
        # Use test helpers (per handover: "Use existing test helpers")
        self.container = create_test_container(name="Tank-003")
        
        # Create active batch + assignment using helpers
        species = create_test_species(name="Atlantic Salmon 3")
        stage = create_test_lifecycle_stage(species=species, name="Fry 3", order=1)
        self.batch = create_test_batch(
            species=species,
            lifecycle_stage=stage,
            batch_number="TEST-003"
        )
        self.batch.status = 'ACTIVE'
        
        self.assignment = create_test_batch_container_assignment(
            batch=self.batch,
            container=self.container,
            lifecycle_stage=stage,
            population_count=5000,
            avg_weight_g=Decimal('50.0')
        )
        
        # Create and pin scenario
        self.scenario = create_test_scenario(user=self.user)
        self.batch.pinned_scenario = self.scenario
        self.batch.save()
    
    @patch('apps.batch.tasks.recompute_batch_window.delay')
    def test_management_command_dry_run(self, mock_delay):
        """Test command with --dry-run does not enqueue tasks."""
        call_command('recompute_recent_daily_states', '--dry-run', '--days=7')
        
        # Verify no tasks enqueued in dry run
        mock_delay.assert_not_called()
    
    @patch('apps.batch.tasks.recompute_batch_window.delay')
    def test_management_command_enqueues_tasks(self, mock_delay):
        """Test command enqueues tasks for active batches."""
        # Mock task result
        mock_task = MagicMock()
        mock_task.id = 'test-task-id-123'
        mock_delay.return_value = mock_task
        
        # Run command
        result = call_command('recompute_recent_daily_states', '--days=7')
        
        # Verify task was enqueued
        mock_delay.assert_called_once()
        args = mock_delay.call_args[0]
        self.assertEqual(args[0], self.batch.id)
    
    @patch('apps.batch.tasks.recompute_batch_window.delay')
    def test_management_command_specific_batch(self, mock_delay):
        """Test command with --batch-id processes only that batch."""
        mock_task = MagicMock()
        mock_task.id = 'test-task-id-123'
        mock_delay.return_value = mock_task
        
        # Run command for specific batch
        call_command(
            'recompute_recent_daily_states',
            f'--batch-id={self.batch.id}',
            '--days=7'
        )
        
        # Verify task was enqueued for correct batch
        mock_delay.assert_called_once()
        args = mock_delay.call_args[0]
        self.assertEqual(args[0], self.batch.id)
    
    def test_management_command_skips_batches_without_scenario(self):
        """Test command skips batches without pinned scenario."""
        # Create batch without scenario
        species = create_test_species(name="Salmon No Scenario")
        stage = create_test_lifecycle_stage(species=species, name="Fry NS", order=1)
        batch_no_scenario = create_test_batch(
            species=species,
            lifecycle_stage=stage,
            batch_number="NO-SCENARIO"
        )
        batch_no_scenario.status = 'ACTIVE'
        batch_no_scenario.save()
        
        container = create_test_container(name="Tank-NoScenario")
        create_test_batch_container_assignment(
            batch=batch_no_scenario,
            container=container,
            lifecycle_stage=stage,
            population_count=1000,
            avg_weight_g=Decimal('50.0')
        )
        
        # Run command (should skip batch without scenario)
        with patch('apps.batch.tasks.recompute_batch_window.delay') as mock_delay:
            call_command('recompute_recent_daily_states', '--days=7')
            
            # Verify only batch WITH scenario was processed
            # self.batch has scenario, batch_no_scenario doesn't
            self.assertEqual(mock_delay.call_count, 1)
            args = mock_delay.call_args[0]
            self.assertEqual(args[0], self.batch.id)  # Only our setUp batch


class IntegrationTestCase(TestCase):
    """
    End-to-end integration tests: signal → task → daily states.
    
    Note: These tests verify the signal/task plumbing works.
    Full validation with growth samples + temperature data deferred
    to Phase 9 with real Faroe Islands dataset.
    """
    
    def setUp(self):
        """Set up test data."""
        # Create user for scenario
        self.user = User.objects.create_user(username='testuser4', password='testpass')
        
        # Use test helpers (per handover: "Use existing test helpers")
        self.container = create_test_container(name="Tank-004")
        
        # Create batch + assignment using helpers
        species = create_test_species(name="Atlantic Salmon 4")
        stage = create_test_lifecycle_stage(species=species, name="Fry 4", order=1)
        self.batch = create_test_batch(
            species=species,
            lifecycle_stage=stage,
            batch_number="TEST-004"
        )
        
        self.assignment = create_test_batch_container_assignment(
            batch=self.batch,
            container=self.container,
            lifecycle_stage=stage,
            population_count=5000,
            avg_weight_g=Decimal('50.0')
        )
        
        # Create and pin scenario
        self.scenario = create_test_scenario(user=self.user)
        self.batch.pinned_scenario = self.scenario
        self.batch.save()
    
    @patch('apps.batch.tasks.recompute_assignment_window.delay')
    @patch('apps.batch.tasks.cache.add')
    def test_growth_sample_triggers_signal_flow(self, mock_cache_add, mock_delay):
        """Test integration: GrowthSample → signal → task enqueued."""
        # Mock cache.add() returns True (dedup allows enqueue)
        mock_cache_add.return_value = True
        
        sample_date = date(2024, 1, 10)
        
        # Create growth sample (triggers signal → enqueues task)
        sample = GrowthSample.objects.create(
            assignment=self.assignment,
            sample_date=sample_date,
            sample_size=100,
            avg_weight_g=150.0
        )
        
        # Verify signal handler enqueued the task
        mock_delay.assert_called_once()
        args = mock_delay.call_args[0]
        self.assertEqual(args[0], self.assignment.id)
        
        # Verify window calculation
        self.assertEqual(args[1], '2024-01-08')  # sample_date - 2
        self.assertEqual(args[2], '2024-01-12')  # sample_date + 2
        
        # Note: Full end-to-end validation (task execution → states created)
        # is deferred to Phase 9 with real Faroe Islands data and Redis running
