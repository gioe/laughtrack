#!/usr/bin/env python3
"""Hermetic API and artwork backend for native screenshot capture lanes."""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse


ASSET_ROOT = Path(__file__).with_name("assets")
ARTWORK_ASSETS = {
    "ali-wong": {
        "filename": "ali-wong.png",
        "sha256": "c8faad8bb8ddd35d3c87560f2a64230d5e543759945973d92d65ff252d614eb9",
        "width": 640,
        "height": 640,
        "category": "portrait",
    },
    "taylor": {
        "filename": "taylor.png",
        "sha256": "aa37df5099d8f9a76d1d2211a64b2787dde28406ef0e0de60e9035956bc63b95",
        "width": 640,
        "height": 640,
        "category": "portrait",
    },
    "andrew-schulz": {
        "filename": "andrew-schulz.png",
        "sha256": "202e6f120b06949529a56069ad2f745928e59dd36d727a765cf0e05f2d70457a",
        "width": 640,
        "height": 640,
        "category": "portrait",
    },
    "josh-johnson": {
        "filename": "josh-johnson.png",
        "sha256": "5f0c670b8b29a0d2a7342fc2e7cb8f616cc281c0a795fc2b852068145ae8e234",
        "width": 640,
        "height": 640,
        "category": "portrait",
    },
    "comedy-store": {
        "filename": "comedy-store.png",
        "sha256": "edfc64bba48f2d1be44a82a9ce049ba24e9af3cbe0f070af0cd578d54db53ba0",
        "width": 640,
        "height": 640,
        "category": "club_logo",
    },
    "comedy-cellar": {
        "filename": "comedy-cellar.png",
        "sha256": "87846444689214e43d194b3f23010af3eb074ec276c223255d434b1a15fb81f2",
        "width": 640,
        "height": 640,
        "category": "club_logo",
    },
    "the-stand": {
        "filename": "the-stand.png",
        "sha256": "1543f166b908c517ca1fd3546e4cb6519b702682bfaf6db74d866a5ca08a7b9b",
        "width": 640,
        "height": 640,
        "category": "club_logo",
    },
    "hollywood-improv": {
        "filename": "hollywood-improv.png",
        "sha256": "774042f4ea3b95b071a2c1e2f905db20421e0833daf5df755622a29e33dc4f54",
        "width": 640,
        "height": 640,
        "category": "club_logo",
    },
    "show-friends": {
        "filename": "show-friends.png",
        "sha256": "b85510b1d88372f3a6ed37fcb2bec076f976e2e56ebad8b371f234c98c95bdbd",
        "width": 640,
        "height": 640,
        "category": "show_art",
    },
    "show-showcase": {
        "filename": "show-showcase.png",
        "sha256": "5a2c78b624508138bf267fc9dbbfe6875eaeeeca70ef45529cf724f91a028df6",
        "width": 640,
        "height": 640,
        "category": "show_art",
    },
    "show-best-of-la": {
        "filename": "show-best-of-la.png",
        "sha256": "b4c52e8fee6c1beeb2e2e54526cc1dd0bc10c1dede5274dde8752320c02cb996",
        "width": 640,
        "height": 640,
        "category": "show_art",
    },
    "show-late-night": {
        "filename": "show-late-night.png",
        "sha256": "4e34b3dc5bf098ec1cc81f7c5c6c7cc3e8ff218793c44cce95a57fab428dabaa",
        "width": 640,
        "height": 640,
        "category": "show_art",
    },
    "joe-rogan": {
        "filename": "joe-rogan.png",
        "sha256": "3affdd8a23299aa8973cf340eb12bdbc1ff71c343632931bf3bbfebacd4d8226",
        "width": 640,
        "height": 640,
        "category": "podcast_art",
    },
    "conan": {
        "filename": "conan.png",
        "sha256": "a27bdd937115eca586060cd633014f5124977f8542057323e08435a7c97bd227",
        "width": 640,
        "height": 640,
        "category": "podcast_art",
    },
    "jtrain": {
        "filename": "jtrain.png",
        "sha256": "d5e5e50be89b449bb65c7c89f5cf821ebdd748a1b465b983772140068799f925",
        "width": 640,
        "height": 640,
        "category": "podcast_art",
    },
    "wtf": {
        "filename": "wtf.png",
        "sha256": "cdd18b18f4d81cc28b789ac2d14fb2db7e97df07b0e3a32f20f598aed95b6b9d",
        "width": 640,
        "height": 640,
        "category": "podcast_art",
    },
}


