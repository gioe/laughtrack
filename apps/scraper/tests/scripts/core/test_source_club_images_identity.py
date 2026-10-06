"""Photo candidates cannot establish or replace a venue's Google identity."""

import json
import os
from contextlib import contextmanager
from copy import deepcopy

import psycopg2
import pytest

from laughtrack.core.services import image_sourcing as images
from scripts.core import source_club_images as script


@pytest.fixture
def club():
    return dict(
        id=41,
        name="Whiplash",
        website="https://whiplash.example",
        place_query="Whiplash, Atlanta, GA",
        google_place_id="verified-atlanta",
    )


@pytest.fixture
def candidate():
    return images.ClubImageCandidate(
        "google places",
        "https://lh3.googleusercontent.com/photo",
        "verified-atlanta",
        [{"displayName": "Venue photographer"}],
    )


@pytest.mark.parametrize(
    "returned_id", ["union-hall-brooklyn", "ponce-city-market-building", "similarly-named-club", None]
)
def test_existing_identity_rejects_other_photos_before_download(monkeypatch, returned_id):
    monkeypatch.setattr(images, "_get_og_image_url", lambda _: None)
    monkeypatch.setattr(
        images,
        "_get_google_places_photo",
        lambda _: images.PlacesPhotoResult("https://lh3.googleusercontent.com/wrong", returned_id, []),
    )
    monkeypatch.setattr(images, "_download_image", lambda _: pytest.fail("Rejected photo downloaded"))
    assert images.fetch_club_image_png("Whiplash", None, expected_place_id="verified-atlanta") is None


@pytest.mark.parametrize("unknown_id", [None, "", "   "])
def test_unknown_business_identity_does_not_adopt_a_search_match(monkeypatch, unknown_id):
    monkeypatch.setattr(images, "_get_og_image_url", lambda _: None)
    monkeypatch.setattr(images, "_get_google_places_photo", lambda _: pytest.fail("Unknown identity searched"))
    assert images.fetch_club_image_png("Whiplash", None, expected_place_id=unknown_id) is None


def test_same_identity_keeps_photo_and_author_attribution(monkeypatch):
    monkeypatch.setattr(images, "_get_og_image_url", lambda _: None)
    monkeypatch.setattr(
        images,
        "_get_google_places_photo",
        lambda _: images.PlacesPhotoResult(
            "https://lh3.googleusercontent.com/correct", "verified-atlanta", [{"displayName": "Photographer"}]
        ),
    )
    monkeypatch.setattr(images, "_download_image", lambda _: b"original")
    monkeypatch.setattr(images, "_resize_image", lambda b: b"png:" + b)
    png, selected = images.fetch_club_image_png("Whiplash", None, expected_place_id="verified-atlanta")
    assert png == b"png:original"
    assert selected.place_id == "verified-atlanta"
    assert selected.attributions == [{"displayName": "Photographer"}]


def test_unknown_identity_can_still_use_its_own_website(monkeypatch):
    monkeypatch.setattr(images, "_get_og_image_url", lambda _: "https://venue.example/photo")
    monkeypatch.setattr(images, "_get_google_places_photo", lambda _: pytest.fail("Google not needed"))
    result = images.find_club_image_source("Whiplash", "https://venue.example", expected_place_id=None)
    assert result.source_label == "website og:image" and result.place_id is None


def test_review_only_stages_photo_and_attribution_without_db_writes(monkeypatch, tmp_path, club, candidate):
    before = deepcopy(club)
    monkeypatch.setattr(script, "fetch_club_image_png", lambda *a, **k: (b"image", candidate))
    monkeypatch.setattr(script, "get_transaction", lambda: pytest.fail("Review mutated database"))
    monkeypatch.setattr(script, "upload_club_image_png", lambda *a: pytest.fail("Review published image"))
    assert script._source_to_review_dir(club, tmp_path) == (True, "google places")
    assert club == before
    assert (tmp_path / "Whiplash.png").read_bytes() == b"image"
    provenance = json.loads((tmp_path / "Whiplash.png.json").read_text())
    assert provenance["club_id"] == 41 and provenance["place_id"] == "verified-atlanta"
    assert provenance["attributions"] == candidate.attributions


def test_dry_run_does_not_mutate_established_identity_or_probe_google(monkeypatch, club):
    before = deepcopy(club)
    monkeypatch.setattr(images, "_get_og_image_url", lambda _: None)
    monkeypatch.setattr(images, "_get_google_places_photo", lambda _: pytest.fail("Paid Google request"))
    monkeypatch.setattr(script, "get_transaction", lambda: pytest.fail("Dry run wrote database"))
    monkeypatch.setattr(script, "upload_club_image_png", lambda *a: pytest.fail("Dry run uploaded"))
    script._print_dry_run([club])
    assert club == before


