"""Tempo Tickets (tempotickets.com) platform scraper.

Two-step (listing -> event) scraper for venues selling through Tempo Tickets.
The listing.php?c=<id> page lists recurring events; each /event/{code} page
exposes its upcoming individual dates in a <select name='EventDateID'>. Generic
and reusable across any Tempo venue, keyed by a `category_id` source-metadata
value. First onboarded venue: ComedySportz Milwaukee (category_id=80).
"""
