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

- Real-process Fastlane lifecycle suite: **13 passed**. Covers both lanes, success and test failure, previous environment present/absent, child reaping, occupied-port refusal, startup exit, invalid HTTP contract, and watcher workflow wiring.
- iPhone 16 Pro, iOS 18.3.1: ran all 16 `NavigationTransitionUITests`, the screenshot Discover-header navigation case, and the held-refresh Discover case under the actual updated Fastfile fixture wrapper. **16 passed, 1 skipped, 1 failed** overall. Navigation alone: 14 passed, intentional iPad-only skip, and the pre-existing scroll-retention failure at `NavigationTransitionUITests.swift:478`. The latter also appears in the baseline iOS 18 CI log; no fixture configure failures occurred.
- Held-refresh initially passed in 74.115 seconds, but its independent rerun exposed a missed pull-to-refresh gesture (no new feed request). The test now identifies the outer Discover scroll view explicitly and drags from the leading gutter outside interactive rail content. The corrected standalone simulator run passed. The server remains independent of the screenshot fixture backend.
- The failing scroll-retention capture visibly shows the expected card, but XCTest reports its queried element as not hittable. This is an independent UI-test issue, not evidence of unavailable fixture data. No production UI code was changed to mask it.
- Native test failure propagated out of the fixture wrapper; its `ensure` cleanup logged that the owned process stopped. Lifecycle regression tests additionally prove that the socket closes and the child is reaped.
- Ruby syntax and workflow YAML validation passed.

The fixture criterion now uses the self-contained lifecycle suite above. Its former bare `test-sim NavigationTransitionUITests` command did not provision its required server. The full native run remains part of this record; it is **not** claimed to be fully green.

Local evidence: `/tmp/task4012-native.log`, `/tmp/task4012-native-all/` (xcresult attachments), and `/tmp/task4012-fixture-commit.log`. Native xcresult: `LaughTrack-wt-d8e748b09d4f/Logs/Test/Test-LaughTrack-2026.09.16_14-58-26--0400.xcresult` under Xcode DerivedData.

No production application behavior changes are part of this task.

The broad commit gate failed in three existing web saved-show tests. Tusk HEAD precheck reproduced those failures on all three runs (not flaky, not diverged); the documented pre-existing-failure commit fallback was used for the CI-only changes. See `/tmp/task4012-precheck.log`.
