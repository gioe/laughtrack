"""Tests for Wikimedia image sourcing URL and request policy."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import pytest

from laughtrack.core.services import image_sourcing
from scripts.core import source_comedian_images
from scripts.core import source_club_images


@dataclass
class _FakeResponse:
    payload: Dict[str, Any]

    def raise_for_status(self) -> None:
        pass

    def json(self) -> Dict[str, Any]:
        return self.payload


@dataclass
class _FakePutResponse:
    status_code: int


def _wikidata_payload(image_url: str) -> Dict[str, Any]:
    return {
        "results": {
            "bindings": [
                {
                    "image": {
                        "value": image_url,
                    },
                },
            ],
        },
    }


def test_wikidata_special_filepath_is_converted_to_upload_thumbnail(monkeypatch):
    def fake_get(_url: str, **_kwargs: Any) -> _FakeResponse:
        return _FakeResponse(
            _wikidata_payload(
                "http://commons.wikimedia.org/wiki/Special:FilePath/"
                "Hasan%20Minhaj%20by%20Gage%20Skidmore.jpg",
            ),
        )

    monkeypatch.setattr(image_sourcing.requests, "get", fake_get)

    image_url = image_sourcing._get_wikidata_image_url("Hasan Minhaj")

    filename = "Hasan_Minhaj_by_Gage_Skidmore.jpg"
    digest = hashlib.md5(filename.encode("utf-8")).hexdigest()
    assert image_url == (
        f"https://upload.wikimedia.org/wikipedia/commons/thumb/{digest[0]}/{digest[:2]}/"
        f"{filename}/500px-{filename}"
    )


def test_wikipedia_requests_use_contact_user_agent(monkeypatch):
    captured_headers: List[Optional[Dict[str, str]]] = []

    def fake_get(_url: str, **kwargs: Any) -> _FakeResponse:
        captured_headers.append(kwargs.get("headers"))
        return _FakeResponse(_wikidata_payload("https://example.com/image.jpg"))

    monkeypatch.setattr(image_sourcing.requests, "get", fake_get)

    assert image_sourcing._get_wikidata_image_url("Tig Notaro") == "https://example.com/image.jpg"

    assert captured_headers
    user_agent = captured_headers[0]["User-Agent"]
    assert "LaughTrack/1.0" in user_agent
    assert "gioematt@gmail.com" in user_agent


def test_wikidata_falls_back_to_commons_file_search(monkeypatch):
    calls: List[str] = []

    def fake_get(url: str, **_kwargs: Any) -> _FakeResponse:
        calls.append(url)
        if url == image_sourcing._WIKIDATA_SPARQL_URL:
            return _FakeResponse({"results": {"bindings": []}})
        return _FakeResponse(
            {
                "query": {
                    "pages": {
                        "1": {
                            "title": "File:Not the right person.jpg",
                            "imageinfo": [{"thumburl": "https://upload.wikimedia.org/wrong.jpg"}],
                        },
                        "2": {
                            "title": "File:Josh Wolf 2016.png",
                            "imageinfo": [
                                {
                                    "thumburl": (
                                        "https://upload.wikimedia.org/wikipedia/commons/thumb/5/5c/"
                                        "Josh_Wolf_2016.png/500px-Josh_Wolf_2016.png"
                                    ),
                                },
                            ],
                        },
                    },
                },
            },
        )

    monkeypatch.setattr(image_sourcing.requests, "get", fake_get)

    assert image_sourcing._get_wikidata_image_url("Josh Wolf") == (
        "https://upload.wikimedia.org/wikipedia/commons/thumb/5/5c/"
        "Josh_Wolf_2016.png/500px-Josh_Wolf_2016.png"
    )
    assert calls == [
        image_sourcing._WIKIDATA_SPARQL_URL,
        image_sourcing._COMMONS_API_URL,
    ]


def test_download_uses_contact_user_agent(monkeypatch):
    captured_headers: List[Optional[Dict[str, str]]] = []

    class FakeDownloadResponse:
        content = b"image-bytes"

        def raise_for_status(self) -> None:
            pass

    def fake_get(_url: str, **kwargs: Any) -> FakeDownloadResponse:
        captured_headers.append(kwargs.get("headers"))
        return FakeDownloadResponse()

    monkeypatch.setattr(image_sourcing.requests, "get", fake_get)

    assert image_sourcing._download_image("https://upload.wikimedia.org/example.jpg") == b"image-bytes"

    user_agent = captured_headers[0]["User-Agent"]
    assert "LaughTrack/1.0" in user_agent
    assert "gioematt@gmail.com" in user_agent


def test_default_image_source_delay_is_at_least_commons_crawl_delay():
    assert image_sourcing._IMAGE_SOURCE_DELAY_S >= 5.0
    assert source_comedian_images._IMAGE_SOURCE_DELAY_S >= 5.0


def test_read_names_file_strips_blanks_and_comment_lines(tmp_path):
    names_file = tmp_path / "names.txt"
    names_file.write_text(
        "\n".join(
            [
                "# previously 429ed comedians",
                "Sheryl Underwood",
                "",
                "Hasan Minhaj",
                "  Tig Notaro  ",
            ],
        ),
        encoding="utf-8",
    )

    assert source_comedian_images._read_names_file(names_file) == [
        "Sheryl Underwood",
        "Hasan Minhaj",
        "Tig Notaro",
    ]


def test_load_env_defaults_populates_missing_environment(monkeypatch, tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join(
            [
                "BUNNYCDN_STORAGE_PASSWORD=from-file",
                "BUNNYCDN_STORAGE_ZONE=image-zone",
                "IMAGE_SOURCE_DELAY_S=2",
            ],
        ),
        encoding="utf-8",
    )
    monkeypatch.delenv("BUNNYCDN_STORAGE_PASSWORD", raising=False)
    monkeypatch.delenv("BUNNYCDN_STORAGE_ZONE", raising=False)
    monkeypatch.setenv("IMAGE_SOURCE_DELAY_S", "already-set")

    source_comedian_images._load_env_defaults(env_file)

    assert source_comedian_images.os.environ["BUNNYCDN_STORAGE_PASSWORD"] == "from-file"
    assert source_comedian_images.os.environ["BUNNYCDN_STORAGE_ZONE"] == "image-zone"
    assert source_comedian_images.os.environ["IMAGE_SOURCE_DELAY_S"] == "already-set"


def test_collect_explicit_names_preserves_order_dedups_and_skips_comments(tmp_path):
    names_file = tmp_path / "names.txt"
    names_file.write_text(
        "\n".join(
            [
                "# curated missing-image comedians",
                "  Tig Notaro  ",
                "",
                "Ali Wong",
                "Hasan Minhaj",
                "Ali Wong",
                "  # still a comment after stripping  ",
                "Maria Bamford",
            ],
        ),
        encoding="utf-8",
    )

    assert source_comedian_images._collect_explicit_names(
        ["Hasan Minhaj", "Tig Notaro", "Hasan Minhaj"],
        names_file,
    ) == [
        "Hasan Minhaj",
        "Tig Notaro",
        "Ali Wong",
        "Maria Bamford",
    ]


def test_collect_explicit_names_rejects_unsafe_file_names(tmp_path):
    names_file = tmp_path / "names.txt"
    names_file.write_text("Safe Name\n../escape\n", encoding="utf-8")

    with pytest.raises(SystemExit) as exc:
        source_comedian_images._collect_explicit_names([], names_file)

    assert exc.value.code == 2


def test_collect_explicit_names_rejects_unsafe_cli_names():
    with pytest.raises(SystemExit) as exc:
        source_comedian_images._collect_explicit_names([".hidden"], None)

    assert exc.value.code == 2


def test_get_missing_image_comedians_filters_false_positive_rows():
    class FakeCursor:
        def __init__(self):
            self.query = ""

        def execute(self, query):
            self.query = query

        def fetchall(self):
            return [
                ("Drag",),
                ("Sketch",),
                ("ComedySportz",),
                ("Real Comic",),
                ("Best of",),
                ("Another Comic",),
            ]

    class FakeConnection:
        def __init__(self):
            self.cursor_obj = FakeCursor()

        def cursor(self):
            return self.cursor_obj

    conn = FakeConnection()

    assert source_comedian_images.get_missing_image_comedians(conn, limit=2) == [
        "Real Comic",
        "Another Comic",
    ]
    assert "LIMIT" not in conn.cursor_obj.query


def test_fetch_comedian_image_png_downloads_and_resizes_wikidata_image(monkeypatch):
    calls: List[str] = []

    class FakeDownloadResponse:
        content = b"raw-image"

        def raise_for_status(self) -> None:
            pass

    def fake_get(url: str, **_kwargs: Any):
        calls.append(url)
        if url == image_sourcing._WIKIDATA_SPARQL_URL:
            return _FakeResponse(_wikidata_payload("https://upload.wikimedia.org/example.jpg"))
        return FakeDownloadResponse()

    monkeypatch.setattr(image_sourcing.requests, "get", fake_get)
    monkeypatch.setattr(image_sourcing, "_resize_image", lambda data: b"png:" + data)

    assert image_sourcing.fetch_comedian_image_png("Tig Notaro") == b"png:raw-image"
    assert calls == [
        image_sourcing._WIKIDATA_SPARQL_URL,
        "https://upload.wikimedia.org/example.jpg",
    ]


def test_fetch_comedian_image_png_falls_back_to_tmdb_when_wikidata_has_no_image(monkeypatch):
    calls: List[str] = []

    class FakeDownloadResponse:
        content = b"tmdb-image"

        def raise_for_status(self) -> None:
            pass

    def fake_get(url: str, **_kwargs: Any):
        calls.append(url)
        if url == image_sourcing._WIKIDATA_SPARQL_URL:
            return _FakeResponse({"results": {"bindings": []}})
        if url == image_sourcing._COMMONS_API_URL:
            return _FakeResponse({"query": {"pages": {}}})
        if url == f"{image_sourcing._TMDB_API_URL}/search/person":
            return _FakeResponse({"results": [{"profile_path": "/profile.png"}]})
        return FakeDownloadResponse()

    monkeypatch.setenv("TMDB_API_KEY", "tmdb-key")
    monkeypatch.setattr(image_sourcing.requests, "get", fake_get)
    monkeypatch.setattr(image_sourcing, "_resize_image", lambda data: b"png:" + data)

    assert image_sourcing.fetch_comedian_image_png("Ali Wong") == b"png:tmdb-image"
    assert calls == [
        image_sourcing._WIKIDATA_SPARQL_URL,
        image_sourcing._COMMONS_API_URL,
        f"{image_sourcing._TMDB_API_URL}/search/person",
        f"{image_sourcing._TMDB_IMAGE_BASE}/profile.png",
    ]


def test_upload_comedian_image_png_resizes_and_puts_to_bunny(monkeypatch):
    captured: Dict[str, Any] = {}

    def fake_put(url: str, **kwargs: Any) -> _FakePutResponse:
        captured["url"] = url
        captured["data"] = kwargs["data"]
        captured["headers"] = kwargs["headers"]
        return _FakePutResponse(status_code=201)

    monkeypatch.setenv("BUNNYCDN_STORAGE_PASSWORD", "secret")
    monkeypatch.setenv("BUNNYCDN_STORAGE_ZONE", "laughtrack-images")
    monkeypatch.setenv("BUNNYCDN_STORAGE_REGION", "ny")
    monkeypatch.setattr(image_sourcing, "_resize_image", lambda data: b"resized:" + data)
    monkeypatch.setattr(image_sourcing.requests, "put", fake_put)

    assert image_sourcing.upload_comedian_image_png("Tig Notaro", b"raw-png") is True
    assert captured["url"] == "https://ny.storage.bunnycdn.com/laughtrack-images/comedians/Tig%20Notaro.png"
    assert captured["data"] == b"resized:raw-png"
    assert captured["headers"] == {
        "AccessKey": "secret",
        "Content-Type": "image/png",
    }


def test_main_upload_from_dir_dry_run_dedups_sibling_stems(monkeypatch, tmp_path, capsys):
    review_dir = tmp_path / "reviewed"
    review_dir.mkdir()
    (review_dir / "Ali Wong.jpg").write_bytes(b"jpg")
    (review_dir / "Ali Wong.png").write_bytes(b"png")
    (review_dir / "Tig Notaro.webp").write_bytes(b"webp")
    (review_dir / "notes.txt").write_text("ignored", encoding="utf-8")

    monkeypatch.setattr(source_comedian_images, "_load_env_defaults", lambda: None)
    monkeypatch.setattr(
        source_comedian_images.sys,
        "argv",
        ["source_comedian_images.py", "--upload-from-dir", str(review_dir), "--dry-run"],
    )

    source_comedian_images.main()

    out = capsys.readouterr().out
    assert "Skipping 1 sibling file(s)" in out
    assert "Ali Wong.png (stem already covered by another file)" in out
    assert "Found 2 reviewed image(s)" in out
    assert "Ali Wong  (Ali Wong.jpg)" in out
    assert "Tig Notaro  (Tig Notaro.webp)" in out


@pytest.mark.parametrize(
    "extra_args",
    [
        ["--name", "Ali Wong"],
        ["--names-file", "names.txt"],
        ["--limit", "5"],
        ["--review-dir", "review"],
    ],
)
def test_main_rejects_upload_from_dir_with_targeting_modes(monkeypatch, tmp_path, capsys, extra_args):
    review_dir = tmp_path / "reviewed"
    review_dir.mkdir()
    names_file = tmp_path / "names.txt"
    names_file.write_text("Ali Wong\n", encoding="utf-8")

    monkeypatch.setattr(source_comedian_images, "_load_env_defaults", lambda: None)
    argv_extra = [str(tmp_path / arg) if arg in {"names.txt", "review"} else arg for arg in extra_args]
    monkeypatch.setattr(
        source_comedian_images.sys,
        "argv",
        [
            "source_comedian_images.py",
            "--upload-from-dir",
            str(review_dir),
            *argv_extra,
        ],
    )

    with pytest.raises(SystemExit) as exc:
        source_comedian_images.main()

    assert exc.value.code == 2
    assert "--upload-from-dir cannot be combined" in capsys.readouterr().err


# ---------------------------------------------------------------------------
# Club image sourcing — image_sourcing service helpers
# ---------------------------------------------------------------------------


def test_extract_og_image_prefers_og_over_twitter():
    html = """
    <head>
      <meta name="twitter:image" content="https://example.com/twitter.png">
      <meta property="og:image" content="https://example.com/og.png">
    </head>
    """
    assert image_sourcing._extract_og_image(html) == "https://example.com/og.png"


def test_extract_og_image_falls_back_to_twitter():
    html = '<meta name="twitter:image" content="https://example.com/tw.jpg">'
    assert image_sourcing._extract_og_image(html) == "https://example.com/tw.jpg"


def test_extract_og_image_handles_content_before_property_and_entities():
    # Both named (&amp;) and numeric (&#38;) entities must decode — html.unescape
    # covers the full entity set, unlike a hand-rolled replace chain.
    html = '<meta content="https://example.com/a.png?x=1&amp;y=2&#38;z=3" property="og:image" />'
    assert image_sourcing._extract_og_image(html) == "https://example.com/a.png?x=1&y=2&z=3"


def test_extract_og_image_returns_none_when_absent():
    assert image_sourcing._extract_og_image("<html><body>no meta</body></html>") is None


def test_get_og_image_url_resolves_relative_and_adds_scheme(monkeypatch):
    captured = {}

    def fake_fetch(url):
        captured["url"] = url
        return '<meta property="og:image" content="/img/hero.png">'

    monkeypatch.setattr(image_sourcing, "_fetch_html", fake_fetch)

    result = image_sourcing._get_og_image_url("comedyclub.com")

    # Bare host gets an https:// scheme, and the relative og:image resolves
    # against that page URL.
    assert captured["url"] == "https://comedyclub.com"
    assert result == "https://comedyclub.com/img/hero.png"


def test_get_og_image_url_returns_none_for_blank_website():
    assert image_sourcing._get_og_image_url("") is None
    assert image_sourcing._get_og_image_url(None) is None


def test_find_club_image_source_prefers_website_og_image(monkeypatch):
    monkeypatch.setattr(image_sourcing, "_get_og_image_url", lambda website: "https://c.com/og.png")
    # Places must not be consulted when the website yields an og:image.
    monkeypatch.setattr(
        image_sourcing,
        "_get_google_places_image_url",
        lambda query: (_ for _ in ()).throw(AssertionError("places should not be called")),
    )

    assert image_sourcing.find_club_image_source("Club", "https://c.com") == (
        "website og:image",
        "https://c.com/og.png",
    )


def test_find_club_image_source_falls_back_to_places(monkeypatch):
    monkeypatch.setattr(image_sourcing, "_get_og_image_url", lambda website: None)
    monkeypatch.setattr(
        image_sourcing,
        "_get_google_places_image_url",
        lambda query: "https://lh3.googleusercontent.com/p.png",
    )

    assert image_sourcing.find_club_image_source(
        "Club", "https://c.com", place_query="Club, Austin, TX"
    ) == ("google places", "https://lh3.googleusercontent.com/p.png")


def test_find_club_image_source_skips_places_when_disabled(monkeypatch):
    monkeypatch.setattr(image_sourcing, "_get_og_image_url", lambda website: None)
    monkeypatch.setattr(
        image_sourcing,
        "_get_google_places_image_url",
        lambda query: (_ for _ in ()).throw(AssertionError("places should not be called")),
    )

    # use_places=False is the dry-run path: never spends paid Places quota.
    assert image_sourcing.find_club_image_source("Club", "https://c.com", use_places=False) is None


def test_fetch_club_image_png_downloads_and_resizes(monkeypatch):
    monkeypatch.setattr(
        image_sourcing,
        "find_club_image_source",
        lambda name, website, **kw: ("website og:image", "https://c.com/og.png"),
    )
    monkeypatch.setattr(image_sourcing, "_download_image", lambda url: b"raw")
    monkeypatch.setattr(image_sourcing, "_resize_image", lambda data: b"png:" + data)

    assert image_sourcing.fetch_club_image_png("Club", "https://c.com") == (b"png:raw", "website og:image")


def test_fetch_club_image_png_returns_none_when_no_source(monkeypatch):
    monkeypatch.setattr(image_sourcing, "find_club_image_source", lambda name, website, **kw: None)
    assert image_sourcing.fetch_club_image_png("Club", "https://c.com") is None


def test_upload_club_image_png_puts_to_clubs_path(monkeypatch):
    captured: Dict[str, Any] = {}

    def fake_put(url: str, **kwargs: Any) -> _FakePutResponse:
        captured["url"] = url
        captured["data"] = kwargs["data"]
        return _FakePutResponse(status_code=201)

    monkeypatch.setenv("BUNNYCDN_STORAGE_PASSWORD", "secret")
    monkeypatch.setenv("BUNNYCDN_STORAGE_ZONE", "laughtrack-images")
    monkeypatch.setenv("BUNNYCDN_STORAGE_REGION", "ny")
    monkeypatch.setattr(image_sourcing, "_resize_image", lambda data: b"resized:" + data)
    monkeypatch.setattr(image_sourcing.requests, "put", fake_put)

    assert image_sourcing.upload_club_image_png("Comedy Cellar", b"raw-png") is True
    assert captured["url"] == "https://ny.storage.bunnycdn.com/laughtrack-images/clubs/Comedy%20Cellar.png"
    assert captured["data"] == b"resized:raw-png"


def test_source_club_image_fetches_then_uploads(monkeypatch):
    monkeypatch.setattr(
        image_sourcing, "fetch_club_image_png", lambda name, website, **kw: (b"png", "google places")
    )
    captured: Dict[str, Any] = {}
    monkeypatch.setattr(
        image_sourcing,
        "upload_club_image_png",
        lambda name, data: captured.update(name=name, data=data) or True,
    )

    assert image_sourcing.source_club_image("Club", None, place_query="Club, NY") is True
    assert captured == {"name": "Club", "data": b"png"}


# ---------------------------------------------------------------------------
# Club image sourcing — source_club_images.py script
# ---------------------------------------------------------------------------


class _FakeClubCursor:
    def __init__(self, rows):
        self.rows = rows
        self.query = ""

    def execute(self, query):
        self.query = query

    def fetchall(self):
        return self.rows


class _FakeClubConnection:
    def __init__(self, rows):
        self.cursor_obj = _FakeClubCursor(rows)

    def cursor(self):
        return self.cursor_obj


def test_get_missing_image_clubs_orders_and_builds_place_query():
    rows = [
        ("Comedy Cellar", "https://cc.com", "New York", "NY"),
        ("No Location Club", "https://nlc.com", None, None),
    ]
    conn = _FakeClubConnection(rows)

    clubs = source_club_images.get_missing_image_clubs(conn, limit=5)

    assert clubs[0] == {
        "name": "Comedy Cellar",
        "website": "https://cc.com",
        "place_query": "Comedy Cellar, New York, NY",
    }
    assert clubs[1]["place_query"] == "No Location Club"
    # Idempotency comes from the WHERE filter — only has_image=false rows.
    assert "has_image = false" in conn.cursor_obj.query


def test_main_dry_run_lists_clubs_and_sources_without_writing(monkeypatch, capsys):
    rows = [
        ("Has OG Club", "https://og.com", "Austin", "TX"),
        ("No OG Club", "https://noog.com", None, None),
    ]
    monkeypatch.setattr(source_club_images, "_load_env_defaults", lambda: None)

    class _Ctx:
        def __enter__(self):
            return _FakeClubConnection(rows)

        def __exit__(self, *a):
            return False

    monkeypatch.setattr(source_club_images, "get_connection", lambda: _Ctx())

    def fake_source(name, website, *, place_query=None, use_places=True):
        assert use_places is False  # dry-run never probes Places
        return ("website og:image", "https://og.com/og.png") if name == "Has OG Club" else None

    monkeypatch.setattr(source_club_images, "find_club_image_source", fake_source)
    # Guard: dry-run must not upload or flip has_image.
    monkeypatch.setattr(
        source_club_images,
        "upload_club_image_png",
        lambda *a, **k: (_ for _ in ()).throw(AssertionError("no upload in dry-run")),
    )
    monkeypatch.setattr(
        source_club_images,
        "_update_has_image",
        lambda *a, **k: (_ for _ in ()).throw(AssertionError("no has_image flip in dry-run")),
    )
    monkeypatch.setattr(source_club_images.sys, "argv", ["source_club_images.py", "--dry-run"])

    source_club_images.main()

    out = capsys.readouterr().out
    assert "Found 2 clubs with has_image=false" in out
    assert "Has OG Club — website og:image" in out
    assert "No OG Club — google places (fallback — not probed in dry-run)" in out


def test_main_review_dir_saves_files_without_cdn_or_flag_flip(monkeypatch, tmp_path, capsys):
    rows = [("Comedy Cellar", "https://cc.com", "New York", "NY")]
    review_dir = tmp_path / "club-images"
    monkeypatch.setattr(source_club_images, "_load_env_defaults", lambda: None)

    class _Ctx:
        def __enter__(self):
            return _FakeClubConnection(rows)

        def __exit__(self, *a):
            return False

    monkeypatch.setattr(source_club_images, "get_connection", lambda: _Ctx())
    monkeypatch.setattr(
        source_club_images,
        "fetch_club_image_png",
        lambda name, website, **kw: (b"png-bytes", "website og:image"),
    )
    # Guards: review mode must never touch the CDN or the has_image column.
    monkeypatch.setattr(
        source_club_images,
        "upload_club_image_png",
        lambda *a, **k: (_ for _ in ()).throw(AssertionError("no CDN upload in review mode")),
    )
    monkeypatch.setattr(
        source_club_images,
        "_update_has_image",
        lambda *a, **k: (_ for _ in ()).throw(AssertionError("no has_image flip in review mode")),
    )
    monkeypatch.setattr(
        source_club_images.sys,
        "argv",
        ["source_club_images.py", "--review-dir", str(review_dir)],
    )

    source_club_images.main()

    saved = review_dir / "Comedy Cellar.png"
    assert saved.read_bytes() == b"png-bytes"
    out = capsys.readouterr().out
    assert "CDN upload skipped, has_image not flipped" in out


def test_source_to_review_dir_skips_unsafe_name(tmp_path):
    review_dir = tmp_path / "out"
    review_dir.mkdir()
    club = {"name": "../escape", "website": "https://x.com", "place_query": "x"}

    ok, label = source_club_images._source_to_review_dir(club, review_dir)

    assert ok is False
    assert list(review_dir.iterdir()) == []


def test_main_rejects_upload_from_dir_with_review_dir(monkeypatch, tmp_path, capsys):
    upload_dir = tmp_path / "reviewed"
    upload_dir.mkdir()
    monkeypatch.setattr(source_club_images, "_load_env_defaults", lambda: None)
    monkeypatch.setattr(
        source_club_images.sys,
        "argv",
        [
            "source_club_images.py",
            "--upload-from-dir",
            str(upload_dir),
            "--review-dir",
            str(tmp_path / "review"),
        ],
    )

    with pytest.raises(SystemExit) as exc:
        source_club_images.main()

    assert exc.value.code == 2
    assert "--upload-from-dir cannot be combined" in capsys.readouterr().err


def test_run_upload_from_dir_rejects_unsafe_stem(tmp_path):
    upload_dir = tmp_path / "reviewed"
    upload_dir.mkdir()
    # Stem "a..b" contains parent-traversal characters — must abort the run.
    (upload_dir / "a..b.png").write_bytes(b"x")

    with pytest.raises(SystemExit) as exc:
        source_club_images._run_upload_from_dir(upload_dir, dry_run=False)

    assert exc.value.code == 2


def test_run_upload_from_dir_uploads_and_flips_has_image(monkeypatch, tmp_path, capsys):
    upload_dir = tmp_path / "reviewed"
    upload_dir.mkdir()
    (upload_dir / "Comedy Cellar.png").write_bytes(b"png-bytes")

    uploaded: Dict[str, Any] = {}
    monkeypatch.setattr(
        source_club_images,
        "upload_club_image_png",
        lambda name, data: uploaded.update(name=name, data=data) or True,
    )
    flipped: Dict[str, Any] = {}
    monkeypatch.setattr(
        source_club_images, "_update_has_image", lambda names: flipped.update(names=list(names))
    )

    source_club_images._run_upload_from_dir(upload_dir, dry_run=False)

    assert uploaded == {"name": "Comedy Cellar", "data": b"png-bytes"}
    # has_image flip happens only after a successful upload, keyed on the stem.
    assert flipped == {"names": ["Comedy Cellar"]}
    assert "Uploaded:  1" in capsys.readouterr().out
