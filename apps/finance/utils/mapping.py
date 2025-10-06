"""Helpers for resolving finance dimension mappings."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional, Tuple

from apps.finance.models import DimCompany, DimSite
from apps.users.models import Subsidiary


class FinanceMappingError(Exception):
    """Raised when finance dimension mappings cannot be resolved."""


@dataclass(frozen=True)
class _CompanyKey:
    geography_id: int
    subsidiary: str


class FinanceDimensionResolver:
    """Caches finance dimension lookups for projection routines."""

    def __init__(self, company_map: Dict[_CompanyKey, DimCompany], site_map: Dict[str, Dict[int, DimSite]]):
        self._company_map = company_map
        self._site_map = site_map

    @classmethod
    def build(cls) -> "FinanceDimensionResolver":
        company_map: Dict[_CompanyKey, DimCompany] = {
            _CompanyKey(company.geography_id, company.subsidiary): company
            for company in DimCompany.objects.select_related("geography")
        }

        site_map: Dict[str, Dict[int, DimSite]] = {
            DimSite.SourceModel.STATION: {},
            DimSite.SourceModel.AREA: {},
        }
        for site in DimSite.objects.select_related("company"):
            site_map.setdefault(site.source_model, {})[site.source_pk] = site

        return cls(company_map=company_map, site_map=site_map)

    def resolve_source(self, assignment) -> Tuple[DimCompany, DimSite]:
        container = assignment.container
        if container.hall_id:
            station = container.hall.freshwater_station
            company = self._get_company(station.geography_id, Subsidiary.FRESHWATER)
            site = self._get_site(DimSite.SourceModel.STATION, station.pk)
            return company, site

        if container.area_id:
            area = container.area
            company = self._get_company(area.geography_id, Subsidiary.FARMING)
            site = self._get_site(DimSite.SourceModel.AREA, area.pk)
            return company, site

        raise FinanceMappingError("Container must be linked to a hall or area")

    def resolve_destination(self, geography_id: Optional[int], subsidiary: Optional[str]) -> Optional[DimCompany]:
        if not geography_id or not subsidiary:
            return None

        return self._company_map.get(_CompanyKey(geography_id, subsidiary))

    def _get_company(self, geography_id: Optional[int], subsidiary: Optional[str]) -> DimCompany:
        if not geography_id or not subsidiary:
            raise FinanceMappingError("Both geography and subsidiary are required to resolve company")

        key = _CompanyKey(geography_id, subsidiary)
        company = self._company_map.get(key)
        if not company:
            raise FinanceMappingError(f"Missing DimCompany for geography={geography_id}, subsidiary={subsidiary}")
        return company

    def _get_site(self, source_model: str, source_pk: int) -> DimSite:
        site = self._site_map.get(source_model, {}).get(source_pk)
        if not site:
            raise FinanceMappingError(
                f"Missing DimSite for source_model={source_model}, source_pk={source_pk}"
            )
        return site
