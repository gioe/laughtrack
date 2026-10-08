"""HTTP schemes are case-insensitive; URL paths and queries are not."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from laughtrack.foundation.infrastructure.http.client import HttpClient
from laughtrack.foundation.utilities.url import URLUtils


@pytest.mark.parametrize("scheme", ["http", "Http", "HTTP", "hTtP", "https", "Https", "HTTPS", "hTtPs"])
def test_http_scheme_preserves_remaining_url(scheme):
    suffix = "Example.COM:8080/CaseSensitive/%2FPath?Token=AbC&Next=%2f#SectionA"
    assert URLUtils.normalize_url(f"{scheme}://{suffix}") == f"{scheme.lower()}://{suffix}"


@pytest.mark.parametrize(
    "url,expected",
    [
        ("", ""),
        ("Example.COM/Show?Token=AbC", "https://Example.COM/Show?Token=AbC"),
        ("example.com/", "https://example.com"),
        ("http://example.com/", "http://example.com"),
        ("https://example.com/", "https://example.com"),
    ],
)
def test_existing_normalization(url, expected):
    assert URLUtils.normalize_url(url) == expected


@pytest.mark.parametrize("url", ["Http://Example.COM/Path/", "HTTPS://Example.COM/Path/"])
@pytest.mark.parametrize("remove_trailing_slash", [True, False])
def test_trailing_slash_option(url, remove_trailing_slash):
    expected = url.split(":", 1)[0].lower() + ":" + url.split(":", 1)[1]
    if remove_trailing_slash:
        expected = expected.rstrip("/")
    assert URLUtils.normalize_url(url, remove_trailing_slash) == expected


@pytest.mark.asyncio
async def test_native_http_receives_real_hostname():
    session = AsyncMock()
    response = MagicMock(status_code=200, text="<html>Deaf Puppy Comedy Club</html>")
    session.get.return_value = response

    result = await HttpClient.fetch_html(session, "Http://www.deafpuppyclub.com")

    assert result == response.text
    assert session.get.call_args.args[0] == "http://www.deafpuppyclub.com"
