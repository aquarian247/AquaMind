#!/usr/bin/env python3
# flake8: noqa
"""SubTransfers-based batch chain stitching with project tuple linking.

This script uses a hybrid approach to identify biological batches:

1. **SubTransfers Chain Tracing**: Builds connected components from physical fish
   movements within environments (FW-only or Sea-only chains)

2. **Project Tuple Linking**: Links FW chains to Sea chains via shared project
   tuples, since FishTalk creates new population IDs when fish transfer from
   station to area (no SubTransfers record exists for this handoff)

Algorithm:
1. Load SubTransfers into a directed graph (populations as nodes, transfers as edges)
2. Find connected components using union-find (each component = environment chain)
3. Classify chains by environment (FW-only, Sea-only, or mixed)
4. Link FW and Sea chains that share the same project tuple
5. Output: linked_batches.csv with full lifecycle batch assignments

Usage:
    # Generate chains with project tuple linking (recommended)
    python subtransfer_chain_stitching.py --csv-dir scripts/migration/data/extract/ --link-by-project
    
    # Filter to recent batches only
    python subtransfer_chain_stitching.py --csv-dir scripts/migration/data/extract/ --min-year 2020 --link-by-project
    
    # SubTransfers-only chains (no linking, for analysis)
    python subtransfer_chain_stitching.py --csv-dir scripts/migration/data/extract/

Output:
    scripts/migration/output/chain_stitching/
    ├── batch_chains.csv           # SubTransfers chains (FW-only or Sea-only)
    ├── batch_summary.csv          # One row per chain with stats
    ├── linked_batches.csv         # Project-linked full lifecycle batches (with --link-by-project)
    ├── linked_batch_summary.csv   # Summary of linked batches
    ├── multi_geography_batches.csv # Anomalies needing review
    └── chain_stitching_report.txt # Summary report
"""

from __future__ import annotations

import argparse
import csv
import os
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# Stage mapping (same as used elsewhere in migration)
def fishtalk_stage_to_aquamind(stage_name: str) -> str | None:
    """Map FishTalk stage names to AquaMind lifecycle stages."""
    if not stage_name:
        return None
    upper = stage_name.upper()
    if any(token in upper for token in ("EGG", "ALEVIN", "SAC", "GREEN", "EYE")):
        return "Egg&Alevin"
    if "FRY" in upper:
        return "Fry"
    if "PARR" in upper:
        return "Parr"
    if "SMOLT" in upper and ("POST" in upper or "LARGE" in upper):
        return "Post-Smolt"
    if "SMOLT" in upper:
        return "Smolt"
    if any(token in upper for token in ("ONGROW", "GROWER", "GRILSE")):
        return "Adult"
    if "BROODSTOCK" in upper:
        return "Adult"
    return None


AQUAMIND_STAGE_ORDER = ["Egg&Alevin", "Fry", "Parr", "Smolt", "Post-Smolt", "Adult"]

# Environment classification
FW_STAGES = {"Egg&Alevin", "Fry", "Parr", "Smolt", "Post-Smolt"}
SEA_STAGES = {"Adult"}


@dataclass
class Population:
    """Population metadata."""
    population_id: str
    name: str = ""
    project_number: str = ""
    input_year: str = ""
    running_number: str = ""
    container_id: str = ""
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    stages: List[Tuple[datetime, str]] = field(default_factory=list)  # (time, stage_name)


