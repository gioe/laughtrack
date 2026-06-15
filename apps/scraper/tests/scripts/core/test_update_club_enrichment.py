"""Integration tests for update_club_enrichment (description backfill).

Mocks the HTTP fetch; verifies that:
- A description parsed from the club website is extracted and counted.
- Known DataDome hosts skip the website fetch and use a cached description.
- An existing description is not overwritten unless --force is passed.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

# Match the path setup the script does at runtime so imports resolve in tests.
_repo_root = Path(__file__).resolve().parents[3]
_src_path = _repo_root / "src"
for p in (str(_src_path), str(_repo_root)):
    if p not in sys.path:
        sys.path.insert(0, p)

from scripts.core import update_club_enrichment as mod  # noqa: E402


def _target(
    club_id: int,
    name: str,
    city: str | None = "New York",
    state: str | None = "NY",
    website: str | None = None,
    has_description: bool = False,
) -> mod._ClubTarget:
    return mod._ClubTarget(
        id=club_id,
        name=name,
        website=website or f"https://{name.lower().replace(' ', '')}.example.com",
        city=city,
        state=state,
        has_description=has_description,
    )


def _ldjson_description_html(description: str = "") -> str:
    if description:
        return (
            '<html><head><script type="application/ld+json">'
            f'{{"@type": "LocalBusiness", "description": "{description}"}}'
            "</script></head></html>"
        )
    return "<html><head><title>nothing</title></head></html>"


async def _noop_async() -> None:
    return None


@pytest.fixture
def patch_fetch_html():
    """Patch HttpClient.fetch_html with a per-URL mapping."""

    pages: dict[str, str] = {}

    async def fake_fetch_html(session, url, logger_context=None):
        return pages.get(url, "")

    with (
        patch.object(mod.HttpClient, "fetch_html", new=fake_fetch_html),
        patch.object(mod, "close_js_browser", new=lambda: _noop_async()),
    ):
        yield pages


def _run_enrich(targets, force=False, dry_run=True):
    return asyncio.run(mod._enrich(targets, force=force, dry_run=dry_run))


def test_description_extracted_from_website(patch_fetch_html):
    target = _target(1, "Comedy Cellar")
    patch_fetch_html[target.website] = _ldjson_description_html("The Comedy Cellar is a NYC institution.")

    summary = _run_enrich([target])

    assert summary["description_hits"] == 1
    assert summary["extracted"] == 1
    assert summary["bot_blocked"] == 0


def test_no_data_when_website_has_no_description(patch_fetch_html):
    target = _target(1, "Empty Club")
    patch_fetch_html[target.website] = _ldjson_description_html()  # no description

    summary = _run_enrich([target])

    assert summary["description_hits"] == 0
    assert summary["extracted"] == 0


def test_bot_blocked_is_counted(patch_fetch_html):
    target = _target(2, "Blocked Club")
    patch_fetch_html[target.website] = (
        "<html><body>Just a moment... cf-browser-verification " "Checking your browser before accessing</body></html>"
    )

    summary = _run_enrich([target])

    assert summary["bot_blocked"] == 1
    assert summary["extracted"] == 0


def test_known_datadome_funny_bone_skips_website_fetch_uses_cached(monkeypatch):
    target = _target(
        1030,
        "Des Moines Funny Bone",
        city="West Des Moines",
        state="IA",
        website="https://desmoines.funnybone.com",
    )

    async def fail_fetch_html(*args, **kwargs):
        raise AssertionError("known DataDome host should not fetch website HTML")

    monkeypatch.setattr(mod.HttpClient, "fetch_html", fail_fetch_html)
    monkeypatch.setattr(mod, "close_js_browser", lambda: _noop_async())

    summary = _run_enrich([target])

    assert summary["description_hits"] == 1
    assert summary["bot_blocked"] == 0
    assert summary["extracted"] == 1


def test_known_datadome_existing_description_is_not_overwritten(monkeypatch):
    target = _target(
        174,
        "Comedy Mothership",
        city="Austin",
        state="TX",
        website="https://comedymothership.com",
        has_description=True,
    )

    async def fail_fetch_html(*args, **kwargs):
        raise AssertionError("known DataDome host should not fetch website HTML")

    monkeypatch.setattr(mod.HttpClient, "fetch_html", fail_fetch_html)
    monkeypatch.setattr(mod, "close_js_browser", lambda: _noop_async())

    summary = _run_enrich([target], force=True)

    # Cached description is suppressed because one already exists, so nothing
    # is extracted for this club.
    assert summary["description_hits"] == 0
    assert summary["extracted"] == 0


def test_known_datadome_laugh_factory_skips_website_fetch(monkeypatch):
    target = _target(
        171,
        "Laugh Factory Covina",
        city="Covina",
        state="CA",
        website="https://www.laughfactory.com/covina",
    )

    async def fail_fetch_html(*args, **kwargs):
        raise AssertionError("known DataDome host should not fetch website HTML")

    monkeypatch.setattr(mod.HttpClient, "fetch_html", fail_fetch_html)
    monkeypatch.setattr(mod, "close_js_browser", lambda: _noop_async())

    summary = _run_enrich([target])

    assert summary["description_hits"] == 1
    assert summary["bot_blocked"] == 0
    assert summary["extracted"] == 1
