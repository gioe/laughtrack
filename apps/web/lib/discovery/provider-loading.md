# Discover provider scheduling (TASK-4033)

The home/feed route preserves the response schema and legacy arrays. It awaits
primary discovery: trending comedians, tonight's shows, nearby shows (including
the hero), and this week's shows. These providers retain per-section error
isolation. Empty or failed primary sections do not discard ready optional content;
if everything is empty, the existing successful empty feed/empty plan is returned.
Authentication errors still fail the request.

## Response budgets

- Policy lookup starts alongside hero/location lookup and has a **150 ms** budget.
  Failure or timeout uses the existing platform default policy.
- Once location and policy resolve, optional providers share **one 750 ms absolute
  deadline**. This includes clubs, nearby comedians, followed-comedian shows,
  episode recommendations, trending podcasts, touring, fresh/rising and affinity.
- The provider phase therefore waits for `max(primary duration, optional duration
  capped at 750 ms)`, not a separate 750 ms per optional provider. Fast providers
  return immediately; there is no mandatory delay when all work finishes early.
- This is not a 750 ms end-to-end SLA. Authentication, rate limiting, location,
  primary queries, event-loop scheduling, serialization and network delivery remain
  outside that optional-work budget. A slow primary query is still awaited.

750 ms allows optional content to participate while limiting the multi-second
cold-query delays observed during the Discover investigation. Production endpoint
and native first-render instrumentation remain TASK-4036; mocked route timings
must not be described as measured iOS render times.

## Policy and compatibility

Use the same policy, actor and captured cycle for pre-fetch rotation selection and
final rail planning. Dynamic-only providers are started only for selected policy
slots; signed-out callers never run affinity. Every final plan is built from the
actual completed payloads, so missing/timed-out content cannot leave unresolved IDs.
No replacement rotation member is chosen if the selected one is empty (existing
selector behavior).

Static arrays must still be loaded even when their policy rail is disabled or
rotated out. Current iOS uses those arrays for category tabs (`HomeView`'s
`selectedPrimitive`/`legacySections` path). Older clients also render fixed arrays;
Android falls back to them for an empty resolved plan. Merely passing
`platform=ios` or `platform=android` does not authorize dropping those fields.
The hero also needs nearby-show data independently of the nearby rail's policy.
All existing fields, platform defaults, candidate limits, selection diversity,
provider safety filters and personalization remain intact. There is no new client
capability/version requirement in this change.

## Late work and refresh

A deadline stops waiting; **it does not cancel SQL**. Optional work is coalesced by
provider and every result-affecting input (including profile ID for personalized
providers). Up to 64 distinct optional loads run per server process, plus a separate
three-slot policy runner. At capacity, callers receive the usual empty fallback
without starting more optional work. Timeout keeps the running load's slot; a
permanently hung load holds it until settlement or process replacement. These
limits are per process, not a distributed database concurrency cap.

Each caller has its own deadline. Timed-out subscribers and timers are removed;
late success or rejection cannot mutate its response. Actual settlement consumes
rejections and frees capacity. No completed personalized results are cached here.
The local-club fallback does not start a global query once its originating request
budget has expired.

A response that used an optional runner fallback is `private, no-store`, allowing
refresh to reach the server instead of reusing a partial 60-second HTTP cache.
Complete responses retain the existing private 60-second cache. On a later
refresh, work still in flight can be joined and returned if it settles within that
new request's deadline. If it has settled, a fresh provider invocation runs and can
appear when it finishes within budget. Persistent slowness can keep a rail absent;
there is no background result cache or guarantee that the next refresh includes it.
A client-side persistent feed cache is separate work (TASK-4034).

## Controlled comparison

Route tests use a fixed fake clock, instant auth/location/policy unless stated,
and deferred provider promises. Time to usable response is the server-side proxy
for first content here; network and UI rendering are not simulated.

| Scenario | Previous all-provider wait | New route behavior |
| --- | --- | --- |
| Ready primary, stalled podcast providers, signed out | Waited for both podcast promises with no deadline | Not ready at 749 ms; usable primary response at 750 ms |
| Same scenario, signed in | Same unbounded wait | Same 750 ms bound; profile ID still forwarded |
| No local inventory, ready podcasts | Returned when all providers completed | Immediate ready podcast rail with coherent empty primary arrays |
| Primary queries reject, ready podcasts | Per-section failures isolated | Same successful optional-content fallback |
| Slow primary | Waited for primary | Still pending at 1,000 ms; returns when primary settles |
| Stalled policy, ready content | Unbounded policy wait | Default platform policy at 150 ms |
| Same-profile refresh during late work | New duplicate provider invocation | Joins the existing work; different profiles remain isolated |

The previous column describes the removed Promise.all behavior, not a production
latency sample. Regression checks also cover disabled/rotated dynamic providers,
legacy static data, resolvable plan IDs, late resolve/reject, refresh recovery and
partial-response caching. The runner tests separately exercise capacity after
timeout, repeated subscriber cleanup, synchronous throws and timer cleanup.

Run from apps/web:

```sh
node_modules/.bin/vitest run app/api/v1/home/feed/route.test.ts lib/discovery/railSelector.test.ts lib/discovery/optionalProviders.test.ts
npm run type-check
```
