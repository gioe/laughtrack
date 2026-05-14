"""Tests for Wikimedia image sourcing URL and request policy."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from laughtrack.core.services import image_sourcing
from scripts.core import source_comedian_images


@dataclass
class _FakeResponse:
    payload: Dict[str, Any]

    def raise_for_status(self) -> None:
        pass

    def json(self) -> Dict[str, Any]:
        return self.payload


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