@dataclass
class BatchChain:
    """A batch identified through SubTransfers chain tracing."""
    chain_id: str
    population_ids: Set[str] = field(default_factory=set)
    geographies: Set[str] = field(default_factory=set)
    org_units: Set[str] = field(default_factory=set)
    containers: Set[str] = field(default_factory=set)
    earliest_start: Optional[datetime] = None
    latest_end: Optional[datetime] = None
    stages: Set[str] = field(default_factory=set)
    is_valid: bool = True  # False if multi-geography
    project_tuples: Set[Tuple[str, str, str]] = field(default_factory=set)  # (project, year, running)
    
    @property
    def population_count(self) -> int:
        return len(self.population_ids)
    
    @property
    def stage_count(self) -> int:
        return len(self.stages)
    
    @property
    def geography(self) -> str:
        """Return single geography or 'MULTI' if multiple."""
        if len(self.geographies) == 1:
            return next(iter(self.geographies))
        return "MULTI"
    
    @property
    def environment(self) -> str:
        """Return environment type: FW, SEA, MIXED, or UNKNOWN."""
        has_fw = bool(self.stages & FW_STAGES)
        has_sea = bool(self.stages & SEA_STAGES)
        if has_fw and has_sea:
            return "MIXED"
        if has_fw:
            return "FW"
        if has_sea:
            return "SEA"
        return "UNKNOWN"


@dataclass
class LinkedBatch:
    """A full lifecycle batch linked via project tuple."""
    batch_id: str
    fw_chains: List[str] = field(default_factory=list)  # Chain IDs
    sea_chains: List[str] = field(default_factory=list)  # Chain IDs
    project_tuples: Set[Tuple[str, str, str]] = field(default_factory=set)
    population_ids: Set[str] = field(default_factory=set)
    geographies: Set[str] = field(default_factory=set)
    stages: Set[str] = field(default_factory=set)
    earliest_start: Optional[datetime] = None
    latest_end: Optional[datetime] = None
    
    @property
    def is_complete(self) -> bool:
        """True if batch has both FW and Sea chains."""
        return bool(self.fw_chains) and bool(self.sea_chains)
    
    @property
    def environment(self) -> str:
        if self.fw_chains and self.sea_chains:
            return "FULL_LIFECYCLE"
        if self.fw_chains:
            return "FW_ONLY"
        if self.sea_chains:
            return "SEA_ONLY"
        return "UNKNOWN"


class UnionFind:
    """Union-Find data structure for finding connected components."""
    
    def __init__(self):
        self.parent: Dict[str, str] = {}
        self.rank: Dict[str, int] = {}
    
    def find(self, x: str) -> str:
        """Find root of x with path compression."""
        if x not in self.parent:
            self.parent[x] = x
            self.rank[x] = 0
        if self.parent[x] != x:
            self.parent[x] = self.find(self.parent[x])
        return self.parent[x]
    
    def union(self, x: str, y: str) -> None:
        """Union two sets by rank."""
        root_x = self.find(x)
        root_y = self.find(y)
        
        if root_x == root_y:
            return
        
        if self.rank[root_x] < self.rank[root_y]:
            root_x, root_y = root_y, root_x
        
        self.parent[root_y] = root_x
        if self.rank[root_x] == self.rank[root_y]:
            self.rank[root_x] += 1
    
    def get_components(self) -> Dict[str, Set[str]]:
        """Get all connected components."""
        components: Dict[str, Set[str]] = defaultdict(set)
        for x in self.parent:
            root = self.find(x)
            components[root].add(x)
        return dict(components)


