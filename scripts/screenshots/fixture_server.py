#!/usr/bin/env python3
"""Hermetic API and artwork backend for native screenshot capture lanes."""

from __future__ import annotations

import argparse
import json
import struct
import zlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse


CONTENT_FIXTURE = {
    "id": "native-screenshot-v1",
    "result_count": 5,
    "featured_entities": {
        "club": {"id": 201, "name": "The Comedy Store"},
        "show": {"id": 101, "name": "Taylor Tomlinson & Friends", "headliner": "Taylor Tomlinson"},
        "comedian": {"id": 301, "name": "Ali Wong"},
        "podcast": {"id": 401, "name": "The Joe Rogan Experience"},
    },
    "dates": {
        "primary_show": "2030-07-18T20:00:00-07:00",
        "secondary_show": "2030-07-19T21:00:00-07:00",
    },
    "artwork": {
        "required_keys": ["taylor", "comedy-store", "ali-wong", "joe-rogan"],
        "fallback_policy": "Authenticated screenshot persona omits remote artwork and uses each platform's branded fallback.",
    },
}

API_PREFIX = "/api/v1/"
ARTWORK_COLORS = {
    "taylor": ((118, 48, 91), (221, 103, 47)),
    "comedy-store": ((42, 42, 42), (207, 75, 40)),
    "ali-wong": ((181, 76, 119), (237, 181, 73)),
    "joe-rogan": ((167, 54, 29), (35, 35, 35)),
}


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


def _social(entity_id: int, handle: str) -> dict:
    return {"id": entity_id, "instagramAccount": handle, "website": f"https://example.invalid/{handle}"}


def _lineup(base_url: str) -> dict:
    return {
        "id": 302,
        "uuid": "fixture-302",
        "name": "Taylor Tomlinson",
        "imageUrl": f"{base_url}/artwork/taylor.png",
        "showCount": 40,
        "socialData": _social(302, "taylortomlinson"),
        "isFavorite": False,
    }


def _comedian(base_url: str, index: int, name: str) -> dict:
    entity_id = 301 + index
    artwork_key = "ali-wong" if index == 0 else "taylor"
    return {
        "id": entity_id,
        "uuid": f"fixture-{entity_id}",
        "name": name,
        "imageUrl": f"{base_url}/artwork/{artwork_key}.png",
        "socialData": _social(entity_id, name.lower().replace(" ", "")),
        "showCount": 28 - index,
        "isFavorite": False,
    }


def _show(base_url: str, show_id: int = 101, name: str = "Taylor Tomlinson & Friends", hour: int = 20) -> dict:
    return {
        "id": show_id,
        "clubId": 201,
        "date": f"2030-07-{18 if show_id == 101 else 19:02d}T{hour:02d}:00:00-07:00",
        "imageUrl": f"{base_url}/artwork/taylor.png",
        "clubName": "The Comedy Store",
        "clubCity": "West Hollywood",
        "clubState": "CA",
        "name": name,
        "room": "Main Room",
        "timezone": "America/Los_Angeles",
        "soldOut": False,
        "tickets": [{"price": 40, "purchaseUrl": f"https://example.invalid/tickets/{show_id}", "soldOut": False, "type": "General Admission"}],
        "lineup": [_lineup(base_url)],
    }


