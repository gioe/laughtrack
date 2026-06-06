#!/usr/bin/env python3
"""
Canonicalize cross-host redirects observed on the 2026-06-06 GHA scrape (TASK-2693).

Background
----------
GHA scraper run 27061765104 emitted 60 distinct ``[HttpClient] Cross-host
redirect: ... consider canonicalizing ...`` warnings. The HttpClient followed
each redirect every run and named the canonical target host. Each suggestion
was audited and classified into one of three buckets:

* ``apply``  — update the column to the canonical host. Cosmetic redirects
  (www-flip, http→https, trailing slash) or restoring a venue's own homepage
  in place of a 3rd-party ticketing widget.
* ``skip``   — leave alone. Either (1) the venue genuinely points at a 3rd-party
  ticketing platform we don't want to enshrine as the venue's homepage
  (laff2nite, livenation, punchup.live, tixr, seatengine-sites), (2) the
  stored URL is already canonical and the redirect happens on a different
  URL the scraper synthesizes internally (Comedy Works × 2, Stand-Up NY
  venuepilot tickets endpoint), or (3) the redirect target is an
  expiring-signed tempfile URL we MUST NOT capture (The Setup × 4
  googleusercontent pub-link cache, per task description).
* ``per-event``  — the redirecting URL is a per-show ticket link not stored in
  ``scraping_sources.source_url`` or ``clubs.website`` (Gotham × 2 Showclix
  handoffs to LeapEvents / Zeffy). No DB UPDATE possible.

After this script runs we expect ~15 ``Cross-host redirect`` warnings to
remain on the next scrape — see ``_RESIDUAL`` at the bottom for the catalog.
The followup work to drive that further down (suppress intentional 3rd-party
handoffs in HttpClient, or migrate the venuepilot/comedyworks scrapers to
use canonical hosts at source) is tracked separately.

What this script does
---------------------
1. For each ``scraping_sources`` row in ``_SOURCE_TARGETS``: load by
   ``(club_id, platform, priority)``, verify the current ``source_url``
   matches the pre-update value, and UPDATE to the canonical target, stamping
   ``metadata.task_2693_canonicalize_source_url`` with the before-value, the
   redirect target observed in the run log, and the GHA run id.
2. For each ``clubs`` row in ``_CLUB_TARGETS``: load by ``id``, verify the
   current ``website`` matches the pre-update value, and UPDATE to the
   canonical target. ``clubs`` has no metadata column, so the audit trail
   lives in this script + the [TASK-2693] commit only.
3. Idempotent: rows already at the target value are skipped silently.

Usage
-----
    cd apps/scraper && make run-script SCRIPT=scripts/core/canonicalize_cross_host_redirects_2026_06_06.py ARGS='--dry-run'
    cd apps/scraper && make run-script SCRIPT=scripts/core/canonicalize_cross_host_redirects_2026_06_06.py
"""

import argparse
import json
import sys
from pathlib import Path

_root = next(p for p in Path(__file__).resolve().parents if (p / "pyproject.toml").exists())
for _path in (_root / "src", _root):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from dotenv import load_dotenv

load_dotenv(_root / ".env")

from laughtrack.adapters.db import get_transaction

_METADATA_KEY = "task_2693_canonicalize_source_url"
_GHA_RUN_ID = "27061765104"
_PROBED_AT = "2026-06-06"


