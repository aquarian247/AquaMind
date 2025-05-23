from django.test import TestCase
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.db.utils import IntegrityError

from apps.batch.models import Batch, BatchContainerAssignment
from decimal import Decimal
from datetime import timedelta, date

from apps.batch.tests.models.test_utils import (
    create_test_species,
    create_test_lifecycle_stage,
    create_test_batch,
    create_test_container,
    create_test_batch_container_assignment,
    create_test_batch_with_assignment
)


class BatchCalculationsTests(TestCase):
    """Test batch calculation methods."""

    def setUp(self):
        self.species = create_test_species()
        self.lc_stage = create_test_lifecycle_stage(species=self.species)
        self.batch = create_test_batch(
            species=self.species,
            lifecycle_stage=self.lc_stage,
            batch_number="BATCH001"
        )
        self.container1 = create_test_container(name="Tank 1")
        self.container2 = create_test_container(name="Tank 2")

    def test_batch_new_no_assignments(self):
        """Test a new Batch with no assignments has zero/default calculated values."""
        # A new batch without assignments should have zero values for calculated fields
        new_batch = Batch.objects.create(
            batch_number="BATCH002",
            species=self.species,
            lifecycle_stage=self.lc_stage,
            start_date=date.today() - timedelta(days=30),
            expected_end_date=date.today() + timedelta(days=335)
        )
        self.assertEqual(new_batch.calculated_population_count, 0)
        self.assertEqual(new_batch.calculated_avg_weight_g, Decimal('0.0'))
        self.assertEqual(new_batch.calculated_biomass_kg, Decimal('0.0'))
        # active_container_count property no longer exists in the Batch model

    def test_batch_one_assignment(self):
        """Test Batch calculations with a single active BCA."""
        assignment_pop = 1000
        assignment_avg_w = Decimal('50.0')
        BatchContainerAssignment.objects.create(
            batch=self.batch,
            container=self.container1,
            lifecycle_stage=self.lc_stage,
            population_count=assignment_pop,
            avg_weight_g=assignment_avg_w,
            assignment_date=date.today(),
            is_active=True
        )

        self.batch.refresh_from_db()
        self.assertEqual(self.batch.calculated_population_count, assignment_pop)
        self.assertEqual(self.batch.calculated_avg_weight_g, assignment_avg_w)
        expected_biomass = (assignment_pop * assignment_avg_w) / Decimal('1000')  # 50.0 kg
        self.assertEqual(self.batch.calculated_biomass_kg, expected_biomass)
        # active_container_count property no longer exists in the Batch model

    def test_batch_multiple_assignments(self):
        """Test Batch calculations with multiple active BCAs."""
        assignment1_pop = 1000
        assignment1_avg_w = Decimal('50.0')
        assignment2_pop = 500
        assignment2_avg_w = Decimal('60.0')
        bca1 = BatchContainerAssignment.objects.create(
            batch=self.batch,
            container=self.container1,
            lifecycle_stage=self.lc_stage,
            population_count=assignment1_pop,
            avg_weight_g=assignment1_avg_w,
            assignment_date=date.today(),
            is_active=True
        )
        bca2 = BatchContainerAssignment.objects.create(
            batch=self.batch,
            container=self.container2,
            lifecycle_stage=self.lc_stage,
            population_count=assignment2_pop,
            avg_weight_g=assignment2_avg_w,
            assignment_date=date.today(),
            is_active=True
        )

        self.batch.refresh_from_db()
        total_pop = assignment1_pop + assignment2_pop  # 1500
        self.assertEqual(self.batch.calculated_population_count, total_pop)
        expected_avg_weight = ((assignment1_pop * assignment1_avg_w) + (assignment2_pop * assignment2_avg_w)) / total_pop
        self.assertEqual(self.batch.calculated_avg_weight_g, expected_avg_weight)
        expected_biomass = ((assignment1_pop * assignment1_avg_w) + (assignment2_pop * assignment2_avg_w)) / Decimal('1000')  # 80.0 kg
        self.assertEqual(self.batch.calculated_biomass_kg, expected_biomass)
        # active_container_count property no longer exists in the Batch model

    def test_batch_ignores_inactive_assignments(self):
        """Test Batch calculations ignore inactive BCAs."""
        assignment_pop = 1000
        assignment_avg_w = Decimal('50.0')
        BatchContainerAssignment.objects.create(
            batch=self.batch,
            container=self.container1,
            lifecycle_stage=self.lc_stage,
            population_count=assignment_pop,
            avg_weight_g=assignment_avg_w,
            assignment_date=date.today() - timedelta(days=10),
            is_active=False
        )

        self.batch.refresh_from_db()
        self.assertEqual(self.batch.calculated_population_count, 0)
        self.assertEqual(self.batch.calculated_avg_weight_g, Decimal('0.0'))
        self.assertEqual(self.batch.calculated_biomass_kg, Decimal('0.0'))
        # active_container_count property no longer exists in the Batch model

    def test_batch_mixed_active_inactive_assignments(self):
        """Test Batch calculations with a mix of active and inactive BCAs."""
        active_pop = 1000
        active_avg_w = Decimal('50.0')
        inactive_pop = 500
        inactive_avg_w = Decimal('60.0')
        BatchContainerAssignment.objects.create(
            batch=self.batch,
            container=self.container1,
            lifecycle_stage=self.lc_stage,
            population_count=active_pop,
            avg_weight_g=active_avg_w,
            assignment_date=date.today(),
            is_active=True
        )
        BatchContainerAssignment.objects.create(
            batch=self.batch,
            container=self.container2,
            lifecycle_stage=self.lc_stage,
            population_count=inactive_pop,
            avg_weight_g=inactive_avg_w,
            assignment_date=date.today() - timedelta(days=10),
            is_active=False
        )

        self.batch.refresh_from_db()
        self.assertEqual(self.batch.calculated_population_count, active_pop)  # Only active BCA counts
        self.assertEqual(self.batch.calculated_avg_weight_g, active_avg_w)  # Only active BCA counts
        expected_biomass = (active_pop * active_avg_w) / Decimal('1000')  # 50.0 kg
        self.assertEqual(self.batch.calculated_biomass_kg, expected_biomass)
        # active_container_count property no longer exists in the Batch model  # Only 1 active container

    def test_deactivate_bca(self):
        """Test Batch calculations when an active BCA is made inactive."""
        assignment_pop = 100
        bca = BatchContainerAssignment.objects.create(
            batch=self.batch,
            container=self.container1,
            lifecycle_stage=self.lc_stage,
            population_count=assignment_pop,
            avg_weight_g=Decimal('50.0'),
            assignment_date=date.today(),
            is_active=True
        )

        self.batch.refresh_from_db()
        self.assertEqual(self.batch.calculated_population_count, assignment_pop)  # Pre-check

        # Make BCA inactive
        bca.is_active = False
        bca.departed_at = date.today()
        bca.save()

        self.batch.refresh_from_db()
        self.assertEqual(self.batch.calculated_population_count, 0)
        self.assertEqual(self.batch.calculated_avg_weight_g, Decimal('0.0'))
        self.assertEqual(self.batch.calculated_biomass_kg, Decimal('0.0'))

    def test_bca_population_change(self):
        """Test Batch calculations when an active BCA's population_count changes."""
        initial_pop = 100
        avg_w = Decimal('50.0')
        bca = BatchContainerAssignment.objects.create(
            batch=self.batch,
            container=self.container1,
            lifecycle_stage=self.lc_stage,
            population_count=initial_pop,
            avg_weight_g=avg_w,
            assignment_date=date.today(),
            is_active=True
        )
        # Initial biomass on BCA: 100 * 50 / 1000 = 5kg

        self.batch.refresh_from_db()
        self.assertEqual(self.batch.calculated_population_count, initial_pop)
        self.assertEqual(self.batch.calculated_avg_weight_g, avg_w)
        self.assertEqual(self.batch.calculated_biomass_kg, bca.biomass_kg)

        # Change population
        updated_pop = 150
        bca.population_count = updated_pop
        bca.save()  # BCA's biomass should now be 150 * 50 / 1000 = 7.5kg

        self.batch.refresh_from_db()
        self.assertEqual(self.batch.calculated_population_count, updated_pop)
        self.assertEqual(self.batch.calculated_avg_weight_g, avg_w)  # Avg weight per fish shouldn't change
        self.assertEqual(self.batch.calculated_biomass_kg, bca.biomass_kg)
        self.assertEqual(bca.biomass_kg, (Decimal(updated_pop) * avg_w) / Decimal(1000))

    def test_bca_avg_weight_change(self):
        """Test Batch calculations when an active BCA's avg_weight_g changes."""
        pop = 100
        initial_avg_w = Decimal('50.0')
        bca = BatchContainerAssignment.objects.create(
            batch=self.batch,
            container=self.container1,
            lifecycle_stage=self.lc_stage,
            population_count=pop,
            avg_weight_g=initial_avg_w,
            assignment_date=date.today(),
            is_active=True
        )
        # Initial biomass on BCA: 100 * 50 / 1000 = 5kg

        self.batch.refresh_from_db()
        self.assertEqual(self.batch.calculated_population_count, pop)
        self.assertEqual(self.batch.calculated_avg_weight_g, initial_avg_w)
        self.assertEqual(self.batch.calculated_biomass_kg, bca.biomass_kg)

        # Change avg_weight_g
        updated_avg_w = Decimal('60.0')
        bca.avg_weight_g = updated_avg_w
        bca.save()  # BCA's biomass should now be 100 * 60 / 1000 = 6kg

        self.batch.refresh_from_db()
        self.assertEqual(self.batch.calculated_population_count, pop)  # Population shouldn't change
        self.assertEqual(self.batch.calculated_avg_weight_g, updated_avg_w)
        self.assertEqual(self.batch.calculated_biomass_kg, bca.biomass_kg)
        self.assertEqual(bca.biomass_kg, (Decimal(pop) * updated_avg_w) / Decimal(1000))

    def test_delete_bca(self):
        """Test Batch calculations when an active BCA is deleted."""
        bca = BatchContainerAssignment.objects.create(
            batch=self.batch,
            container=self.container1,
            lifecycle_stage=self.lc_stage,
            population_count=100,
            avg_weight_g=Decimal('50.0'),
            assignment_date=date.today(),
            is_active=True
        )

        self.batch.refresh_from_db()
        self.assertNotEqual(self.batch.calculated_population_count, 0)  # Pre-check

        bca.delete()

        self.batch.refresh_from_db()
        self.assertEqual(self.batch.calculated_population_count, 0)
        self.assertEqual(self.batch.calculated_avg_weight_g, Decimal('0.0'))
        self.assertEqual(self.batch.calculated_biomass_kg, Decimal('0.0'))
