# Discover latency telemetry — TASK-4036

## What is measured

The feed route emits a bounded `Server-Timing` header on responses and one
`discover_feed_performance` structured log through the existing Vercel request
context / `waitUntil` path. Local development has the header but deliberately
skips detached logging when that context is absent, matching request-counter
behavior. Existing request counters remain intact. Report scheduling, synchronous
sink exceptions and rejected/stalled reporter promises never fail or get awaited
by the response. No new database writes or vendor SDKs are introduced.

`feed_total` starts on entry to the feed handler and ends after the response body
is constructed. It includes rate limiting, auth, policy/hero lookup, provider
waiting and serialization. It excludes platform ingress/queuing and transfer to
the client. Provider duration starts at that request's invocation and ends at its
observed settlement/fallback. Coalesced calls measure each caller's wait, not the
underlying query's complete execution time. Optional timeouts measure the portion
of the shared deadline remaining when that provider was invoked; they need not
all equal 750 ms. Late completion cannot rewrite an already-reported outcome.

Fixed providers: `auth`, `policy`, `hero`, `trending_comedians`, `clubs`,
`comedians_near_you`, `shows_tonight`, `shows_near_zip`, `trending_this_week`,
`podcast_episodes`, `trending_podcasts`, `followed_shows`, `touring`, `fresh`,
`affinity`. Outcomes are `success`, `error`, `timeout`, `skipped`. A successful
empty result is success. Policy errors are observed before fallback; providers
omitted by policy/account/location are skipped. Capacity refusal is also skipped.
Unstarted work on validation/auth failure remains skipped. There are at most 15
provider observations and one total per response; durations clamp to 0–120000 ms.

Do not add concurrent provider durations to estimate total latency. Provider
errors/timeouts remain isolated by existing fallbacks. Primary failures retain
their original fallback; optional failures are now consistently marked incomplete
and get private/no-store caching, like other optional budget failures.

## iOS first useful content and same-response correlation

`discover_first_content` starts at an actual Discover refresh, before cache lookup,
and ends when the first nonempty planned rail's SwiftUI `.task` runs after mounting.
This is a useful-content mount proxy, **not** a display compositor/pixel fence,
image-download completion, app-process launch, or spinner/view-creation timing.
One generation produces at most one event; rerenders and additional rail mounts
are ignored. Cancellation/context replacement cannot report an obsolete attempt.
Empty/error/spinner-only states produce no first-content event. Legacy compatibility
fallback and separate category screens are outside this planned Discover metric.
The current server emits a rail plan for successful feeds.

The source is `persisted_cache`, `in_memory`, or `network`, determined from the
content actually installed before the mount callback. `account` is only
`anonymous` or `authenticated`. Cache-first events have no unrelated server timing.
`first_content_ms` and `client_load_ms` use monotonic process uptime. The latter
covers the shared client feed-load operation, including retries, response transfer,
decoding and cache write; it is not pure network time.

A request-local capture middleware reads only allowlisted `Server-Timing` values
from the final `getHomeFeed` response. The coalescer carries these values with its
result to every waiter. For network-first content they become numeric
`server_feed_total_ms` and `server_<provider>_ms` fields in **the same first-content
event**. This establishes causal response correlation without shared clocks,
unique request IDs, user IDs or high-cardinality join keys. Server outcome labels
remain in the server log/header; missing timings stay missing, never fabricated.
An HTTP cache may replay response timing; `network` means the API load path, not
proof of a new origin execution. Do not interpret header timing as origin work
performed during the current launch without checking response-cache behavior.

The iOS event uses OSLog subsystem `com.laughtrack.performance`, category `discover`.
It bypasses Firebase/AnalyticsManager because the existing Firebase fanout has a
global signed-in user ID. Temporarily clearing that identity would race unrelated
events. Read device/simulator logs through Console or:

```sh
xcrun simctl spawn booted log show --last 10m --info --style compact \
  --predicate 'subsystem == "com.laughtrack.performance" AND category == "discover"'
```

For backend logs, filter the existing deployment runtime log stream for
`[discover-performance]` and parse the following JSON. OSLog is local device
telemetry; this task does not install an identity-free remote iOS collection
service. Do not claim a fleet-wide iOS percentile from local log captures.

## Privacy and cardinality

New payloads contain only fixed event/schema/provider names, outcome/status-class
labels, categorical platform/account/source, and bounded numeric milliseconds.
They never copy URLs/query strings, ZIPs, distance, user/session/impression IDs,
tokens, error objects, entity IDs or response bodies. Server context values are
selected internally from closed unions. iOS header parsing allowlists 16 names,
rejects malformed/nonfinite/negative/out-of-range numbers, and drops headers over
4096 bytes; its logger additionally filters the outgoing payload. At most 20 iOS
parameters are possible (3 categorical/first-content + client duration +16 server
values). Timings are numeric measurements, not dimensions or histogram labels.
Existing vendor/platform log envelopes and pre-existing unrelated logs are not
changed by this instrumentation.

## Initial baseline and budgets

