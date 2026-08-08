from __future__ import annotations

import hashlib
import json
import re
import threading
import urllib.error
import urllib.request
from datetime import date, datetime, timedelta
from pathlib import Path

import pytest

from scripts.screenshots.fixture_server import (
    ARTWORK_ASSETS,
    ASSET_ROOT,
    CONTENT_FIXTURE,
    CURATED_MODE,
    DEFAULT_MODE,
    EPISODE_RELEASE_DATE,
    FALLBACK_MODE,
    FixtureServer,
    HOME_FEED_EPISODE_RELEASE_DATETIME,
    PRIMARY_SHOW_DATE,
    REVIEW_ANCHOR_DATE,
    SECONDARY_SHOW_DATE,
    artwork_png,
    fixture_mode_fingerprint,
    fixture_response,
)


SEARCH_PATHS = (
    "/api/v1/shows/search",
    "/api/v1/comedians/search",
    "/api/v1/clubs/search",
    "/api/v1/podcasts/search",
)
CATALOG_PATH = Path(__file__).resolve().parents[3] / "screenshots" / "catalog.json"
IOS_OPENAPI_PATH = (
    Path(__file__).resolve().parents[3]
    / "ios"
    / "Sources"
    / "LaughTrackAPIClient"
    / "openapi.json"
)
TIMEZONE_SUFFIX = re.compile(r"(?:Z|[+-]\d{2}:\d{2})$")


@pytest.fixture
def fixture_server() -> str:
    server = FixtureServer(("127.0.0.1", 0))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


def get_json(url: str) -> dict:
    with urllib.request.urlopen(url) as response:
        return json.loads(response.read())


def artwork_keys(value: object) -> set[str]:
    if isinstance(value, dict):
        return set().union(*(artwork_keys(item) for item in value.values()))
    if isinstance(value, list):
        return set().union(*(artwork_keys(item) for item in value))
    if isinstance(value, str) and value.startswith("http://fixture/artwork/"):
        return {value.rsplit("/", 1)[-1].removesuffix(".png")}
    return set()


def validate_openapi_value(
    value: object,
    schema: dict,
    document: dict,
    path: str = "$",
) -> None:
    if "$ref" in schema:
        ref = schema["$ref"]
        assert ref.startswith("#/"), f"{path}: unsupported schema reference {ref}"
        resolved: object = document
        for segment in ref.removeprefix("#/").split("/"):
            assert isinstance(resolved, dict), f"{path}: invalid schema reference {ref}"
            resolved = resolved[segment]
        assert isinstance(resolved, dict), f"{path}: schema reference is not an object"
        validate_openapi_value(value, resolved, document, path)
        return

    declared_types = schema.get("type")
    if isinstance(declared_types, str):
        declared_types = [declared_types]
    if declared_types is None:
        declared_types = []

    if value is None:
        assert "null" in declared_types, f"{path}: null is not allowed"
        return

    type_checks = {
        "object": lambda candidate: isinstance(candidate, dict),
        "array": lambda candidate: isinstance(candidate, list),
        "string": lambda candidate: isinstance(candidate, str),
        "integer": lambda candidate: isinstance(candidate, int)
        and not isinstance(candidate, bool),
        "number": lambda candidate: isinstance(candidate, (int, float))
        and not isinstance(candidate, bool),
        "boolean": lambda candidate: isinstance(candidate, bool),
    }
    non_null_types = [item for item in declared_types if item != "null"]
    assert not non_null_types or any(
        type_checks[item](value) for item in non_null_types
    ), f"{path}: expected {declared_types}, got {type(value).__name__}"

    if isinstance(value, dict):
        missing = set(schema.get("required", [])) - set(value)
        assert not missing, f"{path}: missing required properties {sorted(missing)}"
        for key, child_schema in schema.get("properties", {}).items():
            if key in value:
                validate_openapi_value(
                    value[key], child_schema, document, f"{path}.{key}"
                )

    if isinstance(value, list) and "items" in schema:
        for index, item in enumerate(value):
            validate_openapi_value(
                item, schema["items"], document, f"{path}[{index}]"
            )

    if schema.get("format") == "date-time":
        assert isinstance(value, str)
        assert TIMEZONE_SUFFIX.search(value), (
            f"{path}: date-time must include Z or a numeric timezone offset"
        )
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        assert parsed.tzinfo is not None, f"{path}: date-time must include a timezone"


def test_default_mode_uses_curated_artwork_for_every_shipping_profile() -> None:
    contract = CONTENT_FIXTURE["modes"][DEFAULT_MODE]

    assert DEFAULT_MODE == CURATED_MODE
    assert set(CONTENT_FIXTURE["profile_modes"].values()) == {CURATED_MODE}
    assert contract["result_count"] == 12
    for path in SEARCH_PATHS:
        payload = fixture_response(path, "http://fixture")
        assert len(payload["data"]) == 12
        assert payload["total"] == 12


