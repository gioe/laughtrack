#!/usr/bin/env python3
"""
Disposition the 27 actionable (platform, external_id) collisions from the
TASK-1956 audit (2026-05-06 snapshot).

Background
----------
TASK-1956 audited the live ``scraping_sources`` table for cases where two
distinct ``club_id``s share the same ``(platform, external_id)`` pair. The
2026-05-06 snapshot found 35 collisions: 5 eventbrite, 29 seatengine,
1 squadup. Each is a latent silent-mismap bug — any audit/disposition/dedup
tool that joins by ``(platform, external_id)`` attributes one club's data to
the other, which is exactly what masked The Well Comedy Club's status in
TASK-1951 and motivated this task. The audit + per-case API probes live
at ``apps/scraper/docs/audits/task-1956-scraping-source-collisions.md`` and
the matching ``task-1956-collision-data.json`` artefact.

Of the 35 collisions, 27 fall into three patterns where the resolution is
unambiguous and structural:

* **Pattern A — manual seatengine_classic row with stale external_id (21):**
  The ``seatengine_classic`` scraper hits the venue's own SeatEngine HTML
  page from ``source_url`` and does NOT consume ``external_id`` at runtime
  (TASK-1951 confirmed this). Each Pattern A row's ``external_id`` was
  populated long ago, points at an unrelated SeatEngine venue (charity
  events, test entries, random orgs), and survives only as legacy metadata.
  The auto-discovered sibling row created by ``seatengine_national`` is the
  CORRECT mapping for that ``external_id``, but for a hidden club nobody
  cares about. Clearing the manual row's wrong id is functionally a no-op
  for scraping but resolves the collision and removes the latent
  silent-mismap risk.

* **Pattern D — both rows seatengine_classic, SE venue deleted upstream (1):**
  ``ext=588`` returns an empty ``name`` and ``null`` ``website`` from
  ``services.seatengine.com/api/v1/venues/588`` — the SE record is gone.
  Both rows in the collision pair (Capitol Hill Comedy Bar club 94 and
  Emerald City Comedy Club club 106) are ``seatengine_classic`` URL-based
  scrapers; both ids are stale legacy data. Clearing on both resolves the
  collision and disconnects from the dead upstream venue.

* **Pattern EB — disabled ghost row of an Eventbrite duplicate-club pair (5):**
  Each pair has one ``enabled=true``+``visible=true`` canonical row and one
  ``enabled=false``+``visible=false`` ghost row, both pointing at the same
  Eventbrite organiser ID. The ghost is a residual artefact of a duplicate
  club that was disabled but its ``external_id`` was left populated.
  Clearing on the ghost is a metadata-only cleanup that resolves the
  collision.

Total rows updated: 28 (21 + 2 + 5).
Total collisions resolved: 27 (21 + 1 + 5; Pattern D is one collision but
clears both rows).

The remaining 8 collisions (Pattern B 1, Pattern C 6, Pattern SQ 1) are
same-venue duplicate-club cases where both rows correctly map to the same
upstream venue — the bug is at the ``clubs`` level, not the
``scraping_sources`` level. Each is filed as a separate follow-up task and
NOT touched by this script.

Why "clear" rather than "correct" the wrong external_ids
--------------------------------------------------------
For Pattern A and Pattern D, the manually-configured row uses
``scraper_key='seatengine_classic'``, which scrapes ``source_url`` HTML
directly and does not consume ``external_id``. Setting these rows to a
"correct" SeatEngine venue ID would require enumerating SE's full venue
space and matching by website per case (~22 venues, hundreds of API calls)
with zero runtime payoff. Clearing the wrong id removes the collision and
the latent mismap risk without adding new state. TASK-1951 took the
"correct the id" path because it was a single venue and the correct id was
already known from the venue's own footer; the cost-benefit flips at scale.

For Pattern EB, the ghost row is already ``enabled=false`` and not
actively scraping — clearing its ``external_id`` is the minimal change to
remove the collision without touching the ``clubs`` row.

What this script does
---------------------
1. Validates expected ``(club_id, platform, scraper_key, external_id)``
   shape on each targeted ``scraping_sources`` row (refuses to write on any
   mismatch — collects all problems first, prints them all, exits non-zero).
2. For each target: ``UPDATE scraping_sources SET external_id=NULL,
   metadata=<merged>::jsonb, updated_at=NOW()`` keyed by ``id``.
3. Stamps ``metadata.task_1956_disposition`` with ``kind`` (one of the three
   pattern labels), ``canonical_other_club_id`` (the sibling row in the
   collision pair that keeps its mapping — null for Pattern D), the SE API
   canonical name + website where applicable, and a per-row rationale.
   Mirrors the TASK-1962 / TASK-1966 / TASK-1979 disposition pattern so the
   forensic audit trail survives downstream upserts (convention #79).

Idempotent: only writes when the row currently has a non-null external_id
OR the metadata key is missing. Safe to re-run.

Verification
------------
After running, the TASK-1956 reproduction query (audit doc) returns 8 rows
(the deferred same-venue dupes). Re-running this script is a no-op.

Usage
-----
    cd apps/scraper
    make run-script SCRIPT=scripts/core/disposition_scraping_source_collisions_2026_05_06.py ARGS='--dry-run'
    make run-script SCRIPT=scripts/core/disposition_scraping_source_collisions_2026_05_06.py
"""

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

