#!/usr/bin/env python3
"""
Apply per-club dispositions for the 9 Eventbrite organizer-mode REROUTED
clubs surfaced by the TASK-1916 audit, after TASK-1891 flipped /o/ URLs
to organizer-mode routing on 2026-05-05.

Background
----------
TASK-1916 (apps/scraper/docs/audits/task-1916-eventbrite-organizer-urls.md)
classified 22 /o/ scraping_sources by re-grouping their organizer feeds on
the venue NAME used by UPSERT_CLUB_BY_EVENTBRITE_VENUE's ON CONFLICT key.
9 clubs were tagged REROUTED (events_stay=0 / events_reroute=N) — every
event in the organizer feed maps to a venue.name that does NOT equal the
existing club name, so the post-flip nightly creates greenfield per-venue
clubs and the original stops receiving new shows. The 10th REROUTED case
(club 809) is covered by TASK-1914.

Re-probed each organizer feed at 2026-05-05 ~15:55 UTC and confirmed the
audit numbers. The probe also extracted the canonical venue.id distribution
for each feed, which dictates whether single-venue mode is viable:

  Single canonical venue.id (clean repoint candidates):
    160 LF Hollywood       → venue.id=28808914  (162 events, 1 group)
    184 Comedy Bar Chicago → venue.id=35896069  (105 events, 1 group)
    169 LF Long Beach      → venue.id=41248441  (89 events,  1 group)
    170 LF San Diego       → venue.id=60930661  (50 events,  1 group)
    1038 Counter Weight    → venue.id=90437249  (1 event,    1 group)

  Fragmented venue.id (single-venue mode NOT viable — Eventbrite emits
  fresh venue.id per occurrence; /venues/{id}/events would silently drop
  events at the OTHER venue.ids):
    199 Riot Comedy Club  → 43 distinct venue.ids under 'Rudyard's' name +
                            25 distinct under 'The Riot Comedy Club upstairs
                            at Rudyard's' (2 names, same physical venue)
    647 Backdoor Comedy   → 3 distinct venue.ids under 'Backdoor Comedy'
    1052 Comedy At Comet  → genuinely multi-venue: Bombs Away brand running
                            at The Comet (3 ids), Mellotone Beer Project (4),
                            'Bombs Away! Comedy at the Comet' (16 events
                            across 16 ids), 'Bombs Away Comedy' (6 / 1 id)

  Misattributed (organizer URL does not represent the original venue):
    1136 Lake Theater & Cafe → 1 event under 'The Fonda Theatre' in
                               Los Angeles, CA (existing club is in Lake
                               Oswego, OR — wrong venue, wrong state)

Disposition matrix
------------------
1. REPOINT (5 clubs): clubs 160, 184, 169, 170, 1038
   - UPDATE the original /o/ scraping_source to venue-mode: external_id =
     <canonical venue.id>, source_url = 'https://www.eventbrite.com'
     (matches UPSERT_CLUB_BY_EVENTBRITE_VENUE's bare-URL convention; the
     scraper checks `'/o/' in source_url` to dispatch organizer mode, so
     anything without /o/ activates single-venue mode and the API call
     uses external_id as the venue_id parameter).
   - HIDE the vestigial new per-venue club created by 2026-05-05 nightly
     (visible=false) and DISABLE its auto-created scraping_source
     (enabled=false). After the repoint, organizer-mode no longer fires
     for this venue, so UPSERT_CLUB_BY_EVENTBRITE_VENUE's ON CONFLICT
     re-assertion (which unconditionally sets enabled=TRUE on the
     auto-created source) won't run, and the disable sticks.

2. HIDE-ORIGINAL (3 clubs): clubs 199, 647, 1052
   - LEAVE the /o/ scraping_source enabled. Organizer-mode keeps running
     and produces fresh shows on the per-venue clubs nightly. These cases
     can't be cleanly repointed (fragmented venue.id or genuinely
     multi-venue), so the per-venue clubs ARE the canonical destinations.
   - HIDE the original (visible=false) so it doesn't surface as a
     duplicate empty venue alongside the per-venue clubs.

3. DISABLE-SOURCE (1 club): club 1136 (Lake Theater & Cafe)
   - DISABLE scraping_source 395 (enabled=false). Original is already
     visible=false (hidden 2026-05-02 via separate migration). The /o/
     URL is wholly misattributed — points at 'The Fonda Theatre' in Los
     Angeles, not the OR venue — so even organizer-mode would create the
     wrong per-venue clubs. Disabling stops the bleed.

Per-disposition rationale rejected alternatives:
- 199, 647 'rename to canonical venue.name': the audit offered "rename
  existing club to <new name>" as an alternative to repoint. Rejected
  here because the dedupe/upsert path STILL fragments by venue.id
  upstream of the name match — renaming only relocates the split.
  TASK-1919's analogous rejection for club 654 'Big Couch' establishes
  the precedent.
- 1052 'split into per-venue clubs': effectively what the nightly
  already did (created 2289 The Comet, 2290 Bombs Away! Comedy at the
  Comet, 2291 Bombs Away Comedy, 2292 Mellotone Beer Project).
  Hiding the brand club preserves that split as the canonical state.
- 199, 647, 1052 'disable /o/ source': would freeze the per-venue clubs'
  show inventory. Their auto-created scraping_sources point at single
  venue.ids in single-venue mode; for fragmenting feeds (199, 647) that
  would only catch ~1 of N events. Keeping organizer-mode enabled
  preserves full coverage via the (name, city, state) dedupe key.

Post-action verification (criterion 6312) is handed off to TASK-1932
since the next nightly is 2026-05-06 06:00 UTC, ~14h after this commit.
The follow-up will re-execute the TASK-1916 probe and confirm:
  - Repoint clubs (160, 184, 169, 170, 1038): show counts on the original
    refresh (last_scraped_date >= 2026-05-06) at the predicted volumes.
  - Hide-original clubs (199, 647, 1052): per-venue clubs receive new
    shows; originals stay at zero new shows.
  - Disabled source (1136): no scrape activity.

What this script does
---------------------
1. Validates expected shape of every targeted clubs / scraping_sources row
   (refuses to write on any mismatch).
2. Per repoint target: UPDATE scraping_sources external_id + source_url +
   updated_at; UPDATE the vestigial new club visible=false; UPDATE its
   auto-created scraping_source enabled=false.
3. Per hide-original target: UPDATE clubs visible=false on the original;
   leave /o/ source enabled.
4. Disable scraping_sources.id=395 for club 1136.
5. Annotates each modified scraping_source's metadata with task_1918_*
   keys carrying the disposition rationale (matches TASK-1925's
   metadata-annotation pattern).

Idempotent: only writes when the live state differs from the target
state. Safe to re-run.

Usage
-----
    cd apps/scraper && make run-script SCRIPT=scripts/core/disposition_eventbrite_organizer_rerouted_clubs.py ARGS='--dry-run'
    cd apps/scraper && make run-script SCRIPT=scripts/core/disposition_eventbrite_organizer_rerouted_clubs.py
"""

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path

