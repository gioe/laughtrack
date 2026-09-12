#!/usr/bin/env python3
"""Hermetic API and artwork backend for native screenshot capture lanes."""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
import threading
from datetime import date, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse


ASSET_ROOT = Path(__file__).with_name("assets")
REVIEW_ANCHOR_DATE = date(2026, 8, 15)
PRIMARY_SHOW_DATE = date(2026, 8, 16)
SECONDARY_SHOW_DATE = date(2026, 8, 17)
# Production episode 47467, verified 2026-09-11:
# https://www.laugh-track.com/api/v1/podcast-episodes/47467
# Only the routing ID is remapped to the stable screenshot fixture ID (501).
EPISODE_RELEASE_DATE = date(2025, 10, 23)
HOME_FEED_EPISODE_RELEASE_DATETIME = "2025-10-23T19:00:00.000Z"
EPISODE_AUDIO_URL = "https://pdst.fm/e/pfx.vpixl.com/u8u9X/pscrb.fm/rss/p/mgln.ai/e/1118/clrtpod.com/m/arttrk.com/p/YMH00/traffic.megaphone.fm/YMH7734324090.mp3?updated=1730821365"
PRIMARY_SHOW_DATETIME = f"{PRIMARY_SHOW_DATE.isoformat()}T20:00:00-04:00"
SECONDARY_SHOW_DATETIME = f"{SECONDARY_SHOW_DATE.isoformat()}T21:00:00-04:00"
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
    "history-hyenas": {
        "filename": "history-hyenas.png",
        "sha256": "053c091b05d8b02c89bbe2c990e18424599081133d24b67db2eb3fbb50cc251c",
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

# Pinned from the public production API on 2026-08-19. Curated storefront
# captures deliberately keep their records and dates deterministic while using
# HTTPS artwork sources read from real production records. Imgix sources that
# negotiate AVIF are pinned to JPEG so both native clients exercise real art
# rather than platform-specific decode fallbacks. The generated assets above
# remain available only to the explicit fallback-focused diagnostic mode.
CURATED_HTTPS_ASSETS = {
    "ali-wong": "https://laughtrack.b-cdn.net/comedians/Ali%20Wong.png",
    "taylor-tomlinson": "https://laughtrack.b-cdn.net/comedian-images/903740/79e27d03-1143-4633-a42f-f5569040fb44/avatar.jpg",
    "andrew-schulz": "https://laughtrack.b-cdn.net/comedians/Andrew%20Schulz.png",
    "josh-johnson": "https://laughtrack.b-cdn.net/comedians/Josh%20Johnson.png",
    "trevor-noah": "https://laughtrack.b-cdn.net/comedians/Trevor%20Noah.png",
    "sam-jay": "https://laughtrack.b-cdn.net/comedians/Sam%20Jay.png",
    "nate-bargatze": "https://laughtrack.b-cdn.net/comedians/Nate%20Bargatze.png",
    "nicole-byer": "https://laughtrack.b-cdn.net/comedian-images/939229/81929c9b-e4b4-4a83-b55f-27f861562532/avatar.jpg",
    "hasan-minhaj": "https://laughtrack.b-cdn.net/comedians/Hasan%20Minhaj.png",
    "atsuko-okatsuka": "https://laughtrack.b-cdn.net/comedians/Atsuko%20Okatsuka.png",
    "roy-wood-jr": "https://laughtrack.b-cdn.net/comedians/Roy%20Wood%20Jr..png",
    "michelle-wolf": "https://laughtrack.b-cdn.net/comedians/Michelle%20Wolf.png",
    "hollywood-improv": "https://laughtrack.b-cdn.net/clubs/Hollywood%20Improv.png",
    "comedy-cellar": "https://laughtrack.b-cdn.net/clubs/Comedy%20Cellar%20New%20York.png",
    "the-stand": "https://laughtrack.b-cdn.net/clubs/The%20Stand.png",
    "gotham-comedy-club": "https://laughtrack.b-cdn.net/clubs/Gotham%20Comedy%20Club.png",
    "ice-house-comedy-club": "https://laughtrack.b-cdn.net/clubs/Ice%20House%20Comedy%20Club.png",
    "comedy-and-magic-club": "https://laughtrack.b-cdn.net/clubs/The%20Comedy%20%26%20Magic%20Club.png",
    "american-comedy-company": "https://laughtrack.b-cdn.net/clubs/American%20Comedy%20Company.png",
    "irvine-improv": "https://laughtrack.b-cdn.net/clubs/Irvine%20Improv.png",
    "cobbs-comedy-club": "https://laughtrack.b-cdn.net/clubs/Cobb's%20Comedy%20Club.png",
    "laugh-boston": "https://laughtrack.b-cdn.net/clubs/Laugh%20Boston.png",
    "comedy-vault": "https://laughtrack.b-cdn.net/clubs/The%20Comedy%20Vault.png",
    "goodnights-comedy-club": "https://laughtrack.b-cdn.net/clubs/Goodnights%20Comedy%20Club.png",
    "history-hyenas": "https://megaphone.imgix.net/podcasts/48030056-989d-11ef-a614-3bc2f8865178/image/171a69e4231342ccae610db68861892b.jpeg?ixlib=rails-4.3.1&max-w=3000&max-h=3000&fit=crop&auto=compress&fm=jpg",
    "jtrain": "https://www.laugh-track.com/api/v1/podcast-artwork?url=https%3A%2F%2Fcontent.production.cdn.art19.com%2Fimages%2F25%2Ff1%2Fb6%2F91%2F25f1b691-87cd-4e74-be13-59508ccf02fc%2Ff2d8fcb6eaad9869b0281db26e4dd937862940e852f3c84aa97e36f52855dd18ac7f1be5e830a73c5235e2c86f19e79c7cafc2c32cdc202aadee0037f9caad98.jpeg",
    "wtf": "https://www.laugh-track.com/api/v1/podcast-artwork?url=https%3A%2F%2Fassets.pippa.io%2Fshows%2F62a222737c02140013aa4c03%2F1656679440477-8e0e5db81e3f07c927b0032af2591499.jpeg",
    "blocks": "https://www.laugh-track.com/api/v1/podcast-artwork?url=https%3A%2F%2Fis1-ssl.mzstatic.com%2Fimage%2Fthumb%2FPodcasts112%2Fv4%2F72%2F3f%2F0a%2F723f0a7e-d02c-b4b9-28e8-7a66bf34b6af%2Fmza_3060685158421747566.png%2F600x600bb.jpg",
    "fly-on-the-wall": "https://www.laugh-track.com/api/v1/podcast-artwork?url=https%3A%2F%2Fimages.castfire.com%2Fimage%2F661%2F0%2F0%2F0%2F0-8382872.jpg",
    "we-might-be-drunk": "https://megaphone.imgix.net/podcasts/594c7c94-98d7-11f0-a551-63ec77ca5cfb/image/207c13a897c640dcd7722654d69bd50b.png?ixlib=rails-4.3.1&max-w=3000&max-h=3000&fit=crop&auto=compress&fm=jpg",
    "you-made-it-weird": "https://megaphone.imgix.net/podcasts/7926a820-34fc-11f1-8539-7b77a5fb5bbd/image/83ee44c93ec0e1cd9fb30c344269c404.jpg?ixlib=rails-4.3.1&max-w=3000&max-h=3000&fit=crop&auto=compress&fm=jpg",
    "honeydew": "https://megaphone.imgix.net/podcasts/d009ef14-01ec-11f1-b436-335cf3c14c8d/image/4359e422f56f9e6d149cf16dede772e3.jpg?ixlib=rails-4.3.1&max-w=3000&max-h=3000&fit=crop&auto=compress&fm=jpg",
    "joe-rogan": "https://www.laugh-track.com/api/v1/podcast-artwork?url=https%3A%2F%2Fis1-ssl.mzstatic.com%2Fimage%2Fthumb%2FPodcasts221%2Fv4%2Fce%2F0a%2Fdb%2Fce0adb4e-6006-8749-6bd1-dda692ce5db4%2Fmza_6849326212804063748.jpg%2F600x600bb.jpg",
    "doug-loves-movies": "https://www.laugh-track.com/api/v1/podcast-artwork?url=https%3A%2F%2Fcontent.production.cdn.art19.com%2Fimages%2F1a%2F96%2F5f%2F27%2F1a965f27-77f3-43de-87cc-8582b2db01a1%2Fc8cf407764c279fe444a806df7c14e885e590b72da03753b17c95948163702edc41458bae996e9d514312eaef1c8037823e68683ab41db61c84f0254bed61823.jpeg",
    "bonfire": "https://www.laugh-track.com/api/v1/podcast-artwork?url=https%3A%2F%2Fimage.simplecastcdn.com%2Fimages%2F47708613-ba9d-4eba-9223-a8682fff8b08%2F8d29e0d2-70cc-446e-8cd3-e3ce4a3659c2%2F3000x3000%2Fbonfirepodcast-3000x3000.jpg%3Faid%3Drss_feed",
    "are-you-garbage": "https://megaphone.imgix.net/podcasts/c2b31d4e-c3fd-11ec-b9c7-6f068016304f/image/387eaf025719eac2071f142cf5ffd635.png?ixlib=rails-4.3.1&max-w=3000&max-h=3000&fit=crop&auto=compress&fm=jpg",
}


CONTENT_FIXTURE = {
    "id": "native-screenshot-v5",
    "default_mode": "curated",
    "review_anchor_date": REVIEW_ANCHOR_DATE.isoformat(),
    "profile_modes": {
        "ios_phone": "curated",
        "ios_large_tablet": "curated",
        "android_phone": "curated",
        "android_small_tablet": "curated",
        "android_large_tablet": "curated",
    },
    "artwork": {
        "root": "scripts/screenshots/assets",
        "provenance": "Curated captures use pinned HTTPS artwork sources read from the public production API on 2026-08-19, normalized to native-compatible raster formats when required. Bundled generated artwork is reserved for fallback-focused diagnostics.",
        "license": "Remote artwork follows its production source terms; bundled fallback artwork is project-owned and redistributable with this repository.",
        "curated_source": "https://www.laugh-track.com/api/v1",
        "assets": ARTWORK_ASSETS,
    },
    "modes": {
        "fallback-focused": {
            "id": "native-screenshot-fallback-focused-v3",
            "result_count": 5,
            "featured_entities": {
                "club": {"id": 202, "name": "Comedy Cellar"},
                "show": {
                    "id": 201,
                    "name": "Taylor Tomlinson & Friends",
                    "headliner": "Taylor Tomlinson",
                },
                "comedian": {"id": 301, "name": "Ali Wong"},
                "podcast": {"id": 401, "name": "History Hyenas"},
                "episode": {"id": 501, "name": "Watch Your Tone with Ryan Sickler | History Hyenas"},
            },
            "dates": {
                "primary_show": PRIMARY_SHOW_DATETIME,
                "secondary_show": SECONDARY_SHOW_DATETIME,
            },
            "artwork": {
                "required_keys": [
                    "ali-wong",
                    "taylor",
                    "comedy-store",
                    "comedy-cellar",
                    "show-friends",
                    "history-hyenas",
                ],
                "fallback_policy": "Missing artwork in authenticated screenshot personas uses each platform's branded fallback; shipping captures may also seed direct production portraits.",
            },
        },
        "curated": {
            "id": "native-screenshot-curated-v3",
            "result_count": 12,
            "featured_entities": {
                "club": {"id": 202, "name": "Comedy Cellar"},
                "show": {
                    "id": 201,
                    "name": "Taylor Tomlinson & Friends",
                    "headliner": "Taylor Tomlinson",
                },
                "comedian": {"id": 301, "name": "Ali Wong"},
                "podcast": {"id": 401, "name": "History Hyenas"},
                "episode": {"id": 501, "name": "Watch Your Tone with Ryan Sickler | History Hyenas"},
            },
            "dates": {
                "primary_show": PRIMARY_SHOW_DATETIME,
                "secondary_show": SECONDARY_SHOW_DATETIME,
            },
            "artwork": {
                "required_keys": [
                    "ali-wong", "taylor-tomlinson", "andrew-schulz", "josh-johnson",
                    "trevor-noah", "sam-jay", "nate-bargatze", "nicole-byer",
                    "hasan-minhaj", "atsuko-okatsuka", "roy-wood-jr", "michelle-wolf",
                    "hollywood-improv", "comedy-cellar", "the-stand", "gotham-comedy-club",
                    "ice-house-comedy-club", "comedy-and-magic-club", "american-comedy-company", "irvine-improv",
                    "cobbs-comedy-club", "laugh-boston", "comedy-vault", "goodnights-comedy-club",
                    "history-hyenas", "jtrain", "wtf", "blocks",
                    "fly-on-the-wall", "we-might-be-drunk", "you-made-it-weird", "honeydew",
                    "joe-rogan", "doug-loves-movies", "bonfire", "are-you-garbage",
                ],
                "categories": {
                    "portraits": [
                        "ali-wong", "taylor-tomlinson", "andrew-schulz", "josh-johnson",
                        "trevor-noah", "sam-jay", "nate-bargatze", "nicole-byer",
                        "hasan-minhaj", "atsuko-okatsuka", "roy-wood-jr", "michelle-wolf"
                    ],
                    "club_logos": [
                        "hollywood-improv", "comedy-cellar", "the-stand", "gotham-comedy-club",
                        "ice-house-comedy-club", "comedy-and-magic-club", "american-comedy-company", "irvine-improv",
                        "cobbs-comedy-club", "laugh-boston", "comedy-vault", "goodnights-comedy-club"
                    ],
                    "podcast_art": [
                        "history-hyenas", "jtrain", "wtf", "blocks",
                        "fly-on-the-wall", "we-might-be-drunk", "you-made-it-weird", "honeydew",
                        "joe-rogan", "doug-loves-movies", "bonfire", "are-you-garbage"
                    ],
                },
                    "url_policy": "Every curated imageUrl is an absolute HTTPS artwork source derived from a public production API record and normalized for native decoding when required; show art follows the production lineup-first, venue-fallback selection rule.",
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
COMEDIAN_ARTWORK = [
    "ali-wong",
    "taylor-tomlinson",
    "andrew-schulz",
    "josh-johnson",
    "trevor-noah",
    "sam-jay",
    "nate-bargatze",
    "nicole-byer",
    "hasan-minhaj",
    "atsuko-okatsuka",
    "roy-wood-jr",
    "michelle-wolf",
]
FALLBACK_COMEDIAN_ARTWORK = ["ali-wong", "taylor"]
CLUB_FIXTURES = [
    {
        "name": "Hollywood Improv",
        "address": "8162 Melrose Ave, Hollywood, CA 90046",
        "zipCode": "90046",
        "city": "Hollywood",
        "state": "CA",
        "artworkKey": "hollywood-improv",
    },
    {
        "name": "Comedy Cellar",
        "address": "117 MacDougal St, New York, NY 10012",
        "zipCode": "10012",
        "city": "New York",
        "state": "NY",
        "artworkKey": "comedy-cellar",
    },
    {
        "name": "The Stand",
        "address": "116 E 16th St, New York, NY 10003",
        "zipCode": "10003",
        "city": "New York",
        "state": "NY",
        "artworkKey": "the-stand",
    },
    {
        "name": "Gotham Comedy Club",
        "address": "208 W 23rd St, New York, NY 10011",
        "zipCode": "10011",
        "city": "New York",
        "state": "NY",
        "artworkKey": "gotham-comedy-club",
    },
    {
        "name": "Ice House Comedy Club",
        "address": "24 N Mentor Ave, Pasadena, CA 91106",
        "zipCode": "91106",
        "city": "Pasadena",
        "state": "CA",
        "artworkKey": "ice-house-comedy-club",
    },
    {
        "name": "The Comedy & Magic Club",
        "address": "1018 Hermosa Ave, Hermosa Beach, CA 90254",
        "zipCode": "90254",
        "city": "Hermosa Beach",
        "state": "CA",
        "artworkKey": "comedy-and-magic-club",
    },
    {
        "name": "American Comedy Company",
        "address": "818 Sixth Ave, San Diego, CA 92101",
        "zipCode": "92101",
        "city": "San Diego",
        "state": "CA",
        "artworkKey": "american-comedy-company",
    },
    {
        "name": "Irvine Improv",
        "address": "527 Spectrum Center Dr, Irvine, CA 92618",
        "zipCode": "92618",
        "city": "Irvine",
        "state": "CA",
        "artworkKey": "irvine-improv",
    },
    {
        "name": "Cobb's Comedy Club",
        "address": "915 Columbus Ave, San Francisco, CA 94133",
        "zipCode": "94133",
        "city": "San Francisco",
        "state": "CA",
        "artworkKey": "cobbs-comedy-club",
    },
    {
        "name": "Laugh Boston",
        "address": "425 Summer St, Boston, MA 02210",
        "zipCode": "02210",
        "city": "Boston",
        "state": "MA",
        "artworkKey": "laugh-boston",
    },
    {
        "name": "The Comedy Vault",
        "address": "18 E Wilson St, Batavia, IL 60510",
        "zipCode": "60510",
        "city": "Batavia",
        "state": "IL",
        "artworkKey": "comedy-vault",
    },
    {
        "name": "Goodnights Comedy Club",
        "address": "401 Woodburn Rd, Raleigh, NC 27605",
        "zipCode": "27605",
        "city": "Raleigh",
        "state": "NC",
        "artworkKey": "goodnights-comedy-club",
    },
]
PODCAST_FIXTURES = [
    ("History Hyenas", "Chris Distefano & Yannis Pappas", "history-hyenas"),
    ("The JTrain Podcast", "Jared Freid", "jtrain"),
    ("WTF with Marc Maron", "Marc Maron", "wtf"),
    ("Blocks w/ Neal Brennan", "Neal Brennan", "blocks"),
    ("Fly on the Wall", "Dana Carvey & David Spade", "fly-on-the-wall"),
    ("We Might Be Drunk", "Sam Morril & Mark Normand", "we-might-be-drunk"),
    ("You Made It Weird", "Pete Holmes", "you-made-it-weird"),
    ("The HoneyDew", "Ryan Sickler", "honeydew"),
    ("The Joe Rogan Experience", "Joe Rogan", "joe-rogan"),
    ("Doug Loves Movies", "Doug Benson", "doug-loves-movies"),
    ("The Bonfire", "Big Jay Oakerson & Robert Kelly", "bonfire"),
    ("Are You Garbage?", "Kevin Ryan & H. Foley", "are-you-garbage"),
]
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
    asset_source = (
        CURATED_HTTPS_ASSETS if mode == CURATED_MODE else ARTWORK_ASSETS
    )
    assets = {key: asset_source[key] for key in contract["artwork"]["required_keys"]}
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


def _artwork_url(base_url: str, key: str, mode: str) -> str:
    if mode == CURATED_MODE:
        return CURATED_HTTPS_ASSETS[key]
    return f"{base_url}/artwork/{key}.png"


def _lineup(
    base_url: str,
    index: int = 1,
    name: str = "Taylor Tomlinson",
    popularity: int = 98,
    show_count: int = 40,
    mode: str = DEFAULT_MODE,
) -> dict:
    entity_id = 301 + index
    artwork_pool = FALLBACK_COMEDIAN_ARTWORK if mode == FALLBACK_MODE else COMEDIAN_ARTWORK
    artwork_key = artwork_pool[index % len(artwork_pool)]
    social_data = _social(entity_id, name.lower().replace(" ", ""))
    social_data["popularity"] = popularity
    return {
        "id": entity_id,
        "uuid": f"fixture-{entity_id}",
        "name": name,
        "imageUrl": _artwork_url(base_url, artwork_key, mode),
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
        "imageUrl": _artwork_url(base_url, artwork_key, mode),
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
    show_date: date | None = None,
    mode: str = DEFAULT_MODE,
    club_id: int = 201,
    club_name: str = "Hollywood Improv",
    club_city: str = "Hollywood",
    club_state: str = "CA",
    club_timezone: str = "America/Los_Angeles",
    utc_offset: str = "-07:00",
    room: str = "Main Room",
    club_artwork_key: str = "hollywood-improv",
) -> dict:
    resolved_date = show_date or (
        PRIMARY_SHOW_DATE if show_id == 101 else SECONDARY_SHOW_DATE
    )
    resolved_lineup = lineup if lineup is not None else [_lineup(base_url, mode=mode)]
    image_url = (
        resolved_lineup[0]["imageUrl"]
        if mode == CURATED_MODE and resolved_lineup
        else _artwork_url(
            base_url,
            club_artwork_key if mode == CURATED_MODE else artwork_key,
            mode,
        )
    )
    return {
        "id": show_id,
        "clubId": club_id,
        "date": f"{resolved_date.isoformat()}T{hour:02d}:00:00{utc_offset}",
        "imageUrl": image_url,
        "clubName": club_name,
        "clubCity": club_city,
        "clubState": club_state,
        "name": name,
        "room": room,
        "timezone": club_timezone,
        "soldOut": False,
        "tickets": [{"price": 40, "purchaseUrl": f"https://example.invalid/tickets/{show_id}", "soldOut": False, "type": "General Admission"}],
        "lineup": resolved_lineup,
    }


def _club_shows(
    base_url: str,
    mode: str = DEFAULT_MODE,
    *,
    id_offset: int = 0,
    club_id: int = 201,
    club_name: str = "Hollywood Improv",
    club_city: str = "Hollywood",
    club_state: str = "CA",
    club_timezone: str = "America/Los_Angeles",
    utc_offset: str = "-07:00",
    room: str = "Main Room",
    club_artwork_key: str = "hollywood-improv",
) -> list[dict]:
    club_kwargs = {
        "club_id": club_id,
        "club_name": club_name,
        "club_city": club_city,
        "club_state": club_state,
        "club_timezone": club_timezone,
        "utc_offset": utc_offset,
        "room": room,
        "club_artwork_key": club_artwork_key,
    }
    taylor = _lineup(base_url, mode=mode)
    ali = _lineup(base_url, 0, "Ali Wong", popularity=96, show_count=36, mode=mode)
    andrew = _lineup(base_url, 2, "Andrew Schulz", popularity=94, show_count=34, mode=mode)
    tonight_artwork = (
        SHOW_ARTWORK if mode == CURATED_MODE else ["show-friends"] * 4
    )
    tonight = [
        _show(
            base_url,
            101 + id_offset,
            "Taylor Tomlinson & Friends",
            20,
            tonight_artwork[0],
            lineup=[taylor],
            show_date=PRIMARY_SHOW_DATE,
            mode=mode,
            **club_kwargs,
        ),
        _show(
            base_url,
            106 + id_offset,
            "Ali Wong: Live",
            19,
            tonight_artwork[1],
            lineup=[ali],
            show_date=PRIMARY_SHOW_DATE,
            mode=mode,
            **club_kwargs,
        ),
        _show(
            base_url,
            107 + id_offset,
            "Andrew Schulz: New Material",
            21,
            tonight_artwork[2],
            lineup=[andrew],
            show_date=PRIMARY_SHOW_DATE,
            mode=mode,
            **club_kwargs,
        ),
        _show(
            base_url,
            108 + id_offset,
            "Late Night with Taylor",
            22,
            tonight_artwork[3],
            lineup=[taylor],
            show_date=PRIMARY_SHOW_DATE,
            mode=mode,
            **club_kwargs,
        ),
    ]
    later = []
    reserved_ids = {show["id"] for show in tonight}
    show_id = 102 + id_offset
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
                SHOW_HOURS[(index + 1) % len(SHOW_HOURS)],
                "show-friends" if mode == FALLBACK_MODE else SHOW_ARTWORK[index % len(SHOW_ARTWORK)],
                # Keep one deterministic, lineup-unannounced showcase so the
                # shipping screenshot matrix exercises dedicated show artwork
                # instead of always preferring a comedian headshot.
                lineup=[] if index == 0 else [lineup],
                show_date=SECONDARY_SHOW_DATE + timedelta(days=index // 5),
                mode=mode,
                **club_kwargs,
            )
        )
        show_id += 1
    return tonight + later


def _comedy_cellar_shows(base_url: str, mode: str = DEFAULT_MODE) -> list[dict]:
    return _club_shows(
        base_url,
        mode,
        id_offset=100,
        club_id=202,
        club_name="Comedy Cellar",
        club_city="New York",
        club_state="NY",
        club_timezone="America/New_York",
        utc_offset="-04:00",
        room="Main Room",
        club_artwork_key="comedy-cellar",
    )


def _club_tonight_shows(base_url: str, mode: str = DEFAULT_MODE) -> list[dict]:
    return [
        show for show in _club_shows(base_url, mode)
        if show["date"].startswith(PRIMARY_SHOW_DATE.isoformat())
    ]


def _comedy_cellar_tonight_shows(
    base_url: str, mode: str = DEFAULT_MODE
) -> list[dict]:
    return [
        show for show in _comedy_cellar_shows(base_url, mode)
        if show["date"].startswith(PRIMARY_SHOW_DATE.isoformat())
    ]


def _podcast_hosts(base_url: str) -> list[dict]:
    return [
        {
            "id": 304,
            "uuid": "fixture-304",
            "name": "Chris Distefano",
            "imageUrl": "https://laughtrack.b-cdn.net/comedians/Chris%20Distefano.png",
        },
        {
            "id": 305,
            "uuid": "fixture-305",
            "name": "Yannis Pappas",
            "imageUrl": "https://laughtrack.b-cdn.net/comedians/Yannis%20Pappas.png",
        },
    ]


def _podcast(base_url: str, mode: str = DEFAULT_MODE) -> dict:
    return {
        "id": 401,
        "slug": "history-hyenas",
        "title": "History Hyenas",
        "episodeCount": 130,
        "hosts": _podcast_hosts(base_url),
        "authorName": "Chris Distefano & Yannis Pappas",
        "websiteUrl": "https://example.invalid/podcasts/history-hyenas",
        "feedUrl": "https://example.invalid/feeds/history-hyenas",
        "imageUrl": _artwork_url(base_url, "history-hyenas", mode),
        "description": "Comedians tear through history's strangest characters, rivalries, and disasters.",
        "isFavorite": False,
    }


def _podcast_episode(base_url: str, mode: str = DEFAULT_MODE) -> dict:
    return {
        "id": 501,
        "title": "Watch Your Tone with Ryan Sickler | History Hyenas",
        # Original episode synopsis, excluding the trailing sponsor/social links.
        "description": "The boys sit down with comedian Ryan Sickler to discuss his new comedy special, near death experiences, and how to monitor your tone when talking your significant other. Check out his new special Live and Alive here: https://www.youtube.com/watch?v=PMGWVyM2NJo",
        "releaseDate": HOME_FEED_EPISODE_RELEASE_DATETIME,
        "durationSeconds": 4654,
        "episodeUrl": None,
        "audioUrl": EPISODE_AUDIO_URL,
        "appearances": [
            *_podcast_hosts(base_url),
            {
                "id": 249148,
                "uuid": "6713c3fbed5bc17713cca3ba90ecd5b0",
                "name": "Ryan Sickler",
                "imageUrl": "https://laughtrack.b-cdn.net/comedian-images/249148/8d0ef3db-606f-4357-84a3-9eee79a9d3b2/avatar.jpg",
            },
        ],
    }


def _home_feed_podcast_episode(base_url: str, mode: str = DEFAULT_MODE) -> dict:
    episode = _podcast_episode(base_url, mode)
    episode["releaseDate"] = HOME_FEED_EPISODE_RELEASE_DATETIME
    podcast = _podcast(base_url, mode)
    guest = episode["appearances"][-1]
    return {
        key: episode[key]
        for key in (
            "id",
            "title",
            "description",
            "releaseDate",
            "durationSeconds",
            "episodeUrl",
            "audioUrl",
        )
    } | {
        "podcast": {
            key: podcast[key]
            for key in ("id", "slug", "title", "imageUrl")
        },
        "recommendation": {
            "reason": "guest_appearance",
            "comedian": guest,
            "appearanceRole": "guest",
            "followedComedian": False,
            "favoritePodcast": False,
        },
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
            "trendingComedians": [{"id": 301, "uuid": "fixture-301", "name": "Ali Wong", "imageUrl": _artwork_url(base_url, "ali-wong", mode), "socialData": _social(301, "aliwong"), "showCount": 28}],
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
            "podcastEpisodes": [_home_feed_podcast_episode(base_url, mode)],
            "trendingPodcasts": [{"id": 401, "slug": "history-hyenas", "title": "History Hyenas", "episodeCount": 130, "authorName": "Chris Distefano & Yannis Pappas", "imageUrl": _artwork_url(base_url, "history-hyenas", mode)}],
            "popularClubs": [{"id": 201, "address": "8162 Melrose Ave, Hollywood, CA", "name": "Hollywood Improv", "imageUrl": _artwork_url(base_url, "hollywood-improv" if mode == CURATED_MODE else "comedy-store", mode), "activeComedianCount": 120, "zipCode": "90046"}],
        }}
    if path == f"{API_PREFIX}shows/search":
        is_pinned_club_search = bool(
            (query or {}).get("club") or (query or {}).get("clubId")
        )
        total = 45 if is_pinned_club_search else result_count
        page = int((query or {}).get("page", ["0"])[0])
        size = int((query or {}).get("size", [str(total)])[0])
        start = max(0, page) * size
        end = min(start + size, total)
        club_query = (query or {}).get("club", [""])[0]
        club_id_query = (query or {}).get("clubId", [""])[0]
        catalog = (
            _comedy_cellar_shows(base_url, mode)
            if "comedy cellar" in club_query.casefold() or club_id_query == "202"
            else _club_shows(base_url, mode)
        )
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
        clubs = [
            {
                "id": 201 + index,
                **{key: value for key, value in club.items() if key != "artworkKey"},
                "imageUrl": _artwork_url(
                    base_url,
                    club["artworkKey"]
                    if mode == CURATED_MODE
                    else ("comedy-cellar" if club["name"] == "Comedy Cellar" else "comedy-store"),
                    mode,
                ),
                "showCount": 120 - index * (10 if mode == FALLBACK_MODE else 5),
                "activeComedianCount": 80 - index,
                "isFavorite": False,
            }
            for index, club in enumerate(CLUB_FIXTURES[:result_count])
        ]
        club_query = (query or {}).get("club", [""])[0].strip().casefold()
        if club_query:
            clubs = [club for club in clubs if club_query in club["name"].casefold()]
        return {"data": clubs, "total": len(clubs), "filters": []}
    if path == f"{API_PREFIX}podcasts/search":
        podcasts = [
            {
                "id": 401 + index,
                "slug": f"fixture-{401 + index}",
                "title": title,
                "episodeCount": 130 - index * 5,
                "hosts": _podcast_hosts(base_url),
                "authorName": author_name,
                "imageUrl": _artwork_url(
                    base_url,
                    artwork_key if mode == CURATED_MODE else "history-hyenas",
                    mode,
                ),
                "description": "Stand-up conversations and new episodes every week.",
                "isFavorite": False,
            }
            for index, (title, author_name, artwork_key) in enumerate(PODCAST_FIXTURES[:result_count])
        ]
        podcast_query = (query or {}).get("q", [""])[0].strip().casefold()
        if podcast_query:
            podcasts = [
                podcast
                for podcast in podcasts
                if podcast_query in podcast["title"].casefold()
            ]
        return {"data": podcasts, "total": len(podcasts), "filters": []}
    if path in {f"{API_PREFIX}clubs/201", f"{API_PREFIX}clubs/202"}:
        club_id = int(path.rsplit("/", 1)[-1])
        club = CLUB_FIXTURES[club_id - 201]
        is_comedy_cellar = club_id == 202
        artwork_key = "comedy-cellar" if is_comedy_cellar else "hollywood-improv"
        if mode == FALLBACK_MODE and not is_comedy_cellar:
            artwork_key = "comedy-store"
        return {
            "data": {
                "id": club_id,
                "name": club["name"],
                "imageUrl": _artwork_url(base_url, artwork_key, mode),
                "heroImageUrl": _artwork_url(base_url, artwork_key, mode),
                "website": (
                    "https://www.comedycellar.com"
                    if is_comedy_cellar
                    else "https://improv.com/hollywood"
                ),
                "address": club["address"],
                "zipCode": club["zipCode"],
                "phoneNumber": (
                    "(212) 254-3480" if is_comedy_cellar else "(323) 651-2583"
                ),
            }
        }
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
    if path == f"{API_PREFIX}clubs/202/highlights":
        return {
            "data": {
                "tonightShows": _comedy_cellar_tonight_shows(base_url, mode),
                "nextShow": _comedy_cellar_shows(base_url, mode)[4],
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
    if path == f"{API_PREFIX}clubs/202/shows":
        return {
            "data": _comedy_cellar_shows(base_url, mode)[:result_count],
            "total": result_count,
        }
    show_detail_prefix = f"{API_PREFIX}shows/"
    if path.startswith(show_detail_prefix) and path.removeprefix(show_detail_prefix).isdigit():
        show_id = int(path.removeprefix(show_detail_prefix))
        all_shows = _club_shows(base_url, mode) + _comedy_cellar_shows(base_url, mode)
        show = next(
            (item for item in all_shows if item["id"] == show_id),
            _show(base_url, show_id, mode=mode),
        )
        club = (
            {"id": 202, "name": "Comedy Cellar", "imageUrl": _artwork_url(base_url, "comedy-cellar", mode), "address": "117 MacDougal St, New York, NY", "timezone": "America/New_York"}
            if show["clubId"] == 202
            else {"id": 201, "name": "Hollywood Improv", "imageUrl": _artwork_url(base_url, "hollywood-improv" if mode == CURATED_MODE else "comedy-store", mode), "address": "8162 Melrose Ave, Hollywood, CA", "timezone": "America/Los_Angeles"}
        )
        return {"data": {**show, "showPageUrl": f"https://example.invalid/show/{show_id}", "club": club, "cta": {"label": "Buy tickets", "isSoldOut": False, "url": f"https://example.invalid/tickets/{show_id}"}, "description": "A special night of new material and surprise guests."}, "relatedShows": []}
    if path == f"{API_PREFIX}comedians/301":
        return {"data": {"id": 301, "uuid": "fixture-301", "name": "Ali Wong", "imageUrl": _artwork_url(base_url, "ali-wong", mode), "socialData": _social(301, "aliwong"), "podcastAppearances": [], "homeLocation": {"city": "San Francisco", "state": "CA", "country": "US"}}}
    if path == f"{API_PREFIX}comedians/301/upcoming-runs":
        return {"data": [{"clubId": 201, "clubName": "Hollywood Improv", "clubImageUrl": _artwork_url(base_url, "hollywood-improv" if mode == CURATED_MODE else "comedy-store", mode), "shows": [_show(base_url, 106, "Ali Wong: Live", 20, mode=mode)]}]}
    if path in {f"{API_PREFIX}comedians/301/co-bill", f"{API_PREFIX}comedians/past-shows"}:
        return {"data": [], **({"total": 0} if path.endswith("past-shows") else {})}
    if path == f"{API_PREFIX}podcasts/401":
        return {
            "podcast": _podcast(base_url, mode),
            "episodes": [_podcast_episode(base_url, mode)],
            "relatedComedians": [
                {
                    "id": 301,
                    "uuid": "fixture-301",
                    "name": "Ali Wong",
                    "imageUrl": _artwork_url(base_url, "ali-wong", mode),
                    "socialData": _social(301, "aliwong"),
                    "showCount": 28,
                    "isFavorite": False,
                }
            ],
        }
    if path == f"{API_PREFIX}podcast-episodes/501":
        return {
            "podcast": _podcast(base_url, mode),
            "episode": _podcast_episode(base_url, mode),
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
    parser.add_argument("--list-curated-assets", action="store_true")
    args = parser.parse_args()
    if args.list_curated_assets:
        for key, url in CURATED_HTTPS_ASSETS.items():
            print(f"{key}\t{url}")
        return 0
    server = FixtureServer((args.host, args.port))
    print(
        f"Fixture server listening on http://{args.host}:{args.port}",
        flush=True,
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
