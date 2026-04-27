# Contributing to the Scraper

## Logging Convention: `print()` vs `Logger`

This codebase intentionally uses both `print()` and `Logger` — they serve distinct purposes and both are correct.

| Use | When |
|-----|------|
| `print()` | User-facing terminal output: menus, prompts, formatted tables. Must reach the user's terminal regardless of the configured log level. `Logger.info` is silently dropped at the default WARNING console level, so interactive output **must** use `print()`. |
| `Logger` | Machine-readable telemetry: structured events, errors, progress markers written to log files or consumed by log aggregators. Use `Logger` for anything that should appear in log files or be monitored programmatically. |

**Rule of thumb:**
- User sees it → `print()`
- Log file / monitoring sees it → `Logger`
- User-facing *error feedback* that also belongs in log files → `Logger.warning` / `Logger.error` is acceptable (these surface on the terminal at the default WARNING level)

Future Logger-migration tasks must **not** require that all `print()` calls be removed from interactive CLI code — doing so would break user-facing menus and prompts.

### Worked Example

See [`src/laughtrack/utilities/domain/club/selector.py`](src/laughtrack/utilities/domain/club/selector.py) for a concrete example of a module that correctly mixes both — `print()` for menu rendering and `Logger` for structured event emission.

## Script Bootstrap (`scripts/core/`, `scripts/utils/`)

Every shebang-executable Python script under `apps/scraper/scripts/` opens with the
same `sys.path` bootstrap block:

```python
import sys
from pathlib import Path

# Locate scraper root (apps/scraper/) by walking up to pyproject.toml, then
# put src/ + scraper root on sys.path so laughtrack and 'scripts' package imports resolve.
_root = next(p for p in Path(__file__).resolve().parents if (p / "pyproject.toml").exists())
for _path in (_root / "src", _root):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))
```

A `_root / "src"`-only variant is also valid for scripts that don't need to import
from the `scripts.*` package (i.e., scripts that only `import laughtrack.…`):

```python
_root = next(p for p in Path(__file__).resolve().parents if (p / "pyproject.toml").exists())
_src = _root / "src"
if str(_src) not in sys.path:
    sys.path.insert(0, str(_src))
```

**Copy the block verbatim into any new script** in `scripts/core/` or `scripts/utils/`,
above the first `from laughtrack…` import. The marker-walk to `pyproject.toml` is
intentional — never replace it with `parents[N]` indexing, which silently breaks
when the script is moved or the directory layout changes.

### Why this isn't extracted to a shared helper

A `scripts/_bootstrap.py` that scripts could `import _bootstrap` looks tempting but
hits a chicken-and-egg problem:

- Scripts run as `__main__` (e.g., `./scrape_shows.py`), so Python adds the script's
  *own* directory (`scripts/core/` or `scripts/utils/`) to `sys.path[0]` — not
  `scripts/`. `import _bootstrap` from a script in `scripts/core/` would not find
  a `_bootstrap.py` placed in `scripts/`.
- The bootstrap itself is what puts `scripts/` on `sys.path`, so by the time
  `import _bootstrap` could resolve, the bootstrap has already done its job.
- Relative imports (`from .. import _bootstrap`) require running as a package
  (`python -m scripts.core.scrape_shows`), but the scripts are designed for
  shebang execution.

The duplicated 4–6 line block is a deliberate trade-off — small enough to copy,
robust to refactoring, and avoids hardcoded `parents[N]` indices. See TASK-1789
for the full rationale.

## Testing Patterns

These patterns apply whenever writing or modifying test files in `apps/scraper/tests/`.

### Smoke Tests

#### Ticketmaster Venues — Patch TicketmasterClient in Sync Pipeline Tests

`TicketmasterEventTransformer.transform_to_show()` instantiates `TicketmasterClient(self.club)`
on every event, and the constructor raises `ValueError` when `TICKETMASTER_API_KEY` is absent.
CI (`scraper-ci.yml`) does **not** set this env var, so the sync pipeline tests
(`test_transformation_pipeline_produces_shows`, `test_transformation_pipeline_preserves_event_name`)
will pass locally but fail in every CI run — producing 0 shows and failing the `len(shows) > 0`
assertion.