def test_shipping_profiles_share_storefront_narrative() -> None:
    catalog = json.loads(CATALOG_PATH.read_text())
    catalog_fixture = catalog["content_fixture"]
    shipping_profile_ids = {
        profile["id"] for profile in catalog["profiles"] if profile["shipping"]
    }
    shipping_modes = {
        profile_id: catalog_fixture["profile_modes"][profile_id]
        for profile_id in shipping_profile_ids
    }
    shipping_contracts = [
        catalog_fixture["modes"][mode] for mode in shipping_modes.values()
    ]

    assert catalog_fixture == CONTENT_FIXTURE
    assert shipping_profile_ids == {
        "ios_phone",
        "android_phone",
        "android_small_tablet",
        "android_large_tablet",
    }
    assert FALLBACK_MODE not in shipping_modes.values()
    assert {contract["result_count"] for contract in shipping_contracts} == {12}
    assert {
        json.dumps(contract["featured_entities"], sort_keys=True)
        for contract in shipping_contracts
    } == {
        json.dumps(
            CONTENT_FIXTURE["modes"][CURATED_MODE]["featured_entities"],
            sort_keys=True,
        )
    }
    assert all(
        contract["featured_entities"]["show"] == {
            "id": 101,
            "name": "Taylor Tomlinson & Friends",
            "headliner": "Taylor Tomlinson",
        }
        for contract in shipping_contracts
    )


def test_fixture_dates_are_plausible_and_deterministic() -> None:
    review_anchor = date.fromisoformat(CONTENT_FIXTURE["review_anchor_date"])
    assert REVIEW_ANCHOR_DATE == review_anchor
    assert PRIMARY_SHOW_DATE == date(2026, 8, 14)
    assert SECONDARY_SHOW_DATE == date(2026, 8, 15)
    assert EPISODE_RELEASE_DATE == date(2026, 8, 1)

    payloads = {}
    for mode, contract in CONTENT_FIXTURE["modes"].items():
        first = fixture_response("/api/v1/shows/search", "http://fixture", mode)
        repeated = fixture_response("/api/v1/shows/search", "http://fixture", mode)
        assert first == repeated
        payloads[mode] = first

        contract_dates = {
            key: datetime.fromisoformat(value)
            for key, value in contract["dates"].items()
        }
        shows_by_id = {show["id"]: show for show in first["data"]}
        assert (
            datetime.fromisoformat(shows_by_id[101]["date"])
            == contract_dates["primary_show"]
        )
        assert (
            datetime.fromisoformat(shows_by_id[102]["date"])
            == contract_dates["secondary_show"]
        )
        assert 0 < (contract_dates["primary_show"].date() - review_anchor).days <= 30
        assert 0 < (contract_dates["secondary_show"].date() - review_anchor).days <= 30
        assert all(
            review_anchor
            < datetime.fromisoformat(show["date"]).date()
            <= review_anchor + timedelta(days=30)
            for show in first["data"]
        )

        episode = fixture_response(
            "/api/v1/podcast-episodes/501", "http://fixture", mode
        )["episode"]
        release_date = date.fromisoformat(episode["releaseDate"])
        assert release_date == EPISODE_RELEASE_DATE
        assert review_anchor - timedelta(days=30) <= release_date <= review_anchor

    assert [show["date"] for show in payloads[CURATED_MODE]["data"][:5]] == [
        show["date"] for show in payloads[FALLBACK_MODE]["data"]
    ]


def test_fallback_focused_mode_remains_available_for_targeted_verification() -> None:
    contract = CONTENT_FIXTURE["modes"][FALLBACK_MODE]
    referenced_artwork: set[str] = set()

    assert FALLBACK_MODE not in CONTENT_FIXTURE["profile_modes"].values()
    assert contract["result_count"] == 5
    assert contract["artwork"]["fallback_policy"]
    for path in SEARCH_PATHS:
        payload = fixture_response(path, "http://fixture", FALLBACK_MODE)
        assert len(payload["data"]) == 5
        assert payload["total"] == 5
        referenced_artwork.update(artwork_keys(payload))
    assert referenced_artwork == set(contract["artwork"]["required_keys"])


def test_home_feed_includes_personalized_followed_comedian_shows() -> None:
    home = fixture_response("/api/v1/home/feed", "http://fixture")["data"]

    assert [show["id"] for show in home["followedComedianShows"]] == [104]
    assert home["followedComedianShows"][0]["name"] == "Late Night at The Store"


