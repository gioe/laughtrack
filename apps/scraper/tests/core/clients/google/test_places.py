"""Tests for GooglePlacesClient — photo + nearby-search HTTP flow."""

from unittest.mock import MagicMock, patch

import pytest
import requests

from laughtrack.core.clients.google import places
from laughtrack.core.clients.google.places import (
    GooglePlacesClient,
    PlaceDetails,
    PlacesNearbyVenue,
    PlacesPhotoResult,
    _normalize_attributions,
)

# ---------------------------------------------------------------------------
# Shared fixtures
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
    with (
        patch("laughtrack.core.clients.google.places.requests.post") as mock_post,
        patch("laughtrack.core.clients.google.places.requests.get") as mock_get,
    ):
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
    with (
        patch("laughtrack.core.clients.google.places.requests.post") as mock_post,
        patch("laughtrack.core.clients.google.places.requests.get") as mock_get,
    ):
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
    with (
        patch("laughtrack.core.clients.google.places.requests.post") as mock_post,
        patch("laughtrack.core.clients.google.places.requests.get") as mock_get,
    ):
        mock_post.return_value = _mock_response(200, json_data=search_body)
        mock_get.return_value = _mock_response(404, json_data=None, text="not found")
        assert configured_client.fetch_photo_url("Comedy Cellar") is None


def test_fetch_photo_url_media_network_error_refunds_slot(configured_client):
    search_body = {"places": [{"id": "ChIJabc", "photos": [{"name": "places/ChIJabc/photos/X"}]}]}
    with (
        patch("laughtrack.core.clients.google.places.requests.post") as mock_post,
        patch("laughtrack.core.clients.google.places.requests.get") as mock_get,
    ):
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
    with (
        patch("laughtrack.core.clients.google.places.requests.post") as mock_post,
        patch("laughtrack.core.clients.google.places.requests.get") as mock_get,
    ):
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
    with (
        patch("laughtrack.core.clients.google.places.requests.post") as mock_post,
        patch("laughtrack.core.clients.google.places.requests.get") as mock_get,
    ):
        mock_post.return_value = _mock_response(200, json_data=search_body)
        mock_get.return_value = _mock_response(200, json_data=media_body)
        result = configured_client.fetch_photo("Comedy Cellar")

    assert result.place_id == "ChIJabc"
    assert result.attributions == []


def test_fetch_photo_returns_none_when_no_photos(configured_client):
    search_body = {"places": [{"id": "ChIJabc", "displayName": {"text": "No Photos Club"}}]}
    with (
        patch("laughtrack.core.clients.google.places.requests.post") as mock_post,
        patch("laughtrack.core.clients.google.places.requests.get") as mock_get,
    ):
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


# ---------------------------------------------------------------------------
# search_nearby + _parse_nearby_places
# ---------------------------------------------------------------------------


def test_parse_nearby_places_extracts_well_formed_venues():
    data = {
        "places": [
            {
                "id": "p1",
                "displayName": {"text": "The Comedy Spot"},
                "formattedAddress": "1 Main St, Akron, OH",
                "location": {"latitude": 41.08, "longitude": -81.52},
                "websiteUri": "https://thecomedyspot.example.com",
                "primaryType": "comedy_club",
            }
        ]
    }
    venues = GooglePlacesClient._parse_nearby_places(data)
    assert venues == [
        PlacesNearbyVenue(
            place_id="p1",
            name="The Comedy Spot",
            address="1 Main St, Akron, OH",
            lat=41.08,
            lng=-81.52,
            website="https://thecomedyspot.example.com",
            primary_type="comedy_club",
        )
    ]


def test_parse_nearby_places_drops_entries_missing_id_or_coords():
    data = {
        "places": [
            {"displayName": {"text": "No id"}, "location": {"latitude": 1, "longitude": 2}},
            {"id": "p2", "displayName": {"text": "No coords"}},
            {"id": "p3", "location": {"latitude": "bad", "longitude": 2}},
        ]
    }
    assert GooglePlacesClient._parse_nearby_places(data) == []


def test_parse_nearby_places_tolerates_missing_name_and_address():
    data = {"places": [{"id": "p1", "location": {"latitude": 1.0, "longitude": 2.0}}]}
    venues = GooglePlacesClient._parse_nearby_places(data)
    assert venues == [PlacesNearbyVenue("p1", "", None, 1.0, 2.0)]