class ChainStitcher:
    """SubTransfers-based batch chain stitcher."""
    
    def __init__(self, csv_dir: Path, min_year: int = 2010):
        self.csv_dir = csv_dir
        self.min_year = min_year
        
        # Data stores
        self.populations: Dict[str, Population] = {}
        self.stage_names: Dict[str, str] = {}  # StageID -> StageName
        self.container_org: Dict[str, str] = {}  # ContainerID -> OrgUnitID
        self.org_geography: Dict[str, str] = {}  # OrgUnitID -> Geography
        self.org_names: Dict[str, str] = {}  # OrgUnitID -> Name
        
        # Graph
        self.uf = UnionFind()
        
        # Results
        self.batch_chains: List[BatchChain] = []
    
    def load_data(self) -> None:
        """Load all required CSV data."""
        print("Loading data from CSV files...")
        
        # Load production stages (reference)
        self._load_production_stages()
        
        # Load org units and build geography mapping
        self._load_org_units()
        
        # Load containers
        self._load_containers()
        
        # Load populations
        self._load_populations()
        
        # Load population stages
        self._load_population_stages()
        
        print(f"  Loaded {len(self.populations):,} populations")
        print(f"  Loaded {len(self.stage_names):,} stage definitions")
        print(f"  Loaded {len(self.container_org):,} containers")
        print(f"  Loaded {len(self.org_geography):,} org units with geography")
    
    def _load_production_stages(self) -> None:
        """Load production stage reference data."""
        path = self.csv_dir / "production_stages.csv"
        if not path.exists():
            print(f"  Warning: {path} not found")
            return
        
        with open(path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                self.stage_names[row["StageID"]] = row["StageName"]
    
    def _load_org_units(self) -> None:
        """Load org units and derive geography."""
        path = self.csv_dir / "org_units.csv"
        if not path.exists():
            print(f"  Warning: {path} not found")
            return
        
        # Known site patterns for geography resolution
        faroe_patterns = ["Gjógv", "Hvannasund", "Argir", "Norðtoftir", "Viðareiði", 
                         "Glyvradalur", "Strond", "Skopun", "Við Áir", "Lambavík",
                         "Borðoyavík", "Tvøroyri", "Hov", "Hvalba", "Gøtuvík",
                         "Fuglafjørður", "Árnafjørður", "Funningsfjørður", "Kolbeinargjógv"]
        scotland_patterns = ["Applecross", "Couldoran", "KinlochMoidart", "Langass", 
                            "Geocrab", "MaragayMor", "Maaey", "SgeirDughall", "Aird",
                            "WestStrome", "EastTarbertBay", "QuarryPoint", "Ardgaddan",
                            "GobaBharra", "Lamlash"]
        
        with open(path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                org_id = row["OrgUnitID"]
                name = row.get("Name", "")
                self.org_names[org_id] = name
                
                # Resolve geography from name patterns
                geography = "Unknown"
                for pattern in faroe_patterns:
                    if pattern.lower() in name.lower():
                        geography = "Faroe Islands"
                        break
                if geography == "Unknown":
                    for pattern in scotland_patterns:
                        if pattern.lower() in name.lower():
                            geography = "Scotland"
                            break
                
                self.org_geography[org_id] = geography
    
    def _load_containers(self) -> None:
        """Load container to org unit mapping."""
        path = self.csv_dir / "containers.csv"
        if not path.exists():
            print(f"  Warning: {path} not found")
            return
        
        with open(path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                self.container_org[row["ContainerID"]] = row.get("OrgUnitID", "")
    
    def _load_populations(self) -> None:
        """Load population metadata."""
        path = self.csv_dir / "populations.csv"
        if not path.exists():
            raise FileNotFoundError(f"Required file not found: {path}")
        
        with open(path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                start_time = None
                end_time = None
                
                if row.get("StartTime"):
                    try:
                        start_time = datetime.strptime(row["StartTime"], "%Y-%m-%d %H:%M:%S")
                    except ValueError:
                        pass
                
                if row.get("EndTime"):
                    try:
                        end_time = datetime.strptime(row["EndTime"], "%Y-%m-%d %H:%M:%S")
                    except ValueError:
                        pass
                
                # Filter by min_year
                if start_time and start_time.year < self.min_year:
                    continue
                
                pop = Population(
                    population_id=row["PopulationID"],
                    name=row.get("PopulationName", ""),
                    project_number=row.get("ProjectNumber", ""),
                    input_year=row.get("InputYear", ""),
                    running_number=row.get("RunningNumber", ""),
                    container_id=row.get("ContainerID", ""),
                    start_time=start_time,
                    end_time=end_time,
                )
                self.populations[pop.population_id] = pop
    
    def _load_population_stages(self) -> None:
        """Load population stage history."""
        path = self.csv_dir / "population_stages.csv"
        if not path.exists():
            print(f"  Warning: {path} not found")
            return
        
        with open(path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                pop_id = row["PopulationID"]
                if pop_id not in self.populations:
                    continue
                
                stage_id = row.get("StageID", "")
                stage_name = self.stage_names.get(stage_id, "")
                
                start_time = None
                if row.get("StartTime"):
                    try:
                        start_time = datetime.strptime(row["StartTime"], "%Y-%m-%d %H:%M:%S")
                    except ValueError:
                        pass
                
                if start_time and stage_name:
                    self.populations[pop_id].stages.append((start_time, stage_name))
        
        # Sort stages by time for each population
        for pop in self.populations.values():
            pop.stages.sort(key=lambda x: x[0])
    
    def build_transfer_graph(self) -> int:
        """Build graph from SubTransfers and find connected components."""
        path = self.csv_dir / "sub_transfers.csv"
        if not path.exists():
            raise FileNotFoundError(f"Required file not found: {path}")
        
        print("Building transfer graph...")
        transfer_count = 0
        
        with open(path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                src_before = row.get("SourcePopBefore", "")
                src_after = row.get("SourcePopAfter", "")
                dst_after = row.get("DestPopAfter", "")
                
                # Skip transfers involving populations we don't have (filtered by year)
                if src_before and src_before not in self.populations:
                    continue
                
                # Union all connected populations
                pops_in_transfer = [p for p in [src_before, src_after, dst_after] if p]
                if len(pops_in_transfer) >= 2:
                    for i in range(1, len(pops_in_transfer)):
                        self.uf.union(pops_in_transfer[0], pops_in_transfer[i])
                    transfer_count += 1
                elif len(pops_in_transfer) == 1:
                    # Single population, ensure it's in the union-find
                    self.uf.find(pops_in_transfer[0])
        
        print(f"  Processed {transfer_count:,} transfers")
        return transfer_count
    
    def identify_batch_chains(self) -> None:
        """Identify batch chains from connected components."""
        print("Identifying batch chains...")
        
        # Ensure all populations are in union-find (even those with no transfers)
        for pop_id in self.populations:
            self.uf.find(pop_id)
        
        # Get connected components
        components = self.uf.get_components()
        print(f"  Found {len(components):,} connected components")
        
        # Build batch chains
        for chain_idx, (root, pop_ids) in enumerate(sorted(components.items(), 
                                                           key=lambda x: -len(x[1]))):
            chain = BatchChain(
                chain_id=f"CHAIN-{chain_idx + 1:05d}",
                population_ids=pop_ids,
            )
            
            # Aggregate metadata from all populations
            for pop_id in pop_ids:
                pop = self.populations.get(pop_id)
                if not pop:
                    continue
                
                # Project tuple for linking
                if pop.project_number and pop.input_year:
                    chain.project_tuples.add((pop.project_number, pop.input_year, pop.running_number or ""))
                
                # Containers and org units
                if pop.container_id:
                    chain.containers.add(pop.container_id)
                    org_id = self.container_org.get(pop.container_id)
                    if org_id:
                        chain.org_units.add(org_id)
                        geo = self.org_geography.get(org_id, "Unknown")
                        chain.geographies.add(geo)
                
                # Time bounds
                if pop.start_time:
                    if chain.earliest_start is None or pop.start_time < chain.earliest_start:
                        chain.earliest_start = pop.start_time
                if pop.end_time:
                    if chain.latest_end is None or pop.end_time > chain.latest_end:
                        chain.latest_end = pop.end_time
                
                # Stages
                for _, stage_name in pop.stages:
                    aquamind_stage = fishtalk_stage_to_aquamind(stage_name)
                    if aquamind_stage:
                        chain.stages.add(aquamind_stage)
            
            # Validate: single geography required
            chain.is_valid = len(chain.geographies) <= 1 or chain.geographies == {"Unknown"}
            
            self.batch_chains.append(chain)
        
        # Sort by population count (descending)
        self.batch_chains.sort(key=lambda c: -c.population_count)
        
        valid_count = sum(1 for c in self.batch_chains if c.is_valid)
        invalid_count = len(self.batch_chains) - valid_count
        print(f"  Valid batches (single geography): {valid_count:,}")
        print(f"  Invalid batches (multi-geography): {invalid_count:,}")
    
    def get_population_geography(self, pop_id: str) -> str:
        """Get geography for a population via its container."""
        pop = self.populations.get(pop_id)
        if not pop or not pop.container_id:
            return "Unknown"
        
        org_id = self.container_org.get(pop.container_id)
        if not org_id:
            return "Unknown"
        
        return self.org_geography.get(org_id, "Unknown")
    
    def link_chains_by_project(self) -> List[LinkedBatch]:
        """Link FW and Sea chains via shared project tuples.
        
        Only links chains that share both:
        1. A project tuple
        2. A primary geography (Faroe Islands or Scotland, not Unknown)
        
        Unknown geography chains are NOT used as bridges between known geographies.
        
        Returns:
            List of LinkedBatch objects representing full lifecycle batches.
        """
        print("Linking chains by project tuple...")
        
        # Build index: project_tuple -> list of chain_ids
        chains_by_id = {c.chain_id: c for c in self.batch_chains}
        
        # Get primary geography for each chain (most common non-Unknown)
        def get_primary_geography(chain: BatchChain) -> str:
            geos = [g for g in chain.geographies if g not in ("Unknown", "MULTI")]
            if geos:
                return geos[0]  # Return first known geography
            return chain.geography
        
        # Build index: (project_tuple, primary_geography) -> list of chain_ids
        tuple_geo_to_chains: Dict[Tuple[str, str, str, str], List[str]] = defaultdict(list)
        
        for chain in self.batch_chains:
            if chain.geography == "MULTI":
                # Skip multi-geography chains entirely
                continue
            
            primary_geo = get_primary_geography(chain)
            
            for pt in chain.project_tuples:
                # Only index with known geography - don't let Unknown bridge
                if primary_geo in ("Faroe Islands", "Scotland"):
                    key = (pt[0], pt[1], pt[2], primary_geo)
                    tuple_geo_to_chains[key].append(chain.chain_id)
                elif primary_geo == "Unknown":
                    # Unknown chains can link with each other but not bridge
                    key = (pt[0], pt[1], pt[2], "Unknown")
                    tuple_geo_to_chains[key].append(chain.chain_id)
        
        # Group chains that share project tuples AND geography using union-find
        chain_uf = UnionFind()
        for chain in self.batch_chains:
            chain_uf.find(chain.chain_id)  # Ensure all chains are in the structure
        
        for key, chain_ids in tuple_geo_to_chains.items():
            if len(chain_ids) > 1:
                for i in range(1, len(chain_ids)):
                    chain_uf.union(chain_ids[0], chain_ids[i])
        
        # Get linked chain groups
        linked_groups = chain_uf.get_components()
        
        # Build LinkedBatch objects
        linked_batches: List[LinkedBatch] = []
        for batch_idx, (root, chain_ids) in enumerate(sorted(linked_groups.items(),
                                                              key=lambda x: -len(x[1]))):
            batch = LinkedBatch(batch_id=f"BATCH-{batch_idx + 1:05d}")
            
            for chain_id in chain_ids:
                chain = chains_by_id.get(chain_id)
                if not chain:
                    continue
                
                # Classify chain by environment
                if chain.environment == "FW":
                    batch.fw_chains.append(chain_id)
                elif chain.environment == "SEA":
                    batch.sea_chains.append(chain_id)
                else:
                    # Unknown or mixed - add to FW for now
                    batch.fw_chains.append(chain_id)
                
                # Aggregate data
                batch.project_tuples.update(chain.project_tuples)
                batch.population_ids.update(chain.population_ids)
                batch.geographies.update(chain.geographies)
                batch.stages.update(chain.stages)
                
                if chain.earliest_start:
                    if batch.earliest_start is None or chain.earliest_start < batch.earliest_start:
                        batch.earliest_start = chain.earliest_start
                if chain.latest_end:
                    if batch.latest_end is None or chain.latest_end > batch.latest_end:
                        batch.latest_end = chain.latest_end
            
            linked_batches.append(batch)
        
        # Sort by population count
        linked_batches.sort(key=lambda b: -len(b.population_ids))
        
        # Stats
        full_lifecycle = sum(1 for b in linked_batches if b.is_complete)
        fw_only = sum(1 for b in linked_batches if b.environment == "FW_ONLY")
        sea_only = sum(1 for b in linked_batches if b.environment == "SEA_ONLY")
        
        print(f"  Created {len(linked_batches):,} linked batches")
        print(f"    Full lifecycle (FW + Sea): {full_lifecycle:,}")
        print(f"    FW only: {fw_only:,}")
        print(f"    Sea only: {sea_only:,}")
        
        return linked_batches
    
    def write_outputs(self, output_dir: Path, dry_run: bool = False, linked_batches: List[LinkedBatch] = None) -> None:
        """Write output CSV files."""
        output_dir.mkdir(parents=True, exist_ok=True)
        
        if dry_run:
            print(f"\n[DRY RUN] Would write to {output_dir}")
            return
        
        print(f"\nWriting outputs to {output_dir}...")
        
        # 1. Batch chains (detailed)
        chains_path = output_dir / "batch_chains.csv"
        with open(chains_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["chain_id", "population_id", "population_name", "project_tuple",
                           "container_id", "org_unit", "geography", "start_time", "end_time",
                           "stages"])
            
            for chain in self.batch_chains:
                for pop_id in sorted(chain.population_ids):
                    pop = self.populations.get(pop_id)
                    if not pop:
                        continue
                    
                    project_tuple = f"{pop.project_number}/{pop.input_year}/{pop.running_number}"
                    org_id = self.container_org.get(pop.container_id, "")
                    org_name = self.org_names.get(org_id, "")
                    geo = self.get_population_geography(pop_id)
                    stages_str = ";".join(s for _, s in pop.stages)
                    
                    writer.writerow([
                        chain.chain_id,
                        pop_id,
                        pop.name,
                        project_tuple,
                        pop.container_id,
                        org_name,
                        geo,
                        pop.start_time.isoformat() if pop.start_time else "",
                        pop.end_time.isoformat() if pop.end_time else "",
                        stages_str,
                    ])
        print(f"  Wrote {chains_path.name}")
        
        # 2. Batch summary
        summary_path = output_dir / "batch_summary.csv"
        with open(summary_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["chain_id", "population_count", "container_count", "org_unit_count",
                           "geography", "environment", "is_valid", "earliest_start", "latest_end",
                           "stage_count", "stages", "project_tuples"])
            
            for chain in self.batch_chains:
                stages_ordered = [s for s in AQUAMIND_STAGE_ORDER if s in chain.stages]
                tuples_str = ";".join(f"{p}/{y}/{r}" for p, y, r in sorted(chain.project_tuples)[:5])
                
                writer.writerow([
                    chain.chain_id,
                    chain.population_count,
                    len(chain.containers),
                    len(chain.org_units),
                    chain.geography,
                    chain.environment,
                    chain.is_valid,
                    chain.earliest_start.isoformat() if chain.earliest_start else "",
                    chain.latest_end.isoformat() if chain.latest_end else "",
                    chain.stage_count,
                    ";".join(stages_ordered),
                    tuples_str,
                ])
        print(f"  Wrote {summary_path.name}")
        
        # 3. Multi-geography batches (anomalies)
        anomalies_path = output_dir / "multi_geography_batches.csv"
        anomalies = [c for c in self.batch_chains if not c.is_valid]
        with open(anomalies_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["chain_id", "population_count", "geographies", "org_units"])
            
            for chain in anomalies:
                org_names = [self.org_names.get(o, o) for o in chain.org_units]
                writer.writerow([
                    chain.chain_id,
                    chain.population_count,
                    ";".join(sorted(chain.geographies)),
                    ";".join(sorted(org_names)[:10]),  # Limit to first 10
                ])
        print(f"  Wrote {anomalies_path.name} ({len(anomalies)} anomalies)")
        
        # 4. Linked batches (if provided)
        if linked_batches:
            linked_path = output_dir / "linked_batches.csv"
            with open(linked_path, "w", encoding="utf-8", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["batch_id", "chain_id", "chain_type", "population_id", 
                               "project_tuple", "geography", "start_time", "end_time", "stages"])
                
                chains_by_id = {c.chain_id: c for c in self.batch_chains}
                for batch in linked_batches:
                    # Write FW chains
                    for chain_id in batch.fw_chains:
                        chain = chains_by_id.get(chain_id)
                        if not chain:
                            continue
                        for pop_id in sorted(chain.population_ids):
                            pop = self.populations.get(pop_id)
                            if not pop:
                                continue
                            project_tuple = f"{pop.project_number}/{pop.input_year}/{pop.running_number}"
                            geo = self.get_population_geography(pop_id)
                            stages_str = ";".join(s for _, s in pop.stages)
                            writer.writerow([
                                batch.batch_id, chain_id, "FW", pop_id,
                                project_tuple, geo,
                                pop.start_time.isoformat() if pop.start_time else "",
                                pop.end_time.isoformat() if pop.end_time else "",
                                stages_str,
                            ])
                    # Write Sea chains
                    for chain_id in batch.sea_chains:
                        chain = chains_by_id.get(chain_id)
                        if not chain:
                            continue
                        for pop_id in sorted(chain.population_ids):
                            pop = self.populations.get(pop_id)
                            if not pop:
                                continue
                            project_tuple = f"{pop.project_number}/{pop.input_year}/{pop.running_number}"
                            geo = self.get_population_geography(pop_id)
                            stages_str = ";".join(s for _, s in pop.stages)
                            writer.writerow([
                                batch.batch_id, chain_id, "SEA", pop_id,
                                project_tuple, geo,
                                pop.start_time.isoformat() if pop.start_time else "",
                                pop.end_time.isoformat() if pop.end_time else "",
                                stages_str,
                            ])
            print(f"  Wrote {linked_path.name}")
            
            # Linked batch summary
            linked_summary_path = output_dir / "linked_batch_summary.csv"
            with open(linked_summary_path, "w", encoding="utf-8", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["batch_id", "environment", "fw_chains", "sea_chains", 
                               "population_count", "geography", "earliest_start", "latest_end",
                               "stage_count", "stages", "is_complete"])
                
                for batch in linked_batches:
                    stages_ordered = [s for s in AQUAMIND_STAGE_ORDER if s in batch.stages]
                    geo = next(iter(batch.geographies)) if len(batch.geographies) == 1 else "MULTI"
                    
                    writer.writerow([
                        batch.batch_id,
                        batch.environment,
                        len(batch.fw_chains),
                        len(batch.sea_chains),
                        len(batch.population_ids),
                        geo,
                        batch.earliest_start.isoformat() if batch.earliest_start else "",
                        batch.latest_end.isoformat() if batch.latest_end else "",
                        len(batch.stages),
                        ";".join(stages_ordered),
                        batch.is_complete,
                    ])
            print(f"  Wrote {linked_summary_path.name}")
        
        # 5. Report
        report_path = output_dir / "chain_stitching_report.txt"
        with open(report_path, "w", encoding="utf-8") as f:
            f.write("=" * 70 + "\n")
            f.write("SUBTRANSFERS CHAIN STITCHING REPORT\n")
            f.write(f"Generated: {datetime.now().isoformat()}\n")
            f.write("=" * 70 + "\n\n")
            
            f.write(f"Input data: {self.csv_dir}\n")
            f.write(f"Min year filter: {self.min_year}\n\n")
            
            f.write("DATA LOADED:\n")
            f.write(f"  Populations: {len(self.populations):,}\n")
            f.write(f"  Containers: {len(self.container_org):,}\n")
            f.write(f"  Org Units: {len(self.org_geography):,}\n\n")
            
            f.write("BATCH CHAINS:\n")
            f.write(f"  Total chains: {len(self.batch_chains):,}\n")
            f.write(f"  Valid (single geography): {sum(1 for c in self.batch_chains if c.is_valid):,}\n")
            f.write(f"  Invalid (multi-geography): {sum(1 for c in self.batch_chains if not c.is_valid):,}\n\n")
            
            # Distribution by population count
            f.write("CHAIN SIZE DISTRIBUTION:\n")
            size_buckets = defaultdict(int)
            for chain in self.batch_chains:
                if chain.population_count == 1:
                    size_buckets["1 pop"] += 1
                elif chain.population_count <= 5:
                    size_buckets["2-5 pops"] += 1
                elif chain.population_count <= 20:
                    size_buckets["6-20 pops"] += 1
                elif chain.population_count <= 100:
                    size_buckets["21-100 pops"] += 1
                else:
                    size_buckets["100+ pops"] += 1
            
            for bucket in ["1 pop", "2-5 pops", "6-20 pops", "21-100 pops", "100+ pops"]:
                f.write(f"  {bucket}: {size_buckets[bucket]:,}\n")
            
            f.write("\n")
            
            # Distribution by stage count
            f.write("STAGE COVERAGE DISTRIBUTION:\n")
            stage_buckets = defaultdict(int)
            for chain in self.batch_chains:
                stage_buckets[chain.stage_count] += 1
            
            for stage_count in sorted(stage_buckets.keys()):
                f.write(f"  {stage_count} stages: {stage_buckets[stage_count]:,}\n")
            
            f.write("\n")
            
            # Top 20 largest chains
            f.write("TOP 20 LARGEST CHAINS:\n")
            for chain in self.batch_chains[:20]:
                stages_str = ",".join(s for s in AQUAMIND_STAGE_ORDER if s in chain.stages)
                f.write(f"  {chain.chain_id}: {chain.population_count} pops, "
                       f"geo={chain.geography}, stages=[{stages_str}]\n")
        
        print(f"  Wrote {report_path.name}")
    
    def run(self, output_dir: Path, dry_run: bool = False, link_by_project: bool = False) -> None:
        """Run the full stitching pipeline."""
        self.load_data()
        self.build_transfer_graph()
        self.identify_batch_chains()
        
        linked_batches = None
        if link_by_project:
            linked_batches = self.link_chains_by_project()
        
        self.write_outputs(output_dir, dry_run, linked_batches)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="SubTransfers-based batch chain stitching with project tuple linking",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # SubTransfers chains with project tuple linking (recommended for full lifecycle)
  python subtransfer_chain_stitching.py --csv-dir scripts/migration/data/extract/ --link-by-project
  
  # SubTransfers-only chains (for analysis)
  python subtransfer_chain_stitching.py --csv-dir scripts/migration/data/extract/
  
  # Filter to 2024+ batches
  python subtransfer_chain_stitching.py --csv-dir scripts/migration/data/extract/ --min-year 2024 --link-by-project
        """,
    )
    parser.add_argument(
        "--csv-dir",
        type=str,
        default="scripts/migration/data/extract/",
        help="Directory containing extracted CSV files",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="scripts/migration/output/chain_stitching/",
        help="Output directory for results",
    )
    parser.add_argument(
        "--min-year",
        type=int,
        default=2020,
        help="Minimum population start year to include (default: 2020)",
    )
    parser.add_argument(
        "--link-by-project",
        action="store_true",
        help="Link FW and Sea chains via shared project tuples for full lifecycle batches",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Analyze without writing output files",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    
    csv_dir = PROJECT_ROOT / args.csv_dir
    output_dir = PROJECT_ROOT / args.output_dir
    
    if not csv_dir.exists():
        print(f"Error: CSV directory not found: {csv_dir}")
        return 1
    
    stitcher = ChainStitcher(csv_dir, min_year=args.min_year)
    
    try:
        stitcher.run(output_dir, dry_run=args.dry_run, link_by_project=args.link_by_project)
    except FileNotFoundError as e:
        print(f"Error: {e}")
        return 1
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    print("\nDone!")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
