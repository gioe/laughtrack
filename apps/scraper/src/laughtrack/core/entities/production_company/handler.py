"""Production company database handler."""

from collections import defaultdict
from typing import Dict, List

from sql.production_company_queries import ProductionCompanyQueries

from laughtrack.core.data.base_handler import BaseDatabaseHandler
from laughtrack.foundation.infrastructure.logger.logger import Logger

from .model import ProductionCompany


class ProductionCompanyHandler(BaseDatabaseHandler[ProductionCompany]):
    """Handler for production company database operations."""

    def get_entity_name(self) -> str:
        return "production_company"

    def get_entity_class(self) -> type[ProductionCompany]:
        return ProductionCompany

    def get_all_production_companies(self) -> List[ProductionCompany]:
        """Fetch all visible production companies with a scraping URL.

        Also loads the venue mappings from production_company_venues and
        populates each company's venue_club_ids list.

        Returns:
            List of ProductionCompany entities with venue_club_ids populated.
        """
        try:
            rows = self.execute_with_cursor(
                ProductionCompanyQueries.GET_ALL_PRODUCTION_COMPANIES,
                return_results=True,
            )
            if not rows:
                Logger.info("No production companies found with scraping URLs")
                return []

            companies = [ProductionCompany.from_db_row(row) for row in rows]

            # Load venue mappings and attach to each company
            venue_rows = self.execute_with_cursor(
                ProductionCompanyQueries.GET_VENUE_MAPPINGS,
                return_results=True,
            )
            if venue_rows:
                mapping: Dict[int, List[int]] = defaultdict(list)
                for vr in venue_rows:
                    mapping[vr["production_company_id"]].append(vr["club_id"])
                for company in companies:
                    company.venue_club_ids = mapping.get(company.id, [])

            Logger.info(f"Retrieved {len(companies)} production companies from database")
            return companies

        except Exception as e:
            Logger.error(f"Error fetching production companies: {e}")
            raise
