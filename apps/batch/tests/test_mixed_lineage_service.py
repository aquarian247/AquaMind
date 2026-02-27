from datetime import date, timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from apps.batch.models import BatchComposition, BatchMixEvent, BatchMixEventComponent
from apps.batch.services.mixed_lineage import MixedLineageService
from apps.batch.tests.api.test_utils import (
    create_test_batch,
    create_test_batch_container_assignment,
    create_test_container,
    create_test_lifecycle_stage,
    create_test_species,
)


class MixedLineageServiceTestCase(TestCase):
    def setUp(self):
        self.species = create_test_species(name="Atlantic Salmon")
        self.lifecycle_stage = create_test_lifecycle_stage(
            species=self.species,
            name="Fry",
            order=2,
        )

    def _create_mixed_batch(self, batch_number: str):
        batch = create_test_batch(
            species=self.species,
            lifecycle_stage=self.lifecycle_stage,
            batch_number=batch_number,
        )
        batch.batch_type = "MIXED"
        batch.save(update_fields=["batch_type"])
        return batch

    def test_standard_batch_returns_self_as_root(self):
        batch = create_test_batch(
            species=self.species,
            lifecycle_stage=self.lifecycle_stage,
            batch_number="STD-1",
        )

        payload = MixedLineageService.build_lineage(batch=batch, as_of_date=date.today())

        self.assertEqual(payload["root_sources"], [
            {
                "batch_id": batch.id,
                "batch_number": "STD-1",
                "percentage": "100.00",
            }
        ])
        self.assertEqual(payload["max_depth"], 0)
        self.assertEqual(payload["graph"]["mix_nodes"], [])

    def test_recursive_compounded_shares_are_flattened(self):
        # M1 = A(60) + B(40), M2 = M1(50) + C(50) => A(30), B(20), C(50)
        batch_a = create_test_batch(
            species=self.species,
            lifecycle_stage=self.lifecycle_stage,
            batch_number="A",
        )
        batch_b = create_test_batch(
            species=self.species,
            lifecycle_stage=self.lifecycle_stage,
            batch_number="B",
        )
        batch_c = create_test_batch(
            species=self.species,
            lifecycle_stage=self.lifecycle_stage,
            batch_number="C",
        )
        mixed_1 = self._create_mixed_batch("M1")
        mixed_2 = self._create_mixed_batch("M2")

        container_1 = create_test_container(name="ML-Tank-1")
        container_2 = create_test_container(name="ML-Tank-2")
        container_3 = create_test_container(name="ML-Tank-3")
        container_4 = create_test_container(name="ML-Tank-4")

        assignment_a = create_test_batch_container_assignment(
            batch=batch_a,
            container=container_1,
            lifecycle_stage=self.lifecycle_stage,
            population_count=600,
            avg_weight_g=Decimal("10.0"),
        )
        assignment_b = create_test_batch_container_assignment(
            batch=batch_b,
            container=container_2,
            lifecycle_stage=self.lifecycle_stage,
            population_count=400,
            avg_weight_g=Decimal("10.0"),
        )
        assignment_c = create_test_batch_container_assignment(
            batch=batch_c,
            container=container_3,
            lifecycle_stage=self.lifecycle_stage,
            population_count=500,
            avg_weight_g=Decimal("10.0"),
        )
        assignment_m1 = create_test_batch_container_assignment(
            batch=mixed_1,
            container=container_4,
            lifecycle_stage=self.lifecycle_stage,
            population_count=500,
            avg_weight_g=Decimal("10.0"),
        )

        mix_1 = BatchMixEvent.objects.create(
            mixed_batch=mixed_1,
            container=container_4,
            mixed_at=timezone.now() - timedelta(days=2),
        )
        BatchMixEventComponent.objects.create(
            mix_event=mix_1,
            source_assignment=assignment_a,
            source_batch=batch_a,
            population_count=600,
            biomass_kg=Decimal("6.0"),
            percentage=Decimal("60.0"),
            is_transferred_in=True,
        )
        BatchMixEventComponent.objects.create(
            mix_event=mix_1,
            source_assignment=assignment_b,
            source_batch=batch_b,
            population_count=400,
            biomass_kg=Decimal("4.0"),
            percentage=Decimal("40.0"),
            is_transferred_in=False,
        )

        mix_2 = BatchMixEvent.objects.create(
            mixed_batch=mixed_2,
            container=container_4,
            mixed_at=timezone.now() - timedelta(days=1),
        )
        BatchMixEventComponent.objects.create(
            mix_event=mix_2,
            source_assignment=assignment_m1,
            source_batch=mixed_1,
            population_count=500,
            biomass_kg=Decimal("5.0"),
            percentage=Decimal("50.0"),
            is_transferred_in=True,
        )
        BatchMixEventComponent.objects.create(
            mix_event=mix_2,
            source_assignment=assignment_c,
            source_batch=batch_c,
            population_count=500,
            biomass_kg=Decimal("5.0"),
            percentage=Decimal("50.0"),
            is_transferred_in=False,
        )

        payload = MixedLineageService.build_lineage(batch=mixed_2, as_of_date=date.today())
        root_by_number = {
            item["batch_number"]: Decimal(item["percentage"])
            for item in payload["root_sources"]
        }

        self.assertEqual(root_by_number["A"], Decimal("30.00"))
        self.assertEqual(root_by_number["B"], Decimal("20.00"))
        self.assertEqual(root_by_number["C"], Decimal("50.00"))
        self.assertEqual(payload["max_depth"], 2)
        self.assertEqual(len(payload["graph"]["mix_nodes"]), 2)

    def test_latest_mix_event_is_chosen_by_as_of_date(self):
        batch_a = create_test_batch(
            species=self.species,
            lifecycle_stage=self.lifecycle_stage,
            batch_number="ASOF-A",
        )
        batch_b = create_test_batch(
            species=self.species,
            lifecycle_stage=self.lifecycle_stage,
            batch_number="ASOF-B",
        )
        mixed = self._create_mixed_batch("ASOF-MIX")

        container = create_test_container(name="ML-Tank-ASOF")
        assignment_a = create_test_batch_container_assignment(
            batch=batch_a,
            container=container,
            lifecycle_stage=self.lifecycle_stage,
            population_count=100,
            avg_weight_g=Decimal("10.0"),
        )
        assignment_b = create_test_batch_container_assignment(
            batch=batch_b,
            container=container,
            lifecycle_stage=self.lifecycle_stage,
            population_count=100,
            avg_weight_g=Decimal("10.0"),
        )

        older_event = BatchMixEvent.objects.create(
            mixed_batch=mixed,
            container=container,
            mixed_at=timezone.now() - timedelta(days=5),
        )
        BatchMixEventComponent.objects.create(
            mix_event=older_event,
            source_assignment=assignment_a,
            source_batch=batch_a,
            population_count=100,
            biomass_kg=Decimal("1.0"),
            percentage=Decimal("100.0"),
            is_transferred_in=True,
        )

        newer_event = BatchMixEvent.objects.create(
            mixed_batch=mixed,
            container=container,
            mixed_at=timezone.now() - timedelta(days=1),
        )
        BatchMixEventComponent.objects.create(
            mix_event=newer_event,
            source_assignment=assignment_b,
            source_batch=batch_b,
            population_count=100,
            biomass_kg=Decimal("1.0"),
            percentage=Decimal("100.0"),
            is_transferred_in=True,
        )

        before_newer = MixedLineageService.build_lineage(
            batch=mixed,
            as_of_date=(timezone.now() - timedelta(days=3)).date(),
        )
        self.assertEqual(before_newer["root_sources"], [
            {
                "batch_id": batch_a.id,
                "batch_number": "ASOF-A",
                "percentage": "100.00",
            }
        ])

        after_newer = MixedLineageService.build_lineage(
            batch=mixed,
            as_of_date=timezone.now().date(),
        )
        self.assertEqual(after_newer["root_sources"], [
            {
                "batch_id": batch_b.id,
                "batch_number": "ASOF-B",
                "percentage": "100.00",
            }
        ])

    def test_composition_fallback_used_when_no_mix_event(self):
        source_1 = create_test_batch(
            species=self.species,
            lifecycle_stage=self.lifecycle_stage,
            batch_number="COMP-1",
        )
        source_2 = create_test_batch(
            species=self.species,
            lifecycle_stage=self.lifecycle_stage,
            batch_number="COMP-2",
        )
        mixed = self._create_mixed_batch("COMP-MIX")

        BatchComposition.objects.create(
            mixed_batch=mixed,
            source_batch=source_1,
            percentage=Decimal("70.0"),
            population_count=700,
            biomass_kg=Decimal("7.0"),
        )
        BatchComposition.objects.create(
            mixed_batch=mixed,
            source_batch=source_2,
            percentage=Decimal("30.0"),
            population_count=300,
            biomass_kg=Decimal("3.0"),
        )

        payload = MixedLineageService.build_lineage(batch=mixed, as_of_date=date.today())

        self.assertEqual(payload["root_sources"], [
            {"batch_id": source_1.id, "batch_number": "COMP-1", "percentage": "70.00"},
            {"batch_id": source_2.id, "batch_number": "COMP-2", "percentage": "30.00"},
        ])
        self.assertIn(
            "Resolved from BatchComposition fallback (no qualifying BatchMixEvent).",
            payload["boundaries"]["resolution_notes"],
        )

    def test_mixed_batch_without_sources_is_marked_unresolved(self):
        mixed = self._create_mixed_batch("UNRESOLVED-MIX")

        payload = MixedLineageService.build_lineage(batch=mixed, as_of_date=date.today())

        self.assertEqual(payload["unresolved_batches"], [mixed.id])
        self.assertEqual(payload["root_sources"], [
            {
                "batch_id": mixed.id,
                "batch_number": "UNRESOLVED-MIX",
                "percentage": "100.00",
            }
        ])
        self.assertIn(
            "No BatchMixEvent or BatchComposition available; lineage unresolved at this batch.",
            payload["boundaries"]["resolution_notes"],
        )

    def test_component_percentages_are_normalized_when_total_not_100(self):
        source_1 = create_test_batch(
            species=self.species,
            lifecycle_stage=self.lifecycle_stage,
            batch_number="NORM-1",
        )
        source_2 = create_test_batch(
            species=self.species,
            lifecycle_stage=self.lifecycle_stage,
            batch_number="NORM-2",
        )
        mixed = self._create_mixed_batch("NORM-MIX")
        container = create_test_container(name="ML-Tank-NORM")

        assignment_1 = create_test_batch_container_assignment(
            batch=source_1,
            container=container,
            lifecycle_stage=self.lifecycle_stage,
            population_count=100,
            avg_weight_g=Decimal("10.0"),
        )
        assignment_2 = create_test_batch_container_assignment(
            batch=source_2,
            container=container,
            lifecycle_stage=self.lifecycle_stage,
            population_count=100,
            avg_weight_g=Decimal("10.0"),
        )
        mix_event = BatchMixEvent.objects.create(
            mixed_batch=mixed,
            container=container,
            mixed_at=timezone.now() - timedelta(days=1),
        )
        BatchMixEventComponent.objects.create(
            mix_event=mix_event,
            source_assignment=assignment_1,
            source_batch=source_1,
            population_count=100,
            biomass_kg=Decimal("1.0"),
            percentage=Decimal("30.0"),
            is_transferred_in=True,
        )
        BatchMixEventComponent.objects.create(
            mix_event=mix_event,
            source_assignment=assignment_2,
            source_batch=source_2,
            population_count=100,
            biomass_kg=Decimal("1.0"),
            percentage=Decimal("30.0"),
            is_transferred_in=False,
        )

        payload = MixedLineageService.build_lineage(batch=mixed, as_of_date=date.today())
        roots = {
            row["batch_number"]: Decimal(row["percentage"])
            for row in payload["root_sources"]
        }
        self.assertEqual(roots["NORM-1"], Decimal("50.00"))
        self.assertEqual(roots["NORM-2"], Decimal("50.00"))

    def test_cycle_is_detected_and_marked_unresolved(self):
        mixed_a = self._create_mixed_batch("CYCLE-A")
        mixed_b = self._create_mixed_batch("CYCLE-B")
        container = create_test_container(name="ML-Tank-CYCLE")

        assignment_a = create_test_batch_container_assignment(
            batch=mixed_a,
            container=container,
            lifecycle_stage=self.lifecycle_stage,
            population_count=100,
            avg_weight_g=Decimal("10.0"),
        )
        assignment_b = create_test_batch_container_assignment(
            batch=mixed_b,
            container=container,
            lifecycle_stage=self.lifecycle_stage,
            population_count=100,
            avg_weight_g=Decimal("10.0"),
        )

        mix_a = BatchMixEvent.objects.create(
            mixed_batch=mixed_a,
            container=container,
            mixed_at=timezone.now() - timedelta(days=2),
        )
        BatchMixEventComponent.objects.create(
            mix_event=mix_a,
            source_assignment=assignment_b,
            source_batch=mixed_b,
            population_count=100,
            biomass_kg=Decimal("1.0"),
            percentage=Decimal("100.0"),
            is_transferred_in=True,
        )

        mix_b = BatchMixEvent.objects.create(
            mixed_batch=mixed_b,
            container=container,
            mixed_at=timezone.now() - timedelta(days=1),
        )
        BatchMixEventComponent.objects.create(
            mix_event=mix_b,
            source_assignment=assignment_a,
            source_batch=mixed_a,
            population_count=100,
            biomass_kg=Decimal("1.0"),
            percentage=Decimal("100.0"),
            is_transferred_in=True,
        )

        payload = MixedLineageService.build_lineage(batch=mixed_a, as_of_date=date.today())

        self.assertIn(mixed_a.id, payload["unresolved_batches"])
        self.assertIn(
            "Cycle detected in lineage graph; cycle node treated as unresolved terminal.",
            payload["boundaries"]["resolution_notes"],
        )
        self.assertEqual(payload["max_depth"], 2)