@pytest.fixture
def database(monkeypatch):
    dsn = os.environ.get("TEST_DATABASE_URL")
    if not dsn:
        pytest.skip("TEST_DATABASE_URL required for isolated PostgreSQL image identity checks")
    conn = psycopg2.connect(dsn)
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TEMP TABLE clubs (
                id int PRIMARY KEY, name text, website text, city text, state text,
                google_place_id text, google_place_attribution jsonb, has_image boolean,
                popularity int DEFAULT 0, total_shows int DEFAULT 0, visible boolean DEFAULT true
            );
            INSERT INTO clubs(id,name,website,city,state,google_place_id,google_place_attribution,has_image)
            VALUES(41,'Whiplash','https://whiplash.example','Atlanta','GA','verified-atlanta',
                   '[{"displayName":"Previous photographer"}]',false);
        """)

    @contextmanager
    def connection():
        yield conn

    monkeypatch.setattr(script, "get_connection", connection)
    monkeypatch.setattr(script, "get_transaction", connection)
    try:
        yield conn
    finally:
        conn.rollback()
        conn.close()


def stored(database):
    with database.cursor() as cur:
        cur.execute("SELECT google_place_id,google_place_attribution,has_image FROM clubs WHERE id=41")
        return cur.fetchone()


def test_review_then_publish_preserves_identity_and_publishes_attribution(database, monkeypatch, tmp_path, candidate):
    club = script.get_missing_image_clubs(database)[0]
    before = stored(database)
    monkeypatch.setattr(script, "fetch_club_image_png", lambda *a, **k: (b"image", candidate))
    assert script._source_to_review_dir(club, tmp_path)[0]
    assert stored(database) == before
    uploads = []
    monkeypatch.setattr(script, "upload_club_image_png", lambda name, png: uploads.append((name, png)) or True)
    script._run_upload_from_dir(tmp_path, dry_run=True)
    assert stored(database) == before and not uploads
    script._run_upload_from_dir(tmp_path, dry_run=False)
    assert uploads == [("Whiplash", b"image")]
    assert stored(database) == ("verified-atlanta", candidate.attributions, True)


@pytest.mark.parametrize("change", ["identity", "name", "bytes", "missing-sidecar", "candidate-id"])
def test_staged_photo_conflicts_are_rejected_before_upload(database, monkeypatch, tmp_path, candidate, change):
    club = script.get_missing_image_clubs(database)[0]
    monkeypatch.setattr(script, "fetch_club_image_png", lambda *a, **k: (b"image", candidate))
    assert script._source_to_review_dir(club, tmp_path)[0]
    if change in ("identity", "name"):
        with database.cursor() as cur:
            cur.execute(
                "UPDATE clubs SET " + ("google_place_id='different'" if change == "identity" else "name='Renamed'")
            )
    elif change == "bytes":
        (tmp_path / "Whiplash.png").write_bytes(b"changed")
    elif change == "missing-sidecar":
        (tmp_path / "Whiplash.png.json").unlink()
    else:
        sidecar = tmp_path / "Whiplash.png.json"
        data = json.loads(sidecar.read_text())
        data["place_id"] = "unrelated-brooklyn"
        sidecar.write_text(json.dumps(data))
    before = stored(database)
    monkeypatch.setattr(script, "upload_club_image_png", lambda *a: pytest.fail("Conflicting image published"))
    script._run_upload_from_dir(tmp_path, dry_run=False)
    assert stored(database) == before


@pytest.mark.parametrize("website", [False, True])
def test_upload_failure_keeps_previous_identity_attribution_and_status(database, monkeypatch, candidate, website):
    club = script.get_missing_image_clubs(database)[0]
    if website:
        candidate = images.ClubImageCandidate("website og:image", "https://whiplash.example/photo")
    before = stored(database)
    monkeypatch.setattr(script, "fetch_club_image_png", lambda *a, **k: (b"image", candidate))
    monkeypatch.setattr(script, "upload_club_image_png", lambda *a: False)
    assert not script._source_to_cdn(club)[0]
    assert stored(database) == before


def test_website_publication_clears_old_photo_attribution_without_touching_identity(database, monkeypatch):
    club = script.get_missing_image_clubs(database)[0]
    candidate = images.ClubImageCandidate("website og:image", "https://whiplash.example/photo")
    monkeypatch.setattr(script, "fetch_club_image_png", lambda *a, **k: (b"image", candidate))
    monkeypatch.setattr(script, "upload_club_image_png", lambda *a: True)
    assert script._source_to_cdn(club)[0]
    assert stored(database) == ("verified-atlanta", [], True)