def test_home_feed_includes_deterministic_podcast_episode_discovery() -> None:
    home = fixture_response("/api/v1/home/feed", "http://fixture")["data"]

    assert len(home["podcastEpisodes"]) == 1
    episode = home["podcastEpisodes"][0]
    assert episode["id"] == 501
    assert episode["title"] == "#2520 - A Night of Comedy"
    assert episode["releaseDate"] == HOME_FEED_EPISODE_RELEASE_DATETIME
    assert episode["durationSeconds"] == 8940
    assert episode["audioUrl"] == "https://example.invalid/audio/501.mp3"
    assert episode["podcast"] == {
        "id": 401,
        "slug": "joe-rogan-experience",
        "title": "The Joe Rogan Experience",
        "imageUrl": "http://fixture/artwork/joe-rogan.png",
    }
    assert episode["recommendation"] == {
        "reason": "guest_appearance",
        "comedian": {
            "id": 301,
            "uuid": "fixture-301",
            "name": "Ali Wong",
            "imageUrl": "http://fixture/artwork/ali-wong.png",
        },
        "appearanceRole": "guest",
        "followedComedian": False,
        "favoritePodcast": False,
    }


def test_home_feed_fixture_matches_current_ios_openapi_schema() -> None:
    document = json.loads(IOS_OPENAPI_PATH.read_text())
    home_feed_schema = document["paths"]["/home/feed"]["get"]["responses"]["200"][
        "content"
    ]["application/json"]["schema"]
    payload = fixture_response("/api/v1/home/feed", "http://fixture")

    validate_openapi_value(payload, home_feed_schema, document)


def test_club_highlights_fixture_populates_tonight_and_qualified_performers() -> None:
    payload = fixture_response("/api/v1/clubs/201/highlights", "http://fixture")
    highlights = payload["data"]

    assert [show["id"] for show in highlights["tonightShows"]] == [101, 106, 107, 108]
    assert [
        show["lineup"][0]["name"] for show in highlights["tonightShows"]
    ] == ["Taylor Tomlinson", "Ali Wong", "Andrew Schulz", "Taylor Tomlinson"]
    assert highlights["tonightShows"][0]["lineup"][0]["socialData"]["popularity"] == 98
    assert highlights["nextShow"]["id"] == 102
    assert highlights["nextShow"]["lineup"] == []
    assert highlights["nextShow"]["imageUrl"].endswith("/artwork/show-friends.png")
    assert len(highlights["frequentPerformers"]) == 3
    assert [performer["id"] for performer in highlights["frequentPerformers"]] == [
        301,
        302,
        303,
    ]

    for show_id in (101, 106, 107):
        detail = fixture_response(f"/api/v1/shows/{show_id}", "http://fixture")
        assert detail["data"]["id"] == show_id
        assert detail["data"]["club"]["id"] == 201


def test_pinned_club_show_search_supports_multiple_pages() -> None:
    first = fixture_response(
        "/api/v1/shows/search",
        "http://fixture",
        query={"club": ["The Comedy Store"], "page": ["0"], "size": ["5"]},
    )
    second = fixture_response(
        "/api/v1/shows/search",
        "http://fixture",
        query={"club": ["The Comedy Store"], "page": ["1"], "size": ["5"]},
    )
    last = fixture_response(
        "/api/v1/shows/search",
        "http://fixture",
        query={"club": ["The Comedy Store"], "page": ["8"], "size": ["5"]},
    )

    assert first["total"] == second["total"] == last["total"] == 45
    assert len(first["data"]) == len(second["data"]) == 5
    assert len(last["data"]) == 5
    assert {show["id"] for show in first["data"]}.isdisjoint(
        show["id"] for show in second["data"]
    )

    highlights = fixture_response(
        "/api/v1/clubs/201/highlights", "http://fixture"
    )["data"]
    assert highlights["tonightShows"] == first["data"][:4]


def test_every_mode_declares_the_deterministic_episode_entity() -> None:
    for contract in CONTENT_FIXTURE["modes"].values():
        assert contract["featured_entities"]["episode"] == {
            "id": 501,
            "name": "#2520 - A Night of Comedy",
        }


