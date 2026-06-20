"""Ludus (ludus.com, formerly Tixato) box-office platform scraper.

Two-step (embed -> detail) scraper for venues ticketing on a Ludus subdomain.
Filters the embed's show_item cards to a configurable comedy category id, layers
the shared comedy keyword/comedian filter to drop venue mis-tags, then fetches
each show's detail page for its upcoming showtimes. Generic across Ludus venues;
first onboarded venue: Park Theatre (Holland).
"""
