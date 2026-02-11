#!/usr/bin/env python3
# flake8: noqa
"""Bulk extract all relevant FishTalk data to CSV files.

This script extracts FishTalk data in bulk for subsequent ETL migration:
- Single Docker connection with multiple queries
- Chunked extraction for large tables (>1M rows)
- Streams directly to CSV (no full dataset in memory)
- Progress reporting with estimated completion time

Usage:
    # Extract all tables
    python bulk_extract_fishtalk.py --output scripts/migration/data/extract/
    
    # Extract specific tables only
    python bulk_extract_fishtalk.py --output scripts/migration/data/extract/ --tables daily_readings,time_readings
    
    # Dry run to estimate volumes
    python bulk_extract_fishtalk.py --output scripts/migration/data/extract/ --dry-run

Output directory structure:
    scripts/migration/data/extract/
    ├── populations.csv               # ~350K rows
    ├── population_stages.csv         # ~150K rows
    ├── containers.csv                # ~17K rows
    ├── org_units.csv                 # ~100 rows
    ├── status_values.csv             # ~8M rows
    ├── daily_sensor_readings.csv     # ~50M rows -> is_manual=True
    ├── time_sensor_readings.csv      # ~50M rows -> is_manual=False
    ├── mortality_actions.csv         # ~5M rows
    ├── feeding_actions.csv           # ~5M rows
    ├── feeding_hand_weights.csv      # ~500K rows
    ├── public_weight_samples.csv     # ~1M rows (PublicWeightSamples)
    ├── ext_weight_samples_v2.csv     # ~1M rows (Ext_WeightSamples_v2)
    ├── transfer_operations.csv       # ~50K rows (legacy PublicTransfers operations)
    ├── transfer_edges.csv            # ~100K rows (legacy PublicTransfers - broken since Jan 2023)
    ├── sub_transfers.csv             # ~205K rows (SubTransfers - active through 2025, for chain stitching)
    ├── operation_stage_changes.csv   # ~27K rows (OperationProductionStageChange for stage timeline)
    ├── production_stages.csv         # ~100 rows (reference)
    ├── public_operation_types.csv    # ~? rows (PublicOperationTypes reference)
    ├── ext_inputs.csv                # ~350K rows (Ext_Inputs_v2 - TRUE biological batch identifier)
    ├── ext_populations.csv           # ~350K rows (Ext_Populations_v2 - population name metadata)
    ├── fish_group_history.csv        # ~221K rows (FishGroupHistory - population to input project)
    ├── input_projects.csv            # ~2K rows (InputProjects - fish group/project anchor)
    ├── population_links.csv          # ~? rows (PopulationLink - FW→Sea linking hints)
    ├── internal_delivery.csv         # ~3K rows (InternalDelivery - FW→Sea delivery header)
    ├── internal_delivery_operations.csv # ~? rows (Operations linked to InternalDelivery)
    ├── internal_delivery_actions.csv # ~? rows (Actions linked to InternalDelivery)
    ├── internal_delivery_action_metadata.csv # ~? rows (ActionMetaData for InternalDelivery ops; params 184/220)
    ├── internal_delivery_planned_activities.csv # ~? rows (PlannedActivities linked to InternalDelivery)
    ├── contacts.csv                  # ~? rows (Contact entities for ActionMetaData(220) GUID lookup)
    ├── contact_types.csv             # ~? rows (Contact type IDs for Contact entities)
    ├── transport_carriers.csv        # ~41 rows (TransportCarrier - carrier name/code)
    ├── transport_methods.csv         # ~14 rows (TransportMethods - transport method metadata)
    ├── ext_transporters.csv          # ~? rows (Ext_Transporters_v2 - transporter names)
    ├── ext_transfers.csv             # ~? rows (Ext_Transfers_v2 - transfer totals)
    ├── plan_transfers.csv            # ~? rows (PlanTransfer - planning transfers)
    ├── reason_for_transfer.csv       # ~? rows (ReasonForTransfer reference)
    ├── wrasse_pop_transfers.csv      # ~? rows (WrassePopTransfer - wrasse transfers by pop)
    ├── wrasse_transfers.csv          # ~? rows (WrasseTransfer - wrasse transfers by container)
    ├── ff_bio_transfers.csv          # ~? rows (FFBioTransfer - financial transfer rollup)
    ├── ff_costing_bio_transfers.csv  # ~? rows (FFCostingBioTransfer - financial transfer deltas)
    ├── ff_costing_bio_transfer_attribute_counts.csv # ~? rows (FFCostingBioTransferAttributeCounts)
    └── grouped_organisation.csv      # ~17K rows (Ext_GroupedOrganisation_v2 - site/hall grouping)
"""

from __future__ import annotations

import argparse
import csv
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aquamind.settings")

from scripts.migration.extractors.base import BaseExtractor, ExtractionContext

