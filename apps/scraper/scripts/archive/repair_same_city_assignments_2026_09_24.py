#!/usr/bin/env python3
"""Reviewed same-city venue assignment repair (TASK-4049).

Background
----------
Source evidence identifies 58 duplicate upcoming performances and three duplicate
Ticketmaster venue shells. Historical shows, run logs, and their click attribution
remain on retained hidden clubs. Attic/Walrus and Yaamava remain distinct venues.

What this does
--------------
Merges only reviewed future show IDs, preserving saved shows, notification IDs,
and click attribution. Canonical ticket types and lineup roles win collisions;
old alternate purchase URLs/roles and stale venue features remain recoverable in
the private backup. Moves duplicate source IDs to canonical venues as disabled
fallbacks, adds database-normalized aliases, hides shells, and repoints home clubs.
Default dry-run rolls back. Restore requires exact post-state and schema equality.

Usage
-----
From apps/scraper with PYTHONPATH=src:.:
  .venv/bin/python scripts/archive/repair_same_city_assignments_2026_09_24.py --dry-run
  ... --apply --backup /private/tmp/task4049-recovery.json
  ... --restore /private/tmp/task4049-recovery.json
Recovery contains user data: never commit it. No automatic deployment hook.
"""

from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
from datetime import datetime
from psycopg2 import sql

