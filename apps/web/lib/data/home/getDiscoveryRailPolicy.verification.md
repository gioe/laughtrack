# Discover policy load verification — TASK-4038

## Confirmed cause

The real Prisma reader against the configured production read-only data path
returned catalog version 6, then threw a ZodError at catalogVersion: expected 5.
Migration 20260817110000_rename_rarely_nearby_rail already advances all platform
policies to 6. The application catalog constant remained 5. This was validation
version drift, not malformed rail configuration, a generated-client mismatch, or
a failed database query. No production data was changed.

Before the fix, the new reader regression reported error instead of success and
all three migration-to-reader cases rejected migrated rows with received 6,
expected 5. Existing tests missed the mismatch because migration and application
fixtures asserted different versions without exercising the boundary.

The fix aligns the application catalog constant to 6. Policy revision numbers are
independent of catalog versions and remain unchanged. Unknown versions still fail
validation; the existing 150ms bound and safe fallback remain in place.

## Read-only verification

On 2026-09-22, a temporary Vitest probe invoked the actual getDiscoveryRailPolicy
and Prisma reader using the configured database, with Node's ws constructor set
for the Neon adapter. All three platform policies loaded successfully:

| Platform | Catalog | Stored policy revision | Stored rails |
| --- | --- | --- | --- |
| iOS | 6 | 9 | 9 |
| Web | 6 | 6 | 9 |
| Android | 6 | 6 | 9 |

The probe compared every returned rail field against a separate stored-row read,
then selected rails through selectDiscoveryPolicyRails. iOS selected 8 enabled
rails and respected the customized order; popular_clubs was disabled. Web and
Android each selected all 9 stored rails.

After warming the connection, 20 sequential iOS reads through the same optional
provider runner and 150ms deadline used by the feed returned 20 successes, zero
errors and zero timeouts. Durations ranged from 35.8 to 127.4ms. Every result used
stored policy revision 9. These are local reader measurements against production
data, not production feed latency percentiles or a deployed-route check. The
original single timeout is not independently attributed to catalog drift; slow
reads can still time out and safely fall back.

## Regression coverage

Run from apps/web:

```sh
npx vitest run lib/data/home/getDiscoveryRailPolicy.test.ts lib/discovery/railPolicy.test.ts lib/discovery/railSelector.test.ts lib/discovery/railPolicyMigration.test.ts app/api/v1/home/feed/route.test.ts app/api/admin/discovery-rails/route.test.ts ui/pages/admin/discovery-rails/AdminDiscoveryRailPolicyEditor.test.tsx
```

All 130 tests and the TypeScript build passed. Coverage includes real migrated
rows for all platforms, custom stored selection, invalid/missing/error fallback,
and exactly bounded timeout with late settlement ignored. The live probe was
removed so routine tests do not require credentials or contact production.