_root = next(p for p in Path(__file__).resolve().parents if (p / "pyproject.toml").exists())
for _path in (_root / "src", _root):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from dotenv import load_dotenv

load_dotenv(_root / ".env")

from laughtrack.adapters.db import get_transaction


_METADATA_KEY = "task_1956_disposition"


@dataclass(frozen=True)
class ClearTarget:
    """A scraping_sources row to NULL out external_id on, with stamped rationale."""

    source_id: int
    expected_club_id: int
    expected_external_id: str
    expected_platform: str
    expected_scraper_key: str
    kind: str
    canonical_other_club_id: Optional[int]
    canonical_se_name: Optional[str]
    canonical_se_website: Optional[str]
    rationale: str


TARGETS: list[ClearTarget] = [
    ClearTarget(
        source_id=1272,
        expected_club_id=2273,
        expected_external_id='28808914',
        expected_platform='eventbrite',
        expected_scraper_key='eventbrite',
        kind='eventbrite_disabled_ghost_dupe',
        canonical_other_club_id=160,
        canonical_se_name=None,
        canonical_se_website=None,
        rationale=(
            "Eventbrite duplicate-club pair: club 160 ('Laugh Factory "
            "Hollywood', visible+enabled, 172 future shows) is the canonical "
            "row; club 2273 ('Laugh Factory - Hollywood', hidden+disabled) is "
            'the residual ghost from a duplicate club artefact. Both rows point '
            'at the same Eventbrite organiser ID 28808914. Ghost row is already '
            'enabled=false and not actively scraping; clearing its external_id '
            'is a metadata-only cleanup that resolves the collision.'
        ),
    ),
    ClearTarget(
        source_id=1278,
        expected_club_id=2279,
        expected_external_id='35896069',
        expected_platform='eventbrite',
        expected_scraper_key='eventbrite',
        kind='eventbrite_disabled_ghost_dupe',
        canonical_other_club_id=184,
        canonical_se_name=None,
        canonical_se_website=None,
        rationale=(
            "Eventbrite duplicate-club pair: club 184 ('The Comedy Bar "
            "Chicago', visible+enabled, 110 future shows) is the canonical row; "
            "club 2279 ('The Comedy Bar - Chicago Main Stage', hidden+disabled) "
            'is the residual ghost from a duplicate club artefact. Both rows '
            'point at the same Eventbrite organiser ID 35896069. Ghost row is '
            'already enabled=false and not actively scraping; clearing its '
            'external_id is a metadata-only cleanup that resolves the '
            'collision.'
        ),
    ),
    ClearTarget(
        source_id=1275,
        expected_club_id=2276,
        expected_external_id='41248441',
        expected_platform='eventbrite',
        expected_scraper_key='eventbrite',
        kind='eventbrite_disabled_ghost_dupe',
        canonical_other_club_id=169,
        canonical_se_name=None,
        canonical_se_website=None,
        rationale=(
            "Eventbrite duplicate-club pair: club 169 ('Laugh Factory Long "
            "Beach', visible+enabled, 94 future shows) is the canonical row; "
            "club 2276 ('Long Beach Laugh Factory', hidden+disabled) is the "
            'residual ghost from a duplicate club artefact. Both rows point at '
            'the same Eventbrite organiser ID 41248441. Ghost row is already '
            'enabled=false and not actively scraping; clearing its external_id '
            'is a metadata-only cleanup that resolves the collision.'
        ),
    ),
    ClearTarget(
        source_id=1276,
        expected_club_id=2277,
        expected_external_id='60930661',
        expected_platform='eventbrite',
        expected_scraper_key='eventbrite',
        kind='eventbrite_disabled_ghost_dupe',
        canonical_other_club_id=170,
        canonical_se_name=None,
        canonical_se_website=None,
        rationale=(
            "Eventbrite duplicate-club pair: club 170 ('Laugh Factory San "
            "Diego', visible+enabled, 50 future shows) is the canonical row; "
            "club 2277 ('Laugh Factory', hidden+disabled) is the residual ghost "
            'from a duplicate club artefact. Both rows point at the same '
            'Eventbrite organiser ID 60930661. Ghost row is already '
            'enabled=false and not actively scraping; clearing its external_id '
            'is a metadata-only cleanup that resolves the collision.'
        ),
    ),
    ClearTarget(
        source_id=1287,
        expected_club_id=2288,
        expected_external_id='90437249',
        expected_platform='eventbrite',
        expected_scraper_key='eventbrite',
        kind='eventbrite_disabled_ghost_dupe',
        canonical_other_club_id=1038,
        canonical_se_name=None,
        canonical_se_website=None,
        rationale=(
            "Eventbrite duplicate-club pair: club 1038 ('Counter Weight "
            "Brewing', visible+enabled, 2 future shows) is the canonical row; "
            "club 2288 ('Counter Weight Brewing Company', hidden+disabled) is "
            'the residual ghost from a duplicate club artefact. Both rows point '
            'at the same Eventbrite organiser ID 90437249. Ghost row is already '
            'enabled=false and not actively scraping; clearing its external_id '
            'is a metadata-only cleanup that resolves the collision.'
        ),
    ),
    ClearTarget(
        source_id=156,
        expected_club_id=108,
        expected_external_id='132',
        expected_platform='seatengine',
        expected_scraper_key='seatengine_classic',
        kind='manual_seatengine_classic_stale_id',
        canonical_other_club_id=334,
        canonical_se_name="Levé's 2015 Charity Ball",
        canonical_se_website='https://leve-nw.org',
        rationale=(
            "Manually-configured seatengine_classic row for club 108 ('Helium & "
            "Elements Restaurant -St. Louis') had external_id=132 but SE API "
            'venue 132 resolves to "Levé\'s 2015 Charity Ball" '
            "(website='https://leve-nw.org'), which is the auto-discovered club "
            '334. The seatengine_classic scraper consumes source_url '
            '(st-louis.heliumcomedy.com/events) HTML directly and does not use '
            'external_id at runtime, so clearing the wrong id is a no-op for '
            'scraping but resolves the (platform, external_id) collision and '
            'removes the latent silent-mismap risk that TASK-1951 hit.'
        ),
    ),
    ClearTarget(
        source_id=480,
        expected_club_id=1031,
        expected_external_id='157',
        expected_platform='seatengine',
        expected_scraper_key='seatengine_classic',
        kind='manual_seatengine_classic_stale_id',
        canonical_other_club_id=359,
        canonical_se_name='Royal Comedy Theatre',
        canonical_se_website='http://royalcomedy.net',
        rationale=(
            "Manually-configured seatengine_classic row for club 1031 ('Tacoma "
            "Comedy Club - Downtown') had external_id=157 but SE API venue 157 "
            "resolves to 'Royal Comedy Theatre' "
            "(website='http://royalcomedy.net'), which is the auto-discovered "
            'club 359. The seatengine_classic scraper consumes source_url '
            '(https://www.tacomacomedyclub.com/events#location=Downtown) HTML '
            'directly and does not use external_id at runtime, so clearing the '
            'wrong id is a no-op for scraping but resolves the (platform, '
            'external_id) collision and removes the latent silent-mismap risk '
            'that TASK-1951 hit.'
        ),
    ),
    ClearTarget(
        source_id=38,
        expected_club_id=69,
        expected_external_id='338',
        expected_platform='seatengine',
        expected_scraper_key='seatengine_classic',
        kind='manual_seatengine_classic_stale_id',
        canonical_other_club_id=368,
        canonical_se_name='Nauti Parrot Dock Bar',
        canonical_se_website='http://nautiparrotdockbar.com',
        rationale=(
            "Manually-configured seatengine_classic row for club 69 ('The "
            "Comedy Club of Kansas City') had external_id=338 but SE API venue "
            "338 resolves to 'Nauti Parrot Dock Bar' "
            "(website='http://nautiparrotdockbar.com'), which is the "
            'auto-discovered club 368. The seatengine_classic scraper consumes '
            'source_url (thecomedyclubkc.com/events) HTML directly and does not '
            'use external_id at runtime, so clearing the wrong id is a no-op '
            'for scraping but resolves the (platform, external_id) collision '
            'and removes the latent silent-mismap risk that TASK-1951 hit.'
        ),
    ),
    ClearTarget(
        source_id=584,
        expected_club_id=90,
        expected_external_id='359',
        expected_platform='seatengine',
        expected_scraper_key='seatengine_classic',
        kind='manual_seatengine_classic_stale_id',
        canonical_other_club_id=388,
        canonical_se_name='HOUSE OF COMEDY ',
        canonical_se_website='http://houseofcomedymd.com',
        rationale=(
            "Manually-configured seatengine_classic row for club 90 ('Bricktown "
            "Comedy Club') had external_id=359 but SE API venue 359 resolves to "
            "'HOUSE OF COMEDY ' (website='http://houseofcomedymd.com'), which "
            'is the auto-discovered club 388. The seatengine_classic scraper '
            'consumes source_url (bricktowncomedyclub.com/events) HTML directly '
            'and does not use external_id at runtime, so clearing the wrong id '
            'is a no-op for scraping but resolves the (platform, external_id) '
            'collision and removes the latent silent-mismap risk that TASK-1951 '
            'hit.'
        ),
    ),
    ClearTarget(
        source_id=333,
        expected_club_id=79,
        expected_external_id='368',
        expected_platform='seatengine',
        expected_scraper_key='seatengine_classic',
        kind='manual_seatengine_classic_stale_id',
        canonical_other_club_id=394,
        canonical_se_name='Campus  JAX Charities',
        canonical_se_website='https://campusjaxcharities.seatengine.com',
        rationale=(
            'Manually-configured seatengine_classic row for club 79 '
            "('Underground Comedy') had external_id=368 but SE API venue 368 "
            "resolves to 'Campus  JAX Charities' "
            "(website='https://campusjaxcharities.seatengine.com'), which is "
            'the auto-discovered club 394. The seatengine_classic scraper '
            'consumes source_url (undergroundcomedydc.com/events) HTML directly '
            'and does not use external_id at runtime, so clearing the wrong id '
            'is a no-op for scraping but resolves the (platform, external_id) '
            'collision and removes the latent silent-mismap risk that TASK-1951 '
            'hit.'
        ),
    ),
    ClearTarget(
        source_id=327,
        expected_club_id=72,
        expected_external_id='389',
        expected_platform='seatengine',
        expected_scraper_key='seatengine_classic',
        kind='manual_seatengine_classic_stale_id',
        canonical_other_club_id=414,
        canonical_se_name='House of Laffs',
        canonical_se_website='https://www.houseoflaffs.com',
        rationale=(
            "Manually-configured seatengine_classic row for club 72 ('The "
            "Comedy Vault') had external_id=389 but SE API venue 389 resolves "
            "to 'House of Laffs' (website='https://www.houseoflaffs.com'), "
            'which is the auto-discovered club 414. The seatengine_classic '
            'scraper consumes source_url (comedyvaultbatavia.com/events) HTML '
            'directly and does not use external_id at runtime, so clearing the '
            'wrong id is a no-op for scraping but resolves the (platform, '
            'external_id) collision and removes the latent silent-mismap risk '
            'that TASK-1951 hit.'
        ),
    ),
    ClearTarget(
        source_id=147,
        expected_club_id=75,
        expected_external_id='392',
        expected_platform='seatengine',
        expected_scraper_key='seatengine_classic',
        kind='manual_seatengine_classic_stale_id',
        canonical_other_club_id=417,
        canonical_se_name='Bridgestone Comedy ',
        canonical_se_website='https://1fcc31bd-2b23-439e-9521-c9ca1dabc300.seatengine.com',
        rationale=(
            "Manually-configured seatengine_classic row for club 75 ('The Dojo "
            "of Comedy') had external_id=392 but SE API venue 392 resolves to "
            "'Bridgestone Comedy ' "
            "(website='https://1fcc31bd-2b23-439e-9521-c9ca1dabc300.seatengine.com'), "
            'which is the auto-discovered club 417. The seatengine_classic '
            'scraper consumes source_url (tiffscomedy.com/events) HTML directly '
            'and does not use external_id at runtime, so clearing the wrong id '
            'is a no-op for scraping but resolves the (platform, external_id) '
            'collision and removes the latent silent-mismap risk that TASK-1951 '
            'hit.'
        ),
    ),
    ClearTarget(
        source_id=139,
        expected_club_id=58,
        expected_external_id='402',
        expected_platform='seatengine',
        expected_scraper_key='seatengine_classic',
        kind='manual_seatengine_classic_stale_id',
        canonical_other_club_id=427,
        canonical_se_name='Sandman Comedy Club ',
        canonical_se_website='https://2b6d2779-d2db-41da-9559-dd8f8b59fa8a.seatengine.com',
        rationale=(
            "Manually-configured seatengine_classic row for club 58 ('The "
            "Comedy Zone - Charlotte') had external_id=402 but SE API venue 402 "
            "resolves to 'Sandman Comedy Club ' "
            "(website='https://2b6d2779-d2db-41da-9559-dd8f8b59fa8a.seatengine.com'), "
            'which is the auto-discovered club 427. The seatengine_classic '
            'scraper consumes source_url (cltcomedyzone.com/events) HTML '
            'directly and does not use external_id at runtime, so clearing the '
            'wrong id is a no-op for scraping but resolves the (platform, '
            'external_id) collision and removes the latent silent-mismap risk '
            'that TASK-1951 hit.'
        ),
    ),
    ClearTarget(
        source_id=326,
        expected_club_id=123,
        expected_external_id='419',
        expected_platform='seatengine',
        expected_scraper_key='seatengine_classic',
        kind='manual_seatengine_classic_stale_id',
        canonical_other_club_id=444,
        canonical_se_name='Boulder Comedy Show',
        canonical_se_website='https://www.bouldercomedyshow.com',
        rationale=(
            "Manually-configured seatengine_classic row for club 123 ('Planet "
            "Of The Tapes') had external_id=419 but SE API venue 419 resolves "
            "to 'Boulder Comedy Show' "
            "(website='https://www.bouldercomedyshow.com'), which is the "
            'auto-discovered club 444. The seatengine_classic scraper consumes '
            'source_url (planetofthetapes.seatengine.com/events) HTML directly '
            'and does not use external_id at runtime, so clearing the wrong id '
            'is a no-op for scraping but resolves the (platform, external_id) '
            'collision and removes the latent silent-mismap risk that TASK-1951 '
            'hit.'
        ),
    ),
    ClearTarget(
        source_id=114,
        expected_club_id=67,
        expected_external_id='425',
        expected_platform='seatengine',
        expected_scraper_key='seatengine_classic',
        kind='manual_seatengine_classic_stale_id',
        canonical_other_club_id=450,
        canonical_se_name='Kes Test 2',
        canonical_se_website='http://kestest.com',
        rationale=(
            "Manually-configured seatengine_classic row for club 67 ('The "
            "Comedy Catch') had external_id=425 but SE API venue 425 resolves "
            "to 'Kes Test 2' (website='http://kestest.com'), which is the "
            'auto-discovered club 450. The seatengine_classic scraper consumes '
            'source_url (thecomedycatch.com/events) HTML directly and does not '
            'use external_id at runtime, so clearing the wrong id is a no-op '
            'for scraping but resolves the (platform, external_id) collision '
            'and removes the latent silent-mismap risk that TASK-1951 hit.'
        ),
    ),
    ClearTarget(
        source_id=98,
        expected_club_id=43,
        expected_external_id='442',
        expected_platform='seatengine',
        expected_scraper_key='seatengine_classic',
        kind='manual_seatengine_classic_stale_id',
        canonical_other_club_id=467,
        canonical_se_name='Rahmein Presents...',
        canonical_se_website='http://Rahmein.seatengine.com',
        rationale=(
            "Manually-configured seatengine_classic row for club 43 ('Brokerage "
            "Comedy Club') had external_id=442 but SE API venue 442 resolves to "
            "'Rahmein Presents...' (website='http://Rahmein.seatengine.com'), "
            'which is the auto-discovered club 467. The seatengine_classic '
            'scraper consumes source_url (brokerage.govs.com/events) HTML '
            'directly and does not use external_id at runtime, so clearing the '
            'wrong id is a no-op for scraping but resolves the (platform, '
            'external_id) collision and removes the latent silent-mismap risk '
            'that TASK-1951 hit.'
        ),
    ),
    ClearTarget(
        source_id=239,
        expected_club_id=42,
        expected_external_id='443',
        expected_platform='seatengine',
        expected_scraper_key='seatengine_classic',
        kind='manual_seatengine_classic_stale_id',
        canonical_other_club_id=468,
        canonical_se_name='The Caravan Fundraisers',
        canonical_se_website='http://caravanfundraisers.seatengine.com',
        rationale=(
            'Manually-configured seatengine_classic row for club 42 ("McGuire\'s '
            'Comedy Club") had external_id=443 but SE API venue 443 resolves to '
            "'The Caravan Fundraisers' "
            "(website='http://caravanfundraisers.seatengine.com'), which is the "
            'auto-discovered club 468. The seatengine_classic scraper consumes '
            'source_url (bohemia.govs.com/events) HTML directly and does not '
            'use external_id at runtime, so clearing the wrong id is a no-op '
            'for scraping but resolves the (platform, external_id) collision '
            'and removes the latent silent-mismap risk that TASK-1951 hit.'
        ),
    ),
    ClearTarget(
        source_id=99,
        expected_club_id=57,
        expected_external_id='448',
        expected_platform='seatengine',
        expected_scraper_key='seatengine_classic',
        kind='manual_seatengine_classic_stale_id',
        canonical_other_club_id=473,
        canonical_se_name='Matt Stanley',
        canonical_se_website='https://b5d22f3e-ce6c-4dc9-b570-f90b0d8ff21a.seatengine.com',
        rationale=(
            "Manually-configured seatengine_classic row for club 57 ('The "
            "Comedy Zone Greensboro') had external_id=448 but SE API venue 448 "
            "resolves to 'Matt Stanley' "
            "(website='https://b5d22f3e-ce6c-4dc9-b570-f90b0d8ff21a.seatengine.com'), "
            'which is the auto-discovered club 473. The seatengine_classic '
            'scraper consumes source_url (thecomedyzone.com/events) HTML '
            'directly and does not use external_id at runtime, so clearing the '
            'wrong id is a no-op for scraping but resolves the (platform, '
            'external_id) collision and removes the latent silent-mismap risk '
            'that TASK-1951 hit.'
        ),
    ),
    ClearTarget(
        source_id=11,
        expected_club_id=59,
        expected_external_id='453',
        expected_platform='seatengine',
        expected_scraper_key='seatengine_classic',
        kind='manual_seatengine_classic_stale_id',
        canonical_other_club_id=478,
        canonical_se_name='Secret Island ',
        canonical_se_website='https://www.secretisland.shannonscorner.com',
        rationale=(
            "Manually-configured seatengine_classic row for club 59 ('Comedy "
            "Zone Jacksonville') had external_id=453 but SE API venue 453 "
            "resolves to 'Secret Island ' "
            "(website='https://www.secretisland.shannonscorner.com'), which is "
            'the auto-discovered club 478. The seatengine_classic scraper '
            'consumes source_url (comedyzone.com/events) HTML directly and does '
            'not use external_id at runtime, so clearing the wrong id is a '
            'no-op for scraping but resolves the (platform, external_id) '
            'collision and removes the latent silent-mismap risk that TASK-1951 '
            'hit.'
        ),
    ),
    ClearTarget(
        source_id=633,
        expected_club_id=116,
        expected_external_id='460',
        expected_platform='seatengine',
        expected_scraper_key='seatengine_classic',
        kind='manual_seatengine_classic_stale_id',
        canonical_other_club_id=484,
        canonical_se_name='Copa Comedy Club',
        canonical_se_website='https://venturaharborcomedyclub.com',
        rationale=(
            "Manually-configured seatengine_classic row for club 116 ('Loonees "
            "Comedy Corner') had external_id=460 but SE API venue 460 resolves "
            "to 'Copa Comedy Club' "
            "(website='https://venturaharborcomedyclub.com'), which is the "
            'auto-discovered club 484. The seatengine_classic scraper consumes '
            'source_url (looneescc.com/events) HTML directly and does not use '
            'external_id at runtime, so clearing the wrong id is a no-op for '
            'scraping but resolves the (platform, external_id) collision and '
            'removes the latent silent-mismap risk that TASK-1951 hit.'
        ),
    ),
    ClearTarget(
        source_id=76,
        expected_club_id=47,
        expected_external_id='466',
        expected_platform='seatengine',
        expected_scraper_key='seatengine_classic',
        kind='manual_seatengine_classic_stale_id',
        canonical_other_club_id=490,
        canonical_se_name='The Cave ',
        canonical_se_website='https://thecavebigbear.com',
        rationale=(
            "Manually-configured seatengine_classic row for club 47 ('Comedy In "
            "Harlem') had external_id=466 but SE API venue 466 resolves to 'The "
            "Cave ' (website='https://thecavebigbear.com'), which is the "
            'auto-discovered club 490. The seatengine_classic scraper consumes '
            'source_url (comedyinharlem.com/events) HTML directly and does not '
            'use external_id at runtime, so clearing the wrong id is a no-op '
            'for scraping but resolves the (platform, external_id) collision '
            'and removes the latent silent-mismap risk that TASK-1951 hit.'
        ),
    ),
    ClearTarget(
        source_id=316,
        expected_club_id=124,
        expected_external_id='483',
        expected_platform='seatengine',
        expected_scraper_key='seatengine_classic',
        kind='manual_seatengine_classic_stale_id',
        canonical_other_club_id=507,
        canonical_se_name='The All New First Fridays ',
        canonical_se_website='https://theallnewfirstfridays.com',
        rationale=(
            "Manually-configured seatengine_classic row for club 124 ('Rooster "
            "T. Feathers Comedy Club') had external_id=483 but SE API venue 483 "
            "resolves to 'The All New First Fridays ' "
            "(website='https://theallnewfirstfridays.com'), which is the "
            'auto-discovered club 507. The seatengine_classic scraper consumes '
            'source_url (rooster-t-feathers.seatengine-sites.com/events) HTML '
            'directly and does not use external_id at runtime, so clearing the '
            'wrong id is a no-op for scraping but resolves the (platform, '
            'external_id) collision and removes the latent silent-mismap risk '
            'that TASK-1951 hit.'
        ),
    ),
    ClearTarget(
        source_id=314,
        expected_club_id=60,
        expected_external_id='504',
        expected_platform='seatengine',
        expected_scraper_key='seatengine_classic',
        kind='manual_seatengine_classic_stale_id',
        canonical_other_club_id=528,
        canonical_se_name='Test Site',
        canonical_se_website='',
        rationale=(
            "Manually-configured seatengine_classic row for club 60 ('The "
            "Comedy Zone - Cherokee') had external_id=504 but SE API venue 504 "
            "resolves to 'Test Site' (website=''), which is the auto-discovered "
            'club 528. The seatengine_classic scraper consumes source_url '
            '(cherokeecomedyzone.com/events) HTML directly and does not use '
            'external_id at runtime, so clearing the wrong id is a no-op for '
            'scraping but resolves the (platform, external_id) collision and '
            'removes the latent silent-mismap risk that TASK-1951 hit.'
        ),
    ),
    ClearTarget(
        source_id=407,
        expected_club_id=134,
        expected_external_id='530',
        expected_platform='seatengine',
        expected_scraper_key='seatengine_classic',
        kind='manual_seatengine_classic_stale_id',
        canonical_other_club_id=550,
        canonical_se_name='Silly Beaver Comedy Club',
        canonical_se_website='https://www.sillybeavercomedy.com',
        rationale=(
            "Manually-configured seatengine_classic row for club 134 ('Helium "
            "Comedy Club - Atlanta') had external_id=530 but SE API venue 530 "
            "resolves to 'Silly Beaver Comedy Club' "
            "(website='https://www.sillybeavercomedy.com'), which is the "
            'auto-discovered club 550. The seatengine_classic scraper consumes '
            'source_url (https://atlanta.heliumcomedy.com/events) HTML directly '
            'and does not use external_id at runtime, so clearing the wrong id '
            'is a no-op for scraping but resolves the (platform, external_id) '
            'collision and removes the latent silent-mismap risk that TASK-1951 '
            'hit.'
        ),
    ),
    ClearTarget(
        source_id=537,
        expected_club_id=92,
        expected_external_id='561',
        expected_platform='seatengine',
        expected_scraper_key='seatengine_classic',
        kind='manual_seatengine_classic_stale_id',
        canonical_other_club_id=581,
        canonical_se_name='Lotus Store ',
        canonical_se_website='',
        rationale=(
            'Manually-configured seatengine_classic row for club 92 ("Bricky\'s '
            'Comedy Club") had external_id=561 but SE API venue 561 resolves to '
            "'Lotus Store ' (website=''), which is the auto-discovered club "
            '581. The seatengine_classic scraper consumes source_url '
            '(brickyscomedy.com/events) HTML directly and does not use '
            'external_id at runtime, so clearing the wrong id is a no-op for '
            'scraping but resolves the (platform, external_id) collision and '
            'removes the latent silent-mismap risk that TASK-1951 hit.'
        ),
    ),
    ClearTarget(
        source_id=86,
        expected_club_id=95,
        expected_external_id='564',
        expected_platform='seatengine',
        expected_scraper_key='seatengine_classic',
        kind='manual_seatengine_classic_stale_id',
        canonical_other_club_id=584,
        canonical_se_name='Cafe Corretto',
        canonical_se_website='https://cafecorretto.romannosejc.com/',
        rationale=(
            "Manually-configured seatengine_classic row for club 95 ('Coastal "
            "Creative') had external_id=564 but SE API venue 564 resolves to "
            "'Cafe Corretto' (website='https://cafecorretto.romannosejc.com/'), "
            'which is the auto-discovered club 584. The seatengine_classic '
            'scraper consumes source_url (coastalcomedynight.com/events) HTML '
            'directly and does not use external_id at runtime, so clearing the '
            'wrong id is a no-op for scraping but resolves the (platform, '
            'external_id) collision and removes the latent silent-mismap risk '
            'that TASK-1951 hit.'
        ),
    ),
    ClearTarget(
        source_id=304,
        expected_club_id=94,
        expected_external_id='588',
        expected_platform='seatengine',
        expected_scraper_key='seatengine_classic',
        kind='both_classic_dead_venue',
        canonical_other_club_id=None,
        canonical_se_name='',
        canonical_se_website='',
        rationale=(
            'SE API venue 588 returns empty name + null website, i.e. the '
            'upstream record is deleted/missing. Both clubs in the collision '
            "pair (94 'Capitol Hill Comedy Bar' and 106 'Emerald City Comedy "
            "Club') use scraper_key=seatengine_classic, which scrapes "
            'source_url HTML directly and does not consume external_id. Both '
            'ids are stale legacy data; clearing on both resolves the collision '
            'and disconnects from the dead upstream venue.'
        ),
    ),
    ClearTarget(
        source_id=14,
        expected_club_id=106,
        expected_external_id='588',
        expected_platform='seatengine',
        expected_scraper_key='seatengine_classic',
        kind='both_classic_dead_venue',
        canonical_other_club_id=None,
        canonical_se_name='',
        canonical_se_website='',
        rationale=(
            'SE API venue 588 returns empty name + null website, i.e. the '
            'upstream record is deleted/missing. Both clubs in the collision '
            "pair (94 'Capitol Hill Comedy Bar' and 106 'Emerald City Comedy "
            "Club') use scraper_key=seatengine_classic, which scrapes "
            'source_url HTML directly and does not consume external_id. Both '
            'ids are stale legacy data; clearing on both resolves the collision '
            'and disconnects from the dead upstream venue.'
        ),
    ),
]