`task-4036-api-baseline.json` records 22 anonymous requests made September 22,2026
through the local Next development server connected to the configured production
read-only data path:11 per dense/sparse market, platform iOS,25-mile radius.
Only category labels and timings were saved, not request ZIPs or payload contents.
The first request per market is identified separately;10 subsequent sequential
requests per market form the warmed development baseline. Development compilation,
Prisma query logging, local CPU load (including a simulator build), and remote DB
network distance all affect these observations. They are not production latency
percentiles or controlled serverless cold-start measurements.

| Warm local baseline (10 samples each) | Dense | Sparse |
| --- | ---: | ---: |
| Feed total median |1496.05 ms|772.3 ms|
| Feed total observed range |1134.2–3109.1 ms|702.7–1502.7 ms|
| Client HTTP wall median |1651 ms|799.25 ms|
| Trending comedians median |1150.9 ms|483.1 ms|
| Shows tonight median |1267.2 ms|442.2 ms|
| Nearby shows median |1173.4 ms|632.4 ms|
| Trending week median |1223.8 ms|314.1 ms|

Dense first-request HTTP time was 13562.4 ms and feed total 6224.9 ms; the difference
includes development compilation/platform work outside the measured handler.
Sparse first-request feed total was 1086.7 ms. No p95 is inferred from these small,
nonrepresentative samples.

The new statuses exposed 19 policy errors and one policy timeout among 20 warm
requests, all safely using defaults. This merits investigation of stored policy
loading/validation; these measurements do not establish the root cause. Dense
optional providers also timed out frequently (touring 8/10, podcast episodes 8/10,
nearby comedians 9/10), while all primary providers succeeded. The actionable next
performance focus is primary query cost and optional completion rates, not summing
all provider spans or treating missing optional content as cheap success.

Initial operational budgets, to validate against representative production data:

| Metric | Budget / action |
| --- | --- |
| In-memory first useful content |100 ms target; inspect main-thread work above 250 ms|
| Persisted-cache first useful content |250 ms target; inspect disk decoding/mount work above 500 ms|
| Network first useful content |1500 ms target; investigate sustained cohorts above 2500 ms|
| Feed total |1000 ms target; investigate sustained cohorts above 1500 ms|
| Primary provider wait |500 ms target each; profile recurring contributors above 750 ms|
| Policy |Existing 150 ms cap; any persistent error rate above 1% warrants investigation|
| Optional work |Existing shared 750 ms cap; timeout rate above 5% warrants query/caching review|

These are targets, not assertions of current compliance. Before adopting percentile
alerts, gather at least 200 observations per stable source/account/platform cohort
across 24 hours, with at least 30 real-device cold launches and 30 warm/cache revisits
per supported device tier for release verification. Publish sample counts,
missing/empty/error/cancelled-load coverage and app/server revisions. Compute
percentiles only on that declared population; first-content events alone exclude
failed/empty loads, so pair them with request outcomes and explicit test runs.
Do not partition by ZIP/user or build a high-cardinality device/request dimension.
A new cold-process run must be labeled as such; the first sample of a loop is not
proof that storage/database/process caches were cold.

## Verification and correlated trace

The simulator fixture test exercises HTTP middleware -> measured/coalesced feed ->
model state -> explicit useful-content mount acknowledgement. Its captured JSON is
in `task-4036-ios-trace.json`. The server durations and 125 ms first-content clock in
that fixture are deliberately synthetic; client-load duration is measured in the
test process. This proves propagation and one-shot attribution, not performance,
and the numbers must not be subtracted as a real-device waterfall.

The existing cache lifecycle UI test also passed on iPhone 16 Pro / iOS 18.3.1.
Its exported app diagnostics contain five actual mounted-view events: network
437.5 ms, persisted cache 163.9 ms, persisted cache 147.0 ms, in-memory retry
38.2 ms, and a deliberately delayed first-install network load 1435.1 ms.
Those exact safe payloads are under `mounted_ui_fixture` in the same trace file.
The local fixture has no Server-Timing header; missing server values remain absent.
These five observations verify the mounted hook and all three source labels, not
a representative device baseline or percentile. The UI test includes pending and
failed refresh, scroll preservation, retry, and first-install loading.

Validation: 115 focused backend tests, TypeScript build, 45 focused simulator
tests, the lifecycle UI test, and Xcode project registration checks passed.
The full web suite still has three unrelated fixed-date saved-show failures
(TASK-3983); all three repeated on unchanged HEAD in three precheck runs, with no
upstream divergence.

Backend tests cover fixed-label outcomes, errors before fallback, timeout then late
settlement, concurrent callers, capacity skip, privacy and stalled/throwing/rejected
reporters. Simulator tests cover cache/network source, parser bounds, mount-time
emission, duplicate suppression and cancellation. Run:

```sh
cd apps/web
npx vitest run lib/metrics/withRequestMetrics.test.ts app/api/v1/home/feed/route.test.ts lib/discovery/optionalProviders.test.ts
# From repository root:
ios/bin/test-sim LaughTrackTests/HomeDiscoverRailPlanTests LaughTrackTests/HomeDiscoverRailAnalyticsTests LaughTrackTests/MainPageCacheTests
```

Rollback removes the feed performance wrapper/observers and iOS mount recorder.
The optional-runner callback is optional and the existing cache/coalescer APIs remain
available. No migration, external credential or API body/schema change is required.