**Fix**: patch `TicketmasterClient` in the transformer module for those two tests:

```python
from unittest.mock import MagicMock, patch

mock_client = MagicMock()
mock_client.create_show.return_value = _fake_show()
with patch(
    "laughtrack.scrapers.implementations.api.ticketmaster.transformer.TicketmasterClient",
    return_value=mock_client,
):
    shows = scraper.transformation_pipeline.transform(page_data)
```

This applies to **all** `live_nation` venue smoke test files. Do not copy the unpatched
Second City pattern — it has the same bug.

**`get_data` tests also need a separate patch.** `test_get_data_returns_page_data_with_events`,
`test_get_data_returns_none_on_exception`, and `test_get_data_returns_non_transformable_when_api_returns_empty` call `get_data()`, which
instantiates `TicketmasterClient` directly in the scraper module (not the transformer). Patching
`TicketmasterClient.fetch_events` at the class level does not prevent the constructor from running.
**Fix**: patch `TicketmasterClient` at the **scraper** module level and configure `fetch_events`
as an `AsyncMock` on the returned instance:

```python
mock_client = MagicMock()
mock_client.fetch_events = AsyncMock(return_value=[_make_api_event()])
with patch(
    "laughtrack.scrapers.implementations.api.ticketmaster.scraper.TicketmasterClient",
    return_value=mock_client,
):
    result = await scraper.get_data(api_url)
```

Two patch targets, two test groups — never mix them:
- `transformer.TicketmasterClient` → `test_transformation_pipeline_*` tests
- `scraper.TicketmasterClient` → `test_get_data_*` tests

**Event IDs in smoke tests must be fake.** Use a clearly synthetic ID like `FAKE0000COBBS001`
or `FAKE0000PLSF001` — never a real Ticketmaster event ID. Real IDs are tied to specific show
dates and look stale once the event passes. The canonical pattern is `FAKE0000<VENUE_CODE>001`
where `<VENUE_CODE>` is a short uppercase abbreviation of the venue name (e.g. `COBBS`, `PLSF`,
`2CTY`).

#### Always Include `test_transformation_pipeline_produces_shows`

Every venue smoke test file (`test_pipeline_smoke.py`) **must** include a
`test_transformation_pipeline_produces_shows` test. This test catches regressions where
`can_transform()` returns `False` for the venue's event type (e.g., due to a generic type
mismatch on `DataTransformer[T]`), causing `transform()` to silently return an empty list
with no error.

```python
def test_transformation_pipeline_produces_shows():
    club = _club()
    scraper = MyVenueScraper(club)
    events = [_make_event("Show A"), _make_event("Show B")]
    page_data = MyVenuePageData(event_list=events)

    shows = scraper.transformation_pipeline.transform(page_data)

    assert len(shows) > 0, (
        "transformation_pipeline.transform() returned 0 Shows — "
        "check can_transform() and that the transformer is registered "
        "with the correct generic type"
    )
    assert all(isinstance(s, Show) for s in shows)
```

This test must be present even when other `to_show()` unit tests exist — those tests
call `event.to_show()` directly and bypass the transformer registry entirely.

#### Check for Unstaged Source Changes Before Committing

Before committing a `test_pipeline_smoke.py`, run:

```bash
git status --short apps/scraper/src/
```

Unstaged source changes (e.g. a new field on a PageData class) that a test
imports will be flagged as a must_fix during code review rather than caught
pre-commit.

#### Verify SCRAPING_URL Against Current Migration for Existing Venues

When writing a `test_pipeline_smoke.py` for an **existing** venue (one that already has a
migration in `prisma/migrations/`), always verify the `DOMAIN`/`SCRAPING_URL` test constants
match the venue's current production `scraping_url`. A prior migration may have updated it
(e.g., `20260319000006_fix_bushwick_scraping_url` changed Bushwick to `bushwickcomedy.com`).

