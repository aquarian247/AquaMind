"""
Tests for container-assignments lifecycle progression endpoint.
"""
from datetime import timedelta
from decimal import Decimal

from rest_framework import status

from tests.base import BaseAPITestCase
from apps.batch.models import BatchContainerAssignment
from apps.batch.tests.api.test_utils import (
    create_test_species,
    create_test_lifecycle_stage,
    create_test_batch,
    create_test_container,
)


class ContainerAssignmentsLifecycleProgressionTestCase(BaseAPITestCase):
    """Test lifecycle progression aggregation bases for batch assignments."""

    def setUp(self):
        super().setUp()

        self.species = create_test_species(name="Atlantic Salmon")
        self.stage_egg = create_test_lifecycle_stage(
            species=self.species, name="Egg&Alevin", order=1
        )
        self.stage_fry = create_test_lifecycle_stage(
            species=self.species, name="Fry", order=2
        )
        self.stage_parr = create_test_lifecycle_stage(
            species=self.species, name="Parr", order=3
        )
        self.stage_smolt = create_test_lifecycle_stage(
            species=self.species, name="Smolt", order=4
        )

        self.batch = create_test_batch(
            species=self.species,
            lifecycle_stage=self.stage_smolt,
            batch_number="BATCH-LC-001",
        )

        self.container_a = create_test_container(name="Lifecycle Tank A")
        self.container_b = create_test_container(name="Lifecycle Tank B")
        self.container_c = create_test_container(name="Lifecycle Tank C")

        def add_assignment(container, lifecycle_stage, day_offset, population, avg_weight, is_active):
            return BatchContainerAssignment.objects.create(
                batch=self.batch,
                container=container,
                lifecycle_stage=lifecycle_stage,
                assignment_date=self.batch.start_date + timedelta(days=day_offset),
                population_count=population,
                avg_weight_g=Decimal(str(avg_weight)),
                is_active=is_active,
                notes="lifecycle progression test",
            )

        # Stage progression with one duplicated container/stage row in Parr.
        add_assignment(self.container_a, self.stage_egg, 0, 1000, 0.0, False)
        add_assignment(self.container_b, self.stage_egg, 0, 1000, 0.0, False)
        add_assignment(self.container_a, self.stage_fry, 60, 900, 10.0, False)
        add_assignment(self.container_b, self.stage_fry, 60, 900, 10.0, False)
        add_assignment(self.container_c, self.stage_parr, 120, 500, 30.0, False)
        add_assignment(self.container_c, self.stage_parr, 130, 450, 35.0, False)
        add_assignment(self.container_c, self.stage_smolt, 180, 400, 80.0, True)

    def _get_url(self, query=""):
        base_url = self.get_api_url("batch", "container-assignments/lifecycle-progression")
        return f"{base_url}?{query}" if query else base_url

    def test_lifecycle_progression_requires_batch(self):
        response = self.client.get(self._get_url())
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("detail", response.data)

    def test_lifecycle_progression_rejects_invalid_basis(self):
        response = self.client.get(
            self._get_url(f"batch={self.batch.id}&basis=not_a_basis")
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("basis", response.data)

    def test_lifecycle_progression_defaults_to_stage_entry(self):
        response = self.client.get(self._get_url(f"batch={self.batch.id}"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["basis"], "stage_entry")

    def test_lifecycle_progression_stage_entry_vs_full_history(self):
        full_history_response = self.client.get(
            self._get_url(f"batch={self.batch.id}&basis=full_history")
        )
        stage_entry_response = self.client.get(
            self._get_url(f"batch={self.batch.id}&basis=stage_entry")
        )

        self.assertEqual(full_history_response.status_code, status.HTTP_200_OK)
        self.assertEqual(stage_entry_response.status_code, status.HTTP_200_OK)

        full_history_stages = {
            stage["lifecycle_stage"]: stage for stage in full_history_response.data["stages"]
        }
        stage_entry_stages = {
            stage["lifecycle_stage"]: stage for stage in stage_entry_response.data["stages"]
        }

        # Parr has two historical rows for one container; stage_entry should count only first entry.
        self.assertEqual(full_history_stages["Parr"]["container_assignments"], 2)
        self.assertEqual(full_history_stages["Parr"]["total_population"], 950)
        self.assertEqual(stage_entry_stages["Parr"]["container_assignments"], 1)
        self.assertEqual(stage_entry_stages["Parr"]["total_population"], 500)

        # Full history totals include duplicated historical population.
        self.assertEqual(full_history_response.data["totals"]["total_population"], 5150)
        self.assertEqual(stage_entry_response.data["totals"]["total_population"], 4700)

    def test_lifecycle_progression_stage_entry_prefers_first_positive_population(self):
        BatchContainerAssignment.objects.create(
            batch=self.batch,
            container=self.container_a,
            lifecycle_stage=self.stage_parr,
            assignment_date=self.batch.start_date + timedelta(days=110),
            population_count=0,
            avg_weight_g=Decimal("0"),
            is_active=False,
            notes="stage entry zero placeholder",
        )
        BatchContainerAssignment.objects.create(
            batch=self.batch,
            container=self.container_a,
            lifecycle_stage=self.stage_parr,
            assignment_date=self.batch.start_date + timedelta(days=111),
            population_count=700,
            avg_weight_g=Decimal("40"),
            is_active=False,
            notes="stage entry first positive",
        )

        stage_entry_response = self.client.get(
            self._get_url(f"batch={self.batch.id}&basis=stage_entry")
        )
        self.assertEqual(stage_entry_response.status_code, status.HTTP_200_OK)

        stage_entry_stages = {
            stage["lifecycle_stage"]: stage for stage in stage_entry_response.data["stages"]
        }
        self.assertEqual(stage_entry_stages["Parr"]["container_assignments"], 2)
        self.assertEqual(stage_entry_stages["Parr"]["total_population"], 1200)
        self.assertEqual(stage_entry_response.data["totals"]["total_population"], 5400)

    def test_lifecycle_progression_active_snapshot(self):
        response = self.client.get(
            self._get_url(f"batch={self.batch.id}&basis=active_snapshot")
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["basis"], "active_snapshot")

        self.assertEqual(len(response.data["stages"]), 1)
        smolt_stage = response.data["stages"][0]
        self.assertEqual(smolt_stage["lifecycle_stage"], "Smolt")
        self.assertEqual(smolt_stage["container_assignments"], 1)
        self.assertEqual(smolt_stage["active_containers"], 1)
        self.assertEqual(smolt_stage["total_population"], 400)
        self.assertEqual(response.data["totals"]["total_population"], 400)