def fetch_current_state(cur, source_ids: list[int]) -> dict[int, dict]:
    cur.execute(
        """
        SELECT id, club_id, platform::text, scraper_key, external_id, enabled, metadata
          FROM scraping_sources
         WHERE id = ANY(%s)
        """,
        (source_ids,),
    )
    cols = [d.name for d in cur.description]
    return {r[0]: dict(zip(cols, r)) for r in cur.fetchall()}


def validate(targets: list[ClearTarget], live: dict[int, dict]) -> list[str]:
    problems: list[str] = []
    for t in targets:
        row = live.get(t.source_id)
        if row is None:
            problems.append(f"source_id={t.source_id}: row not found in scraping_sources")
            continue
        if row["club_id"] != t.expected_club_id:
            problems.append(
                f"source_id={t.source_id}: club_id={row['club_id']} (expected {t.expected_club_id})"
            )
        if row["platform"] != t.expected_platform:
            problems.append(
                f"source_id={t.source_id}: platform={row['platform']!r} (expected {t.expected_platform!r})"
            )
        if row["scraper_key"] != t.expected_scraper_key:
            problems.append(
                f"source_id={t.source_id}: scraper_key={row['scraper_key']!r} (expected {t.expected_scraper_key!r})"
            )
        if str(row["external_id"]) != t.expected_external_id:
            problems.append(
                f"source_id={t.source_id}: external_id={row['external_id']!r} (expected {t.expected_external_id!r})"
            )
    return problems


