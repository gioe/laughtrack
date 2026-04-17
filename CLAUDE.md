## Investigating API Responses — Use Direct HTTP Calls, Not WebFetch

WebFetch summarizes JSON content via an AI model — it may report fewer array items
than the actual response (e.g., "30 events" when the API returned 105). This can
produce wrong initial hypotheses when investigating API behavior.

When inspecting API response structure, item counts, or cross-page consistency, use
a direct Python call instead:

```python
# In apps/scraper/ where ssl cert issues apply, disable cert verification:
import ssl, urllib.request, json
ctx = ssl.create_default_context()
ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE
with urllib.request.urlopen(url, context=ctx) as r:
    data = json.loads(r.read())
print(len(data), data[0])  # actual count and first item
```

WebFetch remains appropriate for reading human-readable HTML pages or docs.

## Scraper Platform Reference

For platform-specific venue onboarding guides (StageTime, Prekindle, Humanitix, Ninkashi, Tixr, Eventbrite, SeatEngine, Squarespace, Tockify, OvationTix, OpenDate, TicketSource, and more), see `apps/scraper/SCRAPERS.md`.

## Scraper Testing Patterns

For testing patterns when writing scraper tests (smoke tests, module loading, mocking, async, VCR cassettes, etc.), see `apps/scraper/CONTRIBUTING.md`.

## Scraper Tests — Module-Level sys.modules Stubs Persist Across Session

Several scraper test files (e.g., `test_comedian_handler.py`, `test_lineup_handler.py`,
`test_social_refresh.py`) inject module stubs at **module level** using
`sys.modules.setdefault(name, stub)`. These stubs persist for the entire pytest session.

**Risk**: Any `__post_init__` or lazy import that reads from a stubbed module and writes
back to `self.X` will silently corrupt instance state. For example, if
`ComedianUtils` is stubbed as a `MagicMock`, then:

```python
# In Comedian.__post_init__ — self.name gets assigned a MagicMock
normalized = ComedianUtils.normalize_name(self.name)  # returns MagicMock
self.name = normalized  # ← corrupts the name
```

**Rule**: When writing or modifying `__post_init__` methods that lazily import from
`laughtrack.utilities.*`, do NOT assign the return value back to `self.X` unless you
also add a guard:

```python
normalized = ComedianUtils.normalize_name(self.name)
if isinstance(normalized, str) and normalized:
    self.name = normalized
```

Long-term fix: refactor module-level stubs to use `pytest` fixtures with `monkeypatch`
so cleanup happens automatically after each test (tracked in TASK-920).

## Scraper Tests — Patching `execute_values`

`base_handler.py` imports `execute_values` directly:

```python
from psycopg2.extras import execute_values
```

To mock it in tests, patch the name in the **module's namespace** — NOT on `psycopg2.extras`:

```python
# ✗ Wrong — patches the original; base_handler already holds a reference to the old name
patch.object(_base_handler_mod.psycopg2.extras, "execute_values", ...)

# ✓ Correct — patches the name as bound in the loaded module
patch.object(_base_handler_mod, "execute_values", ...)
```

This applies to any function imported with `from X import Y` — always patch at the usage site.

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

## Eventbrite — Two Distinct Category Numbering Systems

The Eventbrite API uses **different category/subcategory IDs** depending on which endpoint is called:

- **Venue/organizer list API** (`/venues/{id}/events/`, `/organizers/{id}/events/`):
  - `category_id=103` → Music (DJ sets, karaoke, concerts)
  - `category_id=105` → Performing & Visual Arts (comedy is subcategory `5010`)

- **Search API** (`/events/search/`), used by `EventbriteNationalScraper`:
  - `category_id=103` → Performing & Visual Arts
  - `subcategory_id=103003` → Comedy

Filters in `EventbriteEvent.to_show()` must account for both paths — blocking `category_id=103`
alone would drop comedy events fetched via the national scraper path. The constants
`_MUSIC_CATEGORY_ID` and `_COMEDY_SUBCATEGORY_IDS` in `entities/event/eventbrite.py` encode
this duality.

