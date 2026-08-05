from __future__ import annotations

import hashlib
import json
import threading
import urllib.error
import urllib.request

import pytest

from scripts.screenshots.fixture_server import (
    ARTWORK_ASSETS,
    ASSET_ROOT,
    CONTENT_FIXTURE,
    CURATED_MODE,
    DEFAULT_MODE,
    FALLBACK_MODE,
    FixtureServer,
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


def test_default_mode_uses_curated_artwork_for_every_shipping_profile() -> None:
    contract = CONTENT_FIXTURE["modes"][DEFAULT_MODE]

    assert DEFAULT_MODE == CURATED_MODE
    assert set(CONTENT_FIXTURE["profile_modes"].values()) == {CURATED_MODE}
    assert contract["result_count"] == 12
    for path in SEARCH_PATHS:
        payload = fixture_response(path, "http://fixture")
        assert len(payload["data"]) == 12
        assert payload["total"] == 12


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


def test_club_highlights_fixture_populates_tonight_and_qualified_performers() -> None:
    payload = fixture_response("/api/v1/clubs/201/highlights", "http://fixture")
    highlights = payload["data"]

    assert [show["id"] for show in highlights["tonightShows"]] == [106, 101, 107, 108]
    assert [
        show["lineup"][0]["name"] for show in highlights["tonightShows"]
    ] == ["Ali Wong", "Taylor Tomlinson", "Andrew Schulz", "Taylor Tomlinson"]
    assert highlights["tonightShows"][1]["lineup"][0]["socialData"]["popularity"] == 98
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
