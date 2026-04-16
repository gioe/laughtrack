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

    def clear_unmatched_shows(self, company: ProductionCompany, venue_club_id: int) -> int:
        """Clear production_company_id for shows that no longer match keywords.

        After a production company scrape with keyword filtering, existing DB rows
        may still have the old production_company_id because the upsert uses
        COALESCE (preserving non-NULL values). This method cleans up shows that
        no longer match the company's keyword filter.

        Returns:
            Number of shows cleared.
        """
        if not company.show_name_keywords:
            return 0

        rows = self.execute_with_cursor(
            ProductionCompanyQueries.GET_FUTURE_SHOWS_FOR_COMPANY_VENUE,
            params=(venue_club_id, company.id),
            return_results=True,
        )
        if not rows:
            return 0

        ids_to_clear = [
            row["id"] for row in rows
            if not company.matches_show_name(row["name"])
        ]
        if not ids_to_clear:
            return 0

        self.execute_with_cursor(
            ProductionCompanyQueries.CLEAR_PRODUCTION_COMPANY_ID,
            params=(ids_to_clear,),
        )
        Logger.info(
            f"Production company '{company.name}': cleared production_company_id "
            f"on {len(ids_to_clear)} non-matching show(s) at club_id={venue_club_id}"
        )
        return len(ids_to_clear)
