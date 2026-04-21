"""SQL queries for ticket operations."""


class TicketQueries:
    """SQL queries for ticket operations."""
    
    GET_TICKETS_FOR_SHOWS = """
        SELECT 
            show_id, price, purchase_url, sold_out, type
        FROM tickets
        WHERE show_id = ANY(%s)
        ORDER BY show_id, price;
    """
    
    BATCH_ADD_TICKETS = '''
        INSERT INTO tickets (
            show_id, purchase_url, price, sold_out, type
        ) 
        VALUES %s 
        ON CONFLICT (show_id, type) 
        DO UPDATE SET
            purchase_url = EXCLUDED.purchase_url,
            price = EXCLUDED.price,
            sold_out = EXCLUDED.sold_out
        RETURNING 
            id, show_id, purchase_url, price, sold_out, type
    '''

    DELETE_INVALID_SCHEMA_ORG_TICKETS_FOR_SHOWS = """
        DELETE FROM tickets
        WHERE show_id = ANY(%s)
          AND (
              type LIKE 'http://schema.org/%%'
              OR type LIKE 'https://schema.org/%%'
          )
    """
    
    BATCH_UPDATE_TICKET_AVAILABILITY = '''
        UPDATE tickets
        SET sold_out = v.sold_out
        FROM (VALUES %s) AS v(ticket_id, sold_out)
        WHERE tickets.id = v.ticket_id::int
    '''