def test_episode_detail_matches_catalog_and_populates_lineup_media() -> None:
    podcast_detail = fixture_response("/api/v1/podcasts/401", "http://fixture")
    episode_detail = fixture_response("/api/v1/podcast-episodes/501", "http://fixture")

    assert set(episode_detail) == {"podcast", "episode"}
    assert episode_detail["podcast"] == podcast_detail["podcast"]
    assert episode_detail["episode"] == podcast_detail["episodes"][0]

    podcast = episode_detail["podcast"]
    episode = episode_detail["episode"]
    assert podcast["id"] == 401
    assert podcast["imageUrl"] == "http://fixture/artwork/joe-rogan.png"
    assert [host["name"] for host in podcast["hosts"]] == ["Joe Rogan"]
    assert episode["id"] == 501
    assert episode["audioUrl"] == "https://example.invalid/audio/501.mp3"
    assert episode["episodeUrl"] == "https://example.invalid/episodes/501"
    assert episode["description"]
    assert episode["durationSeconds"] == 8940
    assert [appearance["name"] for appearance in episode["appearances"]] == [
        "Joe Rogan",
        "Ali Wong",
    ]
    host_ids = {host["id"] for host in podcast["hosts"]}
    assert [
        appearance["name"]
        for appearance in episode["appearances"]
        if appearance["id"] not in host_ids
    ] == ["Ali Wong"]


def test_episode_detail_is_served_at_the_exact_native_api_path(
    fixture_server: str,
) -> None:
    response = get_json(f"{fixture_server}/api/v1/podcast-episodes/501")

    assert response["podcast"]["id"] == 401
    assert response["episode"]["id"] == 501


def test_curated_mode_populates_dense_search_results_with_distinct_artwork() -> None:
    contract = CONTENT_FIXTURE["modes"][CURATED_MODE]
    referenced_artwork: set[str] = set()

    assert contract["result_count"] == 12
    for path in SEARCH_PATHS:
        payload = fixture_response(path, "http://fixture", CURATED_MODE)
        assert len(payload["data"]) == 12
        assert payload["total"] == 12
        referenced_artwork.update(artwork_keys(payload))

    required = set(contract["artwork"]["required_keys"])
    assert required == {
        key
        for category in contract["artwork"]["categories"].values()
        for key in category
    }
    assert required == referenced_artwork
    assert len({artwork_png(key) for key in required}) == len(required)
    assert all(artwork_png(key).startswith(b"\x89PNG\r\n\x1a\n") for key in required)


def test_curated_artwork_contract_matches_bundled_checksummed_files() -> None:
    declared_files = {metadata["filename"] for metadata in ARTWORK_ASSETS.values()}

    assert set(ASSET_ROOT.glob("*.png")) == {
        ASSET_ROOT / filename for filename in declared_files
    }
    assert set(CONTENT_FIXTURE["artwork"]["assets"]) == set(ARTWORK_ASSETS)
    for key, metadata in ARTWORK_ASSETS.items():
        body = artwork_png(key)
        assert hashlib.sha256(body).hexdigest() == metadata["sha256"]
        assert metadata["width"] == metadata["height"] == 640


def test_artwork_endpoint_serves_bundled_bytes_and_rejects_unknown_keys(
    fixture_server: str,
) -> None:
    with urllib.request.urlopen(f"{fixture_server}/artwork/ali-wong.png") as response:
        assert response.headers.get_content_type() == "image/png"
        assert response.read() == artwork_png("ali-wong")

    with pytest.raises(urllib.error.HTTPError) as error:
        urllib.request.urlopen(f"{fixture_server}/artwork/not-declared.png")
    assert error.value.code == 404


def test_mode_fingerprints_are_stable_and_distinct() -> None:
    fallback = fixture_mode_fingerprint(FALLBACK_MODE)
    curated = fixture_mode_fingerprint(CURATED_MODE)

    assert len(fallback) == 64
    assert len(curated) == 64
    assert fallback == fixture_mode_fingerprint(FALLBACK_MODE)
    assert curated == fixture_mode_fingerprint(CURATED_MODE)
    assert fallback != curated


def test_control_endpoint_configures_server_mode(fixture_server: str) -> None:
    assert get_json(f"{fixture_server}/fixture/status")["mode"] == CURATED_MODE

    configured = get_json(f"{fixture_server}/fixture/configure?mode={FALLBACK_MODE}")
    assert configured == {
        "mode": FALLBACK_MODE,
        "result_count": 5,
        "fingerprint": fixture_mode_fingerprint(FALLBACK_MODE),
        "required_assets": CONTENT_FIXTURE["modes"][FALLBACK_MODE]["artwork"]["required_keys"],
    }
    assert get_json(f"{fixture_server}/fixture/status") == configured
    assert len(get_json(f"{fixture_server}/api/v1/shows/search")["data"]) == 5


def test_control_endpoint_rejects_unknown_mode_without_changing_state(fixture_server: str) -> None:
    with pytest.raises(urllib.error.HTTPError) as error:
        get_json(f"{fixture_server}/fixture/configure?mode=unknown")

    assert error.value.code == 400
    assert get_json(f"{fixture_server}/fixture/status")["mode"] == CURATED_MODE