_root = next(p for p in Path(__file__).resolve().parents if (p / "pyproject.toml").exists())
for _path in (_root / "src", _root):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from dotenv import load_dotenv

load_dotenv(_root / ".env")

from laughtrack.adapters.db import get_transaction


_VENUE_MODE_SOURCE_URL = "https://www.eventbrite.com"
_METADATA_KEY = "task_1918_disposition"


@dataclass(frozen=True)
class RepointTarget:
    """Repoint an /o/ organizer source to a single canonical Eventbrite venue.id."""
    original_club_id: int
    original_club_name: str
    original_source_id: int
    original_external_id: str          # the organizer.id (current value)
    new_external_id: str               # the canonical venue.id
    new_per_venue_club_id: int
    new_per_venue_club_name: str
    new_per_venue_source_id: int


@dataclass(frozen=True)
class HideOriginalTarget:
    """Hide the original club and leave /o/ source enabled (organizer-mode populates per-venue clubs)."""
    original_club_id: int
    original_club_name: str
    original_source_id: int            # left enabled — recorded for shape check / metadata only
    rationale: str


@dataclass(frozen=True)
class DisableSourceTarget:
    """Disable the misattributed scraping_source for a hidden original."""
    original_club_id: int
    original_club_name: str
    original_source_id: int


