"""Dedicated Playhouse Square (Cleveland) comedy scraper package.

Playhouse Square is a Tessitura OPERATOR but is NOT on the WordPress
tessi_production REST integration the generic ``tessitura`` scraper targets, so
it cannot be onboarded via that scraper. Its events come from a custom
carbonhouse "showtime" CMS load-more AJAX feed; comedy is isolated from the
multi-genre feed by a known-comedian heuristic. See scraper.py / comedy_filter.py.
"""