# scraping_sources.source_url updates.
# (club_id, platform, priority, before_url, after_url, redirect_observed)
_SOURCE_TARGETS: list[tuple[int, str, int, str, str, str]] = [
    (6, "custom", 0,
     "grislypearstandup.com/calendar",
     "www.grislypearstandup.com/calendar",
     "https://grislypearstandup.com/calendar -> https://www.grislypearstandup.com/calendar"),
    (11, "custom", 0,
     "thetinycupboard.com/calendar",
     "www.thetinycupboard.com/calendar",
     "https://thetinycupboard.com/calendar -> https://www.thetinycupboard.com/calendar"),
    (13, "custom", 0,
     "eastvillecomedy.com/calendar",
     "www.eastvillecomedy.com/calendar",
     "https://eastvillecomedy.com/calendar -> https://www.eastvillecomedy.com/calendar"),
    (48, "custom", 0,
     "tribecacomedyclub.com/calendar",
     "www.tribecacomedyclub.com/calendar",
     "https://tribecacomedyclub.com/calendar -> https://www.tribecacomedyclub.com/calendar"),
    (49, "custom", 0,
     "darkhorsecomedyclub.com/calendar",
     "www.darkhorsecomedyclub.com/calendar",
     "https://darkhorsecomedyclub.com/calendar -> https://www.darkhorsecomedyclub.com/calendar"),
    (50, "custom", 0,
     "midtowncomedyclub.com/calendar",
     "www.midtowncomedyclub.com/calendar",
     "https://midtowncomedyclub.com/calendar -> https://www.midtowncomedyclub.com/calendar"),
    (63, "custom", 0,
     "https://www.tkscomedy.com/dallas-addison-tk-s-comedy-events",
     "https://tkscomedy.com/dallas-addison-tk-s-comedy-events",
     "https://www.tkscomedy.com/dallas-addison-tk-s-comedy-events -> https://tkscomedy.com/dallas-addison-tk-s-comedy-events"),
    (1350, "custom", 0,
     "https://comedycraftbeer.com/calendar",
     "https://www.comedycraftbeer.com/calendar",
     "https://comedycraftbeer.com/calendar -> https://www.comedycraftbeer.com/calendar"),
]