def test_search_nearby_returns_empty_when_unconfigured(monkeypatch):
    monkeypatch.delenv("GOOGLE_PLACES_API_KEY", raising=False)
    client = GooglePlacesClient()
    assert client.search_nearby("comedy club", 41.0, -81.0, 30.0) == []


def test_search_nearby_returns_empty_for_blank_query(configured_client):
    assert configured_client.search_nearby("", 41.0, -81.0, 30.0) == []


def test_search_nearby_clamps_bias_radius_to_50km(configured_client):
    body = {"places": [{"id": "p1", "location": {"latitude": 1.0, "longitude": 2.0}}]}
    with patch("laughtrack.core.clients.google.places.requests.post") as mock_post:
        mock_post.return_value = _mock_response(200, json_data=body)
        configured_client.search_nearby("comedy club", 41.0, -81.0, 100.0, max_pages=1)
    _args, kwargs = mock_post.call_args
    radius = kwargs["json"]["locationBias"]["circle"]["radius"]
    assert radius == 50_000.0  # 100 mi would exceed the API ceiling


def test_search_nearby_paginates_and_dedupes(configured_client):
    page1 = {
        "nextPageToken": "tok",
        "places": [
            {"id": "p1", "location": {"latitude": 1.0, "longitude": 2.0}},
            {"id": "p2", "location": {"latitude": 1.1, "longitude": 2.1}},
        ],
    }
    page2 = {
        "places": [
            {"id": "p2", "location": {"latitude": 1.1, "longitude": 2.1}},  # dup
            {"id": "p3", "location": {"latitude": 1.2, "longitude": 2.2}},
        ]
    }
    with patch("laughtrack.core.clients.google.places.requests.post") as mock_post:
        mock_post.side_effect = [
            _mock_response(200, json_data=page1),
            _mock_response(200, json_data=page2),
        ]
        venues = configured_client.search_nearby("comedy club", 41.0, -81.0, 30.0)

    assert [v.place_id for v in venues] == ["p1", "p2", "p3"]
    assert mock_post.call_count == 2
    # Second request must carry the page token from the first response.
    second_kwargs = mock_post.call_args_list[1][1]
    assert second_kwargs["json"]["pageToken"] == "tok"
    assert configured_client.calls_made == 2


def test_search_nearby_stops_when_no_page_token(configured_client):
    body = {"places": [{"id": "p1", "location": {"latitude": 1.0, "longitude": 2.0}}]}
    with patch("laughtrack.core.clients.google.places.requests.post") as mock_post:
        mock_post.return_value = _mock_response(200, json_data=body)
        configured_client.search_nearby("comedy club", 41.0, -81.0, 30.0, max_pages=3)
    assert mock_post.call_count == 1  # no nextPageToken -> single page


def test_search_nearby_refunds_slot_on_network_error(configured_client):
    with patch("laughtrack.core.clients.google.places.requests.post") as mock_post:
        mock_post.side_effect = requests.RequestException("boom")
        assert configured_client.search_nearby("comedy club", 41.0, -81.0, 30.0) == []
    assert configured_client.calls_made == 0  # reserved slot rolled back


# ---------------------------------------------------------------------------
# GooglePlacesClient.fetch_place_details
# ---------------------------------------------------------------------------


_DETAILS_BODY = {
    "formattedAddress": "123 Main St, San Francisco, CA 94102, USA",
    "location": {"latitude": 37.7793, "longitude": -122.4193},
    "addressComponents": [
        {
            "longText": "California",
            "shortText": "CA",
            "types": ["administrative_area_level_1", "political"],
        },
        {
            "longText": "San Francisco",
            "shortText": "San Francisco",
            "types": ["locality", "political"],
        },
    ],
}


def test_fetch_place_details_unconfigured_returns_none(monkeypatch):
    monkeypatch.delenv("GOOGLE_PLACES_API_KEY", raising=False)
    client = GooglePlacesClient()
    assert client.fetch_place_details("ChIJabc") is None


def test_fetch_place_details_blank_id_returns_none(configured_client):
    assert configured_client.fetch_place_details("") is None
    assert configured_client.fetch_place_details("   ") is None