FOLDS = {5115: 5114, 5225: 5364, 10023: 12796}
SHOW_MAP = {
    1014021: 5740237,
    1014022: 5740238,
    1014023: 5740239,
    1014029: 5740233,
    1014030: 5740234,
    1014076: 5740243,
    1014090: 5740232,
    1014106: 5740240,
    1220285: 5740245,
    1220286: 5740247,
    1482081: 5740252,
    1482082: 5740253,
    1482083: 5740260,
    1482084: 5740261,
    1482085: 5740262,
    2223659: 5740246,
    2223662: 5740250,
    2443702: 5740236,
    2832505: 6977157,
    2832506: 6977158,
    2841464: 2876861,
    2876589: 2841694,
    2987249: 5740264,
    2987250: 5740265,
    2987251: 5740266,
    2987252: 5740267,
    3135870: 3708622,
    3201439: 5740257,
    3201440: 5740248,
    3541588: 5740255,
    3541589: 5740256,
    3541590: 5740268,
    3595393: 5740254,
    3740919: 5740244,
    3879575: 5740242,
    3967417: 5740263,
    3967449: 5740251,
    4190809: 5740235,
    4501841: 5740269,
    4501842: 5740270,
    4501843: 5740272,
    4501844: 5740271,
    4501845: 5740259,
    4501846: 5740273,
    5473441: 5740258,
    5525127: 5740249,
    6904546: 6017989,
    6904547: 6017990,
    6904549: 6067069,
    7075650: 7082340,
    7124455: 7131652,
    7124456: 7131653,
    7220970: 7224899,
    7268132: 7224900,
    7268133: 7272092,
    7268134: 7272093,
    7316068: 7322230,
    7351170: 7361463,
}
SHOW_MOVES = {}  # Reviewed noncolliding future IDs -> canonical club ID.
EQUIVALENT_EVENT_URLS = {
    (1014021, 5740237),
    (1014022, 5740238),
    (1014023, 5740239),
    (1014029, 5740233),
    (1014030, 5740234),
    (1014076, 5740243),
    (1014090, 5740232),
    (1482081, 5740252),
    (1482082, 5740253),
    (1482083, 5740260),
    (1482084, 5740261),
    (1482085, 5740262),
    (2987249, 5740264),
    (2987250, 5740265),
    (2987251, 5740266),
    (2987252, 5740267),
    (3135870, 3708622),
    (3541588, 5740255),
    (3541589, 5740256),
    (3967449, 5740251),
    (4501841, 5740269),
    (4501842, 5740270),
    (4501843, 5740272),
    (4501844, 5740271),
    (5525127, 5740249),
}  # Source-verified explicit pairs only.
EXPECTED_SHOWS = {
    1014021: {
        "club_id": 575,
        "date": "2026-10-02T23:00:00+00:00",
        "name": "Zainab Johnson LIVE @ The Attic Comedy Club!",
        "room": "",
        "show_page_url": "https://www.eventbrite.com/e/zainab-johnson-live-the-attic-comedy-club-tickets-1968283994412",
    },
    1014022: {
        "club_id": 575,
        "date": "2026-10-03T01:00:00+00:00",
        "name": "Zainab Johnson LIVE @ The Attic Comedy Club! Show #2",
        "room": "",
        "show_page_url": "https://www.eventbrite.com/e/zainab-johnson-live-the-attic-comedy-club-show-2-tickets-1968287117754",
    },
    1014023: {
        "club_id": 575,
        "date": "2026-10-03T23:00:00+00:00",
        "name": "Zainab Johnson LIVE @ The Attic Comedy Club! Show #3",
        "room": "",
        "show_page_url": "https://www.eventbrite.com/e/zainab-johnson-live-the-attic-comedy-club-show-3-tickets-1968288663377",
    },
    1014029: {
        "club_id": 575,
        "date": "2026-09-26T23:00:00+00:00",
        "name": "Kevin Farley LIVE @ The Attic Comedy Club",
        "room": "",
        "show_page_url": "https://www.eventbrite.com/e/kevin-farley-live-the-attic-comedy-club-tickets-1977497911486",
    },
    1014030: {
        "club_id": 575,
        "date": "2026-09-27T01:00:00+00:00",
        "name": "Kevin Farley LIVE @ The Attic Comedy Club",
        "room": "",
        "show_page_url": "https://www.eventbrite.com/e/kevin-farley-live-the-attic-comedy-club-tickets-1977498507268",
    },
    1014076: {
        "club_id": 575,
        "date": "2026-10-16T23:00:00+00:00",
        "name": "Jamie Wolf LIVE Comedy Show @ The Attic Comedy Club",
        "room": "",
        "show_page_url": "https://www.eventbrite.com/e/jamie-wolf-live-comedy-show-the-attic-comedy-club-tickets-1983617902544",
    },
    1014090: {
        "club_id": 575,
        "date": "2026-09-26T01:00:00+00:00",
        "name": "Spanish Comedy Night @ The Attic Comedy Club with Headliner Fabrizio Copano",
        "room": "",
        "show_page_url": "https://www.eventbrite.com/e/spanish-comedy-night-the-attic-comedy-club-with-headliner-fabrizio-copano-tickets-1984648931379",
    },
    1014106: {
        "club_id": 575,
        "date": "2026-10-10T23:00:00+00:00",
        "name": "Aaron Berg at The Attic Comedy Club, Columbus, Ohio",
        "room": "",
        "show_page_url": "https://www.eventbrite.com/e/aaron-berg-at-the-attic-comedy-club-columbus-ohio-tickets-1986036142565",
    },
    1220285: {
        "club_id": 575,
        "date": "2026-10-23T23:00:00+00:00",
        "name": "Jim Florentine Live Standup Comedy Show @ The Attic Comedy Club Columbus",
        "room": "",
        "show_page_url": "https://www.eventbrite.com/e/jim-florentine-live-standup-comedy-show-the-attic-comedy-club-columbus-tickets-1987946101303",
    },
    1220286: {
        "club_id": 575,
        "date": "2026-10-24T23:00:00+00:00",
        "name": "Jim Florentine Live Standup Comedy Show @ The Attic Comedy Club Columbus",
        "room": "",
        "show_page_url": "https://www.eventbrite.com/e/jim-florentine-live-standup-comedy-show-the-attic-comedy-club-columbus-tickets-1987946460377",
    },
    1482081: {
        "club_id": 575,
        "date": "2026-11-08T00:00:00+00:00",
        "name": "Ed Bassmaster Live Standup Comedy Show @ The Attic Comedy Club Columbus",
        "room": "",
        "show_page_url": "https://www.eventbrite.com/e/ed-bassmaster-live-standup-comedy-show-the-attic-comedy-club-columbus-tickets-1988370728374",
    },
    1482082: {
        "club_id": 575,
        "date": "2026-11-08T02:30:00+00:00",
        "name": "Ed Bassmaster Live Standup Comedy Show @ The Attic Comedy Club (Late Show)",
        "room": "",
        "show_page_url": "https://www.eventbrite.com/e/ed-bassmaster-live-standup-comedy-show-the-attic-comedy-club-late-show-tickets-1988370965082",
    },
    1482083: {
        "club_id": 575,
        "date": "2026-11-28T00:00:00+00:00",
        "name": "Chris Kattan Live Standup Comedy Show @ The Attic Comedy Club Columbus",
        "room": "",
        "show_page_url": "https://www.eventbrite.com/e/chris-kattan-live-standup-comedy-show-the-attic-comedy-club-columbus-tickets-1988449141911",
    },
    1482084: {
        "club_id": 575,
        "date": "2026-11-28T02:00:00+00:00",
        "name": "Chris Kattan Live Standup Comedy Show @ The Attic Comedy Club Columbus",
        "room": "",
        "show_page_url": "https://www.eventbrite.com/e/chris-kattan-live-standup-comedy-show-the-attic-comedy-club-columbus-tickets-1988449216133",
    },
    1482085: {
        "club_id": 575,
        "date": "2026-11-29T00:00:00+00:00",
        "name": "Chris Kattan Live Standup Comedy Show @ The Attic Comedy Club Columbus",
        "room": "",
        "show_page_url": "https://www.eventbrite.com/e/chris-kattan-live-standup-comedy-show-the-attic-comedy-club-columbus-tickets-1988449252241",
    },
    2223659: {
        "club_id": 575,
        "date": "2026-10-24T01:00:00+00:00",
        "name": "On The Offensive @ The Attic Comedy Club Columbus",
        "room": "",
        "show_page_url": "https://www.eventbrite.com/e/on-the-offensive-the-attic-comedy-club-columbus-tickets-1989622831448",
    },
    2223662: {
        "club_id": 575,
        "date": "2026-10-30T00:00:00+00:00",
        "name": "Jerrel's Wheel of Comedy at The Attic Comedy Club, Columbus, Ohio",
        "room": "",
        "show_page_url": "https://www.eventbrite.com/e/jerrels-wheel-of-comedy-at-the-attic-comedy-club-columbus-ohio-tickets-1989623073171",
    },
    2443702: {
        "club_id": 575,
        "date": "2026-10-02T00:00:00+00:00",
        "name": "Raj Suresh @ The Attic Comedy Club Columbus",
        "room": "",
        "show_page_url": "https://www.eventbrite.com/e/raj-suresh-the-attic-comedy-club-columbus-tickets-1991243122783",
    },
    2832505: {
        "club_id": 4691,
        "date": "2026-10-04T03:00:00+00:00",
        "name": "Ron White",
        "room": "",
        "show_page_url": "https://www.ticketmaster.com/event/Z7r9jZ1A70taU",
    },
    2832506: {
        "club_id": 4691,
        "date": "2026-11-20T04:00:00+00:00",
        "name": "Nikki Glaser",
        "room": "",
        "show_page_url": "https://www.ticketmaster.com/event/Z7r9jZ1A7Opvx",
    },
    2841464: {
        "club_id": 5225,
        "date": "2026-10-03T00:30:00+00:00",
        "name": "Terry Fator",
        "room": "",
        "show_page_url": "https://www.ticketmaster.com/event/Z7r9jZ1A70grK",
    },
    2841694: {
        "club_id": 5364,
        "date": "2026-11-06T01:30:00+00:00",
        "name": "Anthony Jeselnik: Wrath of Man",
        "room": "",
        "show_page_url": "https://us.atgtickets.com/events/anthony-jeselnik/mahalia-jackson-theater",
    },
    2876589: {
        "club_id": 5225,
        "date": "2026-11-06T01:30:00+00:00",
        "name": "Anthony Jeselnik: Wrath of Man",
        "room": "",
        "show_page_url": "https://us.atgtickets.com/events/anthony-jeselnik/mahalia-jackson-theater",
    },
    2876861: {
        "club_id": 5364,
        "date": "2026-10-03T00:30:00+00:00",
        "name": "Terry Fator",
        "room": "",
        "show_page_url": "https://www.ticketmaster.com/event/Z7r9jZ1A70grK",
    },
    2987249: {
        "club_id": 575,
        "date": "2026-12-12T00:00:00+00:00",
        "name": "David Koechner LIVE Comedy Show @ The Attic Comedy Club!",
        "room": "",
        "show_page_url": "https://www.eventbrite.com/e/david-koechner-live-comedy-show-the-attic-comedy-club-tickets-1992024956268",
    },
    2987250: {
        "club_id": 575,
        "date": "2026-12-12T02:30:00+00:00",
        "name": "David Koechner LIVE Comedy Show @ The Attic Comedy Club!",
        "room": "",
        "show_page_url": "https://www.eventbrite.com/e/david-koechner-live-comedy-show-the-attic-comedy-club-tickets-1992025113739",
    },
    2987251: {
        "club_id": 575,
        "date": "2026-12-13T00:00:00+00:00",
        "name": "David Koechner LIVE Comedy Show @ The Attic Comedy Club!",
        "room": "",
        "show_page_url": "https://www.eventbrite.com/e/david-koechner-live-comedy-show-the-attic-comedy-club-tickets-1992025512933",
    },
    2987252: {
        "club_id": 575,
        "date": "2026-12-13T02:30:00+00:00",
        "name": "David Koechner LIVE Comedy Show @ The Attic Comedy Club!",
        "room": "",
        "show_page_url": "https://www.eventbrite.com/e/david-koechner-live-comedy-show-the-attic-comedy-club-tickets-1992025741617",
    },
    3135870: {
        "club_id": 10023,
        "date": "2026-12-11T00:30:00+00:00",
        "name": "John Mulaney: Mister Whatever",
        "room": "",
        "show_page_url": "https://www.vanwezel.org/events/detail/john-mulaney-mister-whatever",
    },
    3201439: {
        "club_id": 575,
        "date": "2026-11-16T01:00:00+00:00",
        "name": "Britton Emert LIVE @ The Attic Comedy Club",
        "room": "",
        "show_page_url": "https://www.eventbrite.com/e/britton-emert-live-the-attic-comedy-club-tickets-1992389014175",
    },
    3201440: {
        "club_id": 575,
        "date": "2026-10-25T01:00:00+00:00",
        "name": "Gauri B LIVE @ The Attic Comedy Club",
        "room": "",
        "show_page_url": "https://www.eventbrite.com/e/gauri-b-live-the-attic-comedy-club-tickets-1992389456498",
    },
    3541588: {
        "club_id": 575,
        "date": "2026-11-14T00:00:00+00:00",
        "name": "Todd Barry Live Standup Comedy Show @ The Attic Comedy Club Columbus",
        "room": "",
        "show_page_url": "https://www.eventbrite.com/e/todd-barry-live-standup-comedy-show-the-attic-comedy-club-columbus-tickets-1992833194731",
    },
    3541589: {
        "club_id": 575,
        "date": "2026-11-14T02:00:00+00:00",
        "name": "Todd Barry Live Standup Comedy Show @ The Attic Comedy Club Columbus",
        "room": "",
        "show_page_url": "https://www.eventbrite.com/e/todd-barry-live-standup-comedy-show-the-attic-comedy-club-columbus-tickets-1992833686201",
    },
    3541590: {
        "club_id": 575,
        "date": "2026-12-20T00:00:00+00:00",
        "name": "Fine, Actually- A Night of Comedy with Holly Hudson",
        "room": "",
        "show_page_url": "https://www.eventbrite.com/e/fine-actually-a-night-of-comedy-with-holly-hudson-tickets-1992843402262",
    },
    3595393: {
        "club_id": 575,
        "date": "2026-11-13T01:00:00+00:00",
        "name": "Saul Trujillo Live Standup Comedy Show @ The Attic Comedy Club Columbus",
        "room": "",
        "show_page_url": "https://www.eventbrite.com/e/saul-trujillo-live-standup-comedy-show-the-attic-comedy-club-columbus-tickets-1993135980371",
    },
    3708622: {
        "club_id": 12796,
        "date": "2026-12-11T00:30:00+00:00",
        "name": "John Mulaney",
        "room": "",
        "show_page_url": "https://www.ticketmaster.com/event/Z7r9jZ1A7P4vV",
    },
    3740919: {
        "club_id": 575,
        "date": "2026-10-17T01:00:00+00:00",
        "name": "Marcus Monroe LIVE @ The Attic Comedy Club",
        "room": "",
        "show_page_url": "https://www.eventbrite.com/e/marcus-monroe-live-the-attic-comedy-club-tickets-1988955016997",
    },
    3879575: {
        "club_id": 575,
        "date": "2026-10-14T23:00:00+00:00",
        "name": "Wednesday Night Comedy Open Mic at The Attic Comedy Club, Columbus",
        "room": "",
        "show_page_url": "https://www.eventbrite.com/e/wednesday-night-comedy-open-mic-at-the-attic-comedy-club-columbus-tickets-1993477139788",
    },
    3967417: {
        "club_id": 575,
        "date": "2026-12-04T01:00:00+00:00",
        "name": "Vincent Royale LIVE Comedy Show @ The Attic Comedy Club",
        "room": "",
        "show_page_url": "https://www.eventbrite.com/e/vincent-royale-live-comedy-show-the-attic-comedy-club-tickets-1992947752376",
    },
    3967449: {
        "club_id": 575,
        "date": "2026-11-07T00:00:00+00:00",
        "name": "Willie Macc LIVE Comedy Show @ The Attic Comedy Club!",
        "room": "",
        "show_page_url": "https://www.eventbrite.com/e/willie-macc-live-comedy-show-the-attic-comedy-club-tickets-1993708816740",
    },
    4190809: {
        "club_id": 575,
        "date": "2026-09-27T23:00:00+00:00",
        "name": "Prime Time Comedy Showcase @ The Attic Comedy Club",
        "room": "",
        "show_page_url": "https://www.eventbrite.com/e/prime-time-comedy-showcase-the-attic-comedy-club-tickets-1992946790499",
    },
    4501841: {
        "club_id": 575,
        "date": "2027-01-16T00:00:00+00:00",
        "name": "Michael Longfellow LIVE Comedy Show @ The Attic Comedy Club!",
        "room": "",
        "show_page_url": "https://www.eventbrite.com/e/michael-longfellow-live-comedy-show-the-attic-comedy-club-tickets-1994865248659",
    },
    4501842: {
        "club_id": 575,
        "date": "2027-01-16T02:00:00+00:00",
        "name": "Michael Longfellow LIVE Comedy Show @ The Attic Comedy Club! Show #2",
        "room": "",
        "show_page_url": "https://www.eventbrite.com/e/michael-longfellow-live-comedy-show-the-attic-comedy-club-show-2-tickets-1994869485331",
    },
    4501843: {
        "club_id": 575,
        "date": "2027-01-17T02:00:00+00:00",
        "name": "Michael Longfellow LIVE Comedy Show @ The Attic Comedy Club! Show #4",
        "room": "",
        "show_page_url": "https://www.eventbrite.com/e/michael-longfellow-live-comedy-show-the-attic-comedy-club-show-4-tickets-1994870476295",
    },
    4501844: {
        "club_id": 575,
        "date": "2027-01-17T00:00:00+00:00",
        "name": "Michael Longfellow LIVE Comedy Show @ The Attic Comedy Club! Show #3",
        "room": "",
        "show_page_url": "https://www.eventbrite.com/e/michael-longfellow-live-comedy-show-the-attic-comedy-club-show-3-tickets-1994870569574",
    },
    4501845: {
        "club_id": 575,
        "date": "2026-11-22T23:00:00+00:00",
        "name": "Lou Pharis LIVE Comedy Show @ The Attic Comedy Club!",
        "room": "",
        "show_page_url": "https://www.eventbrite.com/e/lou-pharis-live-comedy-show-the-attic-comedy-club-tickets-1994870785219",
    },
    4501846: {
        "club_id": 575,
        "date": "2027-01-24T00:00:00+00:00",
        "name": "Kristin Chirico Live Standup Comedy Show @ The Attic Comedy Club Columbus",
        "room": "",
        "show_page_url": "https://www.eventbrite.com/e/kristin-chirico-live-standup-comedy-show-the-attic-comedy-club-columbus-tickets-1994871891528",
    },
    5473441: {
        "club_id": 575,
        "date": "2026-11-21T02:00:00+00:00",
        "name": "Amy Brown & Holly Ballantine Live Comedy Show @ The Attic Comedy Club!",
        "room": "",
        "show_page_url": "https://www.eventbrite.com/e/amy-brown-holly-ballantine-live-comedy-show-the-attic-comedy-club-tickets-1997878900573",
    },
    5525127: {
        "club_id": 575,
        "date": "2026-10-25T22:00:00+00:00",
        "name": "Steven Castillo Live Comedy Show @ The Attic Comedy Club!",
        "room": "",
        "show_page_url": "https://www.eventbrite.com/e/steven-castillo-live-comedy-show-the-attic-comedy-club-tickets-1997899246428",
    },
    5740232: {
        "club_id": 29044,
        "date": "2026-09-26T01:00:00+00:00",
        "name": "Fabrizio Copano LIVE en Español @ The Attic Comedy Club!",
        "room": "",
        "show_page_url": "https://www.eventbrite.com/e/fabrizio-copano-live-en-espanol-the-attic-comedy-club-tickets-1984648931379",
    },
    5740233: {
        "club_id": 29044,
        "date": "2026-09-26T23:00:00+00:00",
        "name": "Kevin Farley LIVE @ The Attic Comedy Club! September 26, 7 PM",
        "room": "",
        "show_page_url": "https://www.eventbrite.com/e/kevin-farley-live-the-attic-comedy-club-september-26-7-pm-tickets-1977497911486",
    },
    5740234: {
        "club_id": 29044,
        "date": "2026-09-27T01:00:00+00:00",
        "name": "Kevin Farley LIVE @ The Attic Comedy Club! September 26, 9 PM",
        "room": "",
        "show_page_url": "https://www.eventbrite.com/e/kevin-farley-live-the-attic-comedy-club-september-26-9-pm-tickets-1977498507268",
    },
    5740235: {
        "club_id": 29044,
        "date": "2026-09-27T23:00:00+00:00",
        "name": "Prime Time Comedy Showcase @ The Attic Comedy Club",
        "room": "",
        "show_page_url": "https://www.eventbrite.com/e/prime-time-comedy-showcase-the-attic-comedy-club-tickets-1992946790499",
    },
    5740236: {
        "club_id": 29044,
        "date": "2026-10-02T00:00:00+00:00",
        "name": "Raj Suresh @ The Attic Comedy Club Columbus",
        "room": "",
        "show_page_url": "https://www.eventbrite.com/e/raj-suresh-the-attic-comedy-club-columbus-tickets-1991243122783",
    },
    5740237: {
        "club_id": 29044,
        "date": "2026-10-02T23:00:00+00:00",
        "name": "Zainab Johnson LIVE @ The Attic Comedy Club! October 2, 7 PM",
        "room": "",
        "show_page_url": "https://www.eventbrite.com/e/zainab-johnson-live-the-attic-comedy-club-october-2-7-pm-tickets-1968283994412",
    },
    5740238: {
        "club_id": 29044,
        "date": "2026-10-03T01:00:00+00:00",
        "name": "Zainab Johnson LIVE @ The Attic Comedy Club! October 2, 9 PM",
        "room": "",
        "show_page_url": "https://www.eventbrite.com/e/zainab-johnson-live-the-attic-comedy-club-october-2-9-pm-tickets-1968287117754",
    },
    5740239: {
        "club_id": 29044,
        "date": "2026-10-03T23:00:00+00:00",
        "name": "Zainab Johnson LIVE @ The Attic Comedy Club! October 3, 7 PM",
        "room": "",
        "show_page_url": "https://www.eventbrite.com/e/zainab-johnson-live-the-attic-comedy-club-october-3-7-pm-tickets-1968288663377",
    },
    5740240: {
        "club_id": 29044,
        "date": "2026-10-10T23:00:00+00:00",
        "name": "Aaron Berg at The Attic Comedy Club, Columbus, Ohio",
        "room": "",
        "show_page_url": "https://www.eventbrite.com/e/aaron-berg-at-the-attic-comedy-club-columbus-ohio-tickets-1986036142565",
    },
    5740242: {
        "club_id": 29044,
        "date": "2026-10-14T23:00:00+00:00",
        "name": "Wednesday Night Comedy Open Mic at The Attic Comedy Club, Columbus",
        "room": "",
        "show_page_url": "https://www.eventbrite.com/e/wednesday-night-comedy-open-mic-at-the-attic-comedy-club-columbus-tickets-1993477139788",
    },
    5740243: {
        "club_id": 29044,
        "date": "2026-10-16T23:00:00+00:00",
        "name": "Jamie Wolf LIVE @ The Attic Comedy Club!",
        "room": "",
        "show_page_url": "https://www.eventbrite.com/e/jamie-wolf-live-the-attic-comedy-club-tickets-1983617902544",
    },
    5740244: {
        "club_id": 29044,
        "date": "2026-10-17T01:00:00+00:00",
        "name": "Marcus Monroe LIVE @ The Attic Comedy Club",
        "room": "",
        "show_page_url": "https://www.eventbrite.com/e/marcus-monroe-live-the-attic-comedy-club-tickets-1988955016997",
    },
    5740245: {
        "club_id": 29044,
        "date": "2026-10-23T23:00:00+00:00",
        "name": "Jim Florentine Live Standup Comedy Show @ The Attic Comedy Club Columbus",
        "room": "",
        "show_page_url": "https://www.eventbrite.com/e/jim-florentine-live-standup-comedy-show-the-attic-comedy-club-columbus-tickets-1987946101303",
    },
    5740246: {
        "club_id": 29044,
        "date": "2026-10-24T01:00:00+00:00",
        "name": "On The Offensive @ The Attic Comedy Club Columbus",
        "room": "",
        "show_page_url": "https://www.eventbrite.com/e/on-the-offensive-the-attic-comedy-club-columbus-tickets-1989622831448",
    },
    5740247: {
        "club_id": 29044,
        "date": "2026-10-24T23:00:00+00:00",
        "name": "Jim Florentine Live Standup Comedy Show @ The Attic Comedy Club Columbus",
        "room": "",
        "show_page_url": "https://www.eventbrite.com/e/jim-florentine-live-standup-comedy-show-the-attic-comedy-club-columbus-tickets-1987946460377",
    },
    5740248: {
        "club_id": 29044,
        "date": "2026-10-25T01:00:00+00:00",
        "name": "Gauri B LIVE @ The Attic Comedy Club",
        "room": "",
        "show_page_url": "https://www.eventbrite.com/e/gauri-b-live-the-attic-comedy-club-tickets-1992389456498",
    },
    5740249: {
        "club_id": 29044,
        "date": "2026-10-25T22:00:00+00:00",
        "name": "Steven Castillo LIVE @ The Attic Comedy Club!",
        "room": "",
        "show_page_url": "https://www.eventbrite.com/e/steven-castillo-live-the-attic-comedy-club-tickets-1997899246428",
    },
    5740250: {
        "club_id": 29044,
        "date": "2026-10-30T00:00:00+00:00",
        "name": "Jerrel's Wheel of Comedy at The Attic Comedy Club, Columbus, Ohio",
        "room": "",
        "show_page_url": "https://www.eventbrite.com/e/jerrels-wheel-of-comedy-at-the-attic-comedy-club-columbus-ohio-tickets-1989623073171",
    },
    5740251: {
        "club_id": 29044,
        "date": "2026-11-07T00:00:00+00:00",
        "name": "Willie Macc LIVE @ The Attic Comedy Club!",
        "room": "",
        "show_page_url": "https://www.eventbrite.com/e/willie-macc-live-the-attic-comedy-club-tickets-1993708816740",
    },
    5740252: {
        "club_id": 29044,
        "date": "2026-11-08T00:00:00+00:00",
        "name": "Ed Bassmaster LIVE @ The Attic Comedy Club! November 7, 7 PM",
        "room": "",
        "show_page_url": "https://www.eventbrite.com/e/ed-bassmaster-live-the-attic-comedy-club-november-7-7-pm-tickets-1988370728374",
    },
    5740253: {
        "club_id": 29044,
        "date": "2026-11-08T02:30:00+00:00",
        "name": "Ed Bassmaster LIVE @ The Attic Comedy Club! November 7, 9:30 PM",
        "room": "",
        "show_page_url": "https://www.eventbrite.com/e/ed-bassmaster-live-the-attic-comedy-club-november-7-930-pm-tickets-1988370965082",
    },
    5740254: {
        "club_id": 29044,
        "date": "2026-11-13T01:00:00+00:00",
        "name": "Saul Trujillo Live Standup Comedy Show @ The Attic Comedy Club Columbus",
        "room": "",
        "show_page_url": "https://www.eventbrite.com/e/saul-trujillo-live-standup-comedy-show-the-attic-comedy-club-columbus-tickets-1993135980371",
    },
    5740255: {
        "club_id": 29044,
        "date": "2026-11-14T00:00:00+00:00",
        "name": "Todd Barry LIVE @ The Attic Comedy Club! November 13, 7 PM",
        "room": "",
        "show_page_url": "https://www.eventbrite.com/e/todd-barry-live-the-attic-comedy-club-november-13-7-pm-tickets-1992833194731",
    },
    5740256: {
        "club_id": 29044,
        "date": "2026-11-14T02:00:00+00:00",
        "name": "Todd Barry LIVE @ The Attic Comedy Club! November 13, 9 PM",
        "room": "",
        "show_page_url": "https://www.eventbrite.com/e/todd-barry-live-the-attic-comedy-club-november-13-9-pm-tickets-1992833686201",
    },
    5740257: {
        "club_id": 29044,
        "date": "2026-11-16T01:00:00+00:00",
        "name": "Britton Emert LIVE @ The Attic Comedy Club",
        "room": "",
        "show_page_url": "https://www.eventbrite.com/e/britton-emert-live-the-attic-comedy-club-tickets-1992389014175",
    },
    5740258: {
        "club_id": 29044,
        "date": "2026-11-21T02:00:00+00:00",
        "name": "Amy Brown & Holly Ballantine Live Comedy Show @ The Attic Comedy Club!",
        "room": "",
        "show_page_url": "https://www.eventbrite.com/e/amy-brown-holly-ballantine-live-comedy-show-the-attic-comedy-club-tickets-1997878900573",
    },
    5740259: {
        "club_id": 29044,
        "date": "2026-11-22T23:00:00+00:00",
        "name": "Lou Pharis LIVE Comedy Show @ The Attic Comedy Club!",
        "room": "",
        "show_page_url": "https://www.eventbrite.com/e/lou-pharis-live-comedy-show-the-attic-comedy-club-tickets-1994870785219",
    },
    5740260: {
        "club_id": 29044,
        "date": "2026-11-28T00:00:00+00:00",
        "name": "Chris Kattan LIVE @ The Attic Comedy Club! November 27, 7 PM",
        "room": "",
        "show_page_url": "https://www.eventbrite.com/e/chris-kattan-live-the-attic-comedy-club-november-27-7-pm-tickets-1988449141911",
    },
    5740261: {
        "club_id": 29044,
        "date": "2026-11-28T02:00:00+00:00",
        "name": "Chris Kattan LIVE @ The Attic Comedy Club! November 27, 9 PM",
        "room": "",
        "show_page_url": "https://www.eventbrite.com/e/chris-kattan-live-the-attic-comedy-club-november-27-9-pm-tickets-1988449216133",
    },
    5740262: {
        "club_id": 29044,
        "date": "2026-11-29T00:00:00+00:00",
        "name": "Chris Kattan LIVE @ The Attic Comedy Club! November 28, 7 PM",
        "room": "",
        "show_page_url": "https://www.eventbrite.com/e/chris-kattan-live-the-attic-comedy-club-november-28-7-pm-tickets-1988449252241",
    },
    5740263: {
        "club_id": 29044,
        "date": "2026-12-04T01:00:00+00:00",
        "name": "Vincent Royale LIVE Comedy Show @ The Attic Comedy Club",
        "room": "",
        "show_page_url": "https://www.eventbrite.com/e/vincent-royale-live-comedy-show-the-attic-comedy-club-tickets-1992947752376",
    },
    5740264: {
        "club_id": 29044,
        "date": "2026-12-12T00:00:00+00:00",
        "name": "David Koechner LIVE @ The Attic Comedy Club! December 11, 7 PM",
        "room": "",
        "show_page_url": "https://www.eventbrite.com/e/david-koechner-live-the-attic-comedy-club-december-11-7-pm-tickets-1992024956268",
    },
    5740265: {
        "club_id": 29044,
        "date": "2026-12-12T02:30:00+00:00",
        "name": "David Koechner LIVE @ The Attic Comedy Club! December 11, 9:30 PM",
        "room": "",
        "show_page_url": "https://www.eventbrite.com/e/david-koechner-live-the-attic-comedy-club-december-11-930-pm-tickets-1992025113739",
    },
    5740266: {
        "club_id": 29044,
        "date": "2026-12-13T00:00:00+00:00",
        "name": "David Koechner LIVE @ The Attic Comedy Club! December 12, 7 PM",
        "room": "",
        "show_page_url": "https://www.eventbrite.com/e/david-koechner-live-the-attic-comedy-club-december-12-7-pm-tickets-1992025512933",
    },
    5740267: {
        "club_id": 29044,
        "date": "2026-12-13T02:30:00+00:00",
        "name": "David Koechner LIVE @ The Attic Comedy Club! December 12, 9:30 PM",
        "room": "",
        "show_page_url": "https://www.eventbrite.com/e/david-koechner-live-the-attic-comedy-club-december-12-930-pm-tickets-1992025741617",
    },
    5740268: {
        "club_id": 29044,
        "date": "2026-12-20T00:00:00+00:00",
        "name": "Fine, Actually- A Night of Comedy with Holly Hudson",
        "room": "",
        "show_page_url": "https://www.eventbrite.com/e/fine-actually-a-night-of-comedy-with-holly-hudson-tickets-1992843402262",
    },
    5740269: {
        "club_id": 29044,
        "date": "2027-01-16T00:00:00+00:00",
        "name": "Michael Longfellow LIVE @ The Attic Comedy Club! January 15, 7 PM",
        "room": "",
        "show_page_url": "https://www.eventbrite.com/e/michael-longfellow-live-the-attic-comedy-club-january-15-7-pm-tickets-1994865248659",
    },
    5740270: {
        "club_id": 29044,
        "date": "2027-01-16T02:00:00+00:00",
        "name": "Michael Longfellow LIVE @ The Attic Comedy Club! January 15, 9 PM",
        "room": "",
        "show_page_url": "https://www.eventbrite.com/e/michael-longfellow-live-the-attic-comedy-club-january-15-9-pm-tickets-1994869485331",
    },
    5740271: {
        "club_id": 29044,
        "date": "2027-01-17T00:00:00+00:00",
        "name": "Michael Longfellow LIVE @ The Attic Comedy Club! January 16, 7 PM",
        "room": "",
        "show_page_url": "https://www.eventbrite.com/e/michael-longfellow-live-the-attic-comedy-club-january-16-7-pm-tickets-1994870569574",
    },
    5740272: {
        "club_id": 29044,
        "date": "2027-01-17T02:00:00+00:00",
        "name": "Michael Longfellow LIVE @ The Attic Comedy Club! January 16, 9 PM",
        "room": "",
        "show_page_url": "https://www.eventbrite.com/e/michael-longfellow-live-the-attic-comedy-club-january-16-9-pm-tickets-1994870476295",
    },
    5740273: {
        "club_id": 29044,
        "date": "2027-01-24T00:00:00+00:00",
        "name": "Kristin Chirico Live Standup Comedy Show @ The Attic Comedy Club Columbus",
        "room": "",
        "show_page_url": "https://www.eventbrite.com/e/kristin-chirico-live-standup-comedy-show-the-attic-comedy-club-columbus-tickets-1994871891528",
    },
    6017989: {
        "club_id": 12796,
        "date": "2026-10-31T17:30:00+00:00",
        "name": "Golden Girls: The Laughs Continue - Ages 18+",
        "room": "",
        "show_page_url": "https://www.ticketmaster.com/event/Z7r9jZ1A70z7E",
    },
    6017990: {
        "club_id": 12796,
        "date": "2026-10-31T23:00:00+00:00",
        "name": "Golden Girls: The Laughs Continue - Ages 18+",
        "room": "",
        "show_page_url": "https://www.ticketmaster.com/event/Z7r9jZ1AAv6u7",
    },
    6067069: {
        "club_id": 12796,
        "date": "2027-01-15T00:00:00+00:00",
        "name": "Jay Leno",
        "room": "",
        "show_page_url": "https://www.ticketmaster.com/event/Z7r9jZ1A7P-JK",
    },
    6904546: {
        "club_id": 10023,
        "date": "2026-10-31T17:30:00+00:00",
        "name": "Golden Girls: The Laughs Continue - Ages 18+",
        "room": "",
        "show_page_url": "https://www.ticketmaster.com/event/Z7r9jZ1A70z7E",
    },
    6904547: {
        "club_id": 10023,
        "date": "2026-10-31T23:00:00+00:00",
        "name": "Golden Girls: The Laughs Continue - Ages 18+",
        "room": "",
        "show_page_url": "https://www.ticketmaster.com/event/Z7r9jZ1AAv6u7",
    },
    6904549: {
        "club_id": 10023,
        "date": "2027-01-15T00:00:00+00:00",
        "name": "Jay Leno",
        "room": "",
        "show_page_url": "https://www.ticketmaster.com/event/Z7r9jZ1A7P-JK",
    },
    6977157: {
        "club_id": 9650,
        "date": "2026-10-04T03:00:00+00:00",
        "name": "Ron White",
        "room": "",
        "show_page_url": "https://www.ticketmaster.com/event/Z7r9jZ1A70taU",
    },
    6977158: {
        "club_id": 9650,
        "date": "2026-11-20T04:00:00+00:00",
        "name": "Nikki Glaser",
        "room": "",
        "show_page_url": "https://www.ticketmaster.com/event/Z7r9jZ1A7Opvx",
    },
    7075650: {
        "club_id": 10023,
        "date": "2027-03-16T23:00:00+00:00",
        "name": "Six: The Musical",
        "room": "",
        "show_page_url": "https://www.ticketmaster.com/event/Z7r9jZ1AAvauV",
    },
    7082340: {
        "club_id": 12796,
        "date": "2027-03-16T23:00:00+00:00",
        "name": "Six: The Musical",
        "room": "",
        "show_page_url": "https://www.ticketmaster.com/event/Z7r9jZ1AAvauV",
    },
    7124455: {
        "club_id": 10023,
        "date": "2027-03-17T17:30:00+00:00",
        "name": "Six: The Musical",
        "room": "",
        "show_page_url": "https://www.ticketmaster.com/event/Z7r9jZ1AAvaug",
    },
    7124456: {
        "club_id": 10023,
        "date": "2027-03-17T23:00:00+00:00",
        "name": "Six: The Musical",
        "room": "",
        "show_page_url": "https://www.ticketmaster.com/event/Z7r9jZ1AAvauU",
    },
    7131652: {
        "club_id": 12796,
        "date": "2027-03-17T17:30:00+00:00",
        "name": "Six: The Musical",
        "room": "",
        "show_page_url": "https://www.ticketmaster.com/event/Z7r9jZ1AAvaug",
    },
    7131653: {
        "club_id": 12796,
        "date": "2027-03-17T23:00:00+00:00",
        "name": "Six: The Musical",
        "room": "",
        "show_page_url": "https://www.ticketmaster.com/event/Z7r9jZ1AAvauU",
    },
    7220970: {
        "club_id": 10023,
        "date": "2027-03-18T23:00:00+00:00",
        "name": "Six: The Musical",
        "room": "",
        "show_page_url": "https://www.ticketmaster.com/event/Z7r9jZ1AAvauM",
    },
    7224899: {
        "club_id": 12796,
        "date": "2027-03-18T23:00:00+00:00",
        "name": "Six: The Musical",
        "room": "",
        "show_page_url": "https://www.ticketmaster.com/event/Z7r9jZ1AAvauM",
    },
    7224900: {
        "club_id": 12796,
        "date": "2027-03-19T23:00:00+00:00",
        "name": "Six: The Musical",
        "room": "",
        "show_page_url": "https://www.ticketmaster.com/event/Z7r9jZ1AAvauz",
    },
    7268132: {
        "club_id": 10023,
        "date": "2027-03-19T23:00:00+00:00",
        "name": "Six: The Musical",
        "room": "",
        "show_page_url": "https://www.ticketmaster.com/event/Z7r9jZ1AAvauz",
    },
    7268133: {
        "club_id": 10023,
        "date": "2027-03-20T17:30:00+00:00",
        "name": "Six: The Musical",
        "room": "",
        "show_page_url": "https://www.ticketmaster.com/event/Z7r9jZ1AAvauy",
    },
    7268134: {
        "club_id": 10023,
        "date": "2027-03-20T23:00:00+00:00",
        "name": "Six: The Musical",
        "room": "",
        "show_page_url": "https://www.ticketmaster.com/event/Z7r9jZ1AAvaCZ",
    },
    7272092: {
        "club_id": 12796,
        "date": "2027-03-20T17:30:00+00:00",
        "name": "Six: The Musical",
        "room": "",
        "show_page_url": "https://www.ticketmaster.com/event/Z7r9jZ1AAvauy",
    },
    7272093: {
        "club_id": 12796,
        "date": "2027-03-20T23:00:00+00:00",
        "name": "Six: The Musical",
        "room": "",
        "show_page_url": "https://www.ticketmaster.com/event/Z7r9jZ1AAvaCZ",
    },
    7316068: {
        "club_id": 10023,
        "date": "2027-03-21T17:30:00+00:00",
        "name": "Six: The Musical",
        "room": "",
        "show_page_url": "https://www.ticketmaster.com/event/Z7r9jZ1A7PVAN",
    },
    7322230: {
        "club_id": 12796,
        "date": "2027-03-21T17:30:00+00:00",
        "name": "Six: The Musical",
        "room": "",
        "show_page_url": "https://www.ticketmaster.com/event/Z7r9jZ1A7PVAN",
    },
    7351170: {
        "club_id": 5115,
        "date": "2026-10-16T23:00:00+00:00",
        "name": "Aziz Ansari",
        "room": "",
        "show_page_url": "https://www.ticketmaster.com/event/Z7r9jZ1AAZ9Ap",
    },
    7361463: {
        "club_id": 5114,
        "date": "2026-10-16T23:00:00+00:00",
        "name": "Aziz Ansari",
        "room": "",
        "show_page_url": "https://www.ticketmaster.com/event/Z7r9jZ1AAZ9Ap",
    },
}
EXPECTED_CLUBS = {
    575: {"address": "892 Oak Street", "city": "Columbus", "name": "The Attic Comedy Club", "state": "OH"},
    4691: {
        "address": "777 San Manuel Blvd., Highland, CA",
        "city": "Highland",
        "name": "Yaamava Resort & Casino at San Manuel",
        "state": "CA",
    },
    5114: {
        "address": "107 WEST STATE STREET, Ithaca, NY",
        "city": "Ithaca",
        "name": "Ithaca's State Theatre",
        "state": "NY",
    },
    5115: {
        "address": "111 W State Street, Ithaca, NY",
        "city": "Ithaca",
        "name": "State Theatre At Ithaca",
        "state": "NY",
    },
    5225: {
        "address": "801 North Rampart Street, New Orleans, LA",
        "city": "New Orleans",
        "name": "Mahalia Jackson Theater",
        "state": "LA",
    },
    5364: {
        "address": "1419 Basin Street, New Orleans, LA",
        "city": "New Orleans",
        "name": "Mahalia Jackson Theater for the Performing Arts",
        "state": "LA",
    },
    9650: {
        "address": "777 San Manuel Blvd S, Highland, CA",
        "city": "Highland",
        "name": "Yaamava Theater",
        "state": "CA",
    },
    10023: {"address": "777 N Tamiami TRL, Sarasota, FL", "city": "Sarasota", "name": "Van Wezel", "state": "FL"},
    12796: {
        "address": "777 N Tamiami Trail, Sarasota, FL",
        "city": "Sarasota",
        "name": "Van Wezel Performing Arts Hall",
        "state": "FL",
    },
    29044: {"address": "143 E Main St, Columbus, OH", "city": "Columbus", "name": "The Walrus", "state": "OH"},
}
EXPECTED_SOURCES = {
    401: {
        "club_id": 575,
        "enabled": True,
        "platform": "eventbrite",
        "priority": 0,
        "scraper_key": "eventbrite",
        "source_url": "https://www.eventbrite.com/o/the-attic-comedy-club-113948356841",
        "ticketmaster_id": None,
    },
    3781: {
        "club_id": 4691,
        "enabled": False,
        "platform": "ticketmaster",
        "priority": 0,
        "scraper_key": "ticketmaster_comedy",
        "source_url": "https://www.ticketmaster.com",
        "ticketmaster_id": "ZFr9jZAvFe",
    },
    4204: {
        "club_id": 5114,
        "enabled": False,
        "platform": "ticketmaster",
        "priority": 0,
        "scraper_key": "ticketmaster_comedy",
        "source_url": "https://www.ticketmaster.com",
        "ticketmaster_id": "ZFr9jZAv7d",
    },
    4205: {
        "club_id": 5115,
        "enabled": False,
        "platform": "ticketmaster",
        "priority": 0,
        "scraper_key": "ticketmaster_comedy",
        "source_url": "https://www.ticketmaster.com",
        "ticketmaster_id": "KovZpZA1JdvA",
    },
    4315: {
        "club_id": 5225,
        "enabled": False,
        "platform": "ticketmaster",
        "priority": 0,
        "scraper_key": "ticketmaster_comedy",
        "source_url": "https://www.ticketmaster.com",
        "ticketmaster_id": "ZFr9jZ7dae",
    },
    4454: {
        "club_id": 5364,
        "enabled": False,
        "platform": "ticketmaster",
        "priority": 0,
        "scraper_key": "ticketmaster_comedy",
        "source_url": "https://www.ticketmaster.com",
        "ticketmaster_id": "KovZpaKkke",
    },
    6450: {
        "club_id": 9650,
        "enabled": True,
        "platform": "ticketmaster",
        "priority": 0,
        "scraper_key": "live_nation",
        "source_url": "https://www.ticketmaster.com",
        "ticketmaster_id": "Z7r9jZaAVT",
    },
    6780: {
        "club_id": 10023,
        "enabled": True,
        "platform": "ticketmaster",
        "priority": 0,
        "scraper_key": "live_nation",
        "source_url": "https://www.ticketmaster.com",
        "ticketmaster_id": "KovZpZA7dtvA",
    },
    7154: {
        "club_id": 12796,
        "enabled": True,
        "platform": "ticketmaster",
        "priority": 0,
        "scraper_key": "live_nation",
        "source_url": "https://www.ticketmaster.com",
        "ticketmaster_id": "ZFr9jZdk16",
    },
    7950: {
        "club_id": 4691,
        "enabled": True,
        "platform": "ticketmaster",
        "priority": 1,
        "scraper_key": "live_nation",
        "source_url": "https://www.ticketmaster.com",
        "ticketmaster_id": "ZFr9jZAvFe",
    },
    8092: {
        "club_id": 5115,
        "enabled": True,
        "platform": "ticketmaster",
        "priority": 1,
        "scraper_key": "live_nation",
        "source_url": "https://www.ticketmaster.com",
        "ticketmaster_id": "KovZpZA1JdvA",
    },
    8249: {
        "club_id": 5225,
        "enabled": True,
        "platform": "ticketmaster",
        "priority": 1,
        "scraper_key": "live_nation",
        "source_url": "https://www.ticketmaster.com",
        "ticketmaster_id": "ZFr9jZ7dae",
    },
    8374: {
        "club_id": 5364,
        "enabled": True,
        "platform": "ticketmaster",
        "priority": 1,
        "scraper_key": "live_nation",
        "source_url": "https://www.ticketmaster.com",
        "ticketmaster_id": "KovZpaKkke",
    },
    9973: {
        "club_id": 29044,
        "enabled": True,
        "platform": "eventbrite",
        "priority": 0,
        "scraper_key": "eventbrite",
        "source_url": "https://www.eventbrite.com",
        "ticketmaster_id": None,
    },
    13027: {
        "club_id": 5114,
        "enabled": True,
        "platform": "ticketmaster",
        "priority": 1,
        "scraper_key": "live_nation",
        "source_url": "https://www.ticketmaster.com",
        "ticketmaster_id": "ZFr9jZAv7d",
    },
}

