## Scraper Platform Reference

For platform-specific venue onboarding guides (StageTime, Prekindle, Humanitix, Ninkashi, Tixr, Eventbrite, SeatEngine, Squarespace, Tockify, OvationTix, OpenDate, TicketSource, and more), see `apps/scraper/SCRAPERS.md`.

## Scraper Smoke Tests — Ticketmaster Venues: Patch TicketmasterClient in Sync Pipeline Tests

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

## Scraper Smoke Tests — Always Include `test_transformation_pipeline_produces_shows`

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

## Scraper Smoke Tests — Check for Unstaged Source Changes Before Committing

Before committing a `test_pipeline_smoke.py`, run:

```bash
git status --short apps/scraper/src/
```

Unstaged source changes (e.g. a new field on a PageData class) that a test
imports will be flagged as a must_fix during code review rather than caught
pre-commit.

## Scraper Smoke Tests — Verify SCRAPING_URL Against Current Migration for Existing Venues

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

## Scraper Smoke Tests — Mock Complex HTML Extractors Directly

When an extractor requires specific CSS classes or container structure (e.g.
Comedy Cellar's `set-header` divs), do NOT build a minimal HTML fixture and
pass it through the real extractor — the fixture will miss required elements
and the extractor will return `None`. Instead, patch `extract_events` directly:

```python
monkeypatch.setattr(MyExtractor, "extract_events", staticmethod(lambda *a: [fake_event]))
```

This bypasses fragile HTML construction while still exercising the full
scraper → extractor call path.

## Scraper Manual Run — Use `make scrape-club`, Not `bin/scrape`

Use `make scrape-club CLUB='<venue name>'` to run a scrape for a specific club.
`bin/scrape` does not exist — the `bin/` directory only contains `migrate` and
`cleanup-stale-scrapers`. Task criteria and next-steps that say "run bin/scrape"
should be interpreted as `make scrape-club CLUB='<name>'`.

The Makefile lives in `apps/scraper/` — always run from that directory:

```bash
cd apps/scraper && make scrape-club CLUB="Esther's Follies"
cd apps/scraper && make scrape-club CLUB="Comedy Cellar"
```

## Scraper Venue PageData — Module Must Be Named `data.py`

All venue scraper PageData modules must be named `data.py` (not `page_data.py`
or any other name). Every existing venue scraper (Gotham, St. Marks, Rockwell, etc.)
follows this convention. Importing from `.data` in `scraper.py` will fail if the
file is named differently.

```python
# In scraper.py — always import from .data
from .data import MyVenuePageData   # ✓ file is data.py
# from .page_data import ...        # ✗ breaks the import
```

## Scraper Bin Tests — Monkeypatch SCRAPER_ROOT for --apply Tests

Scripts that call `path.relative_to(SCRAPER_ROOT)` in print/display code (e.g., `delete_directory()`)
will raise `ValueError` in tests when paths are in `tmp_path`, because `tmp_path` is not under
`SCRAPER_ROOT`. Always monkeypatch `SCRAPER_ROOT` to an ancestor of your test paths:

```python
monkeypatch.setattr(_mod, "SCRAPER_ROOT", tmp_path)
```

This applies to any bin script test that uses `tmp_path` for directories that the script displays
relative to the project root.

## Scraper Documentation — Verify API Endpoints from Client Source

When writing or updating SCRAPERS.md (or any documentation about scraper API
endpoints), always read the actual client file directly:
  apps/scraper/src/laughtrack/core/clients/{platform}/client.py

Do NOT rely on explore-agent summaries for endpoint URLs — agents can conflate
platform details (e.g., Squarespace GetItemsByMonth vs. Wix paginated-events).
A 30-second file read avoids a review-cycle correction.

## Playwright MCP — Chrome Already Open Conflict

When the Playwright MCP browser fails with:
  "Opening in existing browser session" / process exits immediately

Chrome is already running with a conflicting profile. Options:
1. Close Chrome manually, then retry `browser_navigate`.
2. Fall back to WebFetch if the page is server-rendered (not a JS widget).
   Playwright is only needed when WebFetch returns misleading/empty results —
   e.g., a 403, missing API calls, or content that requires JS execution.

The Playwright pattern below is specifically for JS-heavy embedded widgets
(Crowdwork, SeatGeek, Wix). For standard HTML pages, WebFetch is sufficient.

## Loading Extension-Less Bin Scripts in Tests — Use SourceFileLoader

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

## Scraper Infrastructure Tests — Bypass Package `__init__` with SourceFileLoader

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

## React SSR `initial*` Props — Seed useState, Don't OR with State

When a Server Component passes an `initial*` value (e.g. `initialZipCapTriggered`) to a Client
Component that tracks derived state, always seed `useState(initialValue)` — never combine the
prop with mutable state via `||` in render:

```tsx
// ✗ Wrong — initialProp never changes after mount, so the hint permanently stays on
const showHint = initialZipCapTriggered || zipCapTriggered;

// ✓ Correct — seed useState with the initial value; state is updated by subsequent fetches
const [zipCapTriggered, setZipCapTriggered] = useState(initialZipCapTriggered ?? false);
```

This applies to any `useInfiniteSearch`-style hook that accepts an `initial*` option:
pass the SSR value into the hook so it can seed its own state, reset on param change,
and overwrite on each fetch — rather than leaving a static prop to dominate the render.

## Makefile Multi-line Python — Use printf Pipe, Not -c with Backslash Continuations

Make collapses backslash-continued lines into a single line before passing them to the shell.
This means any Python with indented blocks (`with`, `if`, `for`, `def`) **cannot** be written
via `-c "line1 \\\n    line2"` — it produces a `SyntaxError` at runtime.

Use `printf '%s\n'` piped to the Python binary instead:

```makefile
# ✗ Wrong — Make collapses continuations; 'with' block becomes one unindented line
	@$(PYTHON) -c "\
import sys; ...; \
with get_connection() as conn: \
    with conn.cursor() as cur: \
        cur.execute(...)"

# ✓ Correct — printf emits a real newline per argument; indentation is preserved
	@printf '%s\n' \
		'import sys; ...' \
		'with get_connection() as conn:' \
		'    with conn.cursor() as cur:' \
		'        cur.execute(...)' \
		| $(PYTHON)
```


## Scraper `bin/migrate` — Assemble DATABASE_URL from .env Components Locally

`bin/migrate` requires a full `DATABASE_URL` env var, but `apps/scraper/.env` stores
the connection as individual components (`DATABASE_HOST`, `DATABASE_USER`,
`DATABASE_PASSWORD`, `DATABASE_NAME`, `DATABASE_PORT`).  When `DATABASE_URL` is not
set, assemble it from components and pass it inline:

```bash
cd apps/scraper && DATABASE_URL="postgresql://${DATABASE_USER}:${DATABASE_PASSWORD}@${DATABASE_HOST}:${DATABASE_PORT:-5432}/${DATABASE_NAME}?sslmode=require" \
  .venv/bin/python bin/migrate
```

Or with a one-liner using Python to read the .env:

```bash
cd apps/scraper && DATABASE_URL=$(python3 -c "
from dotenv import dotenv_values
v = dotenv_values('.env')
print(f\"postgresql://{v['DATABASE_USER']}:{v['DATABASE_PASSWORD']}@{v['DATABASE_HOST']}:{v.get('DATABASE_PORT','5432')}/{v['DATABASE_NAME']}?sslmode=require\")
") .venv/bin/python bin/migrate
```

## Scraper Venue Scrapers — Test Concurrent Shows for Multi-Room Venues

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

## Scraper Entity `from_dict()` — Test Compact Time/Date Formats Upfront

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

## Scraper Alerting Tests — Mock MonitoringConfig

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

## Scraper pytest PATH — Pre-existing Failure Checks

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

## Creating New Files — Always Use Absolute Paths or the Write Tool

When creating new files (e.g., `__init__.py`, test stubs, migration files), always use either:
- The **Write tool** with an absolute `file_path` argument, or
- `touch /absolute/path/to/file` in Bash

Never use `touch relative/path` when the shell's CWD might be a subdirectory (e.g., `apps/scraper/`).
Using a path like `touch apps/scraper/tests/...` from within `apps/scraper/` silently creates the file
at `apps/scraper/apps/scraper/tests/...` — the doubled path is invisible until a later step fails.

## Venue Onboarding — Always Use HTTPS for Website URL

When writing a migration for a new venue, always use `https://` for the `website`
column — even if the task description or source page shows `http://`. Most modern
venues serve over HTTPS, and storing `http://` causes a redirect (or mixed-content
warning) in production.

Quick check before writing the migration:
```bash
curl -sI https://www.example.com | head -1   # should return 200, not 301
```

The migration runs before code review; a stale `http://` URL requires a corrective
UPDATE migration that cannot be merged until after the original one lands.

## Scraper Codebase Scope — src/ and web/ Both Count

When auditing scraper methods for unused/dead code, always search **both**:
- `apps/scraper/src/` — core library code
- `apps/scraper/web/` — companion Flask/FastAPI tools (e.g., `seatengine_api_tool/`)

Searches scoped only to `src/` will miss callers in `web/` and produce false "unused" findings.

```bash
# ✗ Wrong — misses web/ callers
grep -r "fetch_venue_details" apps/scraper/src/

# ✓ Correct — full scraper scope
grep -r "fetch_venue_details" apps/scraper/src/ apps/scraper/web/
```

## Scraper Logger — Context Dict Not Visible in Console Output

`Logger.warn(message, context_dict)` passes `context_dict` as `extra` to Python's
logging module. The console format string is:

    %(levelname)s | ... | %(message)s

Extra fields are **NOT** rendered — they are silently dropped at the terminal.
Always embed key debugging info directly in the message string:

```python
# ✗ Wrong — key/class names invisible in console output
Logger.warn("Duplicate key", {"key": k, "kept": kept_cls, "ignored": ignored_cls})

# ✓ Correct — all info in the message itself
Logger.warn(f"Duplicate key '{k}': keeping {kept_cls}, ignoring {ignored_cls}")
```

## VCR Cassette Refresh — Instagram / TikTok Social Tests

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

## Prisma orderBy Field Names — Verify Against Schema

Invalid field names in `orderBy` arrays cause `PrismaClientKnownRequestError` at runtime
(not a compile-time error), because helpers like `getGenericClauses` return loosely-typed
objects rather than `Prisma.*OrderByWithRelationInput`. Before adding a field to any `orderBy`
clause, verify it exists on the target model in `apps/web/prisma/schema.prisma`.

This applies equally to tiebreaker entries — they receive no extra type-checking:
```ts
// ✗ Wrong — Show has no totalShows field; crashes at runtime
orderBy: [{ popularity: "desc" }, { totalShows: "desc" }, { name: "asc" }]

// ✓ Correct — all fields exist on Show
orderBy: [{ popularity: "desc" }, { name: "asc" }]
```

## Prisma Select Consts — Avoid `new Date()` at Module Level

Never include `new Date()` in a module-level `as const` Prisma select object (e.g., inside a
`where: { date: { gt: new Date() } }` filter). The date is captured once at server startup,
not per request — causing stale date filters over long-lived server processes.

Instead, build the select object inside the query function body so `new Date()` is evaluated
fresh per request:

```ts
// ✗ Wrong — stale after server startup
const SELECT = { _count: { select: { items: { where: { date: { gt: new Date() } } } } } } as const;

// ✓ Correct — fresh per request
function buildSelect() {
    return { _count: { select: { items: { where: { date: { gt: new Date() } } } } } } as const;
}
```


## Prisma DIRECT_URL — Migration-Only, Not a Runtime Dependency

`DIRECT_URL` in `schema.prisma` (`directUrl = env("DIRECT_URL")`) is consumed
exclusively by the Prisma migration CLI (`prisma migrate deploy/dev`). The runtime
`PrismaClient` (and the `@prisma/adapter-neon` Pool) use only `DATABASE_URL`.

Do NOT add a module-level guard for `DIRECT_URL` in `lib/db.ts` or any other
runtime module — it will crash app servers and CI build jobs in environments
that run the app but not migrations.

## Prisma Interactive Transactions (Neon Serverless)

`db.$transaction(async (tx) => { ... })` **works correctly** with this project's Neon setup.
The project uses `@prisma/adapter-neon` with `@neondatabase/serverless` Pool (WebSocket
protocol), which connects directly to the Neon compute endpoint — not through PgBouncer.
The PgBouncer transaction-mode limitation (which blocks interactive transactions) does NOT
apply here.

When setting a specific isolation level, use the Prisma enum:
```ts
db.$transaction(async (tx) => { ... }, {
    isolationLevel: Prisma.TransactionIsolationLevel.RepeatableRead,
})
```

## Prisma Migrations

`prisma migrate dev` **cannot be run locally** in this project for two reasons:
1. The local PostgreSQL database is always empty (no tables); the real data lives in Neon serverless.
2. The shadow database validation fails on migration `20260308000000_set_email_scraper_fields` which contains a data-dependent operation requiring "Gotham Comedy Club" to exist.

**Workaround for new migrations**: Write the migration SQL manually, create the migration directory under `prisma/migrations/<timestamp>_<name>/migration.sql`, and commit both the schema and the migration file. The migration will be applied to the real DB via `prisma migrate deploy` in the deployment environment.

**After deploying UPDATE migrations**: `prisma migrate deploy` exits 0 even when a WHERE clause matches 0 rows — always verify the row count was non-zero after applying any migration that uses `UPDATE ... WHERE ...`. Query the DB or check the scraper behavior immediately after deploy to confirm the update took effect.

## Vitest Route Tests — Mocking the rateLimit Chain

Any route test that imports a handler using `@/lib/rateLimit` will transitively
load `@/auth` → `next-auth` → `next/server` (without .js), which fails in Node ESM.
Fix by adding this mock before the route import:

```ts
vi.mock("@/lib/rateLimit", () => ({
    checkRateLimit: vi.fn(() => ({ allowed: true, limit: 100, remaining: 99, resetAt: 0 })),
    getClientIp: vi.fn(() => "127.0.0.1"),
    RATE_LIMITS: { publicRead: {}, publicReadAuth: {} },
    rateLimitHeaders: vi.fn(() => ({})),
    rateLimitResponse: vi.fn(),
}));
```

## Vitest Route Tests — Auth/Authz Coverage

When writing tests for an auth-required route, always include at minimum:
- A test where `auth()` returns `null` → expect 401
- A test where `session.profile` is absent → expect 422
- A test where a user-scoped resource is requested with a mismatched userId → expect 403

Also: `mockAuth.mockResolvedValue(null as any)` — the `as any` cast is required because
`auth` is typed as `NextMiddleware`, which does not accept `null` directly.

## Public GET Routes — Rate Limiting

Use `applyPublicReadRateLimit(request, "<route-prefix>")` for all public GET API routes.
It automatically grants higher limits to authenticated users (keyed by user ID) vs anonymous
callers (keyed by IP), consistent with every other public GET route in the codebase.
Do NOT call `checkRateLimit` with `RATE_LIMITS.publicRead` directly in route handlers.

Also note: when mocking `@/lib/rateLimit` in Vitest, export `applyPublicReadRateLimit` as well:
```ts
applyPublicReadRateLimit: vi.fn(() => Promise.resolve({ allowed: true, limit: 60, remaining: 59, resetAt: 0 })),
```

## Python Test Directory Naming

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

## Testing RateLimiter Delay Calculations

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

## Tailwind Content Array — New Directories Under apps/web/ui/

When creating a new subdirectory under `apps/web/ui/` (e.g. `ui/util/`, `ui/hooks/`),
add a matching glob to the `content` array in `apps/web/tailwind.config.ts`:

    "./ui/<new-dir>/**/*.{js,ts,jsx,tsx}"

Without this, Tailwind's JIT purger will strip all classes from files in that directory
in production builds.

## Scraper Test Module Stubs — Use sys.modules.setdefault()

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

## Scraper Test Stubs — as_package=True Requires Real __path__

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

## Scraper Tests — patch.object for Dynamically Loaded Modules

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

## Scraper Tests — Mock RateLimiter Singleton via monkeypatch

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

## Testing Concurrent asyncio Races

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

## React Component and Hook Tests — Vitest Setup

The project uses `happy-dom` + `@testing-library/react` for React unit tests.
Add this docblock to any test file that renders React or calls hooks:

```
/**
 * @vitest-environment happy-dom
 */
```

Key mocking patterns:
- Mock `@/hooks/useUrlParams` (not `next/navigation` directly) to isolate hooks that read/write URL params.
- Mock heavy child components by path (e.g. `@/ui/components/params/sort`) to avoid their `next/navigation` dependency chain.
- Use `container.querySelector(...)` for scoped element queries when multiple renders exist in the same test — `getByTestId` queries the full document body and will throw on multiple matches.

Do NOT install `@vitejs/plugin-react` for test JSX support — it conflicts with vitest's bundled vite version.
The `esbuild.jsx: "automatic"` setting in `vitest.config.ts` handles JSX transform without a plugin.

## Vitest `vi.mock` Factories — Use `vi.hoisted()` for Shared Mock Variables

`vi.mock()` factories are hoisted to the top of the file before module-level `const`/`let`
variables are initialized. If a factory captures a variable defined in the module body,
it will throw `ReferenceError: Cannot access '<name>' before initialization`.

Fix: declare shared mock state with `vi.hoisted()`, which runs before hoisting:

```ts
const { mockFn } = vi.hoisted(() => ({ mockFn: vi.fn() }));

vi.mock("some-module", () => ({ fn: mockFn })); // ✓ safe
```

## `tusk commit` With New Test Directories — Verify Files Are Staged

When creating a new test directory (e.g., `tests/scrapers/.../the_rockwell/`) and calling
`tusk commit` with specific file paths, the commit output can be obscured by grep filters or
truncated output. If the files are untracked (not yet `git add`-ed), `tusk commit` may fail
silently on the `git add` step while still marking criteria done.

**Before calling `tusk criteria done --skip-verify`**, always verify all intended files are
either staged or committed:

```bash
git status --short apps/scraper/tests/   # confirms untracked test files
```

If files show as `??` (untracked) after a `tusk commit` call, stage and commit them manually:

```bash
git add <file1> <file2> && git commit -m "[TASK-<id>] <message>" \
  --trailer "Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

## HttpConvenienceMixin — Helper Methods Must Delegate to self.fetch_json()

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