def test_fetch_place_details_happy_path_parses_fields(configured_client, monkeypatch):
    mock_get = MagicMock(return_value=_mock_response(200, json_data=_DETAILS_BODY))
    monkeypatch.setattr(places.requests, "get", mock_get)

    result = configured_client.fetch_place_details("ChIJabc")

    assert result == PlaceDetails(
        place_id="ChIJabc",
        formatted_address="123 Main St, San Francisco, CA 94102, USA",
        state_code="CA",
        city="San Francisco",
        lat=37.7793,
        lng=-122.4193,
    )
    # Place Details is a GET to /places/{id} with the documented field mask.
    _args, kwargs = mock_get.call_args
    assert mock_get.call_args[0][0].endswith("/places/ChIJabc")
    assert kwargs["headers"]["X-Goog-FieldMask"] == "formattedAddress,location,addressComponents"
    assert kwargs["headers"]["X-Goog-Api-Key"] == "fake-key"
    assert configured_client.calls_made == 1


def test_fetch_place_details_http_error_returns_none(configured_client, monkeypatch):
    monkeypatch.setattr(
        places.requests, "get", MagicMock(return_value=_mock_response(404, json_data=None, text="not found"))
    )
    assert configured_client.fetch_place_details("ChIJabc") is None


def test_fetch_place_details_network_error_refunds_slot(configured_client, monkeypatch):
    monkeypatch.setattr(places.requests, "get", MagicMock(side_effect=requests.ConnectionError("dns fail")))
    assert configured_client.fetch_place_details("ChIJabc") is None
    assert configured_client.calls_made == 0  # reserved slot rolled back


def test_fetch_place_details_tolerates_missing_components(configured_client, monkeypatch):
    body = {"location": {"latitude": 1.0, "longitude": 2.0}}
    monkeypatch.setattr(places.requests, "get", MagicMock(return_value=_mock_response(200, json_data=body)))
    result = configured_client.fetch_place_details("ChIJabc")
    assert result == PlaceDetails("ChIJabc", None, None, None, 1.0, 2.0)


# ---------------------------------------------------------------------------
# GooglePlacesClient.find_place_id
# ---------------------------------------------------------------------------


def test_find_place_id_unconfigured_returns_none(monkeypatch):
    monkeypatch.delenv("GOOGLE_PLACES_API_KEY", raising=False)
    client = GooglePlacesClient()
    assert client.find_place_id("Comedy Cellar") is None


def test_find_place_id_blank_query_returns_none(configured_client):
    assert configured_client.find_place_id("") is None
    assert configured_client.find_place_id("   ") is None


def test_find_place_id_happy_path_returns_top_id(configured_client):
    body = {"places": [{"id": "ChIJtop"}, {"id": "ChIJother"}]}
    with patch("laughtrack.core.clients.google.places.requests.post") as mock_post:
        mock_post.return_value = _mock_response(200, json_data=body)
        place_id = configured_client.find_place_id("Comedy Cellar, New York, NY")

    assert place_id == "ChIJtop"
    _args, kwargs = mock_post.call_args
    assert kwargs["headers"]["X-Goog-FieldMask"] == "places.id"
    assert kwargs["json"] == {"textQuery": "Comedy Cellar, New York, NY", "pageSize": 1}
    assert configured_client.calls_made == 1


def test_find_place_id_no_results_returns_none(configured_client):
    with patch("laughtrack.core.clients.google.places.requests.post") as mock_post:
        mock_post.return_value = _mock_response(200, json_data={"places": []})
        assert configured_client.find_place_id("Made-Up Place") is None


def test_find_place_id_http_error_returns_none(configured_client):
    with patch("laughtrack.core.clients.google.places.requests.post") as mock_post:
        mock_post.return_value = _mock_response(403, json_data=None, text="forbidden")
        assert configured_client.find_place_id("Comedy Cellar") is None


def test_find_place_id_network_error_refunds_slot(configured_client):
    with patch("laughtrack.core.clients.google.places.requests.post") as mock_post:
        mock_post.side_effect = requests.ConnectionError("dns fail")
        assert configured_client.find_place_id("Comedy Cellar") is None
    assert configured_client.calls_made == 0