# Table configurations
# Format: (name, query, headers, estimated_rows, chunk_size)
# chunk_size=0 means extract all at once
TABLE_CONFIGS = {
    "populations": {
        "query": """
            SELECT 
                CONVERT(varchar(36), PopulationID) AS PopulationID,
                CONVERT(varchar(50), ProjectNumber) AS ProjectNumber,
                CONVERT(varchar(10), InputYear) AS InputYear,
                CONVERT(varchar(10), RunningNumber) AS RunningNumber,
                CONVERT(varchar(36), ContainerID) AS ContainerID,
                CONVERT(varchar(100), Species) AS Species,
                CONVERT(varchar(19), StartTime, 120) AS StartTime,
                CONVERT(varchar(19), EndTime, 120) AS EndTime
            FROM dbo.Populations
            ORDER BY StartTime ASC
        """,
        "headers": ["PopulationID", "ProjectNumber", "InputYear", "RunningNumber", 
                   "ContainerID", "Species", "StartTime", "EndTime"],
        "estimated_rows": 350000,
        "chunk_size": 0,  # Small enough to extract at once
    },
    "population_stages": {
        "query": """
            SELECT 
                CONVERT(varchar(36), PopulationID) AS PopulationID,
                CONVERT(varchar(36), StageID) AS StageID,
                CONVERT(varchar(19), StartTime, 120) AS StartTime
            FROM dbo.PopulationProductionStages
            ORDER BY StartTime ASC
        """,
        "headers": ["PopulationID", "StageID", "StartTime"],
        "estimated_rows": 150000,
        "chunk_size": 0,
    },
    "production_stages": {
        "query": """
            SELECT 
                CONVERT(varchar(36), StageID) AS StageID,
                CONVERT(varchar(100), StageName) AS StageName
            FROM dbo.ProductionStages
        """,
        "headers": ["StageID", "StageName"],
        "estimated_rows": 100,
        "chunk_size": 0,
    },
    "public_operation_types": {
        "query": """
            SELECT
                CONVERT(varchar(10), OperationType) AS OperationType,
                CONVERT(varchar(10), TextID) AS TextID,
                ISNULL(Text, '') AS Text
            FROM dbo.PublicOperationTypes
        """,
        "headers": ["OperationType", "TextID", "Text"],
        "estimated_rows": 200,
        "chunk_size": 0,
    },
    "containers": {
        "query": """
            SELECT 
                CONVERT(varchar(36), c.ContainerID) AS ContainerID,
                CONVERT(varchar(200), c.ContainerName) AS ContainerName,
                CONVERT(varchar(36), c.OrgUnitID) AS OrgUnitID,
                CONVERT(varchar(50), c.OfficialID) AS OfficialID,
                CONVERT(varchar(50), c.ContainerType) AS ContainerType,
                CONVERT(varchar(36), c.GroupID) AS GroupID
            FROM dbo.Containers c
        """,
        "headers": ["ContainerID", "ContainerName", "OrgUnitID", "OfficialID", "ContainerType", "GroupID"],
        "estimated_rows": 17000,
        "chunk_size": 0,
    },
    "org_units": {
        "query": """
            SELECT 
                CONVERT(varchar(36), ou.OrgUnitID) AS OrgUnitID,
                CONVERT(varchar(200), ou.Name) AS Name,
                CONVERT(varchar(20), l.Latitude) AS Latitude,
                CONVERT(varchar(20), l.Longitude) AS Longitude
            FROM dbo.OrganisationUnit ou
            LEFT JOIN dbo.Locations l ON ou.LocationID = l.LocationID
        """,
        "headers": ["OrgUnitID", "Name", "Latitude", "Longitude"],
        "estimated_rows": 100,
        "chunk_size": 0,
    },
    "status_values": {
        "query_template": """
            SELECT 
                CONVERT(varchar(36), PopulationID) AS PopulationID,
                CONVERT(varchar(19), StatusTime, 120) AS StatusTime,
                CONVERT(varchar(20), CurrentCount) AS CurrentCount,
                CONVERT(varchar(20), CurrentBiomassKg) AS CurrentBiomassKg,
                CONVERT(varchar(20), Temperature) AS Temperature
            FROM dbo.PublicStatusValues
            WHERE StatusTime >= '{start_date}' AND StatusTime < '{end_date}'
            ORDER BY StatusTime ASC
        """,
        "headers": ["PopulationID", "StatusTime", "CurrentCount", "CurrentBiomassKg", "Temperature"],
        "estimated_rows": 8000000,
        "chunk_size": 500000,
        "chunk_by": "date",
    },
    "daily_sensor_readings": {
        "query_template": """
            SELECT 
                CONVERT(varchar(36), ContainerID) AS ContainerID,
                CONVERT(varchar(36), SensorID) AS SensorID,
                CONVERT(varchar(10), Date, 120) AS ReadingDate,
                CONVERT(varchar(32), Reading) AS Reading
            FROM dbo.Ext_DailySensorReadings_v2
            WHERE Date >= '{start_date}' AND Date < '{end_date}'
            ORDER BY Date ASC
        """,
        "headers": ["ContainerID", "SensorID", "ReadingDate", "Reading"],
        "estimated_rows": 50000000,
        "chunk_size": 1000000,
        "chunk_by": "date",
    },
    "time_sensor_readings": {
        "query_template": """
            SELECT 
                CONVERT(varchar(36), ContainerID) AS ContainerID,
                CONVERT(varchar(36), SensorID) AS SensorID,
                CONVERT(varchar(19), ReadingTime, 120) AS ReadingTime,
                CONVERT(varchar(32), Reading) AS Reading
            FROM dbo.Ext_SensorReadings_v2
            WHERE ReadingTime >= '{start_date}' AND ReadingTime < '{end_date}'
            ORDER BY ReadingTime ASC
        """,
        "headers": ["ContainerID", "SensorID", "ReadingTime", "Reading"],
        "estimated_rows": 50000000,
        "chunk_size": 1000000,
        "chunk_by": "date",
    },
    "mortality_actions": {
        "query": """
            SELECT 
                CONVERT(varchar(36), m.ActionID) AS ActionID,
                CONVERT(varchar(36), a.PopulationID) AS PopulationID,
                CONVERT(varchar(19), o.StartTime, 120) AS OperationStartTime,
                CONVERT(varchar(32), m.MortalityCount) AS MortalityCount,
                CONVERT(varchar(64), m.MortalityBiomass) AS MortalityBiomass,
                CONVERT(varchar(36), m.MortalityCauseID) AS MortalityCauseID,
                ISNULL(mc.DefaultText, '') AS CauseText,
                REPLACE(REPLACE(REPLACE(ISNULL(m.Comment, ''), '|', '/'), CHAR(13), ' '), CHAR(10), ' ') AS Comment
            FROM dbo.Mortality m
            JOIN dbo.Action a ON a.ActionID = m.ActionID
            JOIN dbo.Operations o ON o.OperationID = a.OperationID
            LEFT JOIN dbo.MortalityCauses mc ON mc.MortalityCausesID = m.MortalityCauseID
            ORDER BY o.StartTime ASC
        """,
        "headers": ["ActionID", "PopulationID", "OperationStartTime", "MortalityCount", 
                   "MortalityBiomass", "MortalityCauseID", "CauseText", "Comment"],
        "estimated_rows": 5000000,
        "chunk_size": 0,
    },
    "feeding_actions": {
        "query": """
            SELECT 
                CONVERT(varchar(36), f.ActionID) AS ActionID,
                CONVERT(varchar(36), a.PopulationID) AS PopulationID,
                CONVERT(varchar(23), COALESCE(o.StartTime, f.OperationStartTime), 121) AS FeedingTime,
                CONVERT(varchar(32), f.FeedAmount) AS FeedAmountG,
                CONVERT(varchar(64), f.FeedBatchID) AS FeedBatchID,
                CONVERT(varchar(64), COALESCE(f.FeedTypeID, fb.FeedTypeID)) AS FeedTypeID,
                ISNULL(ft.Name, '') AS FeedTypeName,
                REPLACE(REPLACE(REPLACE(ISNULL(o.Comment, ''), '|', '/'), CHAR(13), ' '), CHAR(10), ' ') AS OperationComment
            FROM dbo.Feeding f
            JOIN dbo.Action a ON a.ActionID = f.ActionID
            LEFT JOIN dbo.Operations o ON o.OperationID = a.OperationID
            LEFT JOIN dbo.FeedBatch fb ON fb.FeedBatchID = f.FeedBatchID
            LEFT JOIN dbo.FeedTypes ft ON ft.FeedTypeID = COALESCE(f.FeedTypeID, fb.FeedTypeID)
            ORDER BY COALESCE(o.StartTime, f.OperationStartTime) ASC
        """,
        "headers": ["ActionID", "PopulationID", "FeedingTime", "FeedAmountG", 
                   "FeedBatchID", "FeedTypeID", "FeedTypeName", "OperationComment"],
        "estimated_rows": 5000000,
        "chunk_size": 0,
    },
    "feeding_hand_weights": {
        "query": """
            SELECT 
                CONVERT(varchar(36), hw.FeedingID) AS FeedingID,
                CONVERT(varchar(36), hw.FTActionID) AS ActionID,
                CONVERT(varchar(23), hw.StartTime, 121) AS FeedingTime,
                CONVERT(varchar(32), hw.FeedAmount) AS FeedAmountG,
                CONVERT(varchar(36), hw.HWUnitID) AS HWUnitID,
                CONVERT(varchar(36), hw.HWSiloID) AS HWSiloID,
                ISNULL(hw.StopReason, '') AS StopReason
            FROM dbo.HWFeeding hw
        """,
        "headers": ["FeedingID", "ActionID", "FeedingTime", "FeedAmountG", "HWUnitID", "HWSiloID", "StopReason"],
        "estimated_rows": 0,  # Table is empty in FishTalk
        "chunk_size": 0,
    },
    "public_weight_samples": {
        "query": """
            SELECT 
                CONVERT(varchar(36), ws.SampleID) AS SampleID,
                CONVERT(varchar(36), ws.PopulationID) AS PopulationID,
                CONVERT(varchar(23), ws.SampleDate, 121) AS SampleDate,
                CONVERT(varchar(32), ws.AvgWeight) AS AvgWeight,
                CONVERT(varchar(32), ws.CVPercent) AS CVPercent,
                CONVERT(varchar(32), ws.ConditionFactor) AS ConditionFactor,
                CONVERT(varchar(32), ws.NumberOfFish) AS NumberOfFish,
                CONVERT(varchar(5), ws.Corrective) AS Corrective,
                CONVERT(varchar(32), ws.SampleReason) AS SampleReason
            FROM dbo.PublicWeightSamples ws
            ORDER BY ws.SampleDate ASC
        """,
        "headers": [
            "SampleID",
            "PopulationID",
            "SampleDate",
            "AvgWeight",
            "CVPercent",
            "ConditionFactor",
            "NumberOfFish",
            "Corrective",
            "SampleReason",
        ],
        "estimated_rows": 1000000,
        "chunk_size": 0,
    },
    "ext_weight_samples_v2": {
        "query": """
            SELECT 
                CONVERT(varchar(36), ws.SampleID) AS SampleID,
                CONVERT(varchar(36), ws.PopulationID) AS PopulationID,
                CONVERT(varchar(23), ws.SampleDate, 121) AS SampleDate,
                CONVERT(varchar(32), ws.AvgWeight) AS AvgWeight,
                CONVERT(varchar(32), ws.CVPercent) AS CVPercent,
                CONVERT(varchar(32), ws.ConditionFactor) AS ConditionFactor,
                CONVERT(varchar(32), ws.NumberOfFish) AS NumberOfFish,
                CONVERT(varchar(5), ws.Corrective) AS Corrective,
                CONVERT(varchar(32), ws.SampleReason) AS SampleReason,
                CONVERT(varchar(32), ws.OperationType) AS OperationType
            FROM dbo.Ext_WeightSamples_v2 ws
            ORDER BY ws.SampleDate ASC
        """,
        "headers": [
            "SampleID",
            "PopulationID",
            "SampleDate",
            "AvgWeight",
            "CVPercent",
            "ConditionFactor",
            "NumberOfFish",
            "Corrective",
            "SampleReason",
            "OperationType",
        ],
        "estimated_rows": 1000000,
        "chunk_size": 0,
    },
    "public_lice_samples": {
        "query": """
            SELECT 
                CONVERT(varchar(36), pls.PopulationID) AS PopulationID,
                CONVERT(varchar(36), pls.SampleID) AS SampleID,
                CONVERT(varchar(19), pls.SampleDate, 120) AS SampleDate,
                CONVERT(varchar(32), pls.NumberOfFish) AS NumberOfFish
            FROM dbo.PublicLiceSamples pls
            ORDER BY pls.SampleDate ASC
        """,
        "headers": ["PopulationID", "SampleID", "SampleDate", "NumberOfFish"],
        "estimated_rows": 200000,
        "chunk_size": 0,
    },
    "public_lice_sample_data": {
        "query": """
            SELECT 
                CONVERT(varchar(36), psd.SampleID) AS SampleID,
                CONVERT(varchar(32), psd.LiceStagesID) AS LiceStagesID,
                CONVERT(varchar(64), psd.LiceCount) AS LiceCount
            FROM dbo.PublicLiceSampleData psd
        """,
        "headers": ["SampleID", "LiceStagesID", "LiceCount"],
        "estimated_rows": 500000,
        "chunk_size": 0,
    },
    "lice_stages": {
        "query": """
            SELECT 
                CONVERT(varchar(32), ls.LiceStagesID) AS LiceStagesID,
                ISNULL(ls.DefaultText, '') AS DefaultText
            FROM dbo.LiceStages ls
        """,
        "headers": ["LiceStagesID", "DefaultText"],
        "estimated_rows": 100,
        "chunk_size": 0,
    },
    "treatments": {
        "query": """
            SELECT 
                CONVERT(varchar(36), t.ActionID) AS ActionID,
                CONVERT(varchar(36), a.PopulationID) AS PopulationID,
                CONVERT(varchar(19), o.StartTime, 120) AS OperationStartTime,
                CONVERT(varchar(19), t.StartTime, 120) AS TreatmentStartTime,
                CONVERT(varchar(19), t.EndTime, 120) AS TreatmentEndTime,
                CONVERT(varchar(19), t.VaccinationDate, 120) AS VaccinationDate,
                CONVERT(varchar(32), t.TreatmentCount) AS TreatmentCount,
                CONVERT(varchar(64), t.AmountKg) AS AmountKg,
                CONVERT(varchar(64), t.AmountLitres) AS AmountLitres,
                CONVERT(varchar(32), t.ReasonForTreatment) AS ReasonForTreatment,
                ISNULL(tr.DefaultText, '') AS ReasonText,
                CONVERT(varchar(32), t.VaccineType) AS VaccineType,
                ISNULL(vt.VaccineName, '') AS VaccineName,
                CONVERT(varchar(32), t.MedicamentID) AS MedicamentID,
                ISNULL(med.MedicamentName, '') AS MedicamentName,
                CONVERT(varchar(32), t.TreatmentCategory) AS TreatmentCategory,
                CONVERT(varchar(32), t.TreatmentMethod) AS TreatmentMethod,
                CONVERT(varchar(32), t.NonMedicalTreatmentMethod) AS NonMedicalTreatmentMethod,
                ISNULL(t.Comment, '') AS Comment
            FROM dbo.Treatment t
            JOIN dbo.Action a ON a.ActionID = t.ActionID
            JOIN dbo.Operations o ON o.OperationID = a.OperationID
            LEFT JOIN dbo.TreatmentReasons tr ON tr.TreatmentReasonsID = t.ReasonForTreatment
            LEFT JOIN dbo.VaccineTypes vt ON vt.VaccineTypeID = t.VaccineType
            LEFT JOIN dbo.Medicaments med ON med.MedicamentID = t.MedicamentID
            ORDER BY o.StartTime ASC
        """,
        "headers": [
            "ActionID",
            "PopulationID",
            "OperationStartTime",
            "TreatmentStartTime",
            "TreatmentEndTime",
            "VaccinationDate",
            "TreatmentCount",
            "AmountKg",
            "AmountLitres",
            "ReasonForTreatment",
            "ReasonText",
            "VaccineType",
            "VaccineName",
            "MedicamentID",
            "MedicamentName",
            "TreatmentCategory",
            "TreatmentMethod",
            "NonMedicalTreatmentMethod",
            "Comment",
        ],
        "estimated_rows": 50000,
        "chunk_size": 0,
    },
    "culling": {
        "query": """
            SELECT 
                CONVERT(varchar(36), c.ActionID) AS ActionID,
                CONVERT(varchar(36), a.PopulationID) AS PopulationID,
                CONVERT(varchar(19), o.StartTime, 120) AS OperationStartTime,
                CONVERT(varchar(32), c.CullingCount) AS CullingCount,
                CONVERT(varchar(64), c.CullingBiomass) AS CullingBiomass,
                CONVERT(varchar(32), c.CullingCauseID) AS CullingCauseID,
                CONVERT(varchar(1), c.CulledAll) AS CulledAll,
                CONVERT(varchar(36), c.IndividID) AS IndividID,
                ISNULL(mc.DefaultText, '') AS CauseText,
                ISNULL(c.Comment, '') AS Comment
            FROM dbo.Culling c
            JOIN dbo.Action a ON a.ActionID = c.ActionID
            JOIN dbo.Operations o ON o.OperationID = a.OperationID
            LEFT JOIN dbo.MortalityCauses mc ON mc.MortalityCausesID = c.CullingCauseID
            ORDER BY o.StartTime ASC
        """,
        "headers": [
            "ActionID",
            "PopulationID",
            "OperationStartTime",
            "CullingCount",
            "CullingBiomass",
            "CullingCauseID",
            "CulledAll",
            "IndividID",
            "CauseText",
            "Comment",
        ],
        "estimated_rows": 50000,
        "chunk_size": 0,
    },
    "escapes": {
        "query": """
            SELECT 
                CONVERT(varchar(36), e.ActionID) AS ActionID,
                CONVERT(varchar(36), a.PopulationID) AS PopulationID,
                CONVERT(varchar(19), o.StartTime, 120) AS OperationStartTime,
                CONVERT(varchar(32), e.EscapeCount) AS EscapeCount,
                CONVERT(varchar(64), e.EscapeBiomass) AS EscapeBiomass,
                CONVERT(varchar(32), e.EscapeCauseID) AS EscapeCauseID,
                CONVERT(varchar(19), e.DiscoveryTime, 120) AS DiscoveryTime,
                CONVERT(varchar(1), e.EscapedAll) AS EscapedAll,
                ISNULL(ec.DefaultText, '') AS CauseText,
                ISNULL(e.Comment, '') AS Comment
            FROM dbo.Escapes e
            JOIN dbo.Action a ON a.ActionID = e.ActionID
            JOIN dbo.Operations o ON o.OperationID = a.OperationID
            LEFT JOIN dbo.EscapeCauses ec ON ec.EscapeCausesID = e.EscapeCauseID
            ORDER BY o.StartTime ASC
        """,
        "headers": [
            "ActionID",
            "PopulationID",
            "OperationStartTime",
            "EscapeCount",
            "EscapeBiomass",
            "EscapeCauseID",
            "DiscoveryTime",
            "EscapedAll",
            "CauseText",
            "Comment",
        ],
        "estimated_rows": 50000,
        "chunk_size": 0,
    },
    "harvest_result": {
        "query": """
            SELECT 
                CONVERT(varchar(36), h.ActionID) AS ActionID,
                CONVERT(varchar(36), a.PopulationID) AS PopulationID,
                CONVERT(varchar(19), o.StartTime, 120) AS OperationStartTime,
                CONVERT(varchar(32), h.Count) AS Count,
                CONVERT(varchar(64), h.GrossBiomass) AS GrossBiomass,
                CONVERT(varchar(64), h.NetBiomass) AS NetBiomass,
                CONVERT(varchar(32), h.QualityID) AS QualityID,
                ISNULL(hq.Name, '') AS QualityName,
                CONVERT(varchar(32), h.ConditionID) AS ConditionID,
                ISNULL(hc.DefaultText, '') AS ConditionName,
                CONVERT(varchar(64), h.FromWeight) AS FromWeight,
                CONVERT(varchar(64), h.ToWeight) AS ToWeight,
                CONVERT(varchar(64), h.IncomeTotal) AS IncomeTotal,
                ISNULL(h.BatchID, '') AS BatchID,
                CONVERT(varchar(19), h.PackingDate, 120) AS PackingDate,
                ISNULL(h.DocumentID, '') AS DocumentID,
                ISNULL(h.Comment, '') AS Comment
            FROM dbo.HarvestResult h
            JOIN dbo.Action a ON a.ActionID = h.ActionID
            JOIN dbo.Operations o ON o.OperationID = a.OperationID
            LEFT JOIN dbo.Ext_HarvestQuality_v2 hq ON hq.HarvestQualityID = h.QualityID
            LEFT JOIN dbo.HarvestCondition hc ON hc.HarvestConditionID = h.ConditionID
            ORDER BY o.StartTime ASC
        """,
        "headers": [
            "ActionID",
            "PopulationID",
            "OperationStartTime",
            "Count",
            "GrossBiomass",
            "NetBiomass",
            "QualityID",
            "QualityName",
            "ConditionID",
            "ConditionName",
            "FromWeight",
            "ToWeight",
            "IncomeTotal",
            "BatchID",
            "PackingDate",
            "DocumentID",
            "Comment",
        ],
        "estimated_rows": 30000,
        "chunk_size": 0,
    },
    "historical_hatching": {
        "query": """
            SELECT 
                CONVERT(varchar(36), hh.ActionID) AS ActionID,
                CONVERT(varchar(36), a.PopulationID) AS PopulationID,
                CONVERT(varchar(19), o.StartTime, 120) AS OperationStartTime,
                CONVERT(varchar(19), hh.HatchingFirstDate, 120) AS HatchingFirstDate,
                CONVERT(varchar(64), hh.HatchingFirstATU) AS HatchingFirstATU,
                CONVERT(varchar(19), hh.HatchingLastDate, 120) AS HatchingLastDate,
                CONVERT(varchar(64), hh.HatchingLastATU) AS HatchingLastATU,
                CONVERT(varchar(64), hh.MinIncubationTemp) AS MinIncubationTemp,
                CONVERT(varchar(64), hh.MaxIncubationTemp) AS MaxIncubationTemp,
                CONVERT(varchar(64), hh.AvgIncubationTemp) AS AvgIncubationTemp
            FROM dbo.HistoricalHatching hh
            JOIN dbo.Action a ON a.ActionID = hh.ActionID
            JOIN dbo.Operations o ON o.OperationID = a.OperationID
            ORDER BY o.StartTime ASC
        """,
        "headers": [
            "ActionID",
            "PopulationID",
            "OperationStartTime",
            "HatchingFirstDate",
            "HatchingFirstATU",
            "HatchingLastDate",
            "HatchingLastATU",
            "MinIncubationTemp",
            "MaxIncubationTemp",
            "AvgIncubationTemp",
        ],
        "estimated_rows": 50000,
        "chunk_size": 0,
    },
    "historical_spawning": {
        "query": """
            SELECT 
                CONVERT(varchar(36), hs.ActionID) AS ActionID,
                CONVERT(varchar(36), a.PopulationID) AS PopulationID,
                CONVERT(varchar(19), o.StartTime, 120) AS OperationStartTime,
                CONVERT(varchar(19), hs.SpawningFirstDate, 120) AS SpawningFirstDate,
                CONVERT(varchar(19), hs.SpawningLastDate, 120) AS SpawningLastDate,
                CONVERT(varchar(36), hs.SpawningSite) AS SpawningSite
            FROM dbo.HistoricalSpawning hs
            JOIN dbo.Action a ON a.ActionID = hs.ActionID
            JOIN dbo.Operations o ON o.OperationID = a.OperationID
            ORDER BY o.StartTime ASC
        """,
        "headers": [
            "ActionID",
            "PopulationID",
            "OperationStartTime",
            "SpawningFirstDate",
            "SpawningLastDate",
            "SpawningSite",
        ],
        "estimated_rows": 50000,
        "chunk_size": 0,
    },
    "historical_start_feeding": {
        "query": """
            SELECT 
                CONVERT(varchar(36), hf.ActionID) AS ActionID,
                CONVERT(varchar(36), a.PopulationID) AS PopulationID,
                CONVERT(varchar(19), o.StartTime, 120) AS OperationStartTime,
                CONVERT(varchar(64), hf.MinSacFryTemp) AS MinSacFryTemp,
                CONVERT(varchar(64), hf.MaxSacFryTemp) AS MaxSacFryTemp,
                CONVERT(varchar(64), hf.AvgSacFryTemp) AS AvgSacFryTemp,
                CONVERT(varchar(19), hf.StartFeedingFirstDate, 120) AS StartFeedingFirstDate,
                CONVERT(varchar(64), hf.StartFeedingFirstATU) AS StartFeedingFirstATU,
                CONVERT(varchar(19), hf.StartFeedingLastDate, 120) AS StartFeedingLastDate,
                CONVERT(varchar(64), hf.StartFeedingLastATU) AS StartFeedingLastATU
            FROM dbo.HistoricalStartFeeding hf
            JOIN dbo.Action a ON a.ActionID = hf.ActionID
            JOIN dbo.Operations o ON o.OperationID = a.OperationID
            ORDER BY o.StartTime ASC
        """,
        "headers": [
            "ActionID",
            "PopulationID",
            "OperationStartTime",
            "MinSacFryTemp",
            "MaxSacFryTemp",
            "AvgSacFryTemp",
            "StartFeedingFirstDate",
            "StartFeedingFirstATU",
            "StartFeedingLastDate",
            "StartFeedingLastATU",
        ],
        "estimated_rows": 50000,
        "chunk_size": 0,
    },
    "spawning_selection": {
        "query": """
            SELECT 
                CONVERT(varchar(36), ss.ActionID) AS ActionID,
                CONVERT(varchar(36), a.PopulationID) AS PopulationID,
                CONVERT(varchar(19), o.StartTime, 120) AS OperationStartTime,
                CONVERT(varchar(36), ss.SpawnID) AS SpawnID,
                ISNULL(ss.SpawnName, '') AS SpawnName,
                CONVERT(varchar(36), ss.IndividID) AS IndividID,
                ISNULL(ss.IndividName, '') AS IndividName,
                ISNULL(ss.PitTag, '') AS PitTag,
                CONVERT(varchar(32), ss.Sex) AS Sex,
                CONVERT(varchar(32), ss.CullingCauseID) AS CullingCauseID,
                ISNULL(ss.MaleSpermDonors, '') AS MaleSpermDonors,
                CONVERT(varchar(64), ss.IndividWeight) AS IndividWeight,
                CONVERT(varchar(1), ss.Returned) AS Returned,
                CONVERT(varchar(32), ss.InitialEggsPerLitre) AS InitialEggsPerLitre,
                CONVERT(varchar(64), ss.InitialLitresOfEggs) AS InitialLitresOfEggs,
                CONVERT(varchar(1), ss.PositiveScreening) AS PositiveScreening,
                CONVERT(varchar(1), ss.Incubated) AS Incubated,
                CONVERT(varchar(64), ss.EggMortaliyRateFirst24Hours) AS EggMortaliyRateFirst24Hours,
                ISNULL(ss.EggSplits, '') AS EggSplits,
                ISNULL(ss.Comment1, '') AS Comment1,
                ISNULL(ss.Comment2, '') AS Comment2,
                ISNULL(ss.Comment3, '') AS Comment3,
                ISNULL(ss.Comment4, '') AS Comment4
            FROM dbo.SpawningSelection ss
            JOIN dbo.Action a ON a.ActionID = ss.ActionID
            JOIN dbo.Operations o ON o.OperationID = a.OperationID
            ORDER BY o.StartTime ASC
        """,
        "headers": [
            "ActionID",
            "PopulationID",
            "OperationStartTime",
            "SpawnID",
            "SpawnName",
            "IndividID",
            "IndividName",
            "PitTag",
            "Sex",
            "CullingCauseID",
            "MaleSpermDonors",
            "IndividWeight",
            "Returned",
            "InitialEggsPerLitre",
            "InitialLitresOfEggs",
            "PositiveScreening",
            "Incubated",
            "EggMortaliyRateFirst24Hours",
            "EggSplits",
            "Comment1",
            "Comment2",
            "Comment3",
            "Comment4",
        ],
        "estimated_rows": 50000,
        "chunk_size": 0,
    },
    "vaccine_types": {
        "query": """
            SELECT 
                CONVERT(varchar(32), vt.VaccineTypeID) AS VaccineTypeID,
                ISNULL(vt.VaccineName, '') AS VaccineName
            FROM dbo.VaccineTypes vt
            ORDER BY vt.VaccineName
        """,
        "headers": ["VaccineTypeID", "VaccineName"],
        "estimated_rows": 500,
        "chunk_size": 0,
    },
    "user_sample_sessions": {
        "query": """
            SELECT 
                CONVERT(varchar(36), us.ActionID) AS ActionID,
                CONVERT(varchar(36), a.PopulationID) AS PopulationID,
                CONVERT(varchar(23), COALESCE(o.StartTime, o.RegistrationTime), 121) AS SampleTime,
                CONVERT(varchar(32), COUNT(*)) AS SampleRows,
                CONVERT(varchar(32), SUM(CASE WHEN us.Returned = 1 THEN 1 ELSE 0 END)) AS ReturnedRows,
                CONVERT(varchar(32), AVG(CAST(us.LivingWeight AS float))) AS AvgWeightG,
                CONVERT(varchar(32), MIN(us.LivingWeight)) AS MinWeightG,
                CONVERT(varchar(32), MAX(us.LivingWeight)) AS MaxWeightG
            FROM dbo.UserSample us
            JOIN dbo.Action a ON a.ActionID = us.ActionID
            LEFT JOIN dbo.Operations o ON o.OperationID = a.OperationID
            GROUP BY us.ActionID, a.PopulationID, COALESCE(o.StartTime, o.RegistrationTime)
            ORDER BY COALESCE(o.StartTime, o.RegistrationTime) ASC
        """,
        "headers": [
            "ActionID",
            "PopulationID",
            "SampleTime",
            "SampleRows",
            "ReturnedRows",
            "AvgWeightG",
            "MinWeightG",
            "MaxWeightG",
        ],
        "estimated_rows": 50000,
        "chunk_size": 0,
    },
    "user_sample_types": {
        "query": """
            SELECT 
                CONVERT(varchar(36), ust.ActionID) AS ActionID,
                CONVERT(varchar(32), ust.SampleType) AS UserSampleTypeID,
                ISNULL(st.DefaultText, '') AS SampleTypeName
            FROM dbo.UserSampleTypes ust
            LEFT JOIN dbo.UserSampleType st ON st.UserSampleTypeID = ust.SampleType
            ORDER BY ust.ActionID, ust.SampleType
        """,
        "headers": ["ActionID", "UserSampleTypeID", "SampleTypeName"],
        "estimated_rows": 50000,
        "chunk_size": 0,
    },
    "user_sample_attributes": {
        "query": """
            SELECT 
                CONVERT(varchar(36), uspv.ActionID) AS ActionID,
                CONVERT(varchar(32), uspv.AttributeID) AS AttributeID,
                ISNULL(fga.Name, '') AS AttributeName,
                'INT' AS ValueType,
                CONVERT(varchar(32), AVG(CAST(uspv.IntValue AS float))) AS AvgValue,
                CONVERT(varchar(32), MIN(uspv.IntValue)) AS MinValue,
                CONVERT(varchar(32), MAX(uspv.IntValue)) AS MaxValue,
                CONVERT(varchar(32), COUNT(*)) AS N
            FROM dbo.UserSampleParameterValue uspv
            LEFT JOIN dbo.FishGroupAttributes fga ON fga.AttributeID = uspv.AttributeID
            WHERE uspv.IntValue IS NOT NULL
            GROUP BY uspv.ActionID, uspv.AttributeID, fga.Name
            UNION ALL
            SELECT 
                CONVERT(varchar(36), uspv.ActionID) AS ActionID,
                CONVERT(varchar(32), uspv.AttributeID) AS AttributeID,
                ISNULL(fga.Name, '') AS AttributeName,
                'FLOAT' AS ValueType,
                CONVERT(varchar(32), AVG(CAST(uspv.FloatValue AS float))) AS AvgValue,
                CONVERT(varchar(32), MIN(uspv.FloatValue)) AS MinValue,
                CONVERT(varchar(32), MAX(uspv.FloatValue)) AS MaxValue,
                CONVERT(varchar(32), COUNT(*)) AS N
            FROM dbo.UserSampleParameterValue uspv
            LEFT JOIN dbo.FishGroupAttributes fga ON fga.AttributeID = uspv.AttributeID
            WHERE uspv.FloatValue IS NOT NULL
            GROUP BY uspv.ActionID, uspv.AttributeID, fga.Name
            ORDER BY ActionID, AttributeID, ValueType
        """,
        "headers": ["ActionID", "AttributeID", "AttributeName", "ValueType", "AvgValue", "MinValue", "MaxValue", "N"],
        "estimated_rows": 200000,
        "chunk_size": 0,
    },
    "feed_reception_lines": {
        "query": """
            SELECT 
                CONVERT(varchar(36), frb.FeedReceptionID) AS FeedReceptionID,
                CONVERT(varchar(36), frb.FeedBatchID) AS FeedBatchID,
                ISNULL(CONVERT(varchar(32), frb.PricePerKg), '') AS PricePerKg,
                ISNULL(CONVERT(varchar(32), frb.ReceptionAmount), '') AS ReceptionAmount,
                CONVERT(varchar(19), frb.ProductionDate, 120) AS ProductionDate,
                CONVERT(varchar(19), frb.OutOfDate, 120) AS OutOfDate,
                ISNULL(frb.ReceiptNumber, '') AS ReceiptNumber,
                ISNULL(frb.SuppliersBatchNumber, '') AS SuppliersBatchNumber,
                CONVERT(varchar(32), frb.FeedReceptionLineNumber) AS FeedReceptionLineNumber,
                CONVERT(varchar(19), fr.ReceptionTime, 120) AS ReceptionTime,
                ISNULL(fr.OrderNumber, '') AS OrderNumber,
                ISNULL(fr.OurOrderNo, '') AS OurOrderNo,
                ISNULL(fr.OurReference, '') AS OurReference,
                ISNULL(fr.GTIN, '') AS GTIN,
                CONVERT(varchar(36), fr.SupplierID) AS SupplierID,
                ISNULL(fr.Comment, '') AS ReceptionComment,
                CONVERT(varchar(36), fb.FeedStoreID) AS FeedStoreID,
                CONVERT(varchar(32), fb.FeedTypeID) AS FeedTypeID,
                ISNULL(fb.BatchNumber, '') AS FeedBatchNumber,
                CONVERT(varchar(19), fb.StartTime, 120) AS FeedBatchStartTime,
                CONVERT(varchar(19), fb.EndTime, 120) AS FeedBatchEndTime,
                ISNULL(fs.Name, '') AS FeedStoreName,
                ISNULL(CONVERT(varchar(32), fs.Capacity), '') AS FeedStoreCapacity,
                CONVERT(varchar(32), fs.FeedStoreTypeID) AS FeedStoreTypeID,
                CONVERT(varchar(36), fsa.ContainerID) AS ContainerID,
                ISNULL(ft.Name, '') AS FeedTypeName
            FROM dbo.FeedStoreUnitAssignment fsa
            JOIN dbo.FeedStore fs ON fs.FeedStoreID = fsa.FeedStoreID
            JOIN dbo.FeedBatch fb ON fb.FeedStoreID = fs.FeedStoreID
            JOIN dbo.FeedReceptionBatches frb ON frb.FeedBatchID = fb.FeedBatchID
            JOIN dbo.FeedReceptions fr ON fr.FeedReceptionID = frb.FeedReceptionID
            LEFT JOIN dbo.FeedTypes ft ON ft.FeedTypeID = fb.FeedTypeID
            ORDER BY fr.ReceptionTime ASC
        """,
        "headers": [
            "FeedReceptionID",
            "FeedBatchID",
            "PricePerKg",
            "ReceptionAmount",
            "ProductionDate",
            "OutOfDate",
            "ReceiptNumber",
            "SuppliersBatchNumber",
            "FeedReceptionLineNumber",
            "ReceptionTime",
            "OrderNumber",
            "OurOrderNo",
            "OurReference",
            "GTIN",
            "SupplierID",
            "ReceptionComment",
            "FeedStoreID",
            "FeedTypeID",
            "FeedBatchNumber",
            "FeedBatchStartTime",
            "FeedBatchEndTime",
            "FeedStoreName",
            "FeedStoreCapacity",
            "FeedStoreTypeID",
            "ContainerID",
            "FeedTypeName",
        ],
        "estimated_rows": 200000,
        "chunk_size": 0,
    },
    "transfer_operations": {
        "query": """
            SELECT 
                CONVERT(varchar(36), o.OperationID) AS OperationID,
                CONVERT(varchar(19), o.StartTime, 120) AS OperationStartTime,
                CONVERT(varchar(19), o.EndTime, 120) AS OperationEndTime,
                CONVERT(varchar(500), o.Comment) AS Comment
            FROM dbo.Operations o
            WHERE o.OperationID IN (SELECT DISTINCT OperationID FROM dbo.PublicTransfers)
            ORDER BY o.StartTime ASC
        """,
        "headers": ["OperationID", "OperationStartTime", "OperationEndTime", "Comment"],
        "estimated_rows": 50000,
        "chunk_size": 0,
    },
    "transfer_edges": {
        "query": """
            SELECT 
                CONVERT(varchar(36), pt.OperationID) AS OperationID,
                CONVERT(varchar(36), pt.SourcePop) AS SourcePop,
                CONVERT(varchar(36), pt.DestPop) AS DestPop,
                CONVERT(varchar(64), pt.ShareCountForward) AS ShareCountForward,
                CONVERT(varchar(64), pt.ShareBiomassForward) AS ShareBiomassForward
            FROM dbo.PublicTransfers pt
            ORDER BY pt.OperationID ASC
        """,
        "headers": ["OperationID", "SourcePop", "DestPop", "ShareCountForward", "ShareBiomassForward"],
        "estimated_rows": 100000,
        "chunk_size": 0,
    },
    # SubTransfers-based stitching tables (replaces project-based stitching)
    "sub_transfers": {
        "query": """
            SELECT 
                CONVERT(varchar(36), st.SubTransferID) AS SubTransferID,
                CONVERT(varchar(36), st.OperationID) AS OperationID,
                CONVERT(varchar(36), st.SourcePopBefore) AS SourcePopBefore,
                CONVERT(varchar(36), st.SourcePopAfter) AS SourcePopAfter,
                CONVERT(varchar(36), st.DestPopBefore) AS DestPopBefore,
                CONVERT(varchar(36), st.DestPopAfter) AS DestPopAfter,
                CONVERT(varchar(10), st.TransferType) AS TransferType,
                CONVERT(varchar(32), st.ShareCountFwd) AS ShareCountFwd,
                CONVERT(varchar(32), st.ShareBiomFwd) AS ShareBiomFwd,
                CONVERT(varchar(32), st.ShareCountBwd) AS ShareCountBwd,
                CONVERT(varchar(32), st.ShareBiomBwd) AS ShareBiomBwd,
                CONVERT(varchar(32), st.BranchedCount) AS BranchedCount,
                CONVERT(varchar(32), st.BranchedBiomass) AS BranchedBiomass,
                CONVERT(varchar(19), o.StartTime, 120) AS OperationTime
            FROM dbo.SubTransfers st
            JOIN dbo.Operations o ON o.OperationID = st.OperationID
            ORDER BY o.StartTime ASC
        """,
        "headers": ["SubTransferID", "OperationID", "SourcePopBefore", "SourcePopAfter", 
                   "DestPopBefore", "DestPopAfter", "TransferType", "ShareCountFwd", 
                   "ShareBiomFwd", "ShareCountBwd", "ShareBiomBwd", "BranchedCount", 
                   "BranchedBiomass", "OperationTime"],
        "estimated_rows": 205000,
        "chunk_size": 0,
    },
    "operation_stage_changes": {
        "query": """
            SELECT 
                CONVERT(varchar(36), opsc.OperationID) AS OperationID,
                CONVERT(varchar(36), opsc.PPSPopID) AS PopulationID,
                CONVERT(varchar(36), opsc.PPSStageID) AS StageID,
                CONVERT(varchar(19), opsc.PPSStartTime, 120) AS StageStartTime,
                CONVERT(varchar(19), o.StartTime, 120) AS OperationTime
            FROM dbo.OperationProductionStageChange opsc
            JOIN dbo.Operations o ON o.OperationID = opsc.OperationID
            ORDER BY opsc.PPSStartTime ASC
        """,
        "headers": ["OperationID", "PopulationID", "StageID", "StageStartTime", "OperationTime"],
        "estimated_rows": 27000,
        "chunk_size": 0,
    },
    # Input-based batch identification (2026-01-22 breakthrough)
    "ext_inputs": {
        "query": """
            SELECT 
                CONVERT(varchar(36), i.PopulationID) AS PopulationID,
                ISNULL(i.InputName, '') AS InputName,
                ISNULL(CONVERT(varchar(10), i.InputNumber), '0') AS InputNumber,
                ISNULL(CONVERT(varchar(10), i.YearClass), '') AS YearClass,
                ISNULL(CONVERT(varchar(36), i.Supplier), '') AS SupplierID,
                CONVERT(varchar(19), i.StartTime, 120) AS StartTime,
                ISNULL(CONVERT(varchar(32), i.InputCount), '0') AS InputCount,
                ISNULL(CONVERT(varchar(32), i.InputBiomass), '0') AS InputBiomass,
                ISNULL(CONVERT(varchar(10), i.Species), '') AS Species,
                ISNULL(CONVERT(varchar(10), i.FishType), '') AS FishType,
                ISNULL(CONVERT(varchar(10), i.Broodstock), '') AS Broodstock,
                ISNULL(i.DeliveryID, '') AS DeliveryID,
                ISNULL(CONVERT(varchar(36), i.Transporter), '') AS Transporter
            FROM dbo.Ext_Inputs_v2 i
            ORDER BY i.StartTime ASC
        """,
        "headers": ["PopulationID", "InputName", "InputNumber", "YearClass", "SupplierID",
                   "StartTime", "InputCount", "InputBiomass", "Species", "FishType",
                   "Broodstock", "DeliveryID", "Transporter"],
        "estimated_rows": 25000,
        "chunk_size": 0,
    },
    "ext_populations": {
        "query": """
            SELECT 
                CONVERT(varchar(36), PopulationID) AS PopulationID,
                CONVERT(varchar(36), ContainerID) AS ContainerID,
                ISNULL(PopulationName, '') AS PopulationName,
                CONVERT(varchar(10), SpeciesID) AS SpeciesID,
                CONVERT(varchar(19), StartTime, 120) AS StartTime,
                CONVERT(varchar(19), EndTime, 120) AS EndTime,
                ISNULL(InputYear, '') AS InputYear,
                ISNULL(InputNumber, '') AS InputNumber,
                CONVERT(varchar(10), RunningNumber) AS RunningNumber,
                ISNULL(Fishgroup, '') AS Fishgroup
            FROM dbo.Ext_Populations_v2
        """,
        "headers": [
            "PopulationID", "ContainerID", "PopulationName", "SpeciesID",
            "StartTime", "EndTime", "InputYear", "InputNumber", "RunningNumber", "Fishgroup",
        ],
        "estimated_rows": 350000,
        "chunk_size": 0,
    },
    "fish_group_history": {
        "query": """
            SELECT
                CONVERT(varchar(36), PopulationID) AS PopulationID,
                CONVERT(varchar(36), InputProjectID) AS InputProjectID
            FROM dbo.FishGroupHistory
        """,
        "headers": ["PopulationID", "InputProjectID"],
        "estimated_rows": 221000,
        "chunk_size": 0,
    },
    "input_projects": {
        "query": """
            SELECT
                CONVERT(varchar(36), InputProjectID) AS InputProjectID,
                CONVERT(varchar(36), SiteID) AS SiteID,
                CONVERT(varchar(20), Species) AS Species,
                CONVERT(varchar(10), YearClass) AS YearClass,
                CONVERT(varchar(2), ProjectNumberOld) AS ProjectNumberOld,
                CONVERT(varchar(100), ProjectName) AS ProjectName,
                CONVERT(varchar(5), Active) AS Active,
                CONVERT(varchar(10), ProjectNumber) AS ProjectNumber
            FROM dbo.InputProjects
        """,
        "headers": [
            "InputProjectID",
            "SiteID",
            "Species",
            "YearClass",
            "ProjectNumberOld",
            "ProjectName",
            "Active",
            "ProjectNumber",
        ],
        "estimated_rows": 2100,
        "chunk_size": 0,
    },
    "population_links": {
        "query": """
            SELECT
                CONVERT(varchar(36), FromPopulationID) AS FromPopulationID,
                CONVERT(varchar(36), ToPopulationID) AS ToPopulationID,
                CONVERT(varchar(36), OperationID) AS OperationID,
                CONVERT(varchar(10), LinkType) AS LinkType
            FROM dbo.PopulationLink
        """,
        "headers": ["FromPopulationID", "ToPopulationID", "OperationID", "LinkType"],
        "estimated_rows": 200000,
        "chunk_size": 0,
    },
    "internal_delivery": {
        "query": """
            SELECT
                CONVERT(varchar(36), SalesOperationID) AS SalesOperationID,
                CONVERT(varchar(36), InputSiteID) AS InputSiteID,
                CONVERT(varchar(36), InputOperationID) AS InputOperationID,
                CONVERT(varchar(36), PlannedActivityID) AS PlannedActivityID
            FROM dbo.InternalDelivery
        """,
        "headers": ["SalesOperationID", "InputSiteID", "InputOperationID", "PlannedActivityID"],
        "estimated_rows": 3000,
        "chunk_size": 0,
    },
    "internal_delivery_operations": {
        "query": """
            SELECT DISTINCT
                CONVERT(varchar(36), o.OperationID) AS OperationID,
                CONVERT(varchar(19), o.StartTime, 120) AS StartTime,
                CONVERT(varchar(19), o.EndTime, 120) AS EndTime,
                CONVERT(varchar(10), o.OperationType) AS OperationType,
                REPLACE(REPLACE(REPLACE(ISNULL(o.Comment, ''), '|', '/'), CHAR(13), ' '), CHAR(10), ' ') AS Comment,
                CONVERT(varchar(19), o.RegistrationTime, 120) AS RegistrationTime
            FROM dbo.Operations o
            JOIN (
                SELECT SalesOperationID AS OperationID FROM dbo.InternalDelivery
                UNION
                SELECT InputOperationID AS OperationID FROM dbo.InternalDelivery WHERE InputOperationID IS NOT NULL
            ) ids ON o.OperationID = ids.OperationID
        """,
        "headers": [
            "OperationID",
            "StartTime",
            "EndTime",
            "OperationType",
            "Comment",
            "RegistrationTime",
        ],
        "estimated_rows": 6000,
        "chunk_size": 0,
    },
    "internal_delivery_actions": {
        "query": """
            SELECT
                CONVERT(varchar(36), a.ActionID) AS ActionID,
                CONVERT(varchar(36), a.PopulationID) AS PopulationID,
                CONVERT(varchar(10), a.ActionType) AS ActionType,
                CONVERT(varchar(10), a.ActionOrder) AS ActionOrder,
                CONVERT(varchar(36), a.OperationID) AS OperationID
            FROM dbo.Action a
            JOIN (
                SELECT SalesOperationID AS OperationID FROM dbo.InternalDelivery
                UNION
                SELECT InputOperationID AS OperationID FROM dbo.InternalDelivery WHERE InputOperationID IS NOT NULL
            ) ids ON a.OperationID = ids.OperationID
        """,
        "headers": ["ActionID", "PopulationID", "ActionType", "ActionOrder", "OperationID"],
        "estimated_rows": 200000,
        "chunk_size": 0,
    },
    "internal_delivery_action_metadata": {
        "query": """
            SET QUOTED_IDENTIFIER ON;
            SELECT
                CONVERT(varchar(36), m.ActionID) AS ActionID,
                CONVERT(varchar(36), a.OperationID) AS OperationID,
                CONVERT(varchar(10), m.ParameterID) AS ParameterID,
                REPLACE(REPLACE(REPLACE(ISNULL(m.ParameterString, ''), '|', '/'), CHAR(13), ' '), CHAR(10), ' ') AS ParameterString,
                ISNULL(CONVERT(varchar(64), m.ParameterValue), '') AS ParameterValue,
                CONVERT(varchar(19), m.ParameterDate, 120) AS ParameterDate,
                ISNULL(CONVERT(varchar(36), m.ParameterGuid), '') AS ParameterGuid,
                CASE WHEN m.ParameterID = 184 AND x.XmlPayload IS NOT NULL THEN '1' ELSE '0' END AS XmlParseable,
                CASE WHEN m.ParameterID = 184 AND x.XmlPayload IS NOT NULL
                    THEN ISNULL(x.XmlPayload.value('(/TransportXML//TripID/text())[1]', 'nvarchar(200)'), '')
                    ELSE ''
                END AS TripID,
                CASE WHEN m.ParameterID = 184 AND x.XmlPayload IS NOT NULL
                    THEN ISNULL(x.XmlPayload.value('(/TransportXML//CompartmentID/text())[1]', 'nvarchar(200)'), '')
                    ELSE ''
                END AS CompartmentID,
                CASE WHEN m.ParameterID = 184 AND x.XmlPayload IS NOT NULL
                    THEN ISNULL(x.XmlPayload.value('(/TransportXML//CompartmentNr/text())[1]', 'nvarchar(200)'), '')
                    ELSE ''
                END AS CompartmentNr,
                CASE WHEN m.ParameterID = 184 AND x.XmlPayload IS NOT NULL
                    THEN ISNULL(x.XmlPayload.value('(/TransportXML//TransporterID/text())[1]', 'nvarchar(200)'), '')
                    ELSE ''
                END AS TransporterID,
                CASE WHEN m.ParameterID = 184 AND x.XmlPayload IS NOT NULL
                    THEN ISNULL(x.XmlPayload.value('(/TransportXML//CarrierID/text())[1]', 'nvarchar(200)'), '')
                    ELSE ''
                END AS CarrierID
            FROM dbo.ActionMetaData m
            JOIN dbo.Action a ON a.ActionID = m.ActionID
            JOIN (
                SELECT SalesOperationID AS OperationID FROM dbo.InternalDelivery
                UNION
                SELECT InputOperationID AS OperationID FROM dbo.InternalDelivery WHERE InputOperationID IS NOT NULL
            ) ids ON a.OperationID = ids.OperationID
            OUTER APPLY (
                SELECT TRY_CONVERT(xml, m.ParameterString) AS XmlPayload
            ) x
            WHERE m.ParameterID IN (184, 220)
        """,
        "headers": [
            "ActionID",
            "OperationID",
            "ParameterID",
            "ParameterString",
            "ParameterValue",
            "ParameterDate",
            "ParameterGuid",
            "XmlParseable",
            "TripID",
            "CompartmentID",
            "CompartmentNr",
            "TransporterID",
            "CarrierID",
        ],
        "estimated_rows": 50000,
        "chunk_size": 0,
    },
    "internal_delivery_planned_activities": {
        "query": """
            SELECT
                CONVERT(varchar(36), p.PlannedActivityID) AS PlannedActivityID,
                CONVERT(varchar(36), p.SiteID) AS SiteID,
                CONVERT(varchar(19), p.DueDate, 120) AS DueDate,
                REPLACE(REPLACE(REPLACE(ISNULL(p.Description, ''), '|', '/'), CHAR(13), ' '), CHAR(10), ' ') AS Description,
                REPLACE(REPLACE(REPLACE(ISNULL(p.Summary, ''), '|', '/'), CHAR(13), ' '), CHAR(10), ' ') AS Summary,
                CONVERT(varchar(10), p.ActivityCategory) AS ActivityCategory,
                CONVERT(varchar(10), p.ActivityType) AS ActivityType,
                CONVERT(varchar(36), p.GroupID) AS GroupID
            FROM dbo.PlannedActivities p
            JOIN (
                SELECT PlannedActivityID
                FROM dbo.InternalDelivery
                WHERE PlannedActivityID IS NOT NULL
            ) ids ON p.PlannedActivityID = ids.PlannedActivityID
        """,
        "headers": [
            "PlannedActivityID",
            "SiteID",
            "DueDate",
            "Description",
            "Summary",
            "ActivityCategory",
            "ActivityType",
            "GroupID",
        ],
        "estimated_rows": 3000,
        "chunk_size": 0,
    },
    "contacts": {
        "query": """
            SELECT
                CONVERT(varchar(36), c.ID) AS ContactID,
                ISNULL(c.Name, '') AS Name,
                CONVERT(varchar(5), c.Active) AS Active
            FROM dbo.Contact c
        """,
        "headers": ["ContactID", "Name", "Active"],
        "estimated_rows": 10000,
        "chunk_size": 0,
    },
    "contact_types": {
        "query": """
            SELECT
                CONVERT(varchar(36), ct.ContactID) AS ContactID,
                CONVERT(varchar(10), ct.ContactTypeID) AS ContactTypeID
            FROM dbo.ContactTypes ct
        """,
        "headers": ["ContactID", "ContactTypeID"],
        "estimated_rows": 50000,
        "chunk_size": 0,
    },
    "transport_carriers": {
        "query": """
            SELECT
                CONVERT(varchar(36), tc.ID) AS TransportCarrierID,
                ISNULL(tc.Name, '') AS Name,
                ISNULL(tc.OfficialCode, '') AS OfficialCode,
                CONVERT(varchar(10), tc.TransportMethodID) AS TransportMethodID,
                CONVERT(varchar(36), tc.ContactID) AS ContactID,
                CONVERT(varchar(5), tc.Active) AS Active
            FROM dbo.TransportCarrier tc
        """,
        "headers": [
            "TransportCarrierID",
            "Name",
            "OfficialCode",
            "TransportMethodID",
            "ContactID",
            "Active",
        ],
        "estimated_rows": 50,
        "chunk_size": 0,
    },
    "transport_methods": {
        "query": """
            SELECT
                CONVERT(varchar(10), tm.TransportMethodID) AS TransportMethodID,
                CONVERT(varchar(10), tm.TextID) AS TextID,
                ISNULL(tm.DefaultText, '') AS DefaultText,
                CONVERT(varchar(5), tm.Active) AS Active,
                CONVERT(varchar(5), tm.SystemDelivered) AS SystemDelivered
            FROM dbo.TransportMethods tm
        """,
        "headers": [
            "TransportMethodID",
            "TextID",
            "DefaultText",
            "Active",
            "SystemDelivered",
        ],
        "estimated_rows": 20,
        "chunk_size": 0,
    },
    "ext_transporters": {
        "query": """
            SELECT
                CONVERT(varchar(36), t.TransporterID) AS TransporterID,
                ISNULL(t.Name, '') AS Name
            FROM dbo.Ext_Transporters_v2 t
        """,
        "headers": ["TransporterID", "Name"],
        "estimated_rows": 200,
        "chunk_size": 0,
    },
    "ext_transfers": {
        "query": """
            SELECT
                CONVERT(varchar(36), SourcePop) AS SourcePop,
                CONVERT(varchar(36), DestPop) AS DestPop,
                CONVERT(varchar(32), TransferredCount) AS TransferredCount,
                CONVERT(varchar(32), TransferredBiomassKg) AS TransferredBiomassKg,
                CONVERT(varchar(32), ShareCountForward) AS ShareCountForward,
                CONVERT(varchar(32), ShareBiomassForward) AS ShareBiomassForward,
                CONVERT(varchar(32), ShareCountBackward) AS ShareCountBackward,
                CONVERT(varchar(32), ShareBiomassBackward) AS ShareBiomassBackward
            FROM dbo.Ext_Transfers_v2
        """,
        "headers": [
            "SourcePop",
            "DestPop",
            "TransferredCount",
            "TransferredBiomassKg",
            "ShareCountForward",
            "ShareBiomassForward",
            "ShareCountBackward",
            "ShareBiomassBackward",
        ],
        "estimated_rows": 200000,
        "chunk_size": 0,
    },
    "plan_transfers": {
        "query": """
            SELECT
                CONVERT(varchar(36), FromPlanPopulationID) AS FromPlanPopulationID,
                CONVERT(varchar(36), ToPlanPopulationID) AS ToPlanPopulationID,
                CONVERT(varchar(32), CountShare) AS CountShare,
                CONVERT(varchar(32), BiomassShare) AS BiomassShare,
                CONVERT(varchar(36), TransferID) AS TransferID,
                CONVERT(varchar(32), CostPrKg) AS CostPrKg,
                CONVERT(varchar(32), CostPrPiece) AS CostPrPiece,
                CONVERT(varchar(10), TransferType) AS TransferType
            FROM dbo.PlanTransfer
        """,
        "headers": [
            "FromPlanPopulationID",
            "ToPlanPopulationID",
            "CountShare",
            "BiomassShare",
            "TransferID",
            "CostPrKg",
            "CostPrPiece",
            "TransferType",
        ],
        "estimated_rows": 20000,
        "chunk_size": 0,
    },
    "reason_for_transfer": {
        "query": """
            SELECT
                CONVERT(varchar(10), ReasonForTransferID) AS ReasonForTransferID,
                CONVERT(varchar(10), TextID) AS TextID,
                ISNULL(DefaultText, '') AS DefaultText,
                CONVERT(varchar(5), Active) AS Active,
                CONVERT(varchar(5), SystemDelivered) AS SystemDelivered
            FROM dbo.ReasonForTransfer
        """,
        "headers": ["ReasonForTransferID", "TextID", "DefaultText", "Active", "SystemDelivered"],
        "estimated_rows": 50,
        "chunk_size": 0,
    },
    "wrasse_pop_transfers": {
        "query": """
            SELECT
                CONVERT(varchar(36), TransferID) AS TransferID,
                CONVERT(varchar(36), FromPopID) AS FromPopID,
                CONVERT(varchar(36), ToPopID) AS ToPopID,
                CONVERT(varchar(36), ExistingPopID) AS ExistingPopID,
                CONVERT(varchar(36), RemainingPopID) AS RemainingPopID,
                CONVERT(varchar(10), ReasonForTransferID) AS ReasonForTransferID,
                CONVERT(varchar(19), TransferTime, 120) AS TransferTime,
                CONVERT(varchar(32), TransferredCount) AS TransferredCount,
                CONVERT(varchar(32), RemainingCount) AS RemainingCount,
                CONVERT(varchar(36), RegisteredBy) AS RegisteredBy,
                CONVERT(varchar(19), RegistrationTime, 120) AS RegistrationTime
            FROM dbo.WrassePopTransfer
        """,
        "headers": [
            "TransferID",
            "FromPopID",
            "ToPopID",
            "ExistingPopID",
            "RemainingPopID",
            "ReasonForTransferID",
            "TransferTime",
            "TransferredCount",
            "RemainingCount",
            "RegisteredBy",
            "RegistrationTime",
        ],
        "estimated_rows": 50000,
        "chunk_size": 0,
    },
    "wrasse_transfers": {
        "query": """
            SELECT
                CONVERT(varchar(36), FromContainerID) AS FromContainerID,
                CONVERT(varchar(36), ToContainerID) AS ToContainerID,
                CONVERT(varchar(10), SpeciesID) AS SpeciesID,
                CONVERT(varchar(19), TransferTime, 120) AS TransferTime,
                CONVERT(varchar(32), TransferredCount) AS TransferredCount,
                CONVERT(varchar(5), AllTransferred) AS AllTransferred,
                CONVERT(varchar(36), RegisteredBy) AS RegisteredBy,
                CONVERT(varchar(19), RegistrationTime, 120) AS RegistrationTime,
                CONVERT(varchar(10), ReasonID) AS ReasonID
            FROM dbo.WrasseTransfer
        """,
        "headers": [
            "FromContainerID",
            "ToContainerID",
            "SpeciesID",
            "TransferTime",
            "TransferredCount",
            "AllTransferred",
            "RegisteredBy",
            "RegistrationTime",
            "ReasonID",
        ],
        "estimated_rows": 50000,
        "chunk_size": 0,
    },
    "ff_bio_transfers": {
        "query": """
            SELECT
                CONVERT(varchar(36), FinancialScenarioID) AS FinancialScenarioID,
                CONVERT(varchar(36), PeriodID) AS PeriodID,
                CONVERT(varchar(10), Generation) AS Generation,
                CONVERT(varchar(10), SpeciesID) AS SpeciesID,
                CONVERT(varchar(10), FishTypeID) AS FishTypeID,
                CONVERT(varchar(36), SiteID) AS SiteID,
                CONVERT(varchar(10), CostingProjectID) AS CostingProjectID,
                CONVERT(varchar(32), TransferCost) AS TransferCost,
                CONVERT(varchar(32), TransferCount) AS TransferCount,
                CONVERT(varchar(32), TransferBiomass) AS TransferBiomass
            FROM dbo.FFBioTransfer
        """,
        "headers": [
            "FinancialScenarioID",
            "PeriodID",
            "Generation",
            "SpeciesID",
            "FishTypeID",
            "SiteID",
            "CostingProjectID",
            "TransferCost",
            "TransferCount",
            "TransferBiomass",
        ],
        "estimated_rows": 20000,
        "chunk_size": 0,
    },
    "ff_costing_bio_transfers": {
        "query": """
            SELECT
                CONVERT(varchar(36), FinancialScenarioID) AS FinancialScenarioID,
                CONVERT(varchar(36), PeriodID) AS PeriodID,
                CONVERT(varchar(10), FromGeneration) AS FromGeneration,
                CONVERT(varchar(10), FromSpeciesID) AS FromSpeciesID,
                CONVERT(varchar(10), FromFishTypeID) AS FromFishTypeID,
                CONVERT(varchar(36), FromSiteID) AS FromSiteID,
                CONVERT(varchar(10), FromCostingProjectID) AS FromCostingProjectID,
                CONVERT(varchar(10), ToGeneration) AS ToGeneration,
                CONVERT(varchar(10), ToSpeciesID) AS ToSpeciesID,
                CONVERT(varchar(10), ToFishTypeID) AS ToFishTypeID,
                CONVERT(varchar(36), ToSiteID) AS ToSiteID,
                CONVERT(varchar(10), ToCostingProjectID) AS ToCostingProjectID,
                CONVERT(varchar(10), Dimension) AS Dimension,
                CONVERT(varchar(5), Actual) AS Actual,
                CONVERT(varchar(36), FromCostCenterID) AS FromCostCenterID,
                CONVERT(varchar(36), ToCostCenterID) AS ToCostCenterID,
                CONVERT(varchar(32), DeltaCount) AS DeltaCount,
                CONVERT(varchar(32), DeltaBiomass) AS DeltaBiomass,
                CONVERT(varchar(32), DeltaInputCount) AS DeltaInputCount,
                CONVERT(varchar(32), DeltaInputBiomass) AS DeltaInputBiomass,
                CONVERT(varchar(32), DeltaMortalityCount) AS DeltaMortalityCount,
                CONVERT(varchar(32), DeltaMortalityBiomass) AS DeltaMortalityBiomass,
                CONVERT(varchar(32), DeltaFeedUse) AS DeltaFeedUse,
                CONVERT(varchar(32), DeltaLossAfterStartFeedingCount) AS DeltaLossAfterStartFeedingCount,
                CONVERT(varchar(32), DeltaLossAfterStartFeedingBiomass) AS DeltaLossAfterStartFeedingBiomass,
                CONVERT(varchar(32), DeltaFishDays) AS DeltaFishDays,
                CONVERT(varchar(32), DeltaCulledCount) AS DeltaCulledCount,
                CONVERT(varchar(32), DeltaCulledBiomass) AS DeltaCulledBiomass,
                CONVERT(varchar(10), TransferType) AS TransferType
            FROM dbo.FFCostingBioTransfer
        """,
        "headers": [
            "FinancialScenarioID",
            "PeriodID",
            "FromGeneration",
            "FromSpeciesID",
            "FromFishTypeID",
            "FromSiteID",
            "FromCostingProjectID",
            "ToGeneration",
            "ToSpeciesID",
            "ToFishTypeID",
            "ToSiteID",
            "ToCostingProjectID",
            "Dimension",
            "Actual",
            "FromCostCenterID",
            "ToCostCenterID",
            "DeltaCount",
            "DeltaBiomass",
            "DeltaInputCount",
            "DeltaInputBiomass",
            "DeltaMortalityCount",
            "DeltaMortalityBiomass",
            "DeltaFeedUse",
            "DeltaLossAfterStartFeedingCount",
            "DeltaLossAfterStartFeedingBiomass",
            "DeltaFishDays",
            "DeltaCulledCount",
            "DeltaCulledBiomass",
            "TransferType",
        ],
        "estimated_rows": 50000,
        "chunk_size": 0,
    },
    "ff_costing_bio_transfer_attribute_counts": {
        "query": """
            SELECT
                CONVERT(varchar(36), FinancialScenarioID) AS FinancialScenarioID,
                CONVERT(varchar(36), PeriodID) AS PeriodID,
                CONVERT(varchar(10), FromGeneration) AS FromGeneration,
                CONVERT(varchar(10), FromSpeciesID) AS FromSpeciesID,
                CONVERT(varchar(10), FromFishTypeID) AS FromFishTypeID,
                CONVERT(varchar(36), FromSiteID) AS FromSiteID,
                CONVERT(varchar(10), FromCostingProjectID) AS FromCostingProjectID,
                CONVERT(varchar(10), ToGeneration) AS ToGeneration,
                CONVERT(varchar(10), ToSpeciesID) AS ToSpeciesID,
                CONVERT(varchar(10), ToFishTypeID) AS ToFishTypeID,
                CONVERT(varchar(36), ToSiteID) AS ToSiteID,
                CONVERT(varchar(10), ToCostingProjectID) AS ToCostingProjectID,
                CONVERT(varchar(10), Dimension) AS Dimension,
                CONVERT(varchar(10), AttributeID) AS AttributeID,
                CONVERT(varchar(32), DeltaCount) AS DeltaCount,
                CONVERT(varchar(32), DeltaCulledCount) AS DeltaCulledCount,
                CONVERT(varchar(32), DeltaMortalityCount) AS DeltaMortalityCount,
                CONVERT(varchar(10), TransferType) AS TransferType
            FROM dbo.FFCostingBioTransferAttributeCounts
        """,
        "headers": [
            "FinancialScenarioID",
            "PeriodID",
            "FromGeneration",
            "FromSpeciesID",
            "FromFishTypeID",
            "FromSiteID",
            "FromCostingProjectID",
            "ToGeneration",
            "ToSpeciesID",
            "ToFishTypeID",
            "ToSiteID",
            "ToCostingProjectID",
            "Dimension",
            "AttributeID",
            "DeltaCount",
            "DeltaCulledCount",
            "DeltaMortalityCount",
            "TransferType",
        ],
        "estimated_rows": 50000,
        "chunk_size": 0,
    },
    "grouped_organisation": {
        "query": """
            SELECT
                CONVERT(varchar(36), ContainerID) AS ContainerID,
                ISNULL(Site, '') AS Site,
                ISNULL(SiteGroup, '') AS SiteGroup,
                ISNULL(Company, '') AS Company,
                ISNULL(ProdStage, '') AS ProdStage,
                ISNULL(ContainerGroup, '') AS ContainerGroup,
                ISNULL(CONVERT(varchar(36), ContainerGroupID), '') AS ContainerGroupID,
                ISNULL(StandName, '') AS StandName,
                ISNULL(CONVERT(varchar(36), StandID), '') AS StandID
            FROM dbo.Ext_GroupedOrganisation_v2
        """,
        "headers": [
            "ContainerID", "Site", "SiteGroup", "Company", "ProdStage",
            "ContainerGroup", "ContainerGroupID", "StandName", "StandID",
        ],
        "estimated_rows": 17000,
        "chunk_size": 0,
    },
    "feed_suppliers": {
        "query": """
            SELECT
                CONVERT(varchar(36), FeedSupplierID) AS FeedSupplierID,
                CONVERT(varchar(200), Name) AS Name
            FROM dbo.Ext_FeedSuppliers_v2
        """,
        "headers": ["FeedSupplierID", "Name"],
        "estimated_rows": 200,
        "chunk_size": 0,
    },
    "feed_types": {
        "query": """
            SELECT
                CONVERT(varchar(36), FeedTypeID) AS FeedTypeID,
                CONVERT(varchar(200), Name) AS Name,
                CONVERT(varchar(36), FeedSupplierID) AS FeedSupplierID
            FROM dbo.Ext_FeedTypes_v2
            WHERE Name IS NOT NULL
        """,
        "headers": ["FeedTypeID", "Name", "FeedSupplierID"],
        "estimated_rows": 5000,
        "chunk_size": 0,
    },
    "feed_stores": {
        "query": """
            SELECT
                CONVERT(varchar(36), FeedStoreID) AS FeedStoreID,
                CONVERT(varchar(200), FeedStoreName) AS FeedStoreName,
                CONVERT(varchar(36), OrgUnitID) AS OrgUnitID,
                CONVERT(varchar(10), Active) AS Active,
                CONVERT(varchar(32), Capacity) AS Capacity,
                CONVERT(varchar(36), FeedStoreTypeID) AS FeedStoreTypeID
            FROM dbo.Ext_FeedStore_v2
            WHERE FeedStoreName IS NOT NULL
        """,
        "headers": ["FeedStoreID", "FeedStoreName", "OrgUnitID", "Active", "Capacity", "FeedStoreTypeID"],
        "estimated_rows": 2000,
        "chunk_size": 0,
    },
    "feed_deliveries": {
        "query": """
            SELECT
                CONVERT(varchar(36), FeedReceptionID) AS FeedReceptionID,
                CONVERT(varchar(32), AmountKg) AS AmountKg,
                CONVERT(varchar(32), Price) AS Price,
                CONVERT(varchar(36), FeedTypeID) AS FeedTypeID,
                CONVERT(varchar(36), FeedStoreID) AS FeedStoreID,
                CONVERT(varchar(36), SupplierID) AS SupplierID,
                CONVERT(varchar(100), BatchNumber) AS BatchNumber,
                CONVERT(varchar(19), ReceptionDate, 120) AS ReceptionDate
            FROM dbo.Ext_FeedDelivery_v2
        """,
        "headers": [
            "FeedReceptionID", "AmountKg", "Price", "FeedTypeID", "FeedStoreID",
            "SupplierID", "BatchNumber", "ReceptionDate",
        ],
        "estimated_rows": 200000,
        "chunk_size": 0,
    },
}


