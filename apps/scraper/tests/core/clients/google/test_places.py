"""Tests for GooglePlacesClient — weekdayDescription parsing + HTTP flow."""

from unittest.mock import MagicMock, patch

import pytest
import requests

from laughtrack.core.clients.google.places import (
    GooglePlacesClient,
    PlacesHoursResult,
    PlacesPhotoResult,
    _normalize_attributions,
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


def test_parse_multi_shift_day_joins_ranges():
    # Lunch + dinner service — both shifts must survive, joined with ", ".
    descs = ["Tuesday: 11:00 AM \u2013 2:00 PM, 5:00 PM \u2013 10:00 PM"]
    assert parse_weekday_descriptions(descs) == {
        "tuesday": "11am-2pm, 5pm-10pm"
    }


def test_parse_multi_shift_with_three_segments():
    descs = [
        "Wednesday: 8:00 AM \u2013 10:00 AM, 12:00 PM \u2013 2:00 PM, 6:00 PM \u2013 9:00 PM"
    ]
    assert parse_weekday_descriptions(descs) == {
        "wednesday": "8am-10am, 12pm-2pm, 6pm-9pm"
    }


def test_parse_multi_shift_partial_parse_keeps_valid_segments():
    # A garbled second segment shouldn't drop the entire day.
    descs = ["Thursday: 5:00 PM \u2013 9:00 PM, NOT A RANGE"]
    assert parse_weekday_descriptions(descs) == {"thursday": "5pm-9pm"}


def test_parse_24_hour_locale_format():
    # Non-US locales return 24-hour times — must convert to 12h output.
    descs = [
        "Monday: 17:00 \u2013 23:00",
        "Tuesday: 09:30 \u2013 17:45",
        "Wednesday: 00:00 \u2013 06:00",
    ]
    assert parse_weekday_descriptions(descs) == {
        "monday": "5pm-11pm",
        "tuesday": "9:30am-5:45pm",
        "wednesday": "12am-6am",
    }


def test_parse_24_hour_with_multi_shift():
    descs = ["Friday: 11:00 \u2013 14:00, 17:00 \u2013 22:00"]
    assert parse_weekday_descriptions(descs) == {
        "friday": "11am-2pm, 5pm-10pm"
    }


def test_parse_warns_when_day_prefix_matches_but_range_unparseable():
    # If the day matched but the rest is gibberish (and not "Closed" / 24-hour
    # phrase), we want a diagnostic log line so unseen formats are spotted
    # in production rather than silently dropped.
    from laughtrack.core.clients.google import places as _places_mod

    descs = ["Monday: someday from dawn til dusk"]
    with patch.object(_places_mod, "Logger") as mock_logger:
        result = parse_weekday_descriptions(descs)

    assert result is None
    assert mock_logger.warn.call_count == 1
    msg = mock_logger.warn.call_args[0][0]
    assert "unparseable hours entry" in msg
    assert "monday" in msg
    assert "Monday: someday from dawn til dusk" in msg


def test_parse_does_not_warn_for_closed_or_24h_phrases():
    from laughtrack.core.clients.google import places as _places_mod

    descs = ["Monday: Closed", "Tuesday: Open 24 hours"]
    with patch.object(_places_mod, "Logger") as mock_logger:
        result = parse_weekday_descriptions(descs)

    assert result == {"tuesday": "24hrs"}
    mock_logger.warn.assert_not_called()


def test_parse_does_not_warn_when_day_prefix_does_not_match():
    from laughtrack.core.clients.google import places as _places_mod

    with patch.object(_places_mod, "Logger") as mock_logger:
        result = parse_weekday_descriptions(["gibberish entry"])

    assert result is None
    mock_logger.warn.assert_not_called()


def test_parse_24h_requires_zero_padded_hours_to_avoid_ambiguity():
    # "5:00 - 7:00" lacks AM/PM and uses single-digit hours — could be
    # mistakenly read as 24-hour and silently relabeled "5am-7am".  Requiring
    # zero-padded hours in the 24h regex routes this to the warn path instead.
    from laughtrack.core.clients.google import places as _places_mod

    with patch.object(_places_mod, "Logger") as mock_logger:
        result = parse_weekday_descriptions(["Monday: 5:00 \u2013 7:00"])

    assert result is None
    assert mock_logger.warn.call_count == 1


def test_parse_rejects_out_of_range_24h_values():
    # 24:00 / 25:00 / 99:00 must NOT silently coerce — they should fall
    # through to the unparseable diagnostic so unexpected inputs are visible.
    from laughtrack.core.clients.google import places as _places_mod

    descs = [
        "Monday: 24:00 \u2013 25:00",
        "Tuesday: 99:00 \u2013 17:00",
        "Wednesday: 12:60 \u2013 13:00",
    ]
    with patch.object(_places_mod, "Logger") as mock_logger:
        result = parse_weekday_descriptions(descs)

    assert result is None
    assert mock_logger.warn.call_count == 3


def test_parse_rejects_out_of_range_12h_values():
    # "13:00 PM" / "5:60 PM" — invalid clock values must route to the warn
    # path rather than producing nonsense output like "13pm".
    from laughtrack.core.clients.google import places as _places_mod

    descs = [
        "Monday: 13:00 PM \u2013 14:00 PM",
        "Tuesday: 5:60 PM \u2013 9:00 PM",
    ]
    with patch.object(_places_mod, "Logger") as mock_logger:
        result = parse_weekday_descriptions(descs)

    assert result is None
    assert mock_logger.warn.call_count == 2


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


# ---------------------------------------------------------------------------
# GooglePlacesClient.fetch_photo_url
# ---------------------------------------------------------------------------


def test_fetch_photo_url_unconfigured_returns_none(monkeypatch):
    monkeypatch.delenv("GOOGLE_PLACES_API_KEY", raising=False)
    client = GooglePlacesClient()
    assert client.fetch_photo_url("Comedy Cellar, New York, NY") is None


def test_fetch_photo_url_blank_query_returns_none(configured_client):
    assert configured_client.fetch_photo_url("") is None
    assert configured_client.fetch_photo_url("   ") is None


def test_fetch_photo_url_happy_path_returns_keyfree_uri(configured_client):
    search_body = {
        "places": [
            {
                "id": "ChIJabc",
                "photos": [{"name": "places/ChIJabc/photos/AeJxyz"}],
            }
        ]
    }
    media_body = {
        "name": "places/ChIJabc/photos/AeJxyz/media",
        "photoUri": "https://lh3.googleusercontent.com/places/abc=s500",
    }
    with patch("laughtrack.core.clients.google.places.requests.post") as mock_post, patch(
        "laughtrack.core.clients.google.places.requests.get"
    ) as mock_get:
        mock_post.return_value = _mock_response(200, json_data=search_body)
        mock_get.return_value = _mock_response(200, json_data=media_body)
        url = configured_client.fetch_photo_url("Comedy Cellar, New York, NY")

    assert url == "https://lh3.googleusercontent.com/places/abc=s500"
    # The returned URL must NOT carry the API key (it is fetched downstream by
    # a key-unaware downloader).
    assert "fake-key" not in url

    # searchText must request the photos field mask.
    _post_args, post_kwargs = mock_post.call_args
    assert "places.photos" in post_kwargs["headers"]["X-Goog-FieldMask"]
    # media call uses skipHttpRedirect so Google returns JSON, and sends the
    # key as a header (not in the returned photoUri).
    _get_args, get_kwargs = mock_get.call_args
    assert get_kwargs["params"]["skipHttpRedirect"] == "true"
    assert get_kwargs["headers"]["X-Goog-Api-Key"] == "fake-key"
    # Two billable Places requests (search + media).
    assert configured_client.calls_made == 2


def test_fetch_photo_url_no_photos_returns_none_without_media_call(configured_client):
    search_body = {"places": [{"id": "ChIJabc", "displayName": {"text": "No Photos Club"}}]}
    with patch("laughtrack.core.clients.google.places.requests.post") as mock_post, patch(
        "laughtrack.core.clients.google.places.requests.get"
    ) as mock_get:
        mock_post.return_value = _mock_response(200, json_data=search_body)
        url = configured_client.fetch_photo_url("No Photos Club")

    assert url is None
    mock_get.assert_not_called()
    # No second request reserved when there is no photo to resolve.
    assert configured_client.calls_made == 1


def test_fetch_photo_url_empty_places_returns_none(configured_client):
    with patch("laughtrack.core.clients.google.places.requests.post") as mock_post:
        mock_post.return_value = _mock_response(200, json_data={"places": []})
        assert configured_client.fetch_photo_url("Made-Up Place") is None


def test_fetch_photo_url_search_http_error_returns_none(configured_client):
    with patch("laughtrack.core.clients.google.places.requests.post") as mock_post:
        mock_post.return_value = _mock_response(403, json_data=None, text="forbidden")
        assert configured_client.fetch_photo_url("Comedy Cellar") is None


def test_fetch_photo_url_search_network_error_refunds_slot(configured_client):
    with patch("laughtrack.core.clients.google.places.requests.post") as mock_post:
        mock_post.side_effect = requests.ConnectionError("dns fail")
        assert configured_client.fetch_photo_url("Comedy Cellar") is None
    assert configured_client.calls_made == 0


def test_fetch_photo_url_media_http_error_returns_none(configured_client):
    search_body = {"places": [{"id": "ChIJabc", "photos": [{"name": "places/ChIJabc/photos/X"}]}]}
    with patch("laughtrack.core.clients.google.places.requests.post") as mock_post, patch(
        "laughtrack.core.clients.google.places.requests.get"
    ) as mock_get:
        mock_post.return_value = _mock_response(200, json_data=search_body)
        mock_get.return_value = _mock_response(404, json_data=None, text="not found")
        assert configured_client.fetch_photo_url("Comedy Cellar") is None


def test_fetch_photo_url_media_network_error_refunds_slot(configured_client):
    search_body = {"places": [{"id": "ChIJabc", "photos": [{"name": "places/ChIJabc/photos/X"}]}]}
    with patch("laughtrack.core.clients.google.places.requests.post") as mock_post, patch(
        "laughtrack.core.clients.google.places.requests.get"
    ) as mock_get:
        mock_post.return_value = _mock_response(200, json_data=search_body)
        mock_get.side_effect = requests.ConnectionError("dns fail")
        assert configured_client.fetch_photo_url("Comedy Cellar") is None
    # Search counted, media refunded.
    assert configured_client.calls_made == 1


# ---------------------------------------------------------------------------
# GooglePlacesClient.fetch_photo (place_id + attribution capture)
# ---------------------------------------------------------------------------


def test_fetch_photo_captures_place_id_and_attribution(configured_client):
    search_body = {
        "places": [
            {
                "id": "ChIJabc",
                "photos": [
                    {
                        "name": "places/ChIJabc/photos/AeJxyz",
                        "authorAttributions": [
                            {
                                "displayName": "Jane Doe",
                                "uri": "https://maps.google.com/jane",
                                "photoUri": "https://lh3.googleusercontent.com/jane",
                            }
                        ],
                    }
                ],
            }
        ]
    }
    media_body = {"photoUri": "https://lh3.googleusercontent.com/places/abc=s500"}
    with patch("laughtrack.core.clients.google.places.requests.post") as mock_post, patch(
        "laughtrack.core.clients.google.places.requests.get"
    ) as mock_get:
        mock_post.return_value = _mock_response(200, json_data=search_body)
        mock_get.return_value = _mock_response(200, json_data=media_body)
        result = configured_client.fetch_photo("Comedy Cellar, New York, NY")

    assert result == PlacesPhotoResult(
        photo_uri="https://lh3.googleusercontent.com/places/abc=s500",
        place_id="ChIJabc",
        attributions=[
            {
                "displayName": "Jane Doe",
                "uri": "https://maps.google.com/jane",
                "photoUri": "https://lh3.googleusercontent.com/jane",
            }
        ],
    )
    # The downloadable URL must not carry the API key.
    assert "fake-key" not in result.photo_uri
    assert configured_client.calls_made == 2


def test_fetch_photo_returns_empty_attributions_when_absent(configured_client):
    search_body = {"places": [{"id": "ChIJabc", "photos": [{"name": "places/ChIJabc/photos/X"}]}]}
    media_body = {"photoUri": "https://lh3.googleusercontent.com/places/x=s500"}
    with patch("laughtrack.core.clients.google.places.requests.post") as mock_post, patch(
        "laughtrack.core.clients.google.places.requests.get"
    ) as mock_get:
        mock_post.return_value = _mock_response(200, json_data=search_body)
        mock_get.return_value = _mock_response(200, json_data=media_body)
        result = configured_client.fetch_photo("Comedy Cellar")

    assert result.place_id == "ChIJabc"
    assert result.attributions == []


def test_fetch_photo_returns_none_when_no_photos(configured_client):
    search_body = {"places": [{"id": "ChIJabc", "displayName": {"text": "No Photos Club"}}]}
    with patch("laughtrack.core.clients.google.places.requests.post") as mock_post, patch(
        "laughtrack.core.clients.google.places.requests.get"
    ) as mock_get:
        mock_post.return_value = _mock_response(200, json_data=search_body)
        result = configured_client.fetch_photo("No Photos Club")

    assert result is None
    mock_get.assert_not_called()
    # No second request reserved when there is no photo to resolve.
    assert configured_client.calls_made == 1


def test_fetch_photo_url_is_thin_wrapper_over_fetch_photo(configured_client):
    """fetch_photo_url returns only the photo_uri from fetch_photo."""
    sentinel = PlacesPhotoResult(
        photo_uri="https://lh3.googleusercontent.com/p=s500",
        place_id="ChIJabc",
        attributions=[{"displayName": "Jane Doe"}],
    )
    with patch.object(configured_client, "fetch_photo", return_value=sentinel) as mock_fetch:
        url = configured_client.fetch_photo_url("Comedy Cellar", max_width_px=300)

    assert url == "https://lh3.googleusercontent.com/p=s500"
    mock_fetch.assert_called_once_with("Comedy Cellar", 300)


# ---------------------------------------------------------------------------
# _normalize_attributions
# ---------------------------------------------------------------------------


def test_normalize_attributions_keeps_string_triples():
    raw = [
        {
            "displayName": "Jane Doe",
            "uri": "https://maps.google.com/jane",
            "photoUri": "https://lh3.googleusercontent.com/jane",
        }
    ]
    assert _normalize_attributions(raw) == raw


def test_normalize_attributions_drops_non_string_and_extra_fields():
    raw = [
        {"displayName": "Jane", "uri": 123, "ignored": "x"},
        {"displayName": "", "uri": "https://u"},  # empty displayName dropped
        "not-a-dict",
    ]
    assert _normalize_attributions(raw) == [
        {"displayName": "Jane"},
        {"uri": "https://u"},
    ]


def test_normalize_attributions_returns_empty_for_non_list():
    assert _normalize_attributions(None) == []
    assert _normalize_attributions({"displayName": "x"}) == []
