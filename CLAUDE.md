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

## Wix Events Scraper — Finding the Events Widget compId

When onboarding a new Wix venue, the events widget `compId` is NOT in the page
source directly. Find it via Playwright browser evaluation:

1. Navigate to the venue homepage in Playwright.
2. Run this JS to walk up from an event's "More info" button to its `comp-` container:

```js
(() => {
  const btn = document.querySelector('[data-hook^="more-info-link-"]');
  let el = btn;
  const ids = [];
  while (el && el !== document.body) {
    const id = el.id || el.getAttribute('data-comp-id') || '';
    if (id.startsWith('comp-')) ids.push({ id, cls: el.className.substring(0, 60) });
    el = el.parentElement;
  }
  return ids;
})()
```

3. The innermost `comp-xxxx` result is the events widget compId. Use it as `compId=<value>`
   in the `collect_scraping_targets()` params.

Note: `categoryId` is NOT required if the venue has no Wix event categories configured.
Applying a Bushwick-specific `categoryId` to a different Wix site returns HTTP 400.

## Ticketmaster Scraper — 0 Events Diagnosis

When a Ticketmaster-backed scraper returns 0 events, the first thing to check is
whether the stored `ticketmaster_id` is the correct **Discovery API venue ID** (format:
alphanumeric, e.g. `KovZ917ARvk`) — NOT a numeric ID from another system.

Verify by searching the Discovery API directly:
```bash
curl -s "https://app.ticketmaster.com/discovery/v2/venues.json?apikey=<KEY>&keyword=<venue name>&countryCode=US" | python3 -c "import sys,json; [print(v['id'], v['name']) for v in json.load(sys.stdin).get('_embedded',{}).get('venues',[])]"
```

Only investigate `classificationName` filters *after* confirming the venue ID returns
events at all (query without any classification filter first).

## Eventbrite Scraper — Organizer ID vs Venue ID

When onboarding a new Eventbrite venue, check whether the Eventbrite ID is a
**venue ID** (typically 8–9 digits, e.g. `253402413`) or an **organizer ID**
(typically 11 digits, e.g. `30460267696`).

The `eventbrite_id` field stores both types. The `EventbriteClient` tries
`/venues/{id}/events/` first; if that returns 404 (None), it automatically falls
back to `/organizers/{id}/events/`.

**Finding the ID:**
- Organizer ID: from the Eventbrite organizer page URL —
  `https://www.eventbrite.com/o/<slug>-<organizer_id>`
- Venue ID: inspect an individual event's JSON — look for `"venue_id"` in the
  page source or Eventbrite API response.

**Diagnosis:** If a scrape returns 0 events with a 404 warning on the venues
endpoint, the stored ID is likely an organizer ID — but the auto-fallback should
handle it transparently. Verify by checking the Eventbrite URL format.

## SeatEngine v3 Platform — Identifying UUID-Based Venues

When onboarding a new SeatEngine venue, check the subdomain before scanning
numeric IDs. The `v-{uuid}.seatengine.net` subdomain pattern (e.g.
`v-cf2b1561-bf36-40b8-8380-9c2a3bd0e4e3.seatengine.net`) means the venue
is on the **v3 platform** — a GraphQL API with UUID venue identifiers.
Scanning numeric IDs 1–700 will find nothing.

**Identification checklist:**
1. Check the page footer for "Powered by Seat Engine" + the banner/contact link.
2. If the linked domain matches `v-*.seatengine.net` → v3 platform (UUID).
3. If there is no `v-` subdomain → v1 platform (numeric ID, REST API).

**v3 setup:** use `scraper='seatengine_v3'` and store the UUID in `seatengine_id`.
The venue UUID is in the page's JSON-LD `<script>` as `"identifier": "..."`.

**v1 setup:** use `scraper='seatengine'` and store the numeric ID in `seatengine_id`.
Use `seatengine_national` to discover v1 venue IDs via enumeration.

## curl_cffi + DataDome — Header Fingerprint Debugging

When a curl_cffi request with `impersonate='chrome124'` succeeds with no custom headers
but returns 403 with your application headers, DataDome is detecting a specific header
combination. The trigger is never a single header — it's a combination (commonly
`Accept-Language + Cache-Control + Pragma` together).

**Diagnostic approach:**
1. Test with no headers → confirm 200
2. Binary search: split your header dict in half and test each half
3. Narrow down to the triggering combo (usually 2–3 headers together)

**Fix pattern:** bypass `BaseApiClient.fetch_html` (which always sends `self.headers`)
and use a bare `AsyncSession.get(url)` — curl_cffi's impersonation fingerprint alone
is enough and does not trigger DataDome:

```python
async with AsyncSession(impersonate=self._get_impersonation_target(url)) as session:
    response = await session.get(url)  # no extra headers
```

Note: `BaseApiClient.fetch_html(headers=None)` falls back to `self.headers` (via
`headers or self.headers`) — passing `None` or `{}` both result in API headers being
sent. A separate fetch method is needed to send zero application headers.

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

## Debugging Auth / Env Var Failures in Production

When a production login or OAuth flow silently fails, inspect the **actual values** of
environment variables — the Vercel dashboard only shows "Encrypted".

```bash
cd apps/web && vercel link --yes --project laughtrack 2>/dev/null; vercel env pull --environment production /tmp/vercel-prod-env && cat /tmp/vercel-prod-env; rm /tmp/vercel-prod-env
```

Check for **leading/trailing whitespace** in auth-related vars — especially `AUTH_URL`.
A trailing space (e.g. `"https://laugh-track.com "`) causes OAuth callback URL mismatches
that fail silently with no useful error message.

If `AUTH_URL` is wrong, remove and re-add it (Vercel does not support in-place edits):
```bash
vercel env rm AUTH_URL production --yes
echo "https://laugh-track.com" | vercel env add AUTH_URL production
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

Do NOT add `__init__.py` to test directories whose path segments match Python stdlib
module names (e.g., a directory named `email/` under `tests/`). pytest's rootdir-based
import mode works without `__init__.py`; adding it causes the test package to shadow
the stdlib module, producing `ModuleNotFoundError` at import time.

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
