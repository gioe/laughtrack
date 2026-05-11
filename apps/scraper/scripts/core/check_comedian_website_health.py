#!/usr/bin/env python3
"""Check stored comedian website URLs and requeue stale records.

This job verifies the current ``website`` and ``website_scraping_url`` values
without spending search-provider quota. Repeated hard failures mark the affected
URL as stale so the existing discovery jobs can revisit it.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, Optional

_root = next(p for p in Path(__file__).resolve().parents if (p / "pyproject.toml").exists())
for _path in (_root / "src", _root):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from laughtrack.adapters.db import create_connection
from laughtrack.foundation.infrastructure.http.client import _bot_block_reason
from laughtrack.foundation.infrastructure.logger.logger import Logger

HealthStatus = Literal["ok", "redirect", "hard_failure", "transient_failure", "bot_block"]
URLFieldName = Literal["website", "website_scraping_url"]

_GET_COMEDIAN_URL_TARGETS = """
    SELECT uuid, name, website, website_scraping_url,
           COALESCE(website_health_failure_count, 0) AS website_health_failure_count,
           COALESCE(website_scraping_url_health_failure_count, 0) AS website_scraping_url_health_failure_count
    FROM comedians
    WHERE parent_comedian_id IS NULL
      AND (
        (website IS NOT NULL AND website <> '')
        OR (website_scraping_url IS NOT NULL AND website_scraping_url <> '')
      )
    ORDER BY popularity DESC NULLS LAST
"""

_UPDATE_WEBSITE_HEALTH = """
    UPDATE comedians
    SET website_health_status = %s,
        website_health_failure_count = %s,
        website_health_checked_at = NOW()
    WHERE uuid = %s
"""

_UPDATE_SCRAPING_URL_HEALTH = """
    UPDATE comedians
    SET website_scraping_url_health_status = %s,
        website_scraping_url_health_failure_count = %s,
        website_scraping_url_health_checked_at = NOW()
    WHERE uuid = %s