CLUB_IDS = sorted(EXPECTED_CLUBS)
SHOW_IDS = sorted(EXPECTED_SHOWS)
CHILDREN = (
    "tickets",
    "lineup_items",
    "tagged_shows",
    "sent_notifications",
    "ticket_purchase_click_events",
    "discovery_show_feature_snapshots",
    "saved_shows",
)
CLUB_REFS = {
    "club_aliases": "club_id",
    "club_discovery_profiles": "club_id",
    "club_image_assets": "club_id",
    "comedians": "home_club_id",
    "email_subscriptions": "club_id",
    "eventbrite_organizer_venues": "club_id",
    "favorite_clubs": "club_id",
    "processed_emails": "club_id",
    "production_company_venues": "club_id",
    "scraper_run_clubs": "club_id",
    "scraping_sources": "club_id",
    "shows": "club_id",
    "tagged_clubs": "club_id",
    "ticket_purchase_click_events": "club_id",
}
ZERO_REFS = set(CLUB_REFS) - {
    "club_aliases",
    "comedians",
    "scraper_run_clubs",
    "scraping_sources",
    "shows",
    "ticket_purchase_click_events",
}
TABLES = [
    "clubs",
    "scraping_sources",
    "shows",
    *CHILDREN,
    *[t for t in CLUB_REFS if t not in {"scraping_sources", "shows", *CHILDREN}],
]


