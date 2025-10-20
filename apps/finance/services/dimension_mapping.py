"""
Dimension mapping service for finance integration.

Maps operational entities (containers, stations, areas) to finance dimensions
(DimCompany, DimSite) for intercompany transaction processing.
"""

from typing import Optional

from apps.finance.models import DimCompany, DimSite
from apps.infrastructure.models import Container


class DimensionMappingService:
    """
    Service for mapping operational entities to finance dimensions.
    
    Handles the mapping:
    - Container → DimSite → DimCompany
    - Supports both freshwater (hall-based) and farming (area-based) containers
    """

    @staticmethod
    def get_company_for_container(container: Container) -> Optional[DimCompany]:
        """
        Get the DimCompany associated with a container.
        
        Args:
            container: Container instance (can be hall-based or area-based)
        
        Returns:
            DimCompany instance or None if mapping not found
        
        Logic:
            - Freshwater containers (hall): Maps via hall → station → DimSite
            - Farming containers (area): Maps via area → DimSite
        """
        site = DimensionMappingService.get_site_for_container(container)
        if site:
            return site.company
        return None

    @staticmethod
    def get_site_for_container(container: Container) -> Optional[DimSite]:
        """
        Get the DimSite associated with a container.
        
        Args:
            container: Container instance
        
        Returns:
            DimSite instance or None if mapping not found
        """
        # Freshwater container (hall-based)
        if container.hall:
            station = container.hall.freshwater_station
            if station:
                return DimSite.objects.filter(
                    source_model=DimSite.SourceModel.STATION,
                    source_pk=station.id,
                ).first()
        
        # Farming container (area-based)
        elif container.area:
            return DimSite.objects.filter(
                source_model=DimSite.SourceModel.AREA,
                source_pk=container.area.id,
            ).first()
        
        return None

    @staticmethod
    def get_companies_for_workflow_actions(actions) -> tuple[
        Optional[DimCompany],
        Optional[DimCompany]
    ]:
        """
        Get source and destination companies from workflow actions.
        
        Args:
            actions: QuerySet of TransferAction instances
        
        Returns:
            Tuple of (source_company, dest_company)
            Either or both can be None if mapping fails
        
        Logic:
            - Gets companies from first action (assumes all actions have
              same source/dest subsidiaries)
            - Returns None if no actions or mapping fails
        """
        if not actions.exists():
            return None, None
        
        # Get first action as representative
        first_action = actions.first()
        
        # Get source company
        source_company = None
        if first_action.source_assignment:
            source_container = first_action.source_assignment.container
            source_company = DimensionMappingService.get_company_for_container(
                source_container
            )
        
        # Get destination company
        dest_company = None
        if first_action.dest_assignment:
            dest_container = first_action.dest_assignment.container
            dest_company = DimensionMappingService.get_company_for_container(
                dest_container
            )
        
        return source_company, dest_company

    @staticmethod
    def validate_intercompany_transfer(
        source_company: Optional[DimCompany],
        dest_company: Optional[DimCompany],
    ) -> bool:
        """
        Validate that a transfer is intercompany.
        
        Args:
            source_company: Source DimCompany
            dest_company: Destination DimCompany
        
        Returns:
            True if transfer crosses company boundaries, False otherwise
        
        Validation:
            - Both companies must exist
            - Companies must be different
            - Typically Freshwater → Farming or Farming → Harvest
        """
        if not source_company or not dest_company:
            return False
        
        if source_company.company_id == dest_company.company_id:
            return False
        
        return True