_REPOINT_TARGETS: list[RepointTarget] = [
    RepointTarget(160, "Laugh Factory Hollywood",   499, "18525142576", "28808914",
                  2273, "Laugh Factory - Hollywood",            1272),
    RepointTarget(184, "The Comedy Bar Chicago",    161, "17584944942", "35896069",
                  2279, "The Comedy Bar - Chicago Main Stage",  1278),
    RepointTarget(169, "Laugh Factory Long Beach",  130, "27817260251", "41248441",
                  2276, "Long Beach Laugh Factory",             1275),
    RepointTarget(170, "Laugh Factory San Diego",   365, "18637206571", "60930661",
                  2277, "Laugh Factory",                        1276),
    RepointTarget(1038, "Counter Weight Brewing",   337, "31188770769", "90437249",
                  2288, "Counter Weight Brewing Company",       1287),
]

_HIDE_ORIGINAL_TARGETS: list[HideOriginalTarget] = [
    HideOriginalTarget(
        199, "The Riot Comedy Club", 151,
        "Fragmented venue.id (43 ids 'Rudyard's' + 25 ids 'The Riot Comedy "
        "Club upstairs at Rudyard's') makes single-venue repoint non-viable. "
        "Per-venue clubs 2280/2281 take over as canonical via organizer-mode "
        "(name, city, state) dedupe.",
    ),
    HideOriginalTarget(
        647, "Backdoor Comedy Club", 238,
        "Fragmented venue.id (3 ids under 'Backdoor Comedy' name) makes "
        "single-venue repoint non-viable. Per-venue club 2285 takes over.",
    ),
    HideOriginalTarget(
        1052, "Comedy At The Comet", 576,
        "Genuinely multi-venue brand (Bombs Away running at The Comet AND "
        "Mellotone Beer Project). Per-venue clubs 2289-2292 already represent "
        "the actual physical venues correctly.",
    ),
]

_DISABLE_SOURCE_TARGETS: list[DisableSourceTarget] = [
    DisableSourceTarget(1136, "Lake Theater & Cafe", 395),
]