# clubs.website updates.
# (club_id, expected_name, before_url, after_url, redirect_observed, note)
# note is "" for plain cosmetic (www-flip / scheme-upgrade), or a short rationale
# for the ~5 non-cosmetic moves (seatengine-→-venue restorations, rebrand domains).
_CLUB_TARGETS: list[tuple[int, str, str, str, str, str]] = [
    # --- seatengine widget URL -> actual venue homepage (8 venues) ---
    (68, "The Comedy Chateau",
     "https://comedychateau.seatengine.com", "https://www.thecomedychateau.com/",
     "https://comedychateau.seatengine.com -> https://www.thecomedychateau.com/",
     "restore venue homepage (was pointing at seatengine ticketing widget)"),
    (85, "Arlington Drafthouse",
     "https://arlingtondrafthouse.seatengine.com", "https://arlingtondrafthouse.com/",
     "https://arlingtondrafthouse.seatengine.com -> https://arlingtondrafthouse.com/",
     "restore venue homepage (was pointing at seatengine ticketing widget)"),
    (123, "Planet Of The Tapes",
     "https://planetofthetapes.seatengine.com", "https://www.planetofthetapes.biz/",
     "https://planetofthetapes.seatengine.com -> https://www.planetofthetapes.biz/",
     "restore venue homepage (was pointing at seatengine ticketing widget)"),
    (131, "Summit City Comedy Club",
     "https://summitcity.seatengine.com/", "https://www.summitcitycomedy.com/",
     "https://summitcity.seatengine.com -> https://www.summitcitycomedy.com/",
     "restore venue homepage (was pointing at seatengine ticketing widget)"),
    (469, "Let's Comedy",
     "http://letscomedytickets.seatengine.com", "https://www.letscomedyftw.com/",
     "http://letscomedytickets.seatengine.com -> https://www.letscomedyftw.com/",
     "restore venue homepage (was pointing at seatengine ticketing widget)"),
    (480, "Governor's Levittown",
     "http://levittown.seatengine.com", "https://govs.govs.com/",
     "http://levittown.seatengine.com -> https://govs.govs.com/",
     "restore venue-group homepage (was pointing at seatengine ticketing widget)"),
    (481, "The Brokerage in Bellmore",
     "http://bellmore.seatengine.com", "https://brokerage.govs.com/",
     "http://bellmore.seatengine.com -> https://brokerage.govs.com/",
     "restore venue-group homepage (was pointing at seatengine ticketing widget)"),
    (482, "McGuires in Bohemia",
     "http://bohemia.seatengine.com", "https://bohemia.govs.com/",
     "http://bohemia.seatengine.com -> https://bohemia.govs.com/",
     "restore venue-group homepage (was pointing at seatengine ticketing widget)"),

    # --- domain rebrand / move (4 venues) ---
    (81, "Vermont Comedy Club",
     "http://vtcomedy.com", "https://www.vermontcomedyclub.com/",
     "http://vtcomedy.com -> https://www.vermontcomedyclub.com/",
     "venue migrated to full-name domain"),
    (117, "Louisville Comedy Club",
     "https://www.louisvillecomedyclub.com", "https://www.louisvillecomedy.com/",
     "https://www.louisvillecomedyclub.com -> https://www.louisvillecomedy.com/",
     "venue dropped 'club' from domain"),
    (118, "Magoobys Joke House",
     "http://magoobys.com", "https://www.magoobysjokehouse.com/",
     "http://magoobys.com -> https://www.magoobysjokehouse.com/",
     "venue migrated to full-name domain"),
    (638, "Harrisburg Comedy Zone",
     "https://harrisburgcomedyzone.com", "https://boomeranggrill.com/harrisburg-comedy-zone/",
     "https://harrisburgcomedyzone.com -> https://boomeranggrill.com/harrisburg-comedy-zone/",
     "venue folded under parent restaurant group (Boomerang Grill)"),
    (2502, "The Dome by Rutter Mills",
     "https://www.thedomevb.com", "https://www.thedomebyruttermills.com/",
     "https://www.thedomevb.com -> https://www.thedomebyruttermills.com/",
     "venue rebranded host"),

    # --- cosmetic: www-flip / scheme-upgrade / trailing slash (25 venues) ---
    (17, "Grove 34",
     "https://www.grove34.com", "https://grove34.com/",
     "https://www.grove34.com -> https://grove34.com/", ""),
    (63, "TK's",
     "https://www.tkscomedy.com", "https://tkscomedy.com/",
     "https://www.tkscomedy.com -> https://tkscomedy.com/", ""),
    (76, "The Velveeta Room",
     "http://thevelveetaroom.com", "https://www.thevelveetaroom.com/",
     "http://thevelveetaroom.com -> https://www.thevelveetaroom.com/", ""),
    (95, "Coastal Creative",
     "https://coastalcomedynight.com", "https://www.coastalcomedynight.com/",
     "https://coastalcomedynight.com -> https://www.coastalcomedynight.com/", ""),
    (106, "Emerald City Comedy Club",
     "https://emeraldcitycomedy.com", "https://www.emeraldcitycomedy.com/",
     "https://emeraldcitycomedy.com -> https://www.emeraldcitycomedy.com/", ""),
    (113, "Hilarities 4th Street Theatre",
     "https://www.hilarities.com", "https://hilarities.com/",
     "https://www.hilarities.com -> https://hilarities.com/", ""),
    (114, "Laugh Camp Comedy Club",
     "https://www.camp-bar.net", "https://camp-bar.net/",
     "https://www.camp-bar.net -> https://camp-bar.net/", ""),
    (119, "Mic Drop Comedy Plano",
     "https://micdropcomedyplano.com", "https://www.micdropcomedyplano.com/",
     "https://micdropcomedyplano.com -> https://www.micdropcomedyplano.com/", ""),
    (121, "Nate Jackson's Super Funny Comedy Club",
     "https://www.superfunnycomedyclub.com", "https://superfunnycomedyclub.com/",
     "https://www.superfunnycomedyclub.com -> https://superfunnycomedyclub.com/", ""),
    (125, "Sticks and Stones Comedy Club",
     "http://sticksandstonescomedyclub.com/", "https://www.sticksandstonescomedyclub.com/",
     "http://sticksandstonescomedyclub.com -> https://www.sticksandstonescomedyclub.com/", ""),
    (127, "Snappers Palm Harbor",
     "https://snappersgrill.com", "https://www.snappersgrill.com/",
     "https://snappersgrill.com -> https://www.snappersgrill.com/", ""),
    (157, "Philly Improv Theater",
     "https://www.phillyimprovtheater.com", "https://phillyimprovtheater.com/",
     "https://www.phillyimprovtheater.com -> https://phillyimprovtheater.com/", ""),
    (288, "Dead Crow Comedy",
     "http://deadcrowcomedy.com", "https://www.deadcrowcomedy.com/",
     "http://deadcrowcomedy.com -> https://www.deadcrowcomedy.com/", ""),
    (409, "Hotbed - DC Comedy Club",
     "https://hotbedcomedydc.com", "https://www.hotbedcomedydc.com/",
     "https://hotbedcomedydc.com -> https://www.hotbedcomedydc.com/", ""),
    (447, "Alameda Comedy",
     "http://alamedacomedy.com", "https://www.alamedacomedy.com/",
     "http://alamedacomedy.com -> https://www.alamedacomedy.com/", ""),
    (519, "Juke Box Comedy Club",
     "https://jukeboxcomedy.com", "https://www.jukeboxcomedy.com/",
     "https://jukeboxcomedy.com -> https://www.jukeboxcomedy.com/", ""),
    (524, "Give a Hoot Comedy Club",
     "https://giveahootcomedy.com", "https://www.giveahootcomedy.com/",
     "https://giveahootcomedy.com -> https://www.giveahootcomedy.com/", ""),
    (542, "The Alley Stage",
     "https://alleystage.org", "https://www.alleystage.org/",
     "https://alleystage.org -> https://www.alleystage.org/", ""),
    (565, "Poe's Magic Theatre",
     "https://poesmagic.com/", "https://www.poesmagic.com/",
     "https://poesmagic.com -> https://www.poesmagic.com/", ""),
    (620, "Comedy Shows Near Me",
     "https://comedyshowsnear.me", "https://www.comedyshowsnear.me/",
     "https://comedyshowsnear.me -> https://www.comedyshowsnear.me/", ""),
    (634, "Mic Drop Comedy Detroit",
     "http://micdropcomedyDetroit.com", "https://www.micdropcomedydetroit.com/",
     "http://micdropcomedyDetroit.com -> https://www.micdropcomedydetroit.com/", ""),
    (796, "The Backline",
     "https://www.backlinecomedy.com", "https://backlinecomedy.com/",
     "https://www.backlinecomedy.com -> https://backlinecomedy.com/", ""),
    (817, "Laughing Skull",
     "https://www.laughingskulllounge.com", "https://laughingskulllounge.com/",
     "https://www.laughingskulllounge.com -> https://laughingskulllounge.com/", ""),
    (1350, "Brew HaHa Comedy at River",
     "https://comedycraftbeer.com", "https://www.comedycraftbeer.com/",
     "https://comedycraftbeer.com -> https://www.comedycraftbeer.com/", ""),
]


