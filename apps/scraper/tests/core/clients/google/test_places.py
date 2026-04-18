"""Tests for GooglePlacesClient — weekdayDescription parsing + HTTP flow."""

from unittest.mock import MagicMock, patch

import pytest
import requests

from laughtrack.core.clients.google.places import (
    GooglePlacesClient,
    PlacesHoursResult,
    parse_weekday_descriptions,
)


# ---------------------------------------------------------------------------
# parse_weekday_descriptions
# ---------------------------------------------------------------------------


def test_parse_standard_weekday_text():
    descs = [
        "Monday: 5:00 PM \u2013 11:00 PM",
        "Tuesday: 5:00 PM \u2013 11:00 PM",
        "Friday: 6:00 PM \u2013 2:00 AM",
    ]
    assert parse_weekday_descriptions(descs) == {
        "monday": "5pm-11pm",
        "tuesday": "5pm-11pm",
        "friday": "6pm-2am",
    }


def test_parse_preserves_minutes_when_nonzero():
    descs = ["Saturday: 5:30 PM \u2013 11:45 PM"]
    assert parse_weekday_descriptions(descs) == {"saturday": "5:30pm-11:45pm"}


def test_parse_tolerates_narrow_nbsp_before_ampm():
    # Google's weekdayDescriptions embed U+202F (narrow no-break space)
    # between the time and AM/PM — parsing must survive them.
    descs = ["Wednesday: 7:00\u202fPM\u2009\u2013\u20099:00\u202fPM"]
    assert parse_weekday_descriptions(descs) == {"wednesday": "7pm-9pm"}


def test_parse_handles_hyphen_fallback():
    descs = ["Thursday: 8:00 PM - 10:00 PM"]
    assert parse_weekday_descriptions(descs) == {"thursday": "8pm-10pm"}


def test_parse_omits_closed_days():
    descs = ["Monday: Closed", "Tuesday: 7:00 PM \u2013 10:00 PM"]
    assert parse_weekday_descriptions(descs) == {"tuesday": "7pm-10pm"}


def test_parse_collapses_open_24_hours():
    descs = ["Friday: Open 24 hours"]
    assert parse_weekday_descriptions(descs) == {"friday": "24hrs"}


def test_parse_returns_none_when_nothing_parses():
    assert parse_weekday_descriptions(["Monday: Closed", "Tuesday: Closed"]) is None
    assert parse_weekday_descriptions([]) is None
    assert parse_weekday_descriptions(["gibberish entry"]) is None


def test_parse_skips_non_string_entries():
    descs = ["Monday: 6:00 PM \u2013 11:00 PM", None, 42, "Tuesday: 6:00 PM \u2013 11:00 PM"]
    assert parse_weekday_descriptions(descs) == {  # type: ignore[arg-type]
        "monday": "6pm-11pm",
        "tuesday": "6pm-11pm",
    }


# ---------------------------------------------------------------------------
# GooglePlacesClient.fetch_hours
# ---------------------------------------------------------------------------


def _mock_response(status_code: int, json_data=None, text: str = "") -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    resp.text = text
    if json_data is None:
        resp.json.side_effect = ValueError("no json")
    else:
        resp.json.return_value = json_data
    return resp


@pytest.fixture
def configured_client(monkeypatch) -> GooglePlacesClient:
    """Return a client with a fake key and zero delay."""
    monkeypatch.setenv("GOOGLE_PLACES_API_KEY", "fake-key")
    monkeypatch.setenv("GOOGLE_PLACES_DELAY_S", "0")
    monkeypatch.setenv("GOOGLE_PLACES_DAILY_LIMIT", "500")
    return GooglePlacesClient()


def test_returns_empty_when_unconfigured(monkeypatch):
    monkeypatch.delenv("GOOGLE_PLACES_API_KEY", raising=False)
    client = GooglePlacesClient()
    assert client.is_configured is False
    assert client.fetch_hours("Comedy Cellar, New York, NY") == PlacesHoursResult(None, None)


def test_returns_empty_for_blank_query(configured_client):
    assert configured_client.fetch_hours("") == PlacesHoursResult(None, None)
    assert configured_client.fetch_hours("   ") == PlacesHoursResult(None, None)