def fixture_response(path: str, base_url: str) -> dict | None:
    """Return the canonical payload for an API path, ignoring query parameters."""
    if path == f"{API_PREFIX}home/feed":
        primary = _show(base_url)
        return {"data": {
            "hero": {"zipCode": "90028", "city": "Los Angeles", "state": "CA", "shows": [primary]},
            "trendingComedians": [{"id": 301, "uuid": "fixture-301", "name": "Ali Wong", "imageUrl": f"{base_url}/artwork/ali-wong.png", "socialData": _social(301, "aliwong"), "showCount": 28}],
            "comediansNearYou": [],
            "showsTonight": [primary],
            "moreNearYou": [_show(base_url, 102, "Comedy Store Showcase", 21)],
            "trendingThisWeek": [_show(base_url, 103, "Best of Los Angeles", 22)],
            "trendingPodcasts": [{"id": 401, "slug": "joe-rogan-experience", "title": "The Joe Rogan Experience", "episodeCount": 2520, "authorName": "Joe Rogan", "imageUrl": f"{base_url}/artwork/joe-rogan.png"}],
            "popularClubs": [{"id": 201, "address": "8433 Sunset Blvd, West Hollywood, CA", "name": "The Comedy Store", "imageUrl": f"{base_url}/artwork/comedy-store.png", "activeComedianCount": 120, "zipCode": "90069"}],
        }}
    if path == f"{API_PREFIX}shows/search":
        shows = [
            _show(base_url),
            _show(base_url, 102, "Comedy Store Showcase", 21),
            _show(base_url, 103, "Best of Los Angeles", 22),
            _show(base_url, 104, "Late Night at The Store", 23),
            _show(base_url, 105, "The Original Room", 19),
        ]
        return {"data": shows, "total": 5, "filters": [], "zipCapTriggered": False}
    if path in {f"{API_PREFIX}comedians/search", f"{API_PREFIX}comedians/suggestions"}:
        names = ["Ali Wong", "Taylor Tomlinson", "Andrew Schulz", "Josh Johnson", "Trevor Noah"]
        response = {"data": [_comedian(base_url, index, name) for index, name in enumerate(names)]}
        if path.endswith("/search"):
            response.update({"total": 5, "filters": [], "homeCityFilters": []})
        return response
    if path == f"{API_PREFIX}clubs/search":
        names = ["The Comedy Store", "Comedy Cellar", "The Stand", "Hollywood Improv", "Largo at the Coronet"]
        return {"data": [
            {"id": 201 + index, "name": name, "imageUrl": f"{base_url}/artwork/comedy-store.png", "address": "8433 Sunset Blvd", "zipCode": "90069", "showCount": 120 - index * 10, "activeComedianCount": 80 - index, "city": "West Hollywood", "state": "CA", "isFavorite": False}
            for index, name in enumerate(names)
        ], "total": 5, "filters": []}
    if path == f"{API_PREFIX}podcasts/search":
        titles = ["The Joe Rogan Experience", "Conan O'Brien Needs a Friend", "The JTrain Podcast", "WTF with Marc Maron", "SmartLess"]
        return {"data": [
            {"id": 401 + index, "slug": f"fixture-{401 + index}", "title": title, "episodeCount": 2520 - index * 100, "hosts": [{"id": 301, "uuid": "fixture-301", "name": "Joe Rogan", "imageUrl": f"{base_url}/artwork/joe-rogan.png"}], "authorName": "Comedy Podcast Network", "imageUrl": f"{base_url}/artwork/joe-rogan.png", "description": "Stand-up conversations and new episodes every week.", "isFavorite": False}
            for index, title in enumerate(titles)
        ], "total": 5, "filters": []}
    if path == f"{API_PREFIX}clubs/201":
        return {"data": {"id": 201, "name": "The Comedy Store", "imageUrl": f"{base_url}/artwork/comedy-store.png", "heroImageUrl": f"{base_url}/artwork/comedy-store.png", "website": "https://thecomedystore.com", "address": "8433 Sunset Blvd, West Hollywood, CA", "zipCode": "90069", "phoneNumber": "(323) 650-6268"}}
    if path == f"{API_PREFIX}clubs/201/shows":
        return {
            "data": [
                _show(base_url),
                _show(base_url, 102, "Comedy Store Showcase", 21),
                _show(base_url, 103, "Best of Los Angeles", 22),
                _show(base_url, 104, "Late Night at The Store", 23),
                _show(base_url, 105, "The Original Room", 19),
            ],
            "total": CONTENT_FIXTURE["result_count"],
        }
    if path == f"{API_PREFIX}shows/101":
        return {"data": {**_show(base_url), "showPageUrl": "https://example.invalid/show/101", "club": {"id": 201, "name": "The Comedy Store", "imageUrl": f"{base_url}/artwork/comedy-store.png", "address": "8433 Sunset Blvd, West Hollywood, CA", "timezone": "America/Los_Angeles"}, "cta": {"label": "Buy tickets", "isSoldOut": False, "url": "https://example.invalid/tickets/101"}, "description": "A special night of new material and surprise guests."}, "relatedShows": []}
    if path == f"{API_PREFIX}comedians/301":
        return {"data": {"id": 301, "uuid": "fixture-301", "name": "Ali Wong", "imageUrl": f"{base_url}/artwork/ali-wong.png", "socialData": _social(301, "aliwong"), "podcastAppearances": [], "homeLocation": {"city": "San Francisco", "state": "CA", "country": "US"}}}
    if path == f"{API_PREFIX}comedians/301/upcoming-runs":
        return {"data": [{"clubId": 201, "clubName": "The Comedy Store", "clubImageUrl": f"{base_url}/artwork/comedy-store.png", "shows": [_show(base_url, 106, "Ali Wong: Live", 20)]}]}
    if path in {f"{API_PREFIX}comedians/301/co-bill", f"{API_PREFIX}comedians/past-shows"}:
        return {"data": [], **({"total": 0} if path.endswith("past-shows") else {})}
    if path == f"{API_PREFIX}podcasts/401":
        return {"podcast": {"id": 401, "slug": "joe-rogan-experience", "title": "The Joe Rogan Experience", "episodeCount": 2520, "hosts": [{"id": 301, "uuid": "fixture-301", "name": "Joe Rogan", "imageUrl": f"{base_url}/artwork/joe-rogan.png"}], "authorName": "Joe Rogan", "websiteUrl": "https://example.invalid/podcasts/jre", "feedUrl": "https://example.invalid/feeds/jre", "imageUrl": f"{base_url}/artwork/joe-rogan.png", "description": "Long-form conversations with comedians, artists, and fascinating guests.", "isFavorite": False}, "episodes": [{"id": 501, "title": "#2520 - A Night of Comedy", "description": "A conversation about stand-up and new material.", "releaseDate": "2030-07-01", "durationSeconds": 8940, "episodeUrl": "https://example.invalid/episodes/501", "audioUrl": "https://example.invalid/audio/501.mp3", "appearances": []}], "relatedComedians": [{"id": 301, "uuid": "fixture-301", "name": "Ali Wong", "imageUrl": f"{base_url}/artwork/ali-wong.png", "socialData": _social(301, "aliwong"), "showCount": 28, "isFavorite": False}]}
    return None


class FixtureHandler(BaseHTTPRequestHandler):
    server_version = "LaughTrackScreenshotFixture/1"

    def do_GET(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
        path = urlparse(self.path).path
        if path == "/health":
            self._write(200, b"ok\n", "text/plain")
            return
        if path.startswith("/artwork/") and path.endswith(".png"):
            self._write(200, artwork_png(path.rsplit("/", 1)[-1][:-4]), "image/png")
            return
        host = self.headers.get("Host", f"127.0.0.1:{self.server.server_port}")
        payload = fixture_response(path, f"http://{host}")
        if payload is None:
            self._write(404, b'{"error":"fixture not found"}', "application/json")
            return
        self._write(200, json.dumps(payload, separators=(",", ":")).encode(), "application/json")

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
    server = ThreadingHTTPServer((args.host, args.port), FixtureHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