CONTENT_FIXTURE = {
    "id": "native-screenshot-v3",
    "default_mode": "curated",
    "profile_modes": {
        "ios_phone": "curated",
        "ios_large_tablet": "curated",
        "android_phone": "curated",
        "android_small_tablet": "curated",
        "android_large_tablet": "curated",
    },
    "artwork": {
        "root": "scripts/screenshots/assets",
        "provenance": "Original fictional illustrations generated for LaughTrack; no third-party logos or celebrity likenesses.",
        "license": "Project fixture artwork; redistribution permitted with this repository.",
        "assets": ARTWORK_ASSETS,
    },
    "modes": {
        "fallback-focused": {
            "id": "native-screenshot-fallback-focused-v2",
            "result_count": 5,
            "featured_entities": {
                "club": {"id": 201, "name": "The Comedy Store"},
                "show": {
                    "id": 101,
                    "name": "Taylor Tomlinson & Friends",
                    "headliner": "Taylor Tomlinson",
                },
                "comedian": {"id": 301, "name": "Ali Wong"},
                "podcast": {"id": 401, "name": "The Joe Rogan Experience"},
                "episode": {"id": 501, "name": "#2520 - A Night of Comedy"},
            },
            "dates": {
                "primary_show": "2030-07-18T20:00:00-07:00",
                "secondary_show": "2030-07-19T21:00:00-07:00",
            },
            "artwork": {
                "required_keys": [
                    "ali-wong",
                    "taylor",
                    "comedy-store",
                    "show-friends",
                    "joe-rogan",
                ],
                "fallback_policy": "Authenticated screenshot persona omits remote artwork and uses each platform's branded fallback.",
            },
        },
        "curated": {
            "id": "native-screenshot-curated-v1",
            "result_count": 12,
            "featured_entities": {
                "club": {"id": 201, "name": "The Comedy Store"},
                "show": {
                    "id": 101,
                    "name": "Taylor Tomlinson & Friends",
                    "headliner": "Taylor Tomlinson",
                },
                "comedian": {"id": 301, "name": "Ali Wong"},
                "podcast": {"id": 401, "name": "The Joe Rogan Experience"},
                "episode": {"id": 501, "name": "#2520 - A Night of Comedy"},
            },
            "dates": {
                "primary_show": "2030-07-18T20:00:00-07:00",
                "secondary_show": "2030-07-19T21:00:00-07:00",
            },
            "artwork": {
                "required_keys": [
                    "ali-wong",
                    "taylor",
                    "andrew-schulz",
                    "josh-johnson",
                    "comedy-store",
                    "comedy-cellar",
                    "the-stand",
                    "hollywood-improv",
                    "show-friends",
                    "show-showcase",
                    "show-best-of-la",
                    "show-late-night",
                    "joe-rogan",
                    "conan",
                    "jtrain",
                    "wtf",
                ],
                "categories": {
                    "portraits": ["ali-wong", "taylor", "andrew-schulz", "josh-johnson"],
                    "club_logos": [
                        "comedy-store",
                        "comedy-cellar",
                        "the-stand",
                        "hollywood-improv",
                    ],
                    "show_art": [
                        "show-friends",
                        "show-showcase",
                        "show-best-of-la",
                        "show-late-night",
                    ],
                    "podcast_art": ["joe-rogan", "conan", "jtrain", "wtf"],
                },
            },
        },
    },
}

API_PREFIX = "/api/v1/"
DEFAULT_MODE = CONTENT_FIXTURE["default_mode"]
CURATED_MODE = "curated"
FALLBACK_MODE = "fallback-focused"