class BulkExtractor:
    """Bulk extractor that streams FishTalk data to CSV files."""
    
    def __init__(self, output_dir: Path, profile: str = "fishtalk_readonly"):
        self.output_dir = output_dir
        self.extractor = BaseExtractor(ExtractionContext(profile=profile))
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
    def get_date_range(self) -> tuple[datetime, datetime]:
        """Get the overall date range from FishTalk data."""
        # Query for min/max dates
        min_rows = self.extractor._run_sqlcmd(
            query="SELECT CONVERT(varchar(10), MIN(StartTime), 120) AS MinDate FROM dbo.Populations WHERE StartTime IS NOT NULL",
            headers=["MinDate"],
        )
        max_rows = self.extractor._run_sqlcmd(
            query="SELECT CONVERT(varchar(10), MAX(EndTime), 120) AS MaxDate FROM dbo.Populations WHERE EndTime IS NOT NULL",
            headers=["MaxDate"],
        )
        
        min_date = datetime(2010, 1, 1)  # Fallback
        max_date = datetime.now()
        
        if min_rows and min_rows[0].get("MinDate"):
            try:
                min_date = datetime.strptime(min_rows[0]["MinDate"], "%Y-%m-%d")
            except (ValueError, TypeError):
                pass
                
        if max_rows and max_rows[0].get("MaxDate"):
            try:
                max_date = datetime.strptime(max_rows[0]["MaxDate"], "%Y-%m-%d")
            except (ValueError, TypeError):
                pass
                
        return min_date, max_date
    
    def count_rows(self, table_name: str) -> int:
        """Get exact row count for a table."""
        config = TABLE_CONFIGS.get(table_name)
        if not config:
            return 0
            
        # Build count query from the base query
        if "query" in config:
            base_query = config["query"]
        else:
            # For chunked tables, we need a simpler count
            table_map = {
                "status_values": "dbo.PublicStatusValues",
                "daily_sensor_readings": "dbo.Ext_DailySensorReadings_v2",
                "time_sensor_readings": "dbo.Ext_SensorReadings_v2",
            }
            if table_name in table_map:
                count_query = f"SELECT COUNT(*) AS RowCount FROM {table_map[table_name]}"
            else:
                return config.get("estimated_rows", 0)
        
        if "query" in config:
            # Extract FROM clause and wrap with COUNT
            # Simple approach: just use the config's table
            from_idx = base_query.upper().find("FROM ")
            if from_idx == -1:
                return config.get("estimated_rows", 0)
            
            from_clause = base_query[from_idx:]
            # Remove ORDER BY if present
            order_idx = from_clause.upper().find("ORDER BY")
            if order_idx != -1:
                from_clause = from_clause[:order_idx]
            
            count_query = f"SELECT COUNT(*) AS RowCount {from_clause}"
        
        try:
            rows = self.extractor._run_sqlcmd(query=count_query, headers=["RowCount"])
            if rows and rows[0].get("RowCount"):
                return int(rows[0]["RowCount"])
        except Exception as e:
            print(f"  Warning: Could not count {table_name}: {e}")
            
        return config.get("estimated_rows", 0)
    
    def extract_simple(self, table_name: str, dry_run: bool = False) -> int:
        """Extract a simple (non-chunked) table."""
        config = TABLE_CONFIGS.get(table_name)
        if not config:
            print(f"  Unknown table: {table_name}")
            return 0
            
        output_path = self.output_dir / f"{table_name}.csv"
        
        if dry_run:
            count = self.count_rows(table_name)
            print(f"  [DRY RUN] {table_name}: ~{count:,} rows -> {output_path.name}")
            return count
        
        print(f"  Extracting {table_name}...", end=" ", flush=True)
        start_time = time.time()
        
        try:
            rows = self.extractor._run_sqlcmd(
                query=config["query"],
                headers=config["headers"],
            )
        except Exception as e:
            print(f"ERROR: {e}")
            return 0
        
        # Write to CSV
        with output_path.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=config["headers"])
            writer.writeheader()
            writer.writerows(rows)
        
        elapsed = time.time() - start_time
        print(f"{len(rows):,} rows in {elapsed:.1f}s ({len(rows)/elapsed:.0f}/s)")
        return len(rows)
    
    def extract_chunked(self, table_name: str, dry_run: bool = False) -> int:
        """Extract a large table in date-based chunks."""
        config = TABLE_CONFIGS.get(table_name)
        if not config or "query_template" not in config:
            print(f"  Unknown chunked table: {table_name}")
            return 0
        
        output_path = self.output_dir / f"{table_name}.csv"
        
        if dry_run:
            count = self.count_rows(table_name)
            print(f"  [DRY RUN] {table_name}: ~{count:,} rows -> {output_path.name}")
            return count
        
        print(f"  Extracting {table_name} (chunked)...")
        start_time = time.time()
        total_rows = 0
        
        # Get date range
        min_date, max_date = self.get_date_range()
        
        # Calculate chunk intervals (monthly chunks for large tables)
        from dateutil.relativedelta import relativedelta
        current_date = min_date
        
        # Open file and write header
        with output_path.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=config["headers"])
            writer.writeheader()
            
            chunk_num = 0
            while current_date < max_date:
                next_date = current_date + relativedelta(months=1)
                if next_date > max_date:
                    next_date = max_date + relativedelta(days=1)
                
                start_str = current_date.strftime("%Y-%m-%d")
                end_str = next_date.strftime("%Y-%m-%d")
                
                query = config["query_template"].format(
                    start_date=start_str,
                    end_date=end_str,
                )
                
                try:
                    rows = self.extractor._run_sqlcmd(
                        query=query,
                        headers=config["headers"],
                    )
                except Exception as e:
                    print(f"    Chunk {chunk_num} ({start_str}): ERROR - {e}")
                    current_date = next_date
                    chunk_num += 1
                    continue
                
                if rows:
                    writer.writerows(rows)
                    total_rows += len(rows)
                
                elapsed = time.time() - start_time
                rate = total_rows / elapsed if elapsed > 0 else 0
                print(f"    Chunk {chunk_num} ({start_str}): {len(rows):,} rows, total: {total_rows:,} ({rate:.0f}/s)")
                
                current_date = next_date
                chunk_num += 1
        
        elapsed = time.time() - start_time
        print(f"  Completed {table_name}: {total_rows:,} rows in {elapsed:.1f}s")
        return total_rows
    
    def extract_table(self, table_name: str, dry_run: bool = False) -> int:
        """Extract a single table (simple or chunked)."""
        config = TABLE_CONFIGS.get(table_name)
        if not config:
            print(f"  Unknown table: {table_name}")
            return 0
        
        if "query_template" in config:
            return self.extract_chunked(table_name, dry_run)
        else:
            return self.extract_simple(table_name, dry_run)
    
    def extract_all(self, tables: Optional[List[str]] = None, dry_run: bool = False) -> Dict[str, int]:
        """Extract all (or specified) tables."""
        if tables is None:
            tables = list(TABLE_CONFIGS.keys())
        
        results = {}
        total_start = time.time()
        
        print(f"\n{'='*70}")
        print("BULK FISHTALK EXTRACTION")
        print(f"{'='*70}")
        print(f"Output directory: {self.output_dir}")
        print(f"Tables to extract: {len(tables)}")
        print(f"Mode: {'DRY RUN' if dry_run else 'LIVE'}")
        print(f"{'='*70}\n")
        
        for i, table_name in enumerate(tables, 1):
            print(f"[{i}/{len(tables)}] {table_name}")
            row_count = self.extract_table(table_name, dry_run)
            results[table_name] = row_count
        
        total_elapsed = time.time() - total_start
        total_rows = sum(results.values())
        
        print(f"\n{'='*70}")
        print("EXTRACTION SUMMARY")
        print(f"{'='*70}")
        for table, count in results.items():
            print(f"  {table}: {count:,} rows")
        print(f"{'='*70}")
        print(f"Total rows: {total_rows:,}")
        print(f"Total time: {total_elapsed:.1f}s ({total_elapsed/60:.1f} minutes)")
        if total_elapsed > 0:
            print(f"Average rate: {total_rows/total_elapsed:,.0f} rows/second")
        print(f"{'='*70}")
        
        return results


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Bulk extract FishTalk data to CSV files for ETL migration"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="scripts/migration/data/extract/",
        help="Output directory for CSV files (default: scripts/migration/data/extract/)",
    )
    parser.add_argument(
        "--tables",
        type=str,
        help="Comma-separated list of tables to extract (default: all)",
    )
    parser.add_argument(
        "--sql-profile",
        type=str,
        default="fishtalk_readonly",
        help="SQL Server profile name (default: fishtalk_readonly)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be extracted without executing",
    )
    parser.add_argument(
        "--list-tables",
        action="store_true",
        help="List available tables and exit",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    
    if args.list_tables:
        print("\nAvailable tables:")
        for name, config in TABLE_CONFIGS.items():
            chunked = "chunked" if "query_template" in config else "simple"
            est = config.get("estimated_rows", 0)
            print(f"  {name}: ~{est:,} rows ({chunked})")
        return 0
    
    output_dir = PROJECT_ROOT / args.output
    
    tables = None
    if args.tables:
        tables = [t.strip() for t in args.tables.split(",")]
        # Validate tables
        invalid = [t for t in tables if t not in TABLE_CONFIGS]
        if invalid:
            print(f"Unknown tables: {invalid}")
            print(f"Available: {list(TABLE_CONFIGS.keys())}")
            return 1
    
    extractor = BulkExtractor(output_dir, profile=args.sql_profile)
    
    try:
        results = extractor.extract_all(tables=tables, dry_run=args.dry_run)
    except KeyboardInterrupt:
        print("\n\nExtraction interrupted by user")
        return 1
    except Exception as e:
        print(f"\nExtraction failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
