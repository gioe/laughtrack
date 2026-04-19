"""Tests for the qualifier-retry hardening in update_comedian_bios.

Verifies that _fetch_summary retries rejected lookups with a "(comedian)"
disambiguation qualifier and surfaces the retry outcome via the summary counter.
"""

from __future__ import annotations

import asyncio
import logging
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

# Match the runtime path setup so the script's imports resolve in tests.
_repo_root = Path(__file__).resolve().parents[3]
_src_path = _repo_root / "src"
for _p in (str(_src_path), str(_repo_root)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from scripts.core import update_comedian_bios as mod  # noqa: E402


@dataclass
class _FakeResponse:
    status_code: int
    payload: Any = None

    def json(self) -> Any:
        return self.payload


class _FakeSession:
    """Async session stub whose `.get` returns responses keyed by title."""

    def __init__(self, responses_by_title: Dict[str, _FakeResponse]):
        self.responses_by_title = responses_by_title
        self.calls: List[str] = []

    async def get(self, url: str, **_kwargs: Any) -> _FakeResponse:
        # Wikipedia summary URLs end with the quoted title; recover it by
        # splitting on the base path and un-quoting underscores back to spaces.
        assert url.startswith(mod._WIKIPEDIA_SUMMARY_BASE)
        raw = url[len(mod._WIKIPEDIA_SUMMARY_BASE):]
        from urllib.parse import unquote
        title = unquote(raw).replace("_", " ")
        self.calls.append(title)
        if title not in self.responses_by_title:
            raise AssertionError(f"Unexpected Wikipedia lookup for title: {title!r}")
        return self.responses_by_title[title]


def _standard_comedian_payload(name: str) -> Dict[str, Any]:
    return {
        "type": "standard",
        "title": name,
        "description": "American stand-up comedian",
        "extract": f"{name} is an American stand-up comedian known for sharp observational humor.",
    }


def _standard_non_comedian_payload(name: str) -> Dict[str, Any]:
    return {
        "type": "standard",
        "title": name,
        "description": "American basketball player",
        "extract": f"{name} is an American businessman and former basketball player.",
    }


def _disambiguation_payload(name: str) -> Dict[str, Any]:
    return {
        "type": "disambiguation",
        "title": name,
        "description": "Topics referred to by the same term",
        "extract": f"{name} may refer to several people.",
    }


def test_extracted_on_first_try_skips_qualifier_retry():
    session = _FakeSession({
        "Dave Chappelle": _FakeResponse(200, _standard_comedian_payload("Dave Chappelle")),
    })

    result = asyncio.run(mod._fetch_summary(session, 1, "Dave Chappelle"))

    assert result.status == "extracted"
    assert result.bio is not None
    assert result.title_used == "Dave Chappelle"
    assert result.qualifier_retry_used is False
    assert session.calls == ["Dave Chappelle"]


def test_not_found_triggers_qualifier_retry_that_succeeds():
    session = _FakeSession({
        "John Smith": _FakeResponse(404),
        "John Smith (comedian)": _FakeResponse(
            200, _standard_comedian_payload("John Smith")
        ),
    })

    result = asyncio.run(mod._fetch_summary(session, 42, "John Smith"))

    assert result.status == "extracted"
    assert result.bio is not None
    assert result.qualifier_retry_used is True
    assert result.title_used == "John Smith (comedian)"
    assert session.calls == ["John Smith", "John Smith (comedian)"]


def test_non_comedian_triggers_qualifier_retry_that_succeeds():
    session = _FakeSession({
        # Common name resolves to a non-comedian page (passes HTTP but fails
        # the comedy-keyword gate inside extract_bio).
        "Michael Jordan": _FakeResponse(
            200, _standard_non_comedian_payload("Michael Jordan")
        ),
        "Michael Jordan (comedian)": _FakeResponse(
            200, _standard_comedian_payload("Michael Jordan")
        ),
    })

    result = asyncio.run(mod._fetch_summary(session, 7, "Michael Jordan"))

    assert result.status == "extracted"
    assert result.qualifier_retry_used is True
    assert session.calls == ["Michael Jordan", "Michael Jordan (comedian)"]


def test_disambiguation_triggers_qualifier_retry_that_succeeds():
    session = _FakeSession({
        "Mike Johnson": _FakeResponse(200, _disambiguation_payload("Mike Johnson")),
        "Mike Johnson (comedian)": _FakeResponse(
            200, _standard_comedian_payload("Mike Johnson")
        ),
    })

    result = asyncio.run(mod._fetch_summary(session, 8, "Mike Johnson"))

    assert result.status == "extracted"
    assert result.qualifier_retry_used is True
    assert session.calls == ["Mike Johnson", "Mike Johnson (comedian)"]


def test_retry_also_fails_preserves_original_status():
    session = _FakeSession({
        "Nobody Here": _FakeResponse(404),
        "Nobody Here (comedian)": _FakeResponse(404),
    })

    result = asyncio.run(mod._fetch_summary(session, 9, "Nobody Here"))

    # The original status is preserved — qualifier retry is an attempt, not a
    # new classification bucket, so operators see the true reason the bio failed.
    assert result.status == "not_found"
    assert result.qualifier_retry_used is False
    assert session.calls == ["Nobody Here", "Nobody Here (comedian)"]


def test_name_with_existing_parenthetical_skips_qualifier_retry():
    # DB names like "Bo Burnham (musician)" should NOT be re-qualified — the
    # resulting title would be "Bo Burnham (musician) (comedian)" which always
    # 404s and wastes a request. The original rejection status is preserved.
    session = _FakeSession({
        "Bo Burnham (musician)": _FakeResponse(
            200, _standard_non_comedian_payload("Bo Burnham")
        ),
    })

    result = asyncio.run(mod._fetch_summary(session, 11, "Bo Burnham (musician)"))

    assert result.status == "not_comedian"
    assert result.qualifier_retry_used is False
    # Only the original lookup happened — no second request with double qualifier.
    assert session.calls == ["Bo Burnham (musician)"]


def test_fetch_failed_does_not_trigger_qualifier_retry():
    # Transient errors shouldn't burn a second request on a different title —
    # the network issue isn't a naming collision.
    session = _FakeSession({
        "Some Comedian": _FakeResponse(500),
    })

    result = asyncio.run(mod._fetch_summary(session, 10, "Some Comedian"))

    assert result.status == "fetch_failed"
    assert result.qualifier_retry_used is False
    assert session.calls == ["Some Comedian"]


def test_accept_and_reject_paths_emit_info_logs(caplog):
    # AC #2 requires accept/reject decisions to surface in nightly logs so
    # operators can spot disambiguation anomalies without a separate audit.
    # Verify both paths emit at INFO with the comedian_id, name, and title used.
    session = _FakeSession({
        "Dave Chappelle": _FakeResponse(
            200, _standard_comedian_payload("Dave Chappelle")
        ),
        "Nobody Real": _FakeResponse(404),
        "Nobody Real (comedian)": _FakeResponse(404),
    })

    with caplog.at_level(logging.INFO):
        asyncio.run(mod._fetch_summary(session, 1, "Dave Chappelle"))
        asyncio.run(mod._fetch_summary(session, 2, "Nobody Real"))

    accept_lines = [r.message for r in caplog.records if "accepted" in r.message]
    reject_lines = [r.message for r in caplog.records if "rejected" in r.message]

    assert any(
        "comedian_id=1" in m and "Dave Chappelle" in m for m in accept_lines
    ), f"expected accept log for comedian_id=1, got: {accept_lines}"
    assert any(
        "comedian_id=2" in m and "Nobody Real" in m and "not_found" in m
        for m in reject_lines
    ), f"expected reject log for comedian_id=2, got: {reject_lines}"


def test_enrich_summary_reports_qualifier_retry_saves():
    # Two comedians: one bio-extracted on first try, one saved only by the
    # qualifier retry. The summary should show qualifier_retry_saves=1.
    session = _FakeSession({
        "Dave Chappelle": _FakeResponse(200, _standard_comedian_payload("Dave Chappelle")),
        "John Smith": _FakeResponse(404),
        "John Smith (comedian)": _FakeResponse(
            200, _standard_comedian_payload("John Smith")
        ),
    })

    # Patch AsyncSession so _enrich uses our fake without touching the network.
    class _FakeAsyncSessionCtx:
        def __init__(self, *_a, **_kw):
            pass

        async def __aenter__(self):
            return session

        async def __aexit__(self, *_exc):
            return False

    saved = mod.AsyncSession
    mod.AsyncSession = _FakeAsyncSessionCtx  # type: ignore[assignment]
    try:
        summary = asyncio.run(
            mod._enrich(
                [(1, "Dave Chappelle"), (2, "John Smith")],
                force=False,
                dry_run=True,
            )
        )
    finally:
        mod.AsyncSession = saved  # type: ignore[assignment]

    assert summary["fetched"] == 2
    assert summary["extracted"] == 2
    assert summary["written"] == 0  # dry_run
    assert summary["qualifier_retry_saves"] == 1