COMEDIAN_NAMES = [
    "Ali Wong",
    "Taylor Tomlinson",
    "Andrew Schulz",
    "Josh Johnson",
    "Trevor Noah",
    "Sam Jay",
    "Nate Bargatze",
    "Nicole Byer",
    "Hasan Minhaj",
    "Atsuko Okatsuka",
    "Roy Wood Jr.",
    "Michelle Wolf",
]
COMEDIAN_ARTWORK = ["ali-wong", "taylor", "andrew-schulz", "josh-johnson"]
FALLBACK_COMEDIAN_ARTWORK = ["ali-wong", "taylor"]
CLUB_NAMES = [
    "The Comedy Store",
    "Comedy Cellar",
    "The Stand",
    "Hollywood Improv",
    "Largo at the Coronet",
    "Gotham Comedy Club",
    "The Bell House",
    "Laugh Factory",
    "Punch Line",
    "Helium Comedy Club",
    "Zanies",
    "Comedy Works",
]
CLUB_ARTWORK = ["comedy-store", "comedy-cellar", "the-stand", "hollywood-improv"]
PODCAST_TITLES = [
    "The Joe Rogan Experience",
    "Conan O'Brien Needs a Friend",
    "The JTrain Podcast",
    "WTF with Marc Maron",
    "SmartLess",
    "Good One",
    "Blocks",
    "Fly on the Wall",
    "We Might Be Drunk",
    "You Made It Weird",
    "The HoneyDew",
    "Working It Out",
]
PODCAST_ARTWORK = ["joe-rogan", "conan", "jtrain", "wtf"]
SHOW_ARTWORK = ["show-friends", "show-showcase", "show-best-of-la", "show-late-night"]
SHOW_NAMES = [
    "Taylor Tomlinson & Friends",
    "Comedy Store Showcase",
    "Best of Los Angeles",
    "Late Night at The Store",
    "The Original Room",
    "Sam Jay: Goodnight",
    "Nate Bargatze: New Material",
    "Nicole Byer & Friends",
    "Hasan Minhaj Live",
    "Atsuko Okatsuka: Full Grown",
    "Roy Wood Jr. Headlines",
    "Michelle Wolf: Work in Progress",
]
SHOW_HOURS = [20, 21, 22, 23, 19]


def _png_dimensions(body: bytes) -> tuple[int, int]:
    if not body.startswith(b"\x89PNG\r\n\x1a\n") or body[12:16] != b"IHDR":
        raise ValueError("artwork is not a PNG with an IHDR header")
    return struct.unpack(">II", body[16:24])


def artwork_png(key: str) -> bytes:
    """Return one checksummed bundled artwork asset, rejecting unknown keys."""
    try:
        metadata = ARTWORK_ASSETS[key]
    except KeyError as exc:
        raise KeyError(f"unknown artwork key: {key}") from exc

    body = (ASSET_ROOT / metadata["filename"]).read_bytes()
    digest = hashlib.sha256(body).hexdigest()
    if digest != metadata["sha256"]:
        raise ValueError(f"artwork checksum mismatch for {key}")
    if _png_dimensions(body) != (metadata["width"], metadata["height"]):
        raise ValueError(f"artwork dimensions mismatch for {key}")
    return body


def fixture_contract(mode: str = DEFAULT_MODE) -> dict:
    """Return one immutable fixture-mode contract, rejecting unknown modes."""
    try:
        return CONTENT_FIXTURE["modes"][mode]
    except KeyError as exc:
        raise ValueError(f"unknown fixture mode: {mode}") from exc