def schema(cur):
    result = {}
    for parent, expected in [("clubs", set(CLUB_REFS.items())), ("shows", {(t, "show_id") for t in CHILDREN})]:
        cur.execute(
            """SELECT c.conrelid::regclass::text,a.attname
            FROM pg_constraint c JOIN LATERAL unnest(c.conkey) k(attnum) ON true
            JOIN pg_attribute a ON a.attrelid=c.conrelid AND a.attnum=k.attnum
            WHERE c.confrelid=%s::regclass AND c.contype='f'""",
            (parent,),
        )
        actual = {(r[0].split(".")[-1].strip('"'), r[1]) for r in cur.fetchall()}
        if actual != expected:
            raise ValueError(f"{parent} foreign keys changed: {actual}; review recovery coverage")
    for table in TABLES:
        cur.execute(
            "SELECT attname,format_type(atttypid,atttypmod) FROM pg_attribute WHERE attrelid=%s::regclass AND attnum>0 AND NOT attisdropped ORDER BY attnum",
            (table,),
        )
        columns = cur.fetchall()
        cur.execute(
            "SELECT a.attname FROM pg_index i JOIN LATERAL unnest(i.indkey) WITH ORDINALITY k(attnum,ord) ON true JOIN pg_attribute a ON a.attrelid=i.indrelid AND a.attnum=k.attnum WHERE i.indrelid=%s::regclass AND i.indisprimary ORDER BY k.ord",
            (table,),
        )
        primary = [r[0] for r in cur.fetchall()]
        if not primary:
            raise ValueError(f"{table} has no primary key for recovery")
        cur.execute(
            "SELECT conname,pg_get_constraintdef(oid) FROM pg_constraint WHERE conrelid=%s::regclass ORDER BY conname",
            (table,),
        )
        constraints = cur.fetchall()
        cur.execute(
            "SELECT indexrelid::regclass::text,pg_get_indexdef(indexrelid) FROM pg_index WHERE indrelid=%s::regclass ORDER BY indexrelid::regclass::text",
            (table,),
        )
        indexes = cur.fetchall()
        result[table] = {"columns": columns, "primary": primary, "constraints": constraints, "indexes": indexes}
    for table, columns in {
        "tickets": {"id", "show_id", "purchase_url", "price", "sold_out", "type"},
        "lineup_items": {"id", "show_id", "comedian_id", "role"},
        "tagged_shows": {"id", "show_id", "tag_id"},
        "saved_shows": {"profile_id", "show_id", "created_at"},
    }.items():
        if {c[0] for c in result[table]["columns"]} != columns:
            raise ValueError(f"{table} columns changed; review merge policy")
    return json.loads(json.dumps(result))


