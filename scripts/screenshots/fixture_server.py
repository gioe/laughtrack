#!/usr/bin/env python3
"""Hermetic API and artwork backend for native screenshot capture lanes."""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
import threading
import zlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse


CONTENT_FIXTURE = {
    "id": "native-screenshot-v2",
    "default_mode": "fallback-focused",
    "profile_modes": {
        "ios_phone": "fallback-focused",
        "ios_large_tablet": "asset-rich",
        "android_phone": "fallback-focused",
        "android_small_tablet": "asset-rich",
        "android_large_tablet": "asset-rich",
    },
    "modes": {
        "fallback-focused": {
            "id": "native-screenshot-v1",
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
                "required_keys": ["taylor", "comedy-store", "ali-wong", "joe-rogan"],
                "fallback_policy": "Authenticated screenshot persona omits remote artwork and uses each platform's branded fallback.",
            },
        },
        "asset-rich": {
            "id": "native-screenshot-asset-rich-v1",
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
                    "podcast_art": ["joe-rogan", "conan", "jtrain", "wtf"],
                },
            },
        },
    },
}

API_PREFIX = "/api/v1/"
DEFAULT_MODE = CONTENT_FIXTURE["default_mode"]
ARTWORK_COLORS = {
    "taylor": ((118, 48, 91), (221, 103, 47)),
    "comedy-store": ((42, 42, 42), (207, 75, 40)),
    "ali-wong": ((181, 76, 119), (237, 181, 73)),
    "joe-rogan": ((167, 54, 29), (35, 35, 35)),
    "andrew-schulz": ((24, 87, 116), (111, 204, 184)),
    "josh-johnson": ((88, 55, 119), (226, 147, 74)),
    "comedy-cellar": ((67, 38, 29), (207, 169, 91)),
    "the-stand": ((24, 63, 45), (102, 190, 113)),
    "hollywood-improv": ((40, 55, 110), (204, 84, 104)),
    "conan": ((186, 82, 38), (242, 187, 73)),
    "jtrain": ((43, 92, 108), (126, 195, 181)),
    "wtf": ((77, 55, 45), (211, 127, 62)),
}

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


def _png_chunk(kind: bytes, data: bytes) -> bytes:
    return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))


def artwork_png(key: str, size: int = 640) -> bytes:
    """Return a deterministic square gradient PNG without third-party dependencies."""
    start, end = ARTWORK_COLORS.get(key, ((55, 55, 55), (221, 103, 47)))
    rows = bytearray()
    denominator = max(size - 1, 1)
    for y in range(size):
        rows.append(0)
        ratio = y / denominator
        color = tuple(round(a + (b - a) * ratio) for a, b in zip(start, end))
        rows.extend(bytes(color) * size)
    ihdr = struct.pack(">IIBBBBB", size, size, 8, 2, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + _png_chunk(b"IHDR", ihdr)
        + _png_chunk(b"IDAT", zlib.compress(bytes(rows), level=9))
        + _png_chunk(b"IEND", b"")
    )


def fixture_contract(mode: str = DEFAULT_MODE) -> dict:
    """Return one immutable fixture-mode contract, rejecting unknown modes."""
    try:
        return CONTENT_FIXTURE["modes"][mode]
    except KeyError as exc:
        raise ValueError(f"unknown fixture mode: {mode}") from exc


def fixture_mode_fingerprint(mode: str = DEFAULT_MODE) -> str:
    """Return a stable fingerprint for the selected fixture mode."""
    encoded = json.dumps(
        fixture_contract(mode),
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
) -> dict:
    entity_id = 301 + index
    artwork_key = COMEDIAN_ARTWORK[index % len(COMEDIAN_ARTWORK)]
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
        if mode == DEFAULT_MODE
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
    artwork_key: str = "taylor",
    lineup: list[dict] | None = None,
    day: int | None = None,
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
        "lineup": lineup if lineup is not None else [_lineup(base_url)],
    }


