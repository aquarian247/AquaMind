"""FishTalk infrastructure extractors."""

from __future__ import annotations

from typing import List

from scripts.migration.extractors.base import BaseExtractor


class InfrastructureExtractor(BaseExtractor):
    def fetch_geographies(self) -> List[dict]:
        query = "SELECT DISTINCT COALESCE(CONVERT(nvarchar(100), NationID), 'Unknown') AS NationID FROM Locations"
        return self._run_sqlcmd(query, ['NationID'])

    def fetch_locations(self) -> List[dict]:
        query = "SELECT TOP 200 LocationID, Name, NationID, Latitude, Longitude FROM Locations ORDER BY Name"
        return self._run_sqlcmd(query, ['LocationID', 'Name', 'NationID', 'Latitude', 'Longitude'])
