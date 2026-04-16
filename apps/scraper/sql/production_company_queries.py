"""SQL queries for production company operations."""


class ProductionCompanyQueries:
    """SQL queries for production company operations."""

    GET_ALL_PRODUCTION_COMPANIES = """
        SELECT * FROM production_companies
        WHERE scraping_url IS NOT NULL AND visible = true
        ORDER BY id
    """

    GET_VENUE_MAPPINGS = """
        SELECT production_company_id, club_id
        FROM production_company_venues
        ORDER BY production_company_id, club_id
    """
