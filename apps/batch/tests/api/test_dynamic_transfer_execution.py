"""API tests for dynamic FW->Sea execution flow."""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from django.test import override_settings
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.batch.models import BatchContainerAssignment, BatchTransferWorkflow, TransferAction
from apps.batch.tests.models.test_utils import (
    create_test_batch,
    create_test_container_type,
    create_test_geography,
    create_test_lifecycle_stage,
    create_test_species,
    create_test_user,
)
from apps.environmental.models import EnvironmentalParameter, EnvironmentalReading
from apps.historian.models import HistorianTag, HistorianTagLink
from apps.infrastructure.models import Area, Container, FreshwaterStation, Hall, TransportCarrier
from apps.users.models import Geography as UserGeography, Role


def _create_assignment(*, batch, container, lifecycle_stage, population, avg_weight):
    return BatchContainerAssignment.objects.create(
        batch=batch,
        container=container,
        lifecycle_stage=lifecycle_stage,
        population_count=population,
        avg_weight_g=Decimal(avg_weight),
        assignment_date=timezone.now().date(),
        is_active=True,
        notes="test-assignment",
    )


class DynamicTransferExecutionApiTests(APITestCase):
    """Covers start/complete handoff + compliance policy behavior."""

    def setUp(self):
        self.user = create_test_user(
            geography=UserGeography.ALL,
            role=Role.ADMIN,
            username="dynamic_admin",
        )
        self.client.force_authenticate(self.user)

        geography = create_test_geography("Dynamic Geo")
        station = FreshwaterStation.objects.create(
            name="FW-Station",
            station_type="FRESHWATER",
            geography=geography,
            latitude=Decimal("62.0001"),
            longitude=Decimal("-6.7713"),
        )
        hall = Hall.objects.create(name="Hall-A", freshwater_station=station)
        area = Area.objects.create(
            name="Area-A",
            geography=geography,
            latitude=Decimal("62.0500"),
            longitude=Decimal("-6.7500"),
            max_biomass=Decimal("50000.00"),
            active=True,
        )
        truck = TransportCarrier.objects.create(
            name="Truck-1",
            carrier_type="TRUCK",
            geography=geography,
            capacity_m3=Decimal("20.00"),
            active=True,
        )
        vessel = TransportCarrier.objects.create(
            name="Vessel-1",
            carrier_type="VESSEL",
            geography=geography,
            capacity_m3=Decimal("100.00"),
            active=True,
        )
        ctype = create_test_container_type("Transport Tank")
        self.station_container = Container.objects.create(
            name="S-Tank-01",
            container_type=ctype,
            hall=hall,
            volume_m3=Decimal("20.00"),
            max_biomass_kg=Decimal("12000.00"),
            active=True,
        )
        self.truck_container = Container.objects.create(
            name="T-Tank-01",
            container_type=ctype,
            carrier=truck,
            volume_m3=Decimal("15.00"),
            max_biomass_kg=Decimal("9000.00"),
            active=True,
        )
        self.vessel_container = Container.objects.create(
            name="V-Tank-01",
            container_type=ctype,
            carrier=vessel,
            volume_m3=Decimal("30.00"),
            max_biomass_kg=Decimal("18000.00"),
            active=True,
        )
        self.ring_container = Container.objects.create(
            name="Ring-A1",
            container_type=ctype,
            area=area,
            volume_m3=Decimal("90.00"),
            max_biomass_kg=Decimal("100000.00"),
            active=True,
        )

        species = create_test_species("Dynamic Salmon")
        self.smolt = create_test_lifecycle_stage(species=species, name="Smolt", order=3)
        self.adult = create_test_lifecycle_stage(species=species, name="Adult", order=6)
        self.batch = create_test_batch(
            species=species,
            lifecycle_stage=self.smolt,
            batch_number="DYN-BATCH-001",
        )
        self.source_assignment = _create_assignment(
            batch=self.batch,
            container=self.station_container,
            lifecycle_stage=self.smolt,
            population=10000,
            avg_weight="50.00",
        )

        self.workflow = BatchTransferWorkflow.objects.create(
            workflow_number="TRF-DYN-001",
            batch=self.batch,
            workflow_type="LIFECYCLE_TRANSITION",
            source_lifecycle_stage=self.smolt,
            dest_lifecycle_stage=self.adult,
            planned_start_date=timezone.now().date(),
            status="PLANNED",
            is_dynamic_execution=True,
            dynamic_route_mode="VIA_TRUCK_TO_VESSEL",
            estimated_total_count=10000,
            estimated_total_biomass_kg=Decimal("500.00"),
            initiated_by=self.user,
        )

        self.oxygen = EnvironmentalParameter.objects.create(name="Oxygen", unit="mg/L")
        self.temperature = EnvironmentalParameter.objects.create(name="Temperature", unit="C")
        self.co2 = EnvironmentalParameter.objects.create(name="CO2", unit="mg/L")

        self._seed_mapping_and_readings(self.station_container)
        self._seed_mapping_and_readings(self.truck_container)
        self._seed_mapping_and_readings(self.vessel_container)
        self._seed_mapping_and_readings(self.ring_container)

    def _seed_mapping_and_readings(self, container):
        for param, value in (
            (self.oxygen, Decimal("9.10")),
            (self.temperature, Decimal("11.50")),
            (self.co2, Decimal("3.20")),
        ):
            tag = HistorianTag.objects.create(tag_name=f"{container.name}-{param.name}")
            HistorianTagLink.objects.create(
                tag=tag,
                container=container,
                parameter=param,
            )
            EnvironmentalReading.objects.create(
                parameter=param,
                container=container,
                batch=self.batch,
                value=value,
                reading_time=timezone.now() - timedelta(minutes=5),
                is_manual=False,
                notes="baseline reading",
            )

    def _start_url(self):
        return f"/api/v1/batch/transfer-workflows/{self.workflow.id}/handoffs/start/"

    def _complete_url(self, action_id):
        return f"/api/v1/batch/transfer-actions/{action_id}/complete-handoff/"

    def _context_url(self):
        return f"/api/v1/batch/transfer-workflows/{self.workflow.id}/execution-context/"

    def _workflow_complete_dynamic_url(self):
        return f"/api/v1/batch/transfer-workflows/{self.workflow.id}/complete-dynamic/"

    def test_start_and_complete_handoff_flow(self):
        start_payload = {
            "leg_type": "STATION_TO_TRUCK",
            "source_assignment_id": self.source_assignment.id,
            "dest_container_id": self.truck_container.id,
            "planned_transferred_count": 10000,
            "planned_transferred_biomass_kg": "500.00",
            "transfer_method": "PUMP",
        }
        start_response = self.client.post(self._start_url(), start_payload, format="json")
        self.assertEqual(
            start_response.status_code,
            status.HTTP_200_OK,
            msg=f"start response: {start_response.data}",
        )
        self.assertEqual(start_response.data["action"]["status"], "IN_PROGRESS")
        self.assertEqual(start_response.data["action"]["created_via"], "DYNAMIC_LIVE")
        self.assertGreaterEqual(start_response.data["snapshot_summary"]["created_count"], 6)

        action_id = start_response.data["action"]["id"]
        complete_response = self.client.post(
            self._complete_url(action_id),
            {
                "transferred_count": 9000,
                "transferred_biomass_kg": "450.00",
                "mortality_during_transfer": 100,
                "transfer_method": "PUMP",
            },
            format="json",
        )
        self.assertEqual(complete_response.status_code, status.HTTP_200_OK)

        action = TransferAction.objects.get(id=action_id)
        self.assertEqual(action.status, "COMPLETED")
        self.assertEqual(action.leg_type, "STATION_TO_TRUCK")
        self.assertIsNotNone(action.executed_at)

        self.source_assignment.refresh_from_db()
        self.assertEqual(self.source_assignment.population_count, 900)

        dest_assignment = action.dest_assignment
        self.assertIsNotNone(dest_assignment)
        self.assertEqual(dest_assignment.container_id, self.truck_container.id)
        self.assertEqual(dest_assignment.population_count, 9000)

        self.workflow.refresh_from_db()
        self.assertEqual(self.workflow.status, "IN_PROGRESS")
        self.assertEqual(self.workflow.actions_completed, 1)

        complete_wf_response = self.client.post(
            self._workflow_complete_dynamic_url(),
            {"completion_note": "Operation finished after manual tally."},
            format="json",
        )
        self.assertEqual(complete_wf_response.status_code, status.HTTP_200_OK)
        self.workflow.refresh_from_db()
        self.assertEqual(self.workflow.status, "COMPLETED")
        self.assertEqual(self.workflow.dynamic_completed_by_id, self.user.id)
        self.assertIsNotNone(self.workflow.dynamic_completed_at)

    def test_second_start_on_same_source_is_blocked(self):
        payload = {
            "leg_type": "STATION_TO_TRUCK",
            "source_assignment_id": self.source_assignment.id,
            "dest_container_id": self.truck_container.id,
            "planned_transferred_count": 5000,
            "planned_transferred_biomass_kg": "250.00",
        }
        first = self.client.post(self._start_url(), payload, format="json")
        self.assertEqual(
            first.status_code,
            status.HTTP_200_OK,
            msg=f"first start response: {first.data}",
        )

        second = self.client.post(self._start_url(), payload, format="json")
        self.assertEqual(second.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("already has an IN_PROGRESS handoff", str(second.data))

    def test_dynamic_execution_context_truck_source_only_after_upstream_complete(self):
        baseline = self.client.get(self._context_url())
        self.assertEqual(baseline.status_code, status.HTTP_200_OK)
        self.assertEqual(len(baseline.data["sources"]["truck"]), 0)

        start = self.client.post(
            self._start_url(),
            {
                "leg_type": "STATION_TO_TRUCK",
                "source_assignment_id": self.source_assignment.id,
                "dest_container_id": self.truck_container.id,
                "planned_transferred_count": 2000,
                "planned_transferred_biomass_kg": "100.00",
            },
            format="json",
        )
        self.assertEqual(
            start.status_code,
            status.HTTP_200_OK,
            msg=f"context start response: {start.data}",
        )
        action_id = start.data["action"]["id"]

        during = self.client.get(self._context_url())
        self.assertEqual(during.status_code, status.HTTP_200_OK)
        self.assertEqual(len(during.data["sources"]["truck"]), 0)

        completed = self.client.post(
            self._complete_url(action_id),
            {
                "transferred_count": 2000,
                "transferred_biomass_kg": "100.00",
                "mortality_during_transfer": 0,
            },
            format="json",
        )
        self.assertEqual(completed.status_code, status.HTTP_200_OK)

        after = self.client.get(self._context_url())
        self.assertEqual(after.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(after.data["sources"]["truck"]), 1)

    @override_settings(TRANSFER_START_MISSING_MAPPING_POLICY="STRICT")
    def test_strict_policy_blocks_missing_mapping(self):
        HistorianTagLink.objects.filter(
            container=self.truck_container,
            parameter=self.co2,
        ).delete()

        response = self.client.post(
            self._start_url(),
            {
                "leg_type": "STATION_TO_TRUCK",
                "source_assignment_id": self.source_assignment.id,
                "dest_container_id": self.truck_container.id,
                "planned_transferred_count": 1000,
                "planned_transferred_biomass_kg": "50.00",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(TransferAction.objects.count(), 0)
        self.assertIn("missing_historian_mapping", str(response.data))

    @override_settings(TRANSFER_START_MISSING_MAPPING_POLICY="OVERRIDE")
    def test_override_policy_requires_note_and_privileged_user(self):
        HistorianTagLink.objects.filter(
            container=self.truck_container,
            parameter=self.co2,
        ).delete()

        blocked = self.client.post(
            self._start_url(),
            {
                "leg_type": "STATION_TO_TRUCK",
                "source_assignment_id": self.source_assignment.id,
                "dest_container_id": self.truck_container.id,
                "planned_transferred_count": 1000,
                "planned_transferred_biomass_kg": "50.00",
            },
            format="json",
        )
        self.assertEqual(blocked.status_code, status.HTTP_400_BAD_REQUEST)

        missing_note = self.client.post(
            self._start_url(),
            {
                "leg_type": "STATION_TO_TRUCK",
                "source_assignment_id": self.source_assignment.id,
                "dest_container_id": self.truck_container.id,
                "planned_transferred_count": 1000,
                "planned_transferred_biomass_kg": "50.00",
                "allow_compliance_override": True,
            },
            format="json",
        )
        self.assertEqual(missing_note.status_code, status.HTTP_400_BAD_REQUEST)

        allowed = self.client.post(
            self._start_url(),
            {
                "leg_type": "STATION_TO_TRUCK",
                "source_assignment_id": self.source_assignment.id,
                "dest_container_id": self.truck_container.id,
                "planned_transferred_count": 1000,
                "planned_transferred_biomass_kg": "50.00",
                "allow_compliance_override": True,
                "compliance_override_note": "CO2 tag pending commissioning.",
            },
            format="json",
        )
        self.assertEqual(allowed.status_code, status.HTTP_200_OK)
        self.assertTrue(allowed.data["snapshot_summary"]["override_applied"])

    @override_settings(TRANSFER_START_MISSING_MAPPING_POLICY="OVERRIDE")
    def test_start_accepts_manual_readings_for_source_and_destination(self):
        HistorianTagLink.objects.filter(container=self.station_container).delete()
        HistorianTagLink.objects.filter(container=self.truck_container).delete()

        response = self.client.post(
            self._start_url(),
            {
                "leg_type": "STATION_TO_TRUCK",
                "source_assignment_id": self.source_assignment.id,
                "dest_container_id": self.truck_container.id,
                "planned_transferred_count": 1000,
                "planned_transferred_biomass_kg": "50.00",
                "allow_compliance_override": True,
                "compliance_override_note": "Local testing without AVEVA mappings.",
                "source_manual_readings": {
                    "oxygen": "8.80",
                    "temperature": "11.20",
                    "co2": "2.60",
                },
                "dest_manual_readings": {
                    "oxygen": "8.40",
                    "temperature": "10.90",
                    "co2": "2.80",
                },
            },
            format="json",
        )
        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
            msg=f"manual reading response: {response.data}",
        )
        summary = response.data["snapshot_summary"]
        self.assertTrue(summary["override_applied"])
        self.assertEqual(summary["manual_input_count"], 6)
        self.assertGreaterEqual(summary["created_count"], 6)

        action_id = response.data["action"]["id"]
        notes_marker = f"[transfer_snapshot] action={action_id};"
        readings = (
            EnvironmentalReading.objects.filter(
                notes__contains=notes_marker,
                is_manual=True,
            )
            .filter(notes__contains="mandatory_start=true")
        )
        self.assertEqual(readings.count(), 6)
        self.assertTrue(
            readings.filter(
                container=self.station_container,
                parameter=self.oxygen,
                value=Decimal("8.80"),
            ).exists()
        )
        self.assertTrue(
            readings.filter(
                container=self.truck_container,
                parameter=self.temperature,
                value=Decimal("10.90"),
            ).exists()
        )

    def test_deprecated_dynamic_create_path_is_blocked(self):
        response = self.client.post(
            "/api/v1/batch/transfer-actions/",
            {
                "workflow": self.workflow.id,
                "action_number": 1,
                "source_assignment": self.source_assignment.id,
                "dest_container": self.truck_container.id,
                "source_population_before": 10000,
                "transferred_count": 500,
                "transferred_biomass_kg": "25.00",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("deprecated", str(response.data).lower())