"""


@dataclass(frozen=True)
class URLHealthResult:
    status: HealthStatus
    status_code: Optional[int] = None
    final_url: Optional[str] = None
    reason: str = ""


@dataclass(frozen=True)
class ComedianURLTarget:
    uuid: str
    name: str
    field_name: URLFieldName
    url: str
    failure_count: int = 0


@dataclass(frozen=True)
class URLHealthUpdate:
    health_status: str
    new_failure_count: int
    queue_for_rediscovery: bool = False


@dataclass
class HealthCheckSummary:
    checked_urls: int = 0
    hard_failures: int = 0
    transient_failures: int = 0
    bot_blocks: int = 0
    queued_for_rediscovery: int = 0


def classify_health_response(response: Any, original_url: str) -> URLHealthResult:
    """Classify a fetched URL without invoking search rediscovery."""
    status_code = getattr(response, "status_code", None)
    body = getattr(response, "text", "") or ""
    final_url = str(getattr(response, "url", "") or original_url)

    if _bot_block_reason(body):
        return URLHealthResult("bot_block", status_code=status_code, final_url=final_url)
    if status_code in (404, 410):
        return URLHealthResult("hard_failure", status_code=status_code, final_url=final_url)
    if status_code is None or status_code >= 500 or status_code in (408, 425, 429):
        return URLHealthResult("transient_failure", status_code=status_code, final_url=final_url)
    if 300 <= status_code < 400:
        return URLHealthResult("redirect", status_code=status_code, final_url=final_url)
    if 400 <= status_code < 500:
        return URLHealthResult("bot_block", status_code=status_code, final_url=final_url)
    if final_url.rstrip("/") != original_url.rstrip("/"):
        return URLHealthResult("redirect", status_code=status_code, final_url=final_url)
    return URLHealthResult("ok", status_code=status_code, final_url=final_url)


def classify_fetch_exception(exc: BaseException) -> URLHealthResult:
    return URLHealthResult("transient_failure", reason=f"{type(exc).__name__}: {exc}")


def plan_url_health_update(
    target: ComedianURLTarget,
    result: URLHealthResult,
    *,
    hard_failure_threshold: int = 3,
) -> URLHealthUpdate:
    if result.status in ("ok", "redirect"):
        return URLHealthUpdate(result.status, 0)
    if result.status == "hard_failure":
        new_count = target.failure_count + 1
        if new_count >= hard_failure_threshold:
            return URLHealthUpdate("stale", new_count, queue_for_rediscovery=True)
        return URLHealthUpdate("hard_failure", new_count)
    if result.status == "bot_block":
        return URLHealthUpdate("bot_block", target.failure_count)
    return URLHealthUpdate("transient_failure", target.failure_count)


def _iter_targets(rows: list[dict[str, Any]]) -> list[ComedianURLTarget]:
    targets: list[ComedianURLTarget] = []
    for row in rows:
        website = row.get("website")
        if website:
            targets.append(
                ComedianURLTarget(
                    uuid=row["uuid"],
                    name=row["name"],
                    field_name="website",
                    url=website,
                    failure_count=row.get("website_health_failure_count") or 0,
                )
            )
        scraping_url = row.get("website_scraping_url")
        if scraping_url and scraping_url != website:
            targets.append(
                ComedianURLTarget(
                    uuid=row["uuid"],
                    name=row["name"],
                    field_name="website_scraping_url",
                    url=scraping_url,
                    failure_count=row.get("website_scraping_url_health_failure_count") or 0,
                )
            )
    return targets


async def _fetch_url(session: Any, url: str, timeout: int) -> URLHealthResult:
    try:
        response = await session.get(url, timeout=timeout, impersonate="chrome", allow_redirects=True)
    except TypeError:
        response = await session.get(url, timeout=timeout, allow_redirects=True)
    except BaseException as exc:
        return classify_fetch_exception(exc)
    return classify_health_response(response, url)


def _update_query(field_name: URLFieldName) -> str:
    if field_name == "website":
        return _UPDATE_WEBSITE_HEALTH
    return _UPDATE_SCRAPING_URL_HEALTH


async def run_health_check(
    *,
    session: Any | None = None,
    limit: int | None = None,
    hard_failure_threshold: int = 3,
    timeout: int = 20,
    commit: bool = True,
) -> HealthCheckSummary:
    conn = create_connection(autocommit=False)
    close_session = False
    if session is None:
        from curl_cffi.requests import AsyncSession

        session = AsyncSession()
        close_session = True

    try:
        with conn.cursor() as cur:
            query = _GET_COMEDIAN_URL_TARGETS
            params: tuple[Any, ...] | None = None
            if limit:
                query += "\n    LIMIT %s"
                params = (limit,)
            cur.execute(query, params)
            rows = cur.fetchall()

        summary = HealthCheckSummary()
        for target in _iter_targets(rows):
            result = await _fetch_url(session, target.url, timeout)
            update = plan_url_health_update(
                target,
                result,
                hard_failure_threshold=hard_failure_threshold,
            )

            summary.checked_urls += 1
            if result.status == "hard_failure":
                summary.hard_failures += 1
            elif result.status == "transient_failure":
                summary.transient_failures += 1
            elif result.status == "bot_block":
                summary.bot_blocks += 1
            if update.queue_for_rediscovery:
                summary.queued_for_rediscovery += 1

            Logger.info(
                "comedian_url_health: "
                f"{target.name} {target.field_name}={target.url} "
                f"status={result.status} health_status={update.health_status} "
                f"failures={update.new_failure_count}"
            )

            if commit:
                with conn.cursor() as cur:
                    cur.execute(
                        _update_query(target.field_name),
                        (update.health_status, update.new_failure_count, target.uuid),
                    )

        if commit:
            conn.commit()

        Logger.info(
            "comedian_url_health summary: "
            f"checked_urls={summary.checked_urls}, "
            f"hard_failures={summary.hard_failures}, "
            f"transient_failures={summary.transient_failures}, "
            f"bot_blocks={summary.bot_blocks}, "
            f"queued_for_rediscovery={summary.queued_for_rediscovery}"
        )
        return summary
    finally:
        if close_session:
            await session.close()
        conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Check comedian website URL health")
    parser.add_argument("--limit", type=int, help="Maximum comedian records to check")
    parser.add_argument("--threshold", type=int, default=3, help="Hard failures before marking stale")
    parser.add_argument("--timeout", type=int, default=20, help="Per-request timeout in seconds")
    parser.add_argument("--dry-run", action="store_true", help="Check URLs without writing health state")
    parser.add_argument("-v", "--verbose", action="store_true", help="Show INFO-level logs")
    args = parser.parse_args()

    if args.verbose:
        current = os.environ.get("LAUGHTRACK_LOG_CONSOLE_LEVEL", "").upper()
        if current not in ("DEBUG", "INFO"):
            os.environ["LAUGHTRACK_LOG_CONSOLE_LEVEL"] = "INFO"

    asyncio.run(
        run_health_check(
            limit=args.limit,
            hard_failure_threshold=args.threshold,
            timeout=args.timeout,
            commit=not args.dry_run,
        )
    )


if __name__ == "__main__":
    main()
