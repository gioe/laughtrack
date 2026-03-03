"""SQL queries for email operations."""


class EmailQueries:
    """SQL queries for email operations."""
    
    GET_USER_EMAIL_MAP = """
        WITH user_favorite_shows AS (
                SELECT 
                    u.email,
                    c.uuid,
                    c.name as comedian_name,
                    array_agg(
                        jsonb_build_object(
                            'id', s.id,
                            'name', s.name,
                            'date', s.date,
                            'show_page_url', s.show_page_url,
                            'club_name', cl.name,
                            'club_timezone', cl.timezone
                        )
                    ) as shows
                FROM users u
                JOIN user_profiles up ON up.user_id = u.id
                JOIN favorite_comedians fc ON fc.profile_id = up.id
                JOIN comedians c ON fc.comedian_id = c.uuid
                JOIN lineup_items li ON li.comedian_id = c.uuid
                JOIN shows s ON li.show_id = s.id
                JOIN clubs cl ON s.club_id = cl.id
                WHERE s.id = ANY(%s)
                AND up.email_show_notifications = true
                GROUP BY u.email, c.name, c.uuid
            )
            SELECT 
                email,
                jsonb_object_agg(
                    comedian_name,
                    shows
                ) as comedian_shows
            FROM user_favorite_shows
                GROUP BY email
        """