# Catalog of suggestions intentionally NOT applied. Used as documentation only.
# Each entry: (kind, scope, club_id, before, after, reason).
_SKIPS: list[tuple[str, str, int, str, str, str]] = [
    # --- scraping_sources.source_url skips ---
    ("setup-signed-url", "scraping_sources", 195,
     "docs.google.com/spreadsheets/d/e/.../pub?gid=495747966&...",
     "doc-0k-94-sheets.googleusercontent.com/pub/.../...",
     "SKIP per task description: Google Sheets pub-link signed tempfile target. The host token is short-lived and would break the scrape the moment the signed URL expires."),
    ("setup-signed-url", "scraping_sources", 658,
     "docs.google.com/spreadsheets/d/e/.../pub?gid=783484107&...",
     "doc-0k-94-sheets.googleusercontent.com/pub/.../...",
     "SKIP per task description: Google Sheets signed tempfile (see club_id=195)."),
    ("setup-signed-url", "scraping_sources", 659,
     "docs.google.com/spreadsheets/d/e/.../pub?gid=38419123&...",
     "doc-0k-94-sheets.googleusercontent.com/pub/.../...",
     "SKIP per task description: Google Sheets signed tempfile (see club_id=195)."),
    ("setup-signed-url", "scraping_sources", 661,
     "docs.google.com/spreadsheets/d/e/.../pub?gid=1575830989&...",
     "doc-0k-94-sheets.googleusercontent.com/pub/.../...",
     "SKIP per task description: Google Sheets signed tempfile (see club_id=195)."),
    ("not-the-stored-url", "scraping_sources", 25,
     "https://t.venuepilot.com/e/let-s-go-mental-open-mic-...",
     "https://tickets.venuepilot.com/e/let-s-go-mental-open-mic-...",
     "SKIP: source_url is 'venuepilot.co/graphql' (the API endpoint, no redirect). The 't.venuepilot.com' URL is per-event metadata from the GraphQL response, synthesized in the standup_ny scraper. DB UPDATE can't fix this; tracked separately."),
    ("not-the-stored-url", "scraping_sources", 1036,
     "https://www.comedyworks.com/events?downtown=1",
     "https://comedyworks.com/events?downtown=1",
     "SKIP: source_url is 'https://comedyworks.com/shows/calendar' (already canonical). The redirecting URL is built from _BASE_URL='https://www.comedyworks.com' in comedy_works_common/scraper.py. DB UPDATE can't fix this; tracked separately."),
    ("not-the-stored-url", "scraping_sources", 1352,
     "https://www.comedyworks.com/events?south=1",
     "https://comedyworks.com/events?south=1",
     "SKIP: same root cause as club_id=1036 — _BASE_URL in comedy_works_common/scraper.py is www-prefixed. DB UPDATE can't fix this; tracked separately."),
    ("per-event-not-stored", "scraping_sources", 18,
     "https://www.showclix.com/event/the-gotham-all-stars2526",
     "https://events.leapevents.com/event/the-gotham-all-stars2526",
     "SKIP: per-show ticket URL from Gotham's S3 events feed; not stored in scraping_sources. Reflects Showclix → LeapEvents corporate rebrand for that ticket."),
    ("per-event-not-stored", "scraping_sources", 18,
     "https://www.showclix.com/event/ms-stand-up-4th-annual-comedy-benefit",
     "https://www.zeffy.com/en-US/ticketing/the-vartanian-vision-...",
     "SKIP: per-show ticket URL from Gotham's S3 events feed; this specific event sells via Zeffy. Not a Gotham platform-wide canonicalization."),

    # --- clubs.website skips: venue -> 3rd-party ticketing platform ---
    ("venue-to-3rd-party-tix", "clubs", 74,
     "http://www.elpasocomicstrip.com", "https://www.laff2nite.com/",
     "SKIP per task description: 3rd-party-ticketing handoff. laff2nite is the venue's white-label seatengine site; we keep the elpasocomicstrip identity on clubs.website."),
    ("venue-to-3rd-party-tix", "clubs", 100,
     "https://comedyoffbroadway.com", "https://www-comedyoffbroadway-com.seatengine.com/",
     "SKIP: venue homepage SSO-redirects to seatengine widget. Keep venue domain as canonical."),
    ("venue-to-3rd-party-tix", "clubs", 171,
     "https://www.laughfactory.com/covina", "https://www.tixr.com/groups/laughfactorycovina",
     "SKIP: venue page redirects to Tixr ticketing group; keep laughfactory.com/covina as the venue identity."),
    ("venue-to-3rd-party-tix", "clubs", 383,
     "https://southcoastcomedy.com", "https://newportcomedyseries.punchup.live/",
     "SKIP per task description: venue redirects to Punchup ticketing; keep the southcoastcomedy.com venue identity."),
    ("venue-to-3rd-party-tix", "clubs", 613,
     "https://www.yardbirdcomedy.com/", "https://yardbird-comedy.seatengine-sites.com/",
     "SKIP: venue redirects to seatengine-sites white-label; keep yardbirdcomedy.com as the venue identity."),
    ("venue-to-3rd-party-tix", "clubs", 2510,
     "https://www.oldnationalcentre.com", "https://www.livenation.com/venue/KovZpZAEAkvA",
     "SKIP per task description: venue redirects to LiveNation; keep the venue's own oldnationalcentre.com identity."),
]