def test_fetch_hours_happy_path_parses_hours(configured_client):
    api_body = {
        "places": [
            {
                "id": "ChIJabc123",
                "displayName": {"text": "Comedy Cellar"},
                "regularOpeningHours": {
                    "weekdayDescriptions": [
                        "Monday: 7:00 PM \u2013 11:00 PM",
                        "Tuesday: 7:00 PM \u2013 11:00 PM",
                        "Friday: 7:00 PM \u2013 1:00 AM",
                    ]
                },
            }
        ]
    }
    with patch("laughtrack.core.clients.google.places.requests.post") as mock_post:
        mock_post.return_value = _mock_response(200, json_data=api_body)
        result = configured_client.fetch_hours("Comedy Cellar, New York, NY")

    assert result.place_id == "ChIJabc123"
    assert result.hours == {
        "monday": "7pm-11pm",
        "tuesday": "7pm-11pm",
        "friday": "7pm-1am",
    }
    # Field mask + API key must be sent as headers (not query params)
    _args, kwargs = mock_post.call_args
    assert kwargs["headers"]["X-Goog-Api-Key"] == "fake-key"
    assert "regularOpeningHours.weekdayDescriptions" in kwargs["headers"]["X-Goog-FieldMask"]
    assert kwargs["json"]["textQuery"] == "Comedy Cellar, New York, NY"
    assert kwargs["json"]["pageSize"] == 1
    assert configured_client.calls_made == 1


def test_fetch_hours_returns_place_id_even_when_hours_missing(configured_client):
    api_body = {
        "places": [
            {
                "id": "ChIJxyz789",
                "displayName": {"text": "Some Club"},
                # no regularOpeningHours field
            }
        ]
    }
    with patch("laughtrack.core.clients.google.places.requests.post") as mock_post:
        mock_post.return_value = _mock_response(200, json_data=api_body)
        result = configured_client.fetch_hours("Some Club, Nowhere")

    assert result.place_id == "ChIJxyz789"
    assert result.hours is None


def test_fetch_hours_empty_places_list_returns_empty(configured_client):
    with patch("laughtrack.core.clients.google.places.requests.post") as mock_post:
        mock_post.return_value = _mock_response(200, json_data={"places": []})
        result = configured_client.fetch_hours("Made-Up Place")

    assert result == PlacesHoursResult(None, None)


def test_fetch_hours_http_error_returns_empty(configured_client):
    with patch("laughtrack.core.clients.google.places.requests.post") as mock_post:
        mock_post.return_value = _mock_response(403, json_data=None, text="forbidden")
        result = configured_client.fetch_hours("Comedy Cellar")

    assert result == PlacesHoursResult(None, None)


def test_fetch_hours_rate_limited_returns_empty(configured_client):
    with patch("laughtrack.core.clients.google.places.requests.post") as mock_post:
        mock_post.return_value = _mock_response(429, text="quota exceeded")
        result = configured_client.fetch_hours("Comedy Cellar")

    assert result == PlacesHoursResult(None, None)


def test_fetch_hours_network_error_returns_empty(configured_client):
    with patch("laughtrack.core.clients.google.places.requests.post") as mock_post:
        mock_post.side_effect = requests.ConnectionError("dns fail")
        result = configured_client.fetch_hours("Comedy Cellar")

    assert result == PlacesHoursResult(None, None)
    # Failed requests must NOT count against the daily quota — otherwise a
    # transient outage could exhaust the cap before any successful call lands.
    assert configured_client.calls_made == 0


def test_daily_limit_stops_further_calls(monkeypatch):
    monkeypatch.setenv("GOOGLE_PLACES_API_KEY", "fake-key")
    monkeypatch.setenv("GOOGLE_PLACES_DELAY_S", "0")
    monkeypatch.setenv("GOOGLE_PLACES_DAILY_LIMIT", "1")
    client = GooglePlacesClient()
    api_body = {"places": [{"id": "ChIJ1", "regularOpeningHours": {"weekdayDescriptions": []}}]}
    with patch("laughtrack.core.clients.google.places.requests.post") as mock_post:
        mock_post.return_value = _mock_response(200, json_data=api_body)
        first = client.fetch_hours("A")
        second = client.fetch_hours("B")

    assert first.place_id == "ChIJ1"
    assert second == PlacesHoursResult(None, None)
    assert mock_post.call_count == 1
    assert client.calls_remaining == 0
