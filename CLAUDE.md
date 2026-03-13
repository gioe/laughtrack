## Scraper DB Connection

`db.get_connection()` (and `db.get_connection(autocommit=True)`) opens a psycopg2 connection with `autocommit=True` by default. Each `cur.execute()` commits immediately — no explicit `conn.commit()` is required. Use `db.get_transaction()` only when you need multi-statement atomicity.

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