def lock_and_validate_schema(cur):
    cur.execute("SET LOCAL lock_timeout='5s'")
    cur.execute(
        sql.SQL("LOCK TABLE {} IN SHARE ROW EXCLUSIVE MODE").format(sql.SQL(",").join(map(sql.Identifier, TABLES)))
    )
    return schema(cur)


def snapshot(cur):
    result = {}
    # Include all historical rows of these retained clubs so unintended changes
    # and concurrent user-reference arrivals make restoration fail closed.
    cur.execute("SELECT id FROM shows WHERE club_id=ANY(%s)", (CLUB_IDS,))
    all_show_ids = sorted(set(SHOW_IDS) | {r[0] for r in cur.fetchall()})
    for table in TABLES:
        clauses = []
        params = []
        if table == "clubs":
            clauses.append(sql.SQL("id=ANY(%s)"))
            params.append(CLUB_IDS)
        if table in CLUB_REFS:
            clauses.append(sql.SQL("{}=ANY(%s)").format(sql.Identifier(CLUB_REFS[table])))
            params.append(CLUB_IDS)
        if table in CHILDREN:
            clauses.append(sql.SQL("show_id=ANY(%s)"))
            params.append(all_show_ids)
        cur.execute(
            sql.SQL("SELECT to_jsonb(t) FROM {} t WHERE {}").format(
                sql.Identifier(table), sql.SQL(" OR ").join(clauses)
            ),
            params,
        )
        result[table] = sorted([r[0] for r in cur.fetchall()], key=lambda r: json.dumps(r, sort_keys=True))
    return result


