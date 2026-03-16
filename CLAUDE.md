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

## TypeScript Check After Writing Test Files

After writing any new `.test.ts` / `.test.tsx` file, run `tsc --noEmit` before committing.
Test files are not compiled by Vitest (it transpiles without type-checking), so TypeScript
errors in tests are only caught by the type-checker — not by `npx vitest run`.

## Scraper DB Connection

`db.get_connection()` (and `db.get_connection(autocommit=True)`) opens a psycopg2 connection with `autocommit=True` by default. Each `cur.execute()` commits immediately — no explicit `conn.commit()` is required. Use `db.get_transaction()` only when you need multi-statement atomicity.

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

## npm audit fix in apps/web

Due to next-auth beta's strict peer dependency declarations, `npm audit fix`
will fail with ERESOLVE unless you pass `--legacy-peer-deps`:

    npm audit fix --legacy-peer-deps

Also: lockfile regeneration can silently bump transitive beta deps (e.g.,
next-auth beta.25 → beta.30). After running audit fix, check `git diff
apps/web/package-lock.json` for implicit version bumps in packages listed
in package.json and update the pinned versions there to match.

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
