"""TicketLeap platform scraper.

Two-step (listing → detail) scraper for venues using events.ticketleap.com.
The listing page embeds event IDs in a window.dataLayer.push JSON payload;
each detail page carries a standard schema.org JSON-LD Event block.
"""