Also note: `category_id` and `subcategory_id` are **top-level fields** in both API responses
and are returned without needing to include them in the `expand` parameter.

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

## Local Dev — Use `npm run dev`

From `apps/web/`, run `npm run dev`. The wrapper at `apps/web/bin/dev` reads
`apps/scraper/.env`, assembles `DATABASE_URL` from the component vars, and
execs `next dev`. Exported `DATABASE_URL` takes precedence over `.env.local`
(Next.js preserves any var already in `process.env`), so you can leave the
broken localhost value in `.env.local` and the wrapper still wins.

Flags:
- `npm run dev -- --fresh` — clears `.next/` before starting. Use this when
  the Tailwind JIT cache looks stale or after editing `tailwind.config.ts`.

The dev server connects to production Neon. Prefer the UI for read-only
verification; avoid destructive actions. A warning prints on startup whenever
`DATABASE_HOST` is not `localhost`/`127.0.0.1`.

## Prisma Migrations

`prisma migrate dev` is **out of scope** for local dev. Reasons:
1. No local `laughtrack` PostgreSQL database is provisioned; runtime hits Neon directly via `bin/dev`.
2. Even pointed at Neon, shadow-DB validation fails on
   `20260308000000_set_email_scraper_fields`, which contains a data-dependent
   operation that requires "Gotham Comedy Club" to exist.

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

## Tailwind Content Array — New Directories Under apps/web/ui/

When creating a new subdirectory under `apps/web/ui/` (e.g. `ui/util/`, `ui/hooks/`),
add a matching glob to the `content` array in `apps/web/tailwind.config.ts`:

    "./ui/<new-dir>/**/*.{js,ts,jsx,tsx}"

Without this, Tailwind's JIT purger will strip all classes from files in that directory
in production builds.

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

## Scraper Tests — Patching Logger Calls

Always patch `Logger` at the **usage site** (the handler/scraper module), not on the
Logger class method directly:

```python
# ✗ Wrong — breaks when Logger in the handler is the real class (loaded before stubs)
logger_mod = sys.modules.get("laughtrack.foundation.infrastructure.logger.logger")
with patch.object(logger_mod.Logger, "warn") as mock_warn:
    handler.some_method()
mock_warn.assert_called_once()

# ✓ Correct — patches the name in the handler module's namespace
with patch.object(_handler_mod, "Logger") as mock_logger:
    handler.some_method()
mock_logger.warn.assert_called_once()
```

Patching the class method (`patch.object(Logger_class, "warn")`) fails silently when
the real logger module has already been loaded into sys.modules by an earlier test
(e.g. test_scraper_resolver.py) — the handler's `Logger` reference is the real class,
but the patch and the reference diverge under certain session orderings.

## Scraper Tests — Direct sys.modules Assignment Must Save/Restore

When a test helper function uses `sys.modules[name] = m` (direct assignment, not
`setdefault`) to register stubs, it MUST save and restore the affected entries using
try/finally — or it will corrupt the session for every test that runs afterward:

```python
# ✗ Wrong — permanently replaces real modules; breaks downstream tests in full suite
def _load_module_with_stubs():
    sys.modules["some.real.module"] = stub_module
    spec.loader.exec_module(mod)
    return mod

# ✓ Correct — save/restore so the stubs only live during module loading
def _load_module_with_stubs():
    _saved = {name: sys.modules.get(name) for name in _stub_names}
    try:
        for name in _stub_names:
            sys.modules[name] = create_stub(name)
        spec.loader.exec_module(mod)
        return mod
    finally:
        for name, original in _saved.items():
            if original is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = original
```

`setdefault` is safe (only sets if absent), but `sys.modules[name] = m` overwrites
existing entries and leaves them replaced for the rest of the pytest session.
The save/restore pattern is required whenever direct assignment is used.
