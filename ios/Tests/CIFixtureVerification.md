# iOS CI fixture verification — TASK-4012

## Baseline investigation

Inspected both simulator jobs in [run 35010580754](https://github.com/gioe/laughtrack/actions/runs/35010580754), plus their current Fastlane/workflow entrypoints.

| Job | Fixture lifecycle | Observed outcomes |
| --- | --- | --- |
| Pinned iOS 18, job 104523327758 | Fastlane `test` starts the fixture server and cleans it up in `ensure`. Its original readiness check only opened a TCP socket. | No missing-configure errors. Held-refresh Discover test passed (74.655s). Failures concerned reaching the This Week show, first podcast result, authentication cancellation, and a show at a retained scroll position. |
| iOS 26 watcher, job 104523327607 | Workflow directly called `fastlane scan`, bypassing fixture ownership. The named watcher lane also omitted the fixture wrapper. | All four screenshot tests and navigation launch helpers failed at `127.0.0.1:8765/fixture/configure`. Held-refresh Discover test passed (82.150s). Separate failures concerned native Settings Reduce Motion assertions and exact floating-point equality in `TabBarBottomSpacingTests` (TASK-4013). |

The held-refresh test owns an independent ephemeral `HeldLaunchServer`; missing screenshot fixtures do not explain that scenario. Its criterion names a valid XCTest method, despite the brief's path-based stale-spec warning.

Both screenshot and navigation tests explicitly supply a loopback API URL. Navigation setup throws before app launch if fixture configuration fails. Screenshot setup records a failure and still sets the loopback URL; neither path falls through to production.

## Required lifecycle

Both simulator jobs must enter a Fastlane lane that owns the fixture process, verifies the curated HTTP configure response, runs tests serially because fixture mode is shared, and reaps its process on success or failure. Occupied ports must fail before test execution rather than borrowing an unknown backend. Preserve the caller's fixture-port environment.

No fixture-dependent test is intentionally skipped for missing infrastructure: startup fails the lane. The existing tablet player test explicitly skips on iPhone because it requires the iPad idiom. The iOS 26 watcher remains non-blocking for independent platform regressions; fixture failures remain visible.

CI retains the fixture-server log as an artifact even after test failure. Fastlane logs identify HTTP readiness and cleanup. The lifecycle regression job exercises both lane entrypoints using real local fixture processes without starting Xcode.

## Current verification

Native simulator and lifecycle regression outcomes will be recorded after execution. No production application behavior changes are part of this task.