def _club_tonight_shows(base_url: str) -> list[dict]:
    taylor = _lineup(base_url)
    ali = _lineup(base_url, 0, "Ali Wong", popularity=96, show_count=36)
    andrew = _lineup(base_url, 2, "Andrew Schulz", popularity=94, show_count=34)
    return [
        _show(base_url, 101, "Taylor Tomlinson & Friends", 20, lineup=[taylor], day=18),
        _show(base_url, 106, "Ali Wong: Live", 19, "ali-wong", lineup=[ali], day=18),
        _show(base_url, 107, "Andrew Schulz: New Material", 21, "andrew-schulz", lineup=[andrew], day=18),
        _show(base_url, 108, "Late Night with Taylor", 22, lineup=[taylor], day=18),
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
        primary = _show(base_url)
        nearby_count = 1 if mode == DEFAULT_MODE else min(result_count - 1, 4)
        nearby = [
            _show(
                base_url,
                102 + index,
                SHOW_NAMES[1 + index],
                SHOW_HOURS[(index + 1) % len(SHOW_HOURS)],
                COMEDIAN_ARTWORK[(index + 1) % len(COMEDIAN_ARTWORK)],
            )
            for index in range(nearby_count)
        ]
        return {"data": {
            "hero": {"zipCode": "90028", "city": "Los Angeles", "state": "CA", "shows": [primary]},
            "trendingComedians": [{"id": 301, "uuid": "fixture-301", "name": "Ali Wong", "imageUrl": f"{base_url}/artwork/ali-wong.png", "socialData": _social(301, "aliwong"), "showCount": 28}],
            "comediansNearYou": [],
            "showsTonight": [primary],
            "moreNearYou": nearby or [_show(base_url, 102, "Comedy Store Showcase", 21)],
            "trendingThisWeek": [_show(base_url, 103, "Best of Los Angeles", 22)],
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
        shows = [
            _show(
                base_url,
                101 + index,
                SHOW_NAMES[index % len(SHOW_NAMES)],
                SHOW_HOURS[index % len(SHOW_HOURS)],
                "taylor" if mode == DEFAULT_MODE else COMEDIAN_ARTWORK[index % len(COMEDIAN_ARTWORK)],
            )
            for index in range(start, end)
        ]
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
                "imageUrl": f"{base_url}/artwork/{'comedy-store' if mode == DEFAULT_MODE else CLUB_ARTWORK[index % len(CLUB_ARTWORK)]}.png",
                "address": "8433 Sunset Blvd",
                "zipCode": "90069",
                "showCount": 120 - index * (10 if mode == DEFAULT_MODE else 5),
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
                "imageUrl": f"{base_url}/artwork/{'joe-rogan' if mode == DEFAULT_MODE else PODCAST_ARTWORK[index % len(PODCAST_ARTWORK)]}.png",
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
                "tonightShows": _club_tonight_shows(base_url),
                "nextShow": _show(base_url, 102, "Comedy Store Showcase", 21),
                "frequentPerformers": [
                    _comedian(base_url, index, name, mode)
                    for index, name in enumerate(COMEDIAN_NAMES[:3])
                ],
            }
        }
    if path == f"{API_PREFIX}clubs/201/shows":
        return {
            "data": [
                _show(
                    base_url,
                    101 + index,
                    name,
                    SHOW_HOURS[index % len(SHOW_HOURS)],
                    "taylor" if mode == DEFAULT_MODE else COMEDIAN_ARTWORK[index % len(COMEDIAN_ARTWORK)],
                )
                for index, name in enumerate(SHOW_NAMES[:result_count])
            ],
            "total": result_count,
        }
    show_detail_prefix = f"{API_PREFIX}shows/"
    if path.startswith(show_detail_prefix) and path.removeprefix(show_detail_prefix).isdigit():
        show_id = int(path.removeprefix(show_detail_prefix))
        show = next(
            (item for item in _club_tonight_shows(base_url) if item["id"] == show_id),
            _show(base_url, show_id),
        )
        return {"data": {**show, "showPageUrl": f"https://example.invalid/show/{show_id}", "club": {"id": 201, "name": "The Comedy Store", "imageUrl": f"{base_url}/artwork/comedy-store.png", "address": "8433 Sunset Blvd, West Hollywood, CA", "timezone": "America/Los_Angeles"}, "cta": {"label": "Buy tickets", "isSoldOut": False, "url": f"https://example.invalid/tickets/{show_id}"}, "description": "A special night of new material and surprise guests."}, "relatedShows": []}
    if path == f"{API_PREFIX}comedians/301":
        return {"data": {"id": 301, "uuid": "fixture-301", "name": "Ali Wong", "imageUrl": f"{base_url}/artwork/ali-wong.png", "socialData": _social(301, "aliwong"), "podcastAppearances": [], "homeLocation": {"city": "San Francisco", "state": "CA", "country": "US"}}}
    if path == f"{API_PREFIX}comedians/301/upcoming-runs":
        return {"data": [{"clubId": 201, "clubName": "The Comedy Store", "clubImageUrl": f"{base_url}/artwork/comedy-store.png", "shows": [_show(base_url, 106, "Ali Wong: Live", 20)]}]}
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
            self._write(200, artwork_png(path.rsplit("/", 1)[-1][:-4]), "image/png")
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
