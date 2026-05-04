"""Tests for the Eventbrite startup token validation.

The validation function lives at module load time on the GHA nightly path,
so the tests stub `Logger` at the usage site (per scraper testing
convention) and replace `requests.get` with a fake — never hitting the
network.
"""
import pytest

from laughtrack.core.clients.eventbrite import health as health_module
from laughtrack.core.clients.eventbrite.health import (
    USERS_ME_URL,
    TOKEN_ENV_VAR,
    validate_eventbrite_token,
)


class _FakeResponse:
    def __init__(self, status_code: int):
        self.status_code = status_code


class _FakeLogger:
    """Drop-in for laughtrack.foundation Logger; collects calls per test."""

    errors: list[str] = []
    infos: list[str] = []

    @classmethod
    def reset(cls):
        cls.errors = []
        cls.infos = []

    @classmethod
    def error(cls, message, context=None, **_kwargs):
        cls.errors.append(message)

    @classmethod
    def info(cls, message, context=None, **_kwargs):
        cls.infos.append(message)


@pytest.fixture
def fake_logger(monkeypatch):
    _FakeLogger.reset()
    # Patch the `Logger` name as bound in the health module's namespace
    # so the function-under-test sees the fake (convention #66).
    monkeypatch.setattr(health_module, "Logger", _FakeLogger)
    return _FakeLogger


def test_eventbrite_token_validation_exits_when_token_missing(monkeypatch, fake_logger):
    monkeypatch.delenv(TOKEN_ENV_VAR, raising=False)

    with pytest.raises(SystemExit) as exc:
        validate_eventbrite_token()

    assert exc.value.code == 1
    assert len(fake_logger.errors) == 1
    assert TOKEN_ENV_VAR in fake_logger.errors[0]


def test_eventbrite_token_validation_exits_on_401(monkeypatch, fake_logger):
    monkeypatch.setenv(TOKEN_ENV_VAR, "fake-stale-token")

    captured = {}

    def fake_get(url, headers=None, timeout=None):
        captured["url"] = url
        captured["headers"] = headers
        captured["timeout"] = timeout
        return _FakeResponse(401)

    monkeypatch.setattr(health_module.requests, "get", fake_get)

    with pytest.raises(SystemExit) as exc:
        validate_eventbrite_token()

    assert exc.value.code == 1
    assert captured["url"] == USERS_ME_URL
    assert captured["headers"] == {"Authorization": "Bearer fake-stale-token"}
    assert captured["timeout"] == health_module.REQUEST_TIMEOUT_SEC
    assert len(fake_logger.errors) == 1
    msg = fake_logger.errors[0]
    assert TOKEN_ENV_VAR in msg
    assert "401" in msg


def test_eventbrite_token_validation_exits_on_500(monkeypatch, fake_logger):
    monkeypatch.setenv(TOKEN_ENV_VAR, "fake-token")
    monkeypatch.setattr(
        health_module.requests, "get", lambda *a, **kw: _FakeResponse(500)
    )

    with pytest.raises(SystemExit) as exc:
        validate_eventbrite_token()

    assert exc.value.code == 1
    assert "500" in fake_logger.errors[0]


def test_eventbrite_token_validation_passes_on_200(monkeypatch, fake_logger):
    monkeypatch.setenv(TOKEN_ENV_VAR, "fake-good-token")
    monkeypatch.setattr(
        health_module.requests, "get", lambda *a, **kw: _FakeResponse(200)
    )

    validate_eventbrite_token()

    assert fake_logger.errors == []
    assert len(fake_logger.infos) == 1
    assert USERS_ME_URL in fake_logger.infos[0]


def test_eventbrite_token_validation_exits_on_request_exception(monkeypatch, fake_logger):
    monkeypatch.setenv(TOKEN_ENV_VAR, "fake-token")

    def fake_get(*_a, **_kw):
        raise health_module.requests.ConnectionError("network down")

    monkeypatch.setattr(health_module.requests, "get", fake_get)

    with pytest.raises(SystemExit) as exc:
        validate_eventbrite_token()

    assert exc.value.code == 1
    assert len(fake_logger.errors) == 1
    assert TOKEN_ENV_VAR in fake_logger.errors[0]