def needs_write(target: ClearTarget, row: dict) -> bool:
    """True if the row still has a non-null external_id OR the metadata key is missing."""
    if row["external_id"] is not None and row["external_id"] != "":
        return True
    md = row.get("metadata") or {}
    return _METADATA_KEY not in md


def main() -> int:
    ap = argparse.ArgumentParser(
        description="TASK-1956: clear external_id on 28 scraping_sources rows to resolve "
        "27 (platform, external_id) collisions across distinct club_ids.",
    )
    ap.add_argument("--dry-run", action="store_true", help="Validate + plan, but do not write")
    args = ap.parse_args()

    print(f"TASK-1956 disposition: {len(TARGETS)} targets queued")
    print(f"  21x manual_seatengine_classic_stale_id  (Pattern A)")
    print(f"   2x both_classic_dead_venue              (Pattern D, ext=588)")
    print(f"   5x eventbrite_disabled_ghost_dupe       (Pattern EB)")
    print()

    with get_transaction() as conn:
        with conn.cursor() as cur:
            live = fetch_current_state(cur, [t.source_id for t in TARGETS])

            problems = validate(TARGETS, live)
            if problems:
                print(f"REFUSING TO WRITE — {len(problems)} shape mismatch(es):")
                for p in problems:
                    print(f"  {p}")
                return 2

            print("=== BEFORE ===")
            for t in TARGETS:
                row = live[t.source_id]
                print(
                    f"  source_id={t.source_id} club={row['club_id']} "
                    f"platform={row['platform']} scraper_key={row['scraper_key']} "
                    f"external_id={row['external_id']!r} enabled={row['enabled']}"
                )
            print()

            to_write = [(t, live[t.source_id]) for t in TARGETS if needs_write(t, live[t.source_id])]
            skipped = len(TARGETS) - len(to_write)
            print(f"plan: {len(to_write)} write(s), {skipped} skipped (already disposed)")

            if args.dry_run:
                print("DRY RUN — no writes")
                return 0

            for t, row in to_write:
                disposition = {
                    "kind": t.kind,
                    "rationale": t.rationale,
                }
                if t.canonical_other_club_id is not None:
                    disposition["canonical_other_club_id"] = t.canonical_other_club_id
                if t.canonical_se_name is not None:
                    disposition["canonical_se_name"] = t.canonical_se_name
                if t.canonical_se_website is not None:
                    disposition["canonical_se_website"] = t.canonical_se_website
                disposition["cleared_external_id"] = t.expected_external_id

                cur.execute(
                    """
                    UPDATE scraping_sources
                       SET external_id = NULL,
                           metadata = COALESCE(metadata, '{}'::jsonb) || %s::jsonb,
                           updated_at = NOW()
                     WHERE id = %s
                    """,
                    (json.dumps({_METADATA_KEY: disposition}), t.source_id),
                )

            print()
            print("=== AFTER ===")
            after = fetch_current_state(cur, [t.source_id for t in TARGETS])
            for t in TARGETS:
                row = after[t.source_id]
                md = row.get("metadata") or {}
                stamp = bool(md.get(_METADATA_KEY))
                print(
                    f"  source_id={t.source_id} club={row['club_id']} "
                    f"external_id={row['external_id']!r} stamped={stamp}"
                )
            print()
            print(f"WROTE {len(to_write)} row(s); committed on transaction exit.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