def _load_metadata(raw) -> dict:
    if isinstance(raw, str):
        return json.loads(raw)
    if raw is None:
        return {}
    return dict(raw)


def _apply_source_targets(cur, dry_run: bool) -> tuple[int, int, list[str]]:
    updated = 0
    skipped_idempotent = 0
    problems: list[str] = []

    for club_id, platform, priority, before_url, after_url, redirect_obs in _SOURCE_TARGETS:
        cur.execute(
            """
            SELECT id, source_url, metadata
            FROM scraping_sources
            WHERE club_id = %s AND platform::text = %s AND priority = %s
            """,
            (club_id, platform, priority),
        )
        row = cur.fetchone()
        if row is None:
            problems.append(
                f"scraping_sources: no row for club_id={club_id}, "
                f"platform={platform}, priority={priority}"
            )
            continue
        ssid, source_url, raw_meta = row
        if source_url == after_url:
            skipped_idempotent += 1
            print(f"  ss   ssid={ssid:>4} cid={club_id:>4} SKIP (already canonical): {source_url}")
            continue
        if source_url != before_url:
            problems.append(
                f"scraping_sources ssid={ssid} cid={club_id}: source_url={source_url!r}, "
                f"expected before-value {before_url!r}"
            )
            continue

        if dry_run:
            print(f"  ss   ssid={ssid:>4} cid={club_id:>4} {before_url!r} -> {after_url!r}")
            continue

        metadata = _load_metadata(raw_meta)
        metadata[_METADATA_KEY] = {
            "previous_source_url": before_url,
            "redirect_observed": redirect_obs,
            "probed_at": _PROBED_AT,
            "gha_run_id": _GHA_RUN_ID,
        }
        cur.execute(
            """
            UPDATE scraping_sources
            SET source_url = %s,
                metadata = %s,
                updated_at = NOW()
            WHERE id = %s
            """,
            (after_url, json.dumps(metadata, sort_keys=True), ssid),
        )
        updated += 1
        print(f"  ss   ssid={ssid:>4} cid={club_id:>4} {before_url!r} -> {after_url!r}")

    return updated, skipped_idempotent, problems


