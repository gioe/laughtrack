from __future__ import annotations

import asyncio
import sys
import types
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_repo_root = Path(__file__).resolve().parents[3]
_src_path = _repo_root / "src"
for _p in (str(_src_path), str(_repo_root)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from scripts.core import check_comedian_website_health as mod  # noqa: E402


@dataclass
class _FakeResponse:
    status_code: int
    text: str = ""
    url: str = "https://example.com/"


class _FakeSession:
    def __init__(self, responses_by_url: dict[str, Any]):
        self.responses_by_url = responses_by_url
        self.calls: list[str] = []

    async def get(self, url: str, **_kwargs: Any) -> _FakeResponse:
        self.calls.append(url)
        response = self.responses_by_url[url]
        if isinstance(response, BaseException):
            raise response
        return response


class _FakeCursor:
    def __init__(self, rows: list[dict[str, Any]]):
        self.rows = rows
        self.executed: list[tuple[str, tuple[Any, ...] | None]] = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def execute(self, query: str, params: tuple[Any, ...] | None = None) -> None:
        self.executed.append((query, params))

    def fetchall(self) -> list[dict[str, Any]]:
        return self.rows


class _FakeConnection:
    def __init__(self, rows: list[dict[str, Any]]):
        self.cursor_obj = _FakeCursor(rows)
        self.commits = 0
        self.closed = False

    def cursor(self, *_args, **_kwargs):
        return self.cursor_obj

    def commit(self) -> None:
        self.commits += 1

    def close(self) -> None:
        self.closed = True


class _FakeConnectionFactory:
    def __init__(self, *connections: _FakeConnection):
        self.connections = list(connections)
        self.autocommit_values: list[bool] = []

    def __call__(self, *, autocommit: bool) -> _FakeConnection:
        self.autocommit_values.append(autocommit)
        if not self.connections:
            raise AssertionError("unexpected database connection")
        return self.connections.pop(0)


class _ControlledSession:
    def __init__(
        self,
        responses_by_url: dict[str, _FakeResponse],
        assert_database_closed,
    ):
        self.responses_by_url = responses_by_url
        self.assert_database_closed = assert_database_closed
        self.release = {url: asyncio.Event() for url in responses_by_url}
        self.started: asyncio.Queue[str] = asyncio.Queue()
        self.completed: asyncio.Queue[str] = asyncio.Queue()
        self.completion_order: list[str] = []
        self.active = 0
        self.max_active = 0

    async def get(self, url: str, **_kwargs: Any) -> _FakeResponse:
        self.assert_database_closed()
        self.active += 1
        self.max_active = max(self.max_active, self.active)
        await self.started.put(url)
        await self.release[url].wait()
        self.active -= 1
        self.completion_order.append(url)
        await self.completed.put(url)
        return self.responses_by_url[url]


class _YieldingSession:
    def __init__(self):
        self.calls = 0
        self.active = 0
        self.max_active = 0

    async def get(self, url: str, **_kwargs: Any) -> _FakeResponse:
        self.calls += 1
        self.active += 1
        self.max_active = max(self.max_active, self.active)
        await asyncio.sleep(0)
        self.active -= 1
        return _FakeResponse(200, "<html>ok</html>", url=url)


def test_classify_health_response_covers_success_redirect_hard_transient_and_bot_blocks():
    ok = mod.classify_health_response(
        _FakeResponse(200, "<html>ok</html>", url="https://a.test"),
        "https://a.test",
    )
    redirect = mod.classify_health_response(
        _FakeResponse(200, "<html>ok</html>", url="https://b.test/new"),
        "https://b.test/old",
    )
    not_found = mod.classify_health_response(_FakeResponse(404, "gone"), "https://c.test")
    server_error = mod.classify_health_response(_FakeResponse(503, "try later"), "https://d.test")
    bot_block = mod.classify_health_response(
        _FakeResponse(403, "<html><title>Just a moment...</title></html>"),
        "https://e.test",
    )

    assert ok.status == "ok"
    assert redirect.status == "redirect"
    assert redirect.final_url == "https://b.test/new"
    assert not_found.status == "hard_failure"
    assert server_error.status == "transient_failure"
    assert bot_block.status == "bot_block"


def test_repeated_hard_failures_mark_url_stale_without_clearing_single_transient_error():
    transient = mod.plan_url_health_update(
        mod.ComedianURLTarget(
            uuid="c1",
            name="Transient Comic",
            field_name="website",
            url="https://transient.example",
            failure_count=2,
        ),
        mod.URLHealthResult(status="transient_failure", status_code=503),
        hard_failure_threshold=3,
    )
    first_hard = mod.plan_url_health_update(
        mod.ComedianURLTarget(
            uuid="c2",
            name="Newly Broken Comic",
            field_name="website",
            url="https://broken.example",
            failure_count=0,
        ),
        mod.URLHealthResult(status="hard_failure", status_code=404),
        hard_failure_threshold=3,
    )
    repeated_hard = mod.plan_url_health_update(
        mod.ComedianURLTarget(
            uuid="c3",
            name="Broken Comic",
            field_name="website",
            url="https://broken.example",
            failure_count=2,
        ),
        mod.URLHealthResult(status="hard_failure", status_code=410),
        hard_failure_threshold=3,
    )

    assert transient.new_failure_count == 2
    assert transient.health_status == "transient_failure"
    assert transient.queue_for_rediscovery is False
    assert first_hard.new_failure_count == 1
    assert first_hard.queue_for_rediscovery is False
    assert repeated_hard.new_failure_count == 3
    assert repeated_hard.health_status == "stale"
    assert repeated_hard.queue_for_rediscovery is True


def test_run_health_check_reports_counts_and_updates_stale_urls(monkeypatch):
    rows = [
        {
            "uuid": "ok",
            "name": "Okay Comic",
            "website": "https://ok.example",
            "website_scraping_url": None,
            "website_health_failure_count": 0,
            "website_scraping_url_health_failure_count": 0,
        },
        {
            "uuid": "gone",
            "name": "Gone Comic",
            "website": "https://gone.example",
            "website_scraping_url": None,
            "website_health_failure_count": 2,
            "website_scraping_url_health_failure_count": 0,
        },
        {
            "uuid": "blocked",
            "name": "Blocked Comic",
            "website": "https://blocked.example",
            "website_scraping_url": None,
            "website_health_failure_count": 0,
            "website_scraping_url_health_failure_count": 0,
        },
        {
            "uuid": "slow",
            "name": "Slow Comic",
            "website": "https://slow.example",
            "website_scraping_url": None,
            "website_health_failure_count": 1,
            "website_scraping_url_health_failure_count": 0,
        },
    ]
    read_conn = _FakeConnection(rows)
    write_conn = _FakeConnection([])
    connection_factory = _FakeConnectionFactory(read_conn, write_conn)
    session = _FakeSession({
        "https://ok.example": _FakeResponse(200, "<html>ok</html>"),
        "https://gone.example": _FakeResponse(404, "gone"),
        "https://blocked.example": _FakeResponse(403, "datadome challenge"),
        "https://slow.example": TimeoutError("timed out"),
    })

    monkeypatch.setattr(mod, "create_connection", connection_factory)

    summary = asyncio.run(
        mod.run_health_check(
            session=session,
            hard_failure_threshold=3,
            commit=True,
        )
    )

    assert summary.checked_urls == 4
    assert summary.hard_failures == 1
    assert summary.transient_failures == 1
    assert summary.bot_blocks == 1
    assert summary.queued_for_rediscovery == 1
    assert connection_factory.autocommit_values == [True, True]
    assert read_conn.closed is True
    assert write_conn.closed is True
    assert write_conn.commits == 0
    assert session.calls == [
        "https://ok.example",
        "https://gone.example",
        "https://blocked.example",
        "https://slow.example",
    ]
    assert any("website_health_status = %s" in query for query, _ in write_conn.cursor_obj.executed)


def test_run_health_check_bounds_concurrency_and_persists_in_target_order(monkeypatch):
    urls = [f"https://comic-{index}.example" for index in range(4)]
    rows = [
        {
            "uuid": f"c{index}",
            "name": f"Comic {index}",
            "website": url,
            "website_scraping_url": None,
            "website_health_failure_count": 2 if index == 1 else 0,
            "website_scraping_url_health_failure_count": 0,
        }
        for index, url in enumerate(urls)
    ]
    read_conn = _FakeConnection(rows)
    write_conn = _FakeConnection([])
    connection_factory = _FakeConnectionFactory(read_conn, write_conn)
    responses = {
        urls[0]: _FakeResponse(200, "ok", url=urls[0]),
        urls[1]: _FakeResponse(404, "gone", url=urls[1]),
        urls[2]: _FakeResponse(503, "retry", url=urls[2]),
        urls[3]: _FakeResponse(403, "blocked", url=urls[3]),
    }

    def assert_database_closed() -> None:
        assert read_conn.closed is True
        assert connection_factory.autocommit_values == [True]

    session = _ControlledSession(responses, assert_database_closed)
    monkeypatch.setattr(mod, "create_connection", connection_factory)

    async def exercise() -> mod.HealthCheckSummary:
        task = asyncio.create_task(
            mod.run_health_check(session=session, concurrency=2, commit=True)
        )

        assert [await session.started.get(), await session.started.get()] == urls[:2]

        session.release[urls[1]].set()
        assert await session.completed.get() == urls[1]
        assert await session.started.get() == urls[2]

        session.release[urls[0]].set()
        assert await session.completed.get() == urls[0]
        assert await session.started.get() == urls[3]

        session.release[urls[3]].set()
        assert await session.completed.get() == urls[3]
        session.release[urls[2]].set()
        assert await session.completed.get() == urls[2]

        return await task

    summary = asyncio.run(exercise())

    assert session.max_active == 2
    assert session.completion_order == [urls[1], urls[0], urls[3], urls[2]]
    assert connection_factory.autocommit_values == [True, True]
    assert [params for _query, params in write_conn.cursor_obj.executed] == [
        ("ok", 0, "c0"),
        ("stale", 3, "c1"),
        ("transient_failure", 0, "c2"),
        ("bot_block", 0, "c3"),
    ]
    assert summary.checked_urls == 4
    assert summary.queued_for_rediscovery == 1


def test_fetch_targets_keeps_production_sized_crawl_at_configured_cap():
    target_count = 4_400
    targets = [
        mod.ComedianURLTarget(
            uuid=f"c{index}",
            name=f"Comic {index}",
            field_name="website",
            url=f"https://comic-{index}.example",
        )
        for index in range(target_count)
    ]
    session = _YieldingSession()

    results = asyncio.run(
        mod._fetch_targets(session, targets, timeout=20, concurrency=10)
    )

    assert len(results) == target_count
    assert session.calls == target_count
    assert session.max_active == 10


def test_health_check_does_not_use_brave_discovery(monkeypatch):
    read_conn = _FakeConnection([
        {
            "uuid": "ok",
            "name": "Okay Comic",
            "website": "https://ok.example",
            "website_scraping_url": None,
            "website_health_failure_count": 0,
            "website_scraping_url_health_failure_count": 0,
        },
    ])
    session = _FakeSession({"https://ok.example": _FakeResponse(200, "<html>ok</html>")})

    connection_factory = _FakeConnectionFactory(read_conn)
    monkeypatch.setattr(mod, "create_connection", connection_factory)

    calls = []

    class ExplodingBraveSearchClient:
        def __init__(self):
            calls.append("created")
            raise AssertionError("health checks must not use Brave discovery")

    monkeypatch.setitem(
        sys.modules,
        "laughtrack.core.clients.brave.search",
        types.SimpleNamespace(BraveSearchClient=ExplodingBraveSearchClient),
    )

    def fail_if_discovery_client_is_created():
        raise AssertionError("health checks must not use Brave discovery")

    monkeypatch.setattr(mod, "_create_search_client", fail_if_discovery_client_is_created, raising=False)

    summary = asyncio.run(mod.run_health_check(session=session, commit=False))

    assert summary.checked_urls == 1
    assert summary.queued_for_rediscovery == 0
    assert connection_factory.autocommit_values == [True]
    assert calls == []