def _load_metadata(raw) -> dict:
    if isinstance(raw, str):
        return json.loads(raw)
    if raw is None:
        return {}
    return dict(raw)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Apply per-club dispositions for the 9 Eventbrite organizer-mode "
            "REROUTED clubs surfaced by TASK-1916. See module docstring for the "
            "full disposition matrix and rationale."
        )
    )
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without writing")
    args = parser.parse_args()

    repoint_club_ids = [t.original_club_id for t in _REPOINT_TARGETS] + [t.new_per_venue_club_id for t in _REPOINT_TARGETS]
    hide_club_ids = [t.original_club_id for t in _HIDE_ORIGINAL_TARGETS]
    disable_club_ids = [t.original_club_id for t in _DISABLE_SOURCE_TARGETS]
    all_club_ids = repoint_club_ids + hide_club_ids + disable_club_ids

    repoint_source_ids = [t.original_source_id for t in _REPOINT_TARGETS] + [t.new_per_venue_source_id for t in _REPOINT_TARGETS]
    hide_source_ids = [t.original_source_id for t in _HIDE_ORIGINAL_TARGETS]
    disable_source_ids = [t.original_source_id for t in _DISABLE_SOURCE_TARGETS]
    all_source_ids = repoint_source_ids + hide_source_ids + disable_source_ids

    with get_transaction() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, name, visible FROM clubs WHERE id = ANY(%s)",
                (all_club_ids,),
            )
            clubs = {r[0]: r for r in cur.fetchall()}

            cur.execute(
                """
                SELECT id, club_id, platform, scraper_key, eventbrite_id, source_url,
                       enabled, priority, metadata
                FROM scraping_sources WHERE id = ANY(%s)
                """,
                (all_source_ids,),
            )
            sources = {r[0]: r for r in cur.fetchall()}

        problems: list[str] = []

        # --- shape validation: REPOINT targets ---
        for t in _REPOINT_TARGETS:
            if t.original_club_id not in clubs:
                problems.append(f"REPOINT: clubs.id={t.original_club_id} missing")
            else:
                _, name, _ = clubs[t.original_club_id]
                if name != t.original_club_name:
                    problems.append(
                        f"REPOINT: clubs.id={t.original_club_id} name={name!r} "
                        f"(expected {t.original_club_name!r})"
                    )

            if t.new_per_venue_club_id not in clubs:
                problems.append(f"REPOINT: vestigial clubs.id={t.new_per_venue_club_id} missing")
            else:
                _, name, _ = clubs[t.new_per_venue_club_id]
                if name != t.new_per_venue_club_name:
                    problems.append(
                        f"REPOINT: vestigial clubs.id={t.new_per_venue_club_id} name={name!r} "
                        f"(expected {t.new_per_venue_club_name!r})"
                    )

            src = sources.get(t.original_source_id)
            if src is None:
                problems.append(f"REPOINT: scraping_sources.id={t.original_source_id} missing")
            else:
                _, src_club, platform, _, ext_id, src_url, enabled, _, _ = src
                if src_club != t.original_club_id:
                    problems.append(
                        f"REPOINT: ss.id={t.original_source_id} club_id={src_club} "
                        f"(expected {t.original_club_id})"
                    )
                if platform != "eventbrite":
                    problems.append(
                        f"REPOINT: ss.id={t.original_source_id} platform={platform!r} "
                        f"(expected 'eventbrite')"
                    )
                # eventbrite_id, source_url, and enabled are all rewritten by the same
                # UPDATE in a single transaction, so live state must reflect either the
                # full pre-write tuple (organizer.id + /o/ URL) or the full post-write
                # tuple (venue.id + bare eventbrite.com URL). enabled stays True in both.
                # A partial state is impossible today but flagging it here keeps the
                # "refuse to write on any mismatch" contract honest if the UPDATE is
                # ever split across calls.
                is_pre = ext_id == t.original_external_id and "/o/" in (src_url or "")
                is_post = ext_id == t.new_external_id and src_url == _VENUE_MODE_SOURCE_URL
                if not (is_pre or is_post):
                    problems.append(
                        f"REPOINT: ss.id={t.original_source_id} (ext_id, source_url) is in a partial "
                        f"state: ext_id={ext_id!r} source_url={src_url!r}. Expected either pre-write "
                        f"(ext_id={t.original_external_id!r}, source_url contains '/o/') or post-write "
                        f"(ext_id={t.new_external_id!r}, source_url={_VENUE_MODE_SOURCE_URL!r})."
                    )
                if not enabled:
                    problems.append(
                        f"REPOINT: ss.id={t.original_source_id} enabled={enabled} "
                        f"(expected True — disposition leaves source enabled in both pre- and post-write states)"
                    )

            new_src = sources.get(t.new_per_venue_source_id)
            if new_src is None:
                problems.append(f"REPOINT: vestigial ss.id={t.new_per_venue_source_id} missing")
            else:
                _, src_club, platform, _, ext_id, _, _, _, _ = new_src
                if src_club != t.new_per_venue_club_id:
                    problems.append(
                        f"REPOINT: vestigial ss.id={t.new_per_venue_source_id} club_id={src_club} "
                        f"(expected {t.new_per_venue_club_id})"
                    )
                if platform != "eventbrite":
                    problems.append(
                        f"REPOINT: vestigial ss.id={t.new_per_venue_source_id} platform={platform!r} "
                        f"(expected 'eventbrite')"
                    )
                if ext_id != t.new_external_id:
                    problems.append(
                        f"REPOINT: vestigial ss.id={t.new_per_venue_source_id} external_id={ext_id!r} "
                        f"(expected {t.new_external_id!r})"
                    )

        # --- shape validation: HIDE-ORIGINAL targets ---
        for t in _HIDE_ORIGINAL_TARGETS:
            if t.original_club_id not in clubs:
                problems.append(f"HIDE: clubs.id={t.original_club_id} missing")
            else:
                _, name, _ = clubs[t.original_club_id]
                if name != t.original_club_name:
                    problems.append(
                        f"HIDE: clubs.id={t.original_club_id} name={name!r} "
                        f"(expected {t.original_club_name!r})"
                    )
            src = sources.get(t.original_source_id)
            if src is None:
                problems.append(f"HIDE: ss.id={t.original_source_id} missing")
            else:
                _, src_club, platform, _, _, src_url, _, _, _ = src
                if src_club != t.original_club_id:
                    problems.append(
                        f"HIDE: ss.id={t.original_source_id} club_id={src_club} "
                        f"(expected {t.original_club_id})"
                    )
                if "/o/" not in (src_url or ""):
                    problems.append(
                        f"HIDE: ss.id={t.original_source_id} source_url={src_url!r} "
                        f"(expected /o/ organizer URL — script assumes organizer-mode "
                        f"keeps running for this disposition)"
                    )

        # --- shape validation: DISABLE-SOURCE targets ---
        for t in _DISABLE_SOURCE_TARGETS:
            if t.original_club_id not in clubs:
                problems.append(f"DISABLE: clubs.id={t.original_club_id} missing")
            else:
                _, name, _ = clubs[t.original_club_id]
                if name != t.original_club_name:
                    problems.append(
                        f"DISABLE: clubs.id={t.original_club_id} name={name!r} "
                        f"(expected {t.original_club_name!r})"
                    )
            src = sources.get(t.original_source_id)
            if src is None:
                problems.append(f"DISABLE: ss.id={t.original_source_id} missing")
            else:
                _, src_club, platform, _, _, src_url, _, _, _ = src
                if src_club != t.original_club_id:
                    problems.append(
                        f"DISABLE: ss.id={t.original_source_id} club_id={src_club} "
                        f"(expected {t.original_club_id})"
                    )
                if platform != "eventbrite":
                    problems.append(
                        f"DISABLE: ss.id={t.original_source_id} platform={platform!r} "
                        f"(expected 'eventbrite')"
                    )
                if "/o/" not in (src_url or ""):
                    problems.append(
                        f"DISABLE: ss.id={t.original_source_id} source_url={src_url!r} "
                        f"(expected /o/ organizer URL — disable target is the misattributed "
                        f"organizer feed)"
                    )

        if problems:
            print("ABORT: shape mismatch — refusing to write:", file=sys.stderr)
            for p in problems:
                print(f"  {p}", file=sys.stderr)
            return 1

        # --- print BEFORE state and compute writes ---
        print("=== BEFORE ===")
        for t in _REPOINT_TARGETS:
            cid, cname, cvis = clubs[t.original_club_id]
            sid, _, _, _, ext, src_url, enabled, _, meta = sources[t.original_source_id]
            ncid, ncname, ncvis = clubs[t.new_per_venue_club_id]
            nsid, _, _, _, vest_ext, _, nenabled, _, nmeta = sources[t.new_per_venue_source_id]
            print(
                f"  REPOINT club={cid} {cname!r} visible={cvis}"
                f" | ss={sid} ext={ext!r} url={src_url!r} enabled={enabled}"
                f" | vestigial club={ncid} {ncname!r} visible={ncvis}"
                f" | vestigial ss={nsid} ext={vest_ext!r} enabled={nenabled}"
            )
        for t in _HIDE_ORIGINAL_TARGETS:
            cid, cname, cvis = clubs[t.original_club_id]
            sid, _, _, _, ext, src_url, enabled, _, _ = sources[t.original_source_id]
            print(
                f"  HIDE   club={cid} {cname!r} visible={cvis}"
                f" | ss={sid} ext={ext!r} url={src_url!r} enabled={enabled}"
            )
        for t in _DISABLE_SOURCE_TARGETS:
            cid, cname, cvis = clubs[t.original_club_id]
            sid, _, _, _, ext, src_url, enabled, _, _ = sources[t.original_source_id]
            print(
                f"  DISABLE club={cid} {cname!r} visible={cvis}"
                f" | ss={sid} ext={ext!r} url={src_url!r} enabled={enabled}"
            )

        writes_planned = 0

        if args.dry_run:
            print("\n--dry-run: planning writes, no DB changes...")

        # --- apply writes ---
        with conn.cursor() as cur:
            # REPOINT
            for t in _REPOINT_TARGETS:
                src = sources[t.original_source_id]
                _, _, _, _, ext_id, src_url, enabled, _, meta_raw = src
                meta = _load_metadata(meta_raw)
                target_url = _VENUE_MODE_SOURCE_URL

                needs_repoint = (ext_id != t.new_external_id) or (src_url != target_url) or (not enabled)
                needs_meta = _METADATA_KEY not in meta
                if needs_repoint or needs_meta:
                    new_meta = dict(meta)
                    new_meta[_METADATA_KEY] = {
                        "kind": "repoint",
                        "from_organizer_id": t.original_external_id,
                        "to_venue_id": t.new_external_id,
                        "rationale": (
                            "Audit (TASK-1916) classified as REROUTED — single canonical "
                            f"venue.id={t.new_external_id} captures the entire feed in "
                            "single-venue mode. Repointed to disable organizer-mode routing "
                            "for this club so events keep landing on the original."
                        ),
                    }
                    print(
                        f"  WRITE ss={t.original_source_id}: ext_id={ext_id!r}→{t.new_external_id!r}"
                        f" url={src_url!r}→{target_url!r} enabled={enabled}→TRUE"
                        f" + metadata[{_METADATA_KEY}]"
                    )
                    if not args.dry_run:
                        cur.execute(
                            """
                            UPDATE scraping_sources
                            SET eventbrite_id = %s,
                                source_url = %s,
                                enabled = TRUE,
                                metadata = %s,
                                updated_at = NOW()
                            WHERE id = %s
                            """,
                            (t.new_external_id, target_url, json.dumps(new_meta), t.original_source_id),
                        )
                    writes_planned += 1

                # Hide vestigial new club
                _, _, ncvis = clubs[t.new_per_venue_club_id]
                if ncvis:
                    print(f"  WRITE clubs.id={t.new_per_venue_club_id}: visible TRUE→FALSE")
                    if not args.dry_run:
                        cur.execute(
                            "UPDATE clubs SET visible = FALSE WHERE id = %s AND visible = TRUE",
                            (t.new_per_venue_club_id,),
                        )
                    writes_planned += 1

                # Disable vestigial scraping_source + annotate
                new_src = sources[t.new_per_venue_source_id]
                _, _, _, _, _, _, nenabled, _, nmeta_raw = new_src
                nmeta = _load_metadata(nmeta_raw)
                nneeds_disable = bool(nenabled)
                nneeds_meta = _METADATA_KEY not in nmeta
                if nneeds_disable or nneeds_meta:
                    new_nmeta = dict(nmeta)
                    new_nmeta[_METADATA_KEY] = {
                        "kind": "vestigial_per_venue",
                        "rationale": (
                            f"Auto-created by 2026-05-05 organizer-mode upsert from /o/ feed "
                            f"on club {t.original_club_id}. Original was repointed to "
                            f"venue-mode (venue.id={t.new_external_id}); organizer-mode no "
                            f"longer fires for this venue, so this row would otherwise sit "
                            f"as an orphan. Disabled + the parent club hidden."
                        ),
                    }
                    print(
                        f"  WRITE vestigial ss={t.new_per_venue_source_id}: enabled={nenabled}→FALSE"
                        f" + metadata[{_METADATA_KEY}]"
                    )
                    if not args.dry_run:
                        cur.execute(
                            """
                            UPDATE scraping_sources
                            SET enabled = FALSE,
                                metadata = %s,
                                updated_at = NOW()
                            WHERE id = %s
                            """,
                            (json.dumps(new_nmeta), t.new_per_venue_source_id),
                        )
                    writes_planned += 1

            # HIDE-ORIGINAL
            for t in _HIDE_ORIGINAL_TARGETS:
                _, _, cvis = clubs[t.original_club_id]
                if cvis:
                    print(f"  WRITE clubs.id={t.original_club_id}: visible TRUE→FALSE")
                    if not args.dry_run:
                        cur.execute(
                            "UPDATE clubs SET visible = FALSE WHERE id = %s AND visible = TRUE",
                            (t.original_club_id,),
                        )
                    writes_planned += 1

                src = sources[t.original_source_id]
                _, _, _, _, _, _, _, _, meta_raw = src
                meta = _load_metadata(meta_raw)
                if _METADATA_KEY not in meta:
                    new_meta = dict(meta)
                    new_meta[_METADATA_KEY] = {
                        "kind": "hide_original_keep_organizer",
                        "rationale": t.rationale,
                    }
                    print(f"  WRITE ss={t.original_source_id}: + metadata[{_METADATA_KEY}] (left enabled)")
                    if not args.dry_run:
                        cur.execute(
                            """
                            UPDATE scraping_sources
                            SET metadata = %s, updated_at = NOW()
                            WHERE id = %s
                            """,
                            (json.dumps(new_meta), t.original_source_id),
                        )
                    writes_planned += 1

            # DISABLE-SOURCE
            for t in _DISABLE_SOURCE_TARGETS:
                src = sources[t.original_source_id]
                _, _, _, _, _, _, enabled, _, meta_raw = src
                meta = _load_metadata(meta_raw)
                needs_disable = bool(enabled)
                needs_meta = _METADATA_KEY not in meta
                if needs_disable or needs_meta:
                    new_meta = dict(meta)
                    new_meta[_METADATA_KEY] = {
                        "kind": "disable_misattributed",
                        "rationale": (
                            "Organizer feed returned 1 event under venue.name='The Fonda "
                            "Theatre' in Los Angeles, CA — wholly different city/state from "
                            "the registered Lake Oswego, OR venue. URL is misattributed; "
                            "leaving enabled would create or refresh a wrong per-venue club."
                        ),
                    }
                    print(
                        f"  WRITE ss={t.original_source_id}: enabled={enabled}→FALSE"
                        f" + metadata[{_METADATA_KEY}]"
                    )
                    if not args.dry_run:
                        cur.execute(
                            """
                            UPDATE scraping_sources
                            SET enabled = FALSE,
                                metadata = %s,
                                updated_at = NOW()
                            WHERE id = %s
                            """,
                            (json.dumps(new_meta), t.original_source_id),
                        )
                    writes_planned += 1

        if writes_planned == 0:
            print("\nNo changes needed (idempotent re-run).")
            return 0

        if args.dry_run:
            print(f"\n--dry-run: {writes_planned} writes planned (none applied).")
            return 0

        print(f"\n=== AFTER ({writes_planned} writes committed on transaction exit) ===")

    # Re-read for confirmation print (transaction has committed).
    with get_transaction() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, name, visible FROM clubs WHERE id = ANY(%s) ORDER BY id",
                (all_club_ids,),
            )
            for cid, cname, cvis in cur.fetchall():
                print(f"  clubs.id={cid:>4} {cname!r:<50} visible={cvis}")

            cur.execute(
                """
                SELECT id, club_id, eventbrite_id, source_url, enabled
                FROM scraping_sources WHERE id = ANY(%s) ORDER BY id
                """,
                (all_source_ids,),
            )
            for sid, cid, ext, src_url, enabled in cur.fetchall():
                print(f"  ss.id={sid:>5} club={cid:>4} ext={ext:<15} enabled={enabled} url={src_url}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