def fixture_mode_fingerprint(mode: str = DEFAULT_MODE) -> str:
    """Return a stable fingerprint for the selected fixture mode."""
    contract = fixture_contract(mode)
    assets = {
        key: ARTWORK_ASSETS[key]
        for key in contract["artwork"]["required_keys"]
    }
    encoded = json.dumps(
        {"contract": contract, "assets": assets},
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    return hashlib.sha256(encoded).hexdigest()


def fixture_mode_summary(mode: str) -> dict:
    contract = fixture_contract(mode)
    return {
        "mode": mode,
        "result_count": contract["result_count"],
        "fingerprint": fixture_mode_fingerprint(mode),
        "required_assets": contract["artwork"]["required_keys"],
    }


def _social(entity_id: int, handle: str) -> dict:
    return {"id": entity_id, "instagramAccount": handle, "website": f"https://example.invalid/{handle}"}


def _lineup(
    base_url: str,
    index: int = 1,
    name: str = "Taylor Tomlinson",
    popularity: int = 98,
    show_count: int = 40,
    mode: str = DEFAULT_MODE,
) -> dict:
    entity_id = 301 + index
    artwork_pool = (
        FALLBACK_COMEDIAN_ARTWORK if mode == FALLBACK_MODE else COMEDIAN_ARTWORK
    )
    artwork_key = artwork_pool[index % len(artwork_pool)]
    social_data = _social(entity_id, name.lower().replace(" ", ""))
    social_data["popularity"] = popularity
    return {
        "id": entity_id,
        "uuid": f"fixture-{entity_id}",
        "name": name,
        "imageUrl": f"{base_url}/artwork/{artwork_key}.png",
        "showCount": show_count,
        "socialData": social_data,
        "isFavorite": False,
    }


def _comedian(base_url: str, index: int, name: str, mode: str = DEFAULT_MODE) -> dict:
    entity_id = 301 + index
    artwork_key = (
        ("ali-wong" if index == 0 else "taylor")
        if mode == FALLBACK_MODE
        else COMEDIAN_ARTWORK[index % len(COMEDIAN_ARTWORK)]
    )
    return {
        "id": entity_id,
        "uuid": f"fixture-{entity_id}",
        "name": name,
        "imageUrl": f"{base_url}/artwork/{artwork_key}.png",
        "socialData": _social(entity_id, name.lower().replace(" ", "")),
        "showCount": 28 - index,
        "isFavorite": False,
    }


def _show(
    base_url: str,
    show_id: int = 101,
    name: str = "Taylor Tomlinson & Friends",
    hour: int = 20,
    artwork_key: str = "show-friends",
    lineup: list[dict] | None = None,
    day: int | None = None,
    mode: str = DEFAULT_MODE,
) -> dict:
    return {
        "id": show_id,
        "clubId": 201,
        "date": f"2030-07-{day if day is not None else (18 if show_id == 101 else 19):02d}T{hour:02d}:00:00-07:00",
        "imageUrl": f"{base_url}/artwork/{artwork_key}.png",
        "clubName": "The Comedy Store",
        "clubCity": "West Hollywood",
        "clubState": "CA",
        "name": name,
        "room": "Main Room",
        "timezone": "America/Los_Angeles",
        "soldOut": False,
        "tickets": [{"price": 40, "purchaseUrl": f"https://example.invalid/tickets/{show_id}", "soldOut": False, "type": "General Admission"}],
        "lineup": lineup if lineup is not None else [_lineup(base_url, mode=mode)],
    }


def _club_shows(base_url: str, mode: str = DEFAULT_MODE) -> list[dict]:
    taylor = _lineup(base_url, mode=mode)
    ali = _lineup(base_url, 0, "Ali Wong", popularity=96, show_count=36, mode=mode)
    andrew = _lineup(base_url, 2, "Andrew Schulz", popularity=94, show_count=34, mode=mode)
    tonight_artwork = (
        SHOW_ARTWORK if mode == CURATED_MODE else ["show-friends"] * 4
    )
    tonight = [
        _show(base_url, 106, "Ali Wong: Live", 19, tonight_artwork[0], lineup=[ali], day=18, mode=mode),
        _show(base_url, 101, "Taylor Tomlinson & Friends", 20, tonight_artwork[1], lineup=[taylor], day=18, mode=mode),
        _show(base_url, 107, "Andrew Schulz: New Material", 21, tonight_artwork[2], lineup=[andrew], day=18, mode=mode),
        _show(base_url, 108, "Late Night with Taylor", 22, tonight_artwork[3], lineup=[taylor], day=18, mode=mode),
    ]
    later = []
    reserved_ids = {show["id"] for show in tonight}
    show_id = 102
    while len(later) < 41:
        if show_id in reserved_ids:
            show_id += 1
            continue
        index = len(later)
        comedian_index = index % len(COMEDIAN_NAMES)
        comedian_name = COMEDIAN_NAMES[comedian_index]
        lineup = _lineup(
            base_url,
            comedian_index,
            comedian_name,
            popularity=90 - comedian_index,
            show_count=32 - comedian_index,
            mode=mode,
        )
        later.append(
            _show(
                base_url,
                show_id,
                SHOW_NAMES[index % len(SHOW_NAMES)],
                SHOW_HOURS[index % len(SHOW_HOURS)],
                "show-friends" if mode == FALLBACK_MODE else SHOW_ARTWORK[index % len(SHOW_ARTWORK)],
                # Keep one deterministic, lineup-unannounced showcase so the
                # shipping screenshot matrix exercises dedicated show artwork
                # instead of always preferring a comedian headshot.
                lineup=[] if index == 0 else [lineup],
                day=19 + index // 5,
                mode=mode,
            )
        )
        show_id += 1
    return tonight + later


def _club_tonight_shows(base_url: str, mode: str = DEFAULT_MODE) -> list[dict]:
    return [
        show for show in _club_shows(base_url, mode)
        if show["date"].startswith("2030-07-18")
    ]


def _podcast_host(base_url: str) -> dict:
    return {
        "id": 304,
        "uuid": "fixture-304",
        "name": "Joe Rogan",
        "imageUrl": f"{base_url}/artwork/joe-rogan.png",
    }


def _podcast(base_url: str) -> dict:
    return {
        "id": 401,
        "slug": "joe-rogan-experience",
        "title": "The Joe Rogan Experience",
        "episodeCount": 2520,
        "hosts": [_podcast_host(base_url)],
        "authorName": "Joe Rogan",
        "websiteUrl": "https://example.invalid/podcasts/jre",
        "feedUrl": "https://example.invalid/feeds/jre",
        "imageUrl": f"{base_url}/artwork/joe-rogan.png",
        "description": "Long-form conversations with comedians, artists, and fascinating guests.",
        "isFavorite": False,
    }


def _podcast_episode(base_url: str) -> dict:
    return {
        "id": 501,
        "title": "#2520 - A Night of Comedy",
        "description": "A conversation about stand-up, new material, and life on the road.",
        "releaseDate": "2030-07-01",
        "durationSeconds": 8940,
        "episodeUrl": "https://example.invalid/episodes/501",
        "audioUrl": "https://example.invalid/audio/501.mp3",
        "appearances": [
            {
                "id": 304,
                "uuid": "fixture-304",
                "name": "Joe Rogan",
                "imageUrl": f"{base_url}/artwork/joe-rogan.png",
            },
            {
                "id": 301,
                "uuid": "fixture-301",
                "name": "Ali Wong",
                "imageUrl": f"{base_url}/artwork/ali-wong.png",
            },
        ],
    }


def fixture_response(
    path: str,
    base_url: str,
    mode: str = DEFAULT_MODE,
    query: dict[str, list[str]] | None = None,
) -> dict | None:
    """Return the canonical payload for an API path and optional pagination query."""
    result_count = fixture_contract(mode)["result_count"]
    if path == f"{API_PREFIX}home/feed":
        primary = _show(base_url, mode=mode)
        nearby_count = 1 if mode == FALLBACK_MODE else min(result_count - 1, 4)
        nearby = [
            _show(
                base_url,
                102 + index,
                SHOW_NAMES[1 + index],
                SHOW_HOURS[(index + 1) % len(SHOW_HOURS)],
                (
                    "show-friends"
                    if mode == FALLBACK_MODE
                    else SHOW_ARTWORK[(index + 1) % len(SHOW_ARTWORK)]
                ),
                mode=mode,
            )
            for index in range(nearby_count)
        ]
        return {"data": {
            "hero": {"zipCode": "90028", "city": "Los Angeles", "state": "CA", "shows": [primary]},
            "trendingComedians": [{"id": 301, "uuid": "fixture-301", "name": "Ali Wong", "imageUrl": f"{base_url}/artwork/ali-wong.png", "socialData": _social(301, "aliwong"), "showCount": 28}],
            "comediansNearYou": [],
            "showsTonight": [primary],
            "moreNearYou": nearby or [_show(base_url, 102, "Comedy Store Showcase", 21, mode=mode)],
            "trendingThisWeek": [
                _show(
                    base_url,
                    103,
                    "Best of Los Angeles",
                    22,
                    "show-friends" if mode == FALLBACK_MODE else "show-best-of-la",
                    mode=mode,
                )
            ],
            "followedComedianShows": [
                _show(
                    base_url,
                    104,
                    "Late Night at The Store",
                    23,
                    "show-friends" if mode == FALLBACK_MODE else "show-late-night",
                    mode=mode,
                )
            ],
            "trendingPodcasts": [{"id": 401, "slug": "joe-rogan-experience", "title": "The Joe Rogan Experience", "episodeCount": 2520, "authorName": "Joe Rogan", "imageUrl": f"{base_url}/artwork/joe-rogan.png"}],
            "popularClubs": [{"id": 201, "address": "8433 Sunset Blvd, West Hollywood, CA", "name": "The Comedy Store", "imageUrl": f"{base_url}/artwork/comedy-store.png", "activeComedianCount": 120, "zipCode": "90069"}],
        }}
    if path == f"{API_PREFIX}shows/search":
        is_pinned_club_search = bool((query or {}).get("club"))
        total = 45 if is_pinned_club_search else result_count
        page = int((query or {}).get("page", ["0"])[0])
        size = int((query or {}).get("size", [str(total)])[0])
        start = max(0, page) * size
        end = min(start + size, total)
        catalog = _club_shows(base_url, mode)
        shows = catalog[start:end]
        return {"data": shows, "total": total, "filters": [], "zipCapTriggered": False}
    if path in {f"{API_PREFIX}comedians/search", f"{API_PREFIX}comedians/suggestions"}:
        response = {
            "data": [
                _comedian(base_url, index, name, mode)
                for index, name in enumerate(COMEDIAN_NAMES[:result_count])
            ]
        }
        if path.endswith("/search"):
            response.update({"total": result_count, "filters": [], "homeCityFilters": []})
        return response
    if path == f"{API_PREFIX}clubs/search":
        return {"data": [
            {
                "id": 201 + index,
                "name": name,
                "imageUrl": f"{base_url}/artwork/{'comedy-store' if mode == FALLBACK_MODE else CLUB_ARTWORK[index % len(CLUB_ARTWORK)]}.png",
                "address": "8433 Sunset Blvd",
                "zipCode": "90069",
                "showCount": 120 - index * (10 if mode == FALLBACK_MODE else 5),
                "activeComedianCount": 80 - index,
                "city": "West Hollywood",
                "state": "CA",
                "isFavorite": False,
            }
            for index, name in enumerate(CLUB_NAMES[:result_count])
        ], "total": result_count, "filters": []}
    if path == f"{API_PREFIX}podcasts/search":
        return {"data": [
            {
                "id": 401 + index,
                "slug": f"fixture-{401 + index}",
                "title": title,
                "episodeCount": 2520 - index * 100,
                "hosts": [_podcast_host(base_url)],
                "authorName": "Comedy Podcast Network",
                "imageUrl": f"{base_url}/artwork/{'joe-rogan' if mode == FALLBACK_MODE else PODCAST_ARTWORK[index % len(PODCAST_ARTWORK)]}.png",
                "description": "Stand-up conversations and new episodes every week.",
                "isFavorite": False,
            }
            for index, title in enumerate(PODCAST_TITLES[:result_count])
        ], "total": result_count, "filters": []}
    if path == f"{API_PREFIX}clubs/201":
        return {"data": {"id": 201, "name": "The Comedy Store", "imageUrl": f"{base_url}/artwork/comedy-store.png", "heroImageUrl": f"{base_url}/artwork/comedy-store.png", "website": "https://thecomedystore.com", "address": "8433 Sunset Blvd, West Hollywood, CA", "zipCode": "90069", "phoneNumber": "(323) 650-6268"}}
    if path == f"{API_PREFIX}clubs/201/highlights":
        return {
            "data": {
                "tonightShows": _club_tonight_shows(base_url, mode),
                "nextShow": _club_shows(base_url, mode)[4],
                "frequentPerformers": [
                    _comedian(base_url, index, name, mode)
                    for index, name in enumerate(COMEDIAN_NAMES[:3])
                ],
            }
        }
    if path == f"{API_PREFIX}clubs/201/shows":
        return {
            "data": _club_shows(base_url, mode)[:result_count],
            "total": result_count,
        }
    show_detail_prefix = f"{API_PREFIX}shows/"
    if path.startswith(show_detail_prefix) and path.removeprefix(show_detail_prefix).isdigit():
        show_id = int(path.removeprefix(show_detail_prefix))
        show = next(
            (item for item in _club_shows(base_url, mode) if item["id"] == show_id),
            _show(base_url, show_id, mode=mode),
        )
        return {"data": {**show, "showPageUrl": f"https://example.invalid/show/{show_id}", "club": {"id": 201, "name": "The Comedy Store", "imageUrl": f"{base_url}/artwork/comedy-store.png", "address": "8433 Sunset Blvd, West Hollywood, CA", "timezone": "America/Los_Angeles"}, "cta": {"label": "Buy tickets", "isSoldOut": False, "url": f"https://example.invalid/tickets/{show_id}"}, "description": "A special night of new material and surprise guests."}, "relatedShows": []}
    if path == f"{API_PREFIX}comedians/301":
        return {"data": {"id": 301, "uuid": "fixture-301", "name": "Ali Wong", "imageUrl": f"{base_url}/artwork/ali-wong.png", "socialData": _social(301, "aliwong"), "podcastAppearances": [], "homeLocation": {"city": "San Francisco", "state": "CA", "country": "US"}}}
    if path == f"{API_PREFIX}comedians/301/upcoming-runs":
        return {"data": [{"clubId": 201, "clubName": "The Comedy Store", "clubImageUrl": f"{base_url}/artwork/comedy-store.png", "shows": [_show(base_url, 106, "Ali Wong: Live", 20, mode=mode)]}]}
    if path in {f"{API_PREFIX}comedians/301/co-bill", f"{API_PREFIX}comedians/past-shows"}:
        return {"data": [], **({"total": 0} if path.endswith("past-shows") else {})}
    if path == f"{API_PREFIX}podcasts/401":
        return {
            "podcast": _podcast(base_url),
            "episodes": [_podcast_episode(base_url)],
            "relatedComedians": [
                {
                    "id": 301,
                    "uuid": "fixture-301",
                    "name": "Ali Wong",
                    "imageUrl": f"{base_url}/artwork/ali-wong.png",
                    "socialData": _social(301, "aliwong"),
                    "showCount": 28,
                    "isFavorite": False,
                }
            ],
        }
    if path == f"{API_PREFIX}podcast-episodes/501":
        return {
            "podcast": _podcast(base_url),
            "episode": _podcast_episode(base_url),
        }
    return None


class FixtureState:
    """Thread-safe mode selection shared by one sequential capture server."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._mode = DEFAULT_MODE

    def current_mode(self) -> str:
        with self._lock:
            return self._mode

    def configure(self, mode: str) -> dict:
        fixture_contract(mode)
        with self._lock:
            self._mode = mode
        return fixture_mode_summary(mode)


class FixtureServer(ThreadingHTTPServer):
    def __init__(self, server_address: tuple[str, int]) -> None:
        super().__init__(server_address, FixtureHandler)
        self.fixture_state = FixtureState()


class FixtureHandler(BaseHTTPRequestHandler):
    server_version = "LaughTrackScreenshotFixture/1"

    def do_GET(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
        parsed = urlparse(self.path)
        path = parsed.path
        if path == "/health":
            self._write(200, b"ok\n", "text/plain")
            return
        if path == "/fixture/status":
            self._write_json(
                200,
                fixture_mode_summary(self.server.fixture_state.current_mode()),
            )
            return
        if path == "/fixture/configure":
            values = parse_qs(parsed.query).get("mode", [])
            if len(values) != 1:
                self._write_json(400, {"error": "fixture mode is required"})
                return
            try:
                summary = self.server.fixture_state.configure(values[0])
            except ValueError as exc:
                self._write_json(400, {"error": str(exc)})
                return
            self._write_json(200, summary)
            return
        if path.startswith("/artwork/") and path.endswith(".png"):
            try:
                body = artwork_png(path.rsplit("/", 1)[-1][:-4])
            except KeyError:
                self._write(404, b'{"error":"artwork not found"}', "application/json")
                return
            self._write(200, body, "image/png")
            return
        host = self.headers.get("Host", f"127.0.0.1:{self.server.server_port}")
        payload = fixture_response(
            path,
            f"http://{host}",
            self.server.fixture_state.current_mode(),
            parse_qs(parsed.query),
        )
        if payload is None:
            self._write(404, b'{"error":"fixture not found"}', "application/json")
            return
        self._write_json(200, payload)

    def _write_json(self, status: int, payload: dict) -> None:
        self._write(
            status,
            json.dumps(payload, separators=(",", ":")).encode(),
            "application/json",
        )

    def _write(self, status: int, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:
        return


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    server = FixtureServer((args.host, args.port))
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
