"""FishTalk infrastructure extractors."""

from __future__ import annotations

from typing import List

from scripts.migration.extractors.base import BaseExtractor


class InfrastructureExtractor(BaseExtractor):
    def fetch_geographies(self) -> List[dict]:
        query = (
            "SELECT DISTINCT COALESCE(CONVERT(nvarchar(100), NationID), 'Unknown') AS NationID "
            "FROM Locations"
        )
        return self._run_sqlcmd(query, ['NationID'])

    def fetch_locations(self) -> List[dict]:
        query = (
            "SELECT LocationID, Name, NationID, Latitude, Longitude "
            "FROM Locations ORDER BY Name"
        )
        return self._run_sqlcmd(
            query,
            ['LocationID', 'Name', 'NationID', 'Latitude', 'Longitude'],
        )

    def fetch_sites(self) -> List[dict]:
        query = (
            "SELECT ou.OrgUnitID, ou.Name, ot.Name AS OrgUnitTypeName, ou.LocationID, "
            "l.Latitude, l.Longitude, l.NationID "
            "FROM dbo.OrganisationUnit ou "
            "LEFT JOIN dbo.OrganisationUnitTypes ot ON ot.OrgUnitTypeID = ou.OrgUnitTypeID "
            "LEFT JOIN dbo.Locations l ON l.LocationID = ou.LocationID "
            "WHERE ou.Active = 1"
        )
        return self._run_sqlcmd(
            query,
            [
                'OrgUnitID',
                'Name',
                'OrgUnitTypeName',
                'LocationID',
                'Latitude',
                'Longitude',
                'NationID',
            ],
        )

    def fetch_containers(self) -> List[dict]:
        query = (
            "SELECT c.ContainerID, c.ContainerName, c.OfficialID, c.OrgUnitID, c.ContainerType, "
            "CONVERT(varchar(32), cp.OverriddenVolumeM3) AS OverriddenVolumeM3, "
            "ou.Name AS OrgUnitName, "
            "eg.Site, eg.SiteGroup, eg.Company, eg.ProdStage, eg.ContainerGroup, "
            "eg.ContainerGroupID, eg.StandName, eg.StandID "
            "FROM dbo.Containers c "
            "OUTER APPLY ("
            "  SELECT TOP 1 h.PhysicsID "
            "  FROM dbo.ContainerPhysicsHistory h "
            "  WHERE h.ContainerID = c.ContainerID "
            "  ORDER BY "
            "    CASE WHEN h.EndTime IS NULL THEN 0 ELSE 1 END, "
            "    h.EndTime DESC, "
            "    h.StartTime DESC"
            ") ph "
            "OUTER APPLY ("
            "  SELECT MAX(CASE WHEN p.ParameterID = 6 THEN p.ParameterValue END) AS OverriddenVolumeM3 "
            "  FROM dbo.ContainerPhysics p "
            "  WHERE p.PhysicsID = ph.PhysicsID"
            ") cp "
            "LEFT JOIN dbo.OrganisationUnit ou ON ou.OrgUnitID = c.OrgUnitID "
            "LEFT JOIN dbo.Ext_GroupedOrganisation_v2 eg ON eg.ContainerID = c.ContainerID"
        )
        return self._run_sqlcmd(
            query,
            [
                'ContainerID',
                'ContainerName',
                'OfficialID',
                'OrgUnitID',
                'ContainerType',
                'OverriddenVolumeM3',
                'OrgUnitName',
                'Site',
                'SiteGroup',
                'Company',
                'ProdStage',
                'ContainerGroup',
                'ContainerGroupID',
                'StandName',
                'StandID',
            ],
        )

    def fetch_container_types(self) -> List[dict]:
        query = "SELECT ContainerTypesID, DefaultText, Active, SystemDelivered FROM ContainerTypes"
        return self._run_sqlcmd(query, ['ContainerTypesID', 'DefaultText', 'Active', 'SystemDelivered'])