def closed_name(old, new):
    return f"{EXPECTED_CLUBS[old]['name']} (duplicate of club {new}; TASK-4049)"


def validate(cur, state):
    for table in ZERO_REFS:
        if state[table]:
            raise ValueError(f"Unreviewed {table} references appeared; refusing repair")
    for alias in state["club_aliases"]:
        expected_aliases = {
            (new, EXPECTED_CLUBS[old]["name"], EXPECTED_CLUBS[old]["city"], EXPECTED_CLUBS[old]["state"])
            for old, new in FOLDS.items()
        }
        if (
            alias.get("source") != "TASK-4049"
            or (alias["club_id"], alias["alias_name"], alias["city"], alias["state"]) not in expected_aliases
        ):
            raise ValueError("Unreviewed alias appeared; refusing repair")
    clubs = {r["id"]: r for r in state["clubs"]}
    if set(clubs) != set(CLUB_IDS):
        raise ValueError("Reviewed club missing")
    for ident, expected in EXPECTED_CLUBS.items():
        row = clubs[ident]
        allowed = {expected["name"]}
        if ident in FOLDS:
            allowed.add(closed_name(ident, FOLDS[ident]))
        if row["name"] not in allowed or any(row[k] != expected[k] for k in ["city", "state", "address"]):
            raise ValueError(f"Club {ident} identity changed")
    sources = {r["id"]: r for r in state["scraping_sources"]}
    if set(sources) != set(EXPECTED_SOURCES):
        raise ValueError("Source inventory changed")
    for ident, expected in EXPECTED_SOURCES.items():
        row = sources[ident]
        old = expected["club_id"]
        moved = old in FOLDS and row["club_id"] == FOLDS[old]
        for key, value in expected.items():
            if moved and key in {"club_id", "priority", "enabled"}:
                continue
            if row[key] != value:
                raise ValueError(f"Source {ident} identity changed")
        if moved and (row["enabled"] or "task_4049_disposition" not in row["metadata"]):
            raise ValueError(f"Source {ident} lost disabled fold disposition")
    rows = {r["id"]: r for r in state["shows"]}
    for ident, expected in EXPECTED_SHOWS.items():
        row = rows.get(ident)
        if row is None and ident in SHOW_MAP:
            continue
        if row is None:
            raise ValueError(f"Reviewed survivor {ident} missing")
        expected_clubs = {expected["club_id"], SHOW_MOVES.get(ident, expected["club_id"])}
        if (
            row["club_id"] not in expected_clubs
            or any(row[k] != expected[k] for k in ["room", "show_page_url", "name"])
            or datetime.fromisoformat(row["date"]) != datetime.fromisoformat(expected["date"])
        ):
            raise ValueError(f"Reviewed show {ident} changed")
    # New upcoming rows need explicit review before a source venue is hidden.
    cur.execute("SELECT id FROM shows WHERE club_id=ANY(%s) AND date>now()", (list(FOLDS),))
    unreviewed = {r[0] for r in cur.fetchall()} - set(SHOW_MAP) - set(SHOW_MOVES)
    if unreviewed:
        raise ValueError(f"Unreviewed future fold shows: {sorted(unreviewed)}")
    for old, new in SHOW_MAP.items():
        a = EXPECTED_SHOWS[old]
        b = EXPECTED_SHOWS[new]
        if datetime.fromisoformat(a["date"]) != datetime.fromisoformat(b["date"]) or a["room"] != b["room"]:
            raise ValueError(f"Performance date/room mismatch: {old}->{new}")
        if a["show_page_url"] != b["show_page_url"] and (old, new) not in EQUIVALENT_EVENT_URLS:
            raise ValueError(f"Unverified different provider URLs: {old}->{new}")
    for old, new in FOLDS.items():
        cur.execute(
            "SELECT club_id FROM club_aliases WHERE normalized_alias_name=lt_normalize_alias_key(%s) AND normalized_city=lt_normalize_alias_key(%s) AND normalized_state=lower(%s)",
            (EXPECTED_CLUBS[old]["name"], EXPECTED_CLUBS[old]["city"], EXPECTED_CLUBS[old]["state"]),
        )
        if any(r[0] != new for r in cur.fetchall()):
            raise ValueError("Alias belongs to another canonical club")