def _apply_club_targets(cur, dry_run: bool) -> tuple[int, int, list[str]]:
    updated = 0
    skipped_idempotent = 0
    problems: list[str] = []

    for club_id, expected_name, before_url, after_url, redirect_obs, note in _CLUB_TARGETS:
        cur.execute("SELECT name, website FROM clubs WHERE id = %s", (club_id,))
        row = cur.fetchone()
        if row is None:
            problems.append(f"clubs cid={club_id}: row not found")
            continue
        name, website = row
        if name != expected_name:
            problems.append(
                f"clubs cid={club_id}: name={name!r}, expected {expected_name!r}"
            )
            continue
        if website == after_url:
            skipped_idempotent += 1
            print(f"  club cid={club_id:>4} SKIP (already canonical): {website}")
            continue
        if website != before_url:
            problems.append(
                f"clubs cid={club_id}: website={website!r}, expected before-value {before_url!r}"
            )
            continue

        suffix = f"  [{note}]" if note else ""
        if dry_run:
            print(f"  club cid={club_id:>4} {before_url!r} -> {after_url!r}{suffix}")
            continue

        cur.execute(
            "UPDATE clubs SET website = %s WHERE id = %s",
            (after_url, club_id),
        )
        updated += 1
        print(f"  club cid={club_id:>4} {before_url!r} -> {after_url!r}{suffix}")

    return updated, skipped_idempotent, problems


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Canonicalize cross-host redirects from GHA run 27061765104 (TASK-2693)."
    )
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without writing")
    args = parser.parse_args()

    print(f"=== TASK-2693: canonicalize cross-host redirects (GHA run {_GHA_RUN_ID}) ===")
    print(f"scraping_sources targets: {len(_SOURCE_TARGETS)}")
    print(f"clubs targets:            {len(_CLUB_TARGETS)}")
    print(f"intentional skips:        {len(_SKIPS)} (see _SKIPS in source)")
    print()

    with get_transaction() as conn:
        with conn.cursor() as cur:
            print("--- scraping_sources.source_url ---")
            ss_updated, ss_skipped, ss_problems = _apply_source_targets(cur, args.dry_run)
            print()
            print("--- clubs.website ---")
            c_updated, c_skipped, c_problems = _apply_club_targets(cur, args.dry_run)
            print()

            problems = ss_problems + c_problems
            if problems:
                print("ABORT: shape mismatch / unexpected state:", file=sys.stderr)
                for p in problems:
                    print(f"  {p}", file=sys.stderr)
                return 1

            if args.dry_run:
                print("--dry-run: no DB write performed.")
                return 0

            print(f"Updated: scraping_sources={ss_updated}, clubs={c_updated}")
            print(f"Skipped (already canonical): scraping_sources={ss_skipped}, clubs={c_skipped}")
            print(f"Audit-only skips documented in _SKIPS: {len(_SKIPS)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