Quick check:
```bash
grep -r "scraping_url" apps/web/prisma/migrations/ | grep "<venue_scraper_key>"
```

A stale domain in a test constant is a silent bug — the test passes locally but exercises a
URL that no longer matches the DB record, and will be flagged as a must_fix in code review.

#### Mock Complex HTML Extractors Directly

When an extractor requires specific CSS classes or container structure (e.g.
Comedy Cellar's `set-header` divs), do NOT build a minimal HTML fixture and
pass it through the real extractor — the fixture will miss required elements
and the extractor will return `None`. Instead, patch `extract_events` directly:

```python
monkeypatch.setattr(MyExtractor, "extract_events", staticmethod(lambda *a: [fake_event]))
```

This bypasses fragile HTML construction while still exercising the full
scraper → extractor call path.

#### Test Concurrent Shows for Multi-Room Venues

When scraping a venue with multiple rooms (e.g., Main Room, Belly Room, Original Room),
always include a test that exercises **two shows starting at the same time in different
rooms**.  A dedup bug that keys on date/time only — rather than the full unique show
identifier — will silently drop one show with no error.

```python
# Example: two concurrent shows at 8 PM in different rooms
async def test_concurrent_shows_same_time_different_rooms(monkeypatch):
    html = _day_html([
        {"slug": "2026-04-01t200000-0700-show-a", "title": "Show A", "room": "Main Room", ...},
        {"slug": "2026-04-01t200000-0700-show-b", "title": "Show B", "room": "Belly Room", ...},
    ])
    result = await scraper.get_data(url)
    assert len(result.event_list) == 2, "Both concurrent shows must be extracted"
```

This applies to any extractor that uses a set or dict to deduplicate extracted events.
Always use the full unique show identifier as the dedup key — not just the datetime portion.

#### Test Compact Time/Date Formats Upfront

When implementing `from_dict()` for a scraper entity that normalizes time or date
strings, write unit tests for compact formats (e.g., `"9PM"`, `"11AM"` — no colon
or space separator) **before** running a live scrape. Sites frequently store time
data in non-standard forms that only surface when hitting the real endpoint; a unit
test for the normalization function catches this without a round-trip to production.

```python
# Example: always test both canonical and compact forms
def test_compact_time_normalised():
    html = _make_rsc_html([_show(time="9PM")])
    events = MyExtractor.extract_shows(html)
    assert events[0].time == "9:00 PM"
```

### Test Infrastructure

#### pytest PATH — Pre-existing Failure Checks

`pytest` is not in PATH in the scraper project. When running pre-existing failure checks
in `apps/scraper/`, use the venv-local binary with an absolute path:

```bash
cd /Users/mattgioe/Desktop/projects/laughtrack/apps/scraper && .venv/bin/pytest --tb=no -q
```

Do not use `python3 -m pytest` — it also fails without venv activation.

**`tusk commit` test context:** `tusk commit` runs its test suite as `cd apps/scraper && python3 -m pytest`.
When reproducing a `tusk commit` test failure manually, always run from `apps/scraper/` — not from
the repo root. Running `python3 -m pytest` from the repo root uses `apps/scraper/` as a path prefix,
which doubles it in collection paths and produces spurious errors (e.g., 122 errors instead of 0).

#### Test Directory Naming

Venue scraper test directories (under `tests/scrapers/implementations/venues/<venue>/`)
**must** have an `__init__.py`. Every existing venue directory has one; without it pytest
throws `import file mismatch` when multiple `test_pipeline_smoke.py` files exist across
venues. Always create it (empty is fine) alongside the test file.

Do NOT add `__init__.py` to test directories whose path segments match Python stdlib
module names OR source package names (e.g., a directory named `email/` or `scripts/`
under `tests/`). pytest's rootdir-based import mode works without `__init__.py`; adding
it causes the test package to shadow the real package, producing `ModuleNotFoundError`
at collection time for any test that imports from that package.

Also check for same-name collisions across test subtrees before adding `__init__.py`.
If two directories in different parts of `tests/` share the same leaf name (e.g.
`tests/core/clients/ticketmaster/` and `tests/scrapers/.../api/ticketmaster/`), adding
`__init__.py` to both causes pytest to assign the same package name `ticketmaster` to
both → `ModuleNotFoundError: No module named 'ticketmaster.test_pipeline_smoke'` in
the full suite. Fix: leave the second directory without `__init__.py`. If the missing
`__init__.py` would cause an `import file mismatch` collision, add `__init__.py` only
to the *other* directories involved in the collision (e.g. the `*_national` sibling).

#### Monkeypatch SCRAPER_ROOT for --apply Tests

Scripts that call `path.relative_to(SCRAPER_ROOT)` in print/display code (e.g., `delete_directory()`)
will raise `ValueError` in tests when paths are in `tmp_path`, because `tmp_path` is not under
`SCRAPER_ROOT`. Always monkeypatch `SCRAPER_ROOT` to an ancestor of your test paths:

```python
monkeypatch.setattr(_mod, "SCRAPER_ROOT", tmp_path)
```

This applies to any bin script test that uses `tmp_path` for directories that the script displays
relative to the project root.

### Module Loading and Imports

#### Loading Extension-Less Bin Scripts — Use SourceFileLoader

`importlib.util.spec_from_file_location()` returns `None` for files without a
`.py` extension (e.g. `bin/migrate`). Use `SourceFileLoader` directly instead:

```python
import importlib.machinery, importlib.util

loader = importlib.machinery.SourceFileLoader("bin_migrate", str(_BIN_PATH))
spec   = importlib.util.spec_from_loader("bin_migrate", loader)
mod    = importlib.util.module_from_spec(spec)
loader.exec_module(mod)
```

Do NOT use `spec_from_file_location(name, path)` for extension-less scripts —
it silently returns `None`, causing `AttributeError` on `spec.loader`.

#### Bypass Package `__init__` with SourceFileLoader

When a test file needs to import from `laughtrack.utilities.infrastructure` (e.g.
`error_handling.py`), importing through the package triggers `__init__.py` which
imports `RateLimiter` → `gioe_libs` (an optional private dep not in requirements.txt).
This causes a `ModuleNotFoundError` in any environment where `gioe_libs` is absent.

**Fix**: load the module file directly via `SourceFileLoader`, bypassing `__init__.py`:

```python
import importlib.machinery, importlib.util, sys
from pathlib import Path

_SCRAPER_SRC = Path(__file__).parents[3] / "src"   # adjust depth to reach apps/scraper/src

def _load_module(dotted_name):
    path = _SCRAPER_SRC / dotted_name.replace(".", "/")
    if not path.suffix:
        path = path.with_suffix(".py")
    loader = importlib.machinery.SourceFileLoader(dotted_name, str(path))
    spec = importlib.util.spec_from_loader(dotted_name, loader)
    mod = importlib.util.module_from_spec(spec)
    sys.modules.setdefault(dotted_name, mod)   # register before exec to prevent circular import issues
    loader.exec_module(mod)
    return mod

_error_handling = _load_module("laughtrack.utilities.infrastructure.error_handling")
ErrorHandler = _error_handling.ErrorHandler
RetryConfig   = _error_handling.RetryConfig
```

**Do NOT** stub `gioe_libs` with a `MagicMock` or non-async object in a conftest.py —
the stub leaks into sibling test directories (e.g. `tests/utilities/test_rate_limiter.py`)
and breaks tests that `await` the rate limiter. A conftest.py with an async-compatible stub
(same `_FakeBaseRateLimiter` as `test_rate_limiter.py`, using `setdefault`) is safe and
preferred for directory-scoped fixes over modifying every test file individually.

#### Test Module Stubs — Use sys.modules.setdefault()

When writing a `_stub()` helper in scraper test files to register fake modules,
always use `sys.modules.setdefault(name, m)` — NOT `sys.modules[name] = m`.
Direct assignment overwrites any real package already loaded, causing test-ordering
failures: tests that run after the stub file see a plain ModuleType instead of the
real package, producing errors like "No module named 'laughtrack.foundation.models'".

```python
# Wrong — overwrites real packages loaded by earlier tests
def _stub(name, **attrs):
    m = ModuleType(name)
    sys.modules[name] = m   # ← always clobbers
    return m

# Correct — safe; skips if the real package is already registered
def _stub(name, **attrs):
    m = ModuleType(name)
    sys.modules.setdefault(name, m)   # ← no-op when already present
    return m
```

#### Test Stubs — as_package=True Requires Real __path__

When a `_stub()` helper supports `as_package=True`, setting `__path__ = []` (empty list)
causes the same submodule-blocking problem as a plain module without `__path__`. Python
cannot find subpackages in an empty path, so later imports like
`from laughtrack.core.entities.tag.model import Tag` fail with `ModuleNotFoundError`
even though the stub is correctly registered via `setdefault`.

Always compute `__path__` from the real source directory:

```python
# ✗ Wrong — empty __path__ blocks submodule discovery for ALL later tests
def _stub(name, as_package=False, **attrs):
    m = ModuleType(name)
    if as_package:
        m.__path__ = []   # ← never do this

# ✓ Correct — real path lets Python find submodules on disk
def _stub(name, as_package=False, **attrs):
    m = ModuleType(name)
    if as_package:
        m.__path__ = [str(_SCRAPER_ROOT / "src" / name.replace(".", "/"))]
        m.__package__ = name
```

This is especially important for namespace packages (no `__init__.py`, e.g.
`laughtrack.core.entities`) and for any package whose submodules may be needed by
later test files in the same pytest run.

### Mocking

#### Alerting Tests — Mock MonitoringConfig

Any test that exercises `_check_and_alert` (or any method that calls
`MonitoringConfig.default()` internally) must mock `MonitoringConfig.default()`
— otherwise the test will silently pass or fail depending on whether Discord is
configured in the local environment.

Pattern:
```python
mock_config = MagicMock()
mock_config.get_configured_channels.return_value = ["discord"]
mock_config.is_discord_configured.return_value = True
mock_config.discord_webhook_url = "https://discord.example/webhook"
with patch('laughtrack.infrastructure.config.monitoring_config.MonitoringConfig') as MockConfig:
    MockConfig.default.return_value = mock_config
    svc._check_and_alert(summary)
```

#### patch.object for Dynamically Loaded Modules

When patching an attribute (e.g. `Logger`) on a module loaded via `_load_module()` /
`importlib.util.spec_from_file_location()`, always use `patch.object(module_obj, "attr")`
— **never** the string form `patch("laughtrack.core.entities.club.service_direct.attr")`.

The string form resolves the dotted path by walking the real `laughtrack.core.entities`
package. If any prior test in the session has imported that real package, Python finds it
in `sys.modules` and looks for a `club` attribute on it — which doesn't exist — raising
`AttributeError`. The isolated test run passes; the full suite run fails.

```python
# ✗ Wrong — breaks when the real laughtrack.core.entities package is in sys.modules
with patch("laughtrack.core.entities.club.service_direct.Logger") as mock_logger:
    service.find_club_by_name("...")

# ✓ Correct — patches the attribute directly on the loaded module object
with patch.object(_club_service_mod, "Logger") as mock_logger:
    service.find_club_by_name("...")
```

This applies to any attribute on any module loaded under a dotted name that shares a
prefix with a real package in the codebase.

#### Mock RateLimiter Singleton via monkeypatch

`RateLimiter()` is a singleton. **Never** mock its methods via direct instance assignment:

```python
# ✗ Wrong — mutates singleton.__dict__, leaks mock to all subsequent tests
scraper.rate_limiter.await_if_needed = fake_fn

# ✓ Correct — monkeypatch restores the attribute after each test
monkeypatch.setattr(scraper.rate_limiter, "await_if_needed", fake_fn)
```

Direct assignment persists after the test ends, causing unrelated test classes to call
your fake function instead of the real one. Symptom: tests like `TestResetDomain` that
call `await rl.await_if_needed(...)` find `_sessions` empty and fail with confusing
`AssertionError: assert 'domain' in {}`.

#### Testing RateLimiter Delay Calculations

When patching `random.uniform` in tests for `_calculate_anti_detection_delay`,
use `side_effect=lambda a, b: a` (returns the lower bound) rather than
`return_value=0.0`. The `return_value` form ignores the distribution bounds
entirely — so `min_delay=2.0` still produces `base=0.0`. Combined with the
`max(delay, 1.0)` floor, this makes all zero-min_delay configs produce 1.0,
masking multiplier effects:

```python
# Wrong — return_value ignores min_delay/max_delay args
with patch("...random.uniform", return_value=0.0): ...

# Correct — returns lower bound; base = min_delay, jitter = -0.5
with patch("...random.uniform", side_effect=lambda a, b: a): ...
```

#### HttpConvenienceMixin — Helper Methods Must Delegate to self.fetch_json()

When adding a new method to `HttpConvenienceMixin` that narrows the return type
of an existing method (e.g. `fetch_json_list` wrapping `fetch_json`), always
delegate to `self.fetch_json()` rather than duplicating the HTTP call:

```python
# ✓ Correct — delegates; tests that mock instance.fetch_json are intercepted
async def fetch_json_list(self, url, **kwargs):
    data = await self.fetch_json(url, **kwargs)
    ...

# ✗ Wrong — duplicate HTTP call bypasses instance-level AsyncMock patches
async def fetch_json_list(self, url, **kwargs):
    session = await self.get_session()
    response = await session.get(url, **kwargs)
    ...
```

Tests mock `scraper.fetch_json = AsyncMock(return_value=data)` at the instance
level — a duplicate implementation bypasses the mock and hits the real network.

### Async and Concurrency

#### Testing Concurrent asyncio Races

`AsyncMock` operations resolve in a single event-loop turn with no suspension.
A test using `asyncio.gather(coroutine_a(), coroutine_b())` may pass even when
a TOCTOU race bug is present, because one coroutine completes entirely before
the other begins — the race window never opens.

To properly force a race, use `asyncio.Event` + a `side_effect` that does
`await asyncio.sleep(0)` at the critical point to yield control to competing
coroutines. Example:

```python
entered = asyncio.Event()
async def slow_side_effect(*args, **kwargs):
    entered.set()            # signal we are inside the critical section
    await asyncio.sleep(0)   # yield so the competing coroutine can run
    return mock.return_value
mock.side_effect = slow_side_effect
```

### VCR Cassettes

#### VCR Cassette Refresh — Instagram / TikTok Social Tests

Cassette tests in `apps/scraper/tests/core/entities/test_social_refresh_vcr.py`
use `record_mode="none"`, which replays pre-recorded HTTP responses. When Instagram
or TikTok changes their API schema, cassettes must be re-recorded.

**Prerequisites:** Run locally (not from CI/cloud). Both platforms block datacenter
IPs. No extra credentials are needed for these public endpoints, but a residential
IP or VPN may be required if your network is flagged.

**Steps:**
1. Change `record_mode` in the `_vcr` instance from `"none"` to `"new_episodes"`.
   To force a full re-record of a specific cassette, delete its YAML from
   `tests/core/entities/cassettes/` first.
2. Run: `cd apps/scraper && python -m pytest tests/core/entities/test_social_refresh_vcr.py -v`
3. Review `git diff tests/core/entities/cassettes/` — confirm changed keys match
   the known schema update. Unexpected changes (redirects, auth challenges) should
   be investigated before committing.
4. Reset `record_mode` back to `"none"`.
5. Re-run tests to confirm replay-only mode passes, then commit the cassette YAMLs:
   `git add tests/core/entities/cassettes/ && git commit -m "Update VCR cassettes: <reason>"`