def merge_show(cur, old, new, club_id):
    for table, columns, conflict in (
        ("lineup_items", "show_id,comedian_id,role", "(show_id,comedian_id)"),
        ("tagged_shows", "show_id,tag_id", "(show_id,tag_id)"),
        ("tickets", "show_id,purchase_url,price,sold_out,type", "(show_id,type)"),
    ):
        tail = columns.split(",", 1)[1]
        cur.execute(
            f"INSERT INTO {table} ({columns}) SELECT %s,{tail} FROM {table} WHERE show_id=%s ON CONFLICT {conflict} DO NOTHING",
            (new, old),
        )
    cur.execute(
        """INSERT INTO saved_shows(profile_id,show_id,created_at)
        SELECT profile_id,%s,created_at FROM saved_shows WHERE show_id=%s
        ON CONFLICT(profile_id,show_id) DO UPDATE SET created_at=LEAST(saved_shows.created_at,EXCLUDED.created_at)""",
        (new, old),
    )
    cur.execute("UPDATE sent_notifications SET show_id=%s WHERE show_id=%s", (new, old))
    cur.execute("UPDATE ticket_purchase_click_events SET show_id=%s,club_id=%s WHERE show_id=%s", (new, club_id, old))
    # Venue features may be invalid after reassignment; archive these derived
    # old snapshots for recovery and let the canonical show recompute its own.
    cur.execute("DELETE FROM shows WHERE id=%s", (old,))
    if cur.rowcount != 1:
        raise ValueError(f"Show {old} disappeared")


def repair(cur, before):
    present = {r["id"] for r in before["shows"]}
    for old, new in SHOW_MAP.items():
        if old in present:
            merge_show(cur, old, new, EXPECTED_SHOWS[new]["club_id"])
    for ident, club in SHOW_MOVES.items():
        cur.execute("UPDATE shows SET club_id=%s WHERE id=%s", (club, ident))
        cur.execute("UPDATE ticket_purchase_click_events SET club_id=%s WHERE show_id=%s", (club, ident))
    for old, new in FOLDS.items():
        expected = EXPECTED_CLUBS[old]
        cur.execute(
            """INSERT INTO club_aliases(club_id,alias_name,city,state,source,verified,updated_at)
            VALUES(%s,%s,%s,%s,'TASK-4049',true,now())
            ON CONFLICT(normalized_alias_name,normalized_city,normalized_state) DO NOTHING""",
            (new, expected["name"], expected["city"], expected["state"]),
        )
        cur.execute("SELECT id,platform FROM scraping_sources WHERE club_id=%s ORDER BY platform,priority,id", (old,))
        for source_id, platform in cur.fetchall():
            cur.execute(
                "SELECT coalesce(max(priority),-1)+1 FROM scraping_sources WHERE club_id=%s AND platform=%s",
                (new, platform),
            )
            priority = cur.fetchone()[0]
            cur.execute(
                """UPDATE scraping_sources SET club_id=%s,priority=%s,enabled=false,
                metadata=coalesce(metadata,'{}'::jsonb)||jsonb_build_object('task_4049_disposition',%s::text),updated_at=now() WHERE id=%s""",
                (new, priority, f"Moved disabled source from club {old} to {new}", source_id),
            )
        cur.execute("UPDATE comedians SET home_club_id=%s WHERE home_club_id=%s", (new, old))
        cur.execute(
            "UPDATE clubs SET name=%s,visible=false,status='closed',closed_at=coalesce(closed_at,now()) WHERE id=%s",
            (closed_name(old, new), old),
        )
    cur.execute(
        "UPDATE clubs c SET total_shows=(SELECT count(*) FROM shows s WHERE s.club_id=c.id) WHERE c.id=ANY(%s)",
        (CLUB_IDS,),
    )


def restore(cur, backup):
    if (
        backup.get("task_id") != 4049
        or backup.get("show_map") != {str(k): v for k, v in SHOW_MAP.items()}
        or backup.get("folds") != {str(k): v for k, v in FOLDS.items()}
        or backup.get("show_moves") != {str(k): v for k, v in SHOW_MOVES.items()}
    ):
        raise ValueError("Recovery file does not match this reviewed TASK-4049 plan")
    live_schema = schema(cur)
    if live_schema != backup["schema"]:
        raise ValueError("Schema changed since backup")
    live = snapshot(cur)
    if live == backup["before"]:
        return
    if live != backup["after"]:
        raise ValueError("Affected rows changed after repair; refusing restore")

    def index(table, rows):
        keys = live_schema[table]["primary"]
        return {tuple(row[k] for k in keys): row for row in rows}

    before = {t: index(t, backup["before"][t]) for t in TABLES}
    after = {t: index(t, backup["after"][t]) for t in TABLES}
    # Remove only new rows first, children before parents; never delete clubs.
    for table in reversed(TABLES):
        keys = live_schema[table]["primary"]
        for ident in after[table].keys() - before[table].keys():
            where = sql.SQL(" AND ").join(sql.SQL("{} IS NOT DISTINCT FROM %s").format(sql.Identifier(k)) for k in keys)
            cur.execute(sql.SQL("DELETE FROM {} WHERE {}").format(sql.Identifier(table), where), ident)
    # Restore removed parents before child reassignments. Existing rows update
    # from full record snapshots, retaining IDs and original business fields.
    for table in TABLES:
        for ident, row in before[table].items():
            if ident not in after[table]:
                cur.execute(
                    sql.SQL("INSERT INTO {} SELECT * FROM jsonb_populate_record(NULL::{},%s::jsonb)").format(
                        sql.Identifier(table), sql.Identifier(table)
                    ),
                    (json.dumps(row),),
                )
            elif row != after[table][ident]:
                keys = live_schema[table]["primary"]
                cols = [c for c in row if c not in keys]
                sets = sql.SQL(",").join(sql.SQL("{}=r.{}").format(sql.Identifier(c), sql.Identifier(c)) for c in cols)
                where = sql.SQL(" AND ").join(
                    sql.SQL("t.{} IS NOT DISTINCT FROM r.{}").format(sql.Identifier(k), sql.Identifier(k)) for k in keys
                )
                cur.execute(
                    sql.SQL("UPDATE {} t SET {} FROM jsonb_populate_record(NULL::{},%s::jsonb) r WHERE {}").format(
                        sql.Identifier(table), sets, sql.Identifier(table), where
                    ),
                    (json.dumps(row),),
                )
    if snapshot(cur) != backup["before"]:
        raise ValueError("Restore did not reproduce exact before-state")


def save_backup(path, payload):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    directory = os.open(Path(path).parent, os.O_RDONLY)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--apply", action="store_true")
    modes.add_argument("--dry-run", action="store_true")
    modes.add_argument("--restore", type=Path)
    parser.add_argument("--backup", type=Path)
    args = parser.parse_args()
    if args.apply and not args.backup:
        parser.error("--apply requires a new private --backup file")
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parents[2] / ".env")
    from laughtrack.adapters.db import get_transaction

    with get_transaction() as conn:
        with conn.cursor() as cur:
            actual_schema = lock_and_validate_schema(cur)
            before = snapshot(cur)
            if args.restore:
                restore(cur, json.loads(args.restore.read_text()))
            else:
                validate(cur, before)
                repair(cur, before)
                validate(cur, snapshot(cur))
            after = snapshot(cur)
            print(
                json.dumps(
                    {"before": {t: len(v) for t, v in before.items()}, "after": {t: len(v) for t, v in after.items()}},
                    sort_keys=True,
                )
            )
            if args.apply:
                save_backup(
                    args.backup,
                    {
                        "task_id": 4049,
                        "show_map": SHOW_MAP,
                        "show_moves": SHOW_MOVES,
                        "folds": FOLDS,
                        "schema": actual_schema,
                        "before": before,
                        "after": after,
                    },
                )
            elif not args.restore:
                conn.rollback()
                print("DRY RUN: rolled back")


if __name__ == "__main__":
    main()
