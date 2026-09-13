# Launch Reduce Motion verification — TASK-3992

Verified 2026-09-13 on iPhone 16 Pro, iOS 18.3.1 Simulator.

## Behavior and boundary

ContentView reads the live system Reduce Motion preference and uses identity
transitions with no surface animation when enabled. Both shared-logo endpoints
disable matched geometry. First-entry elements appear immediately. The loading
artwork switches to a separate static branch, canceling an already-running bloom
and pausing its decorative timelines. With the preference off, the existing
0.42-second surface transition, 0.985 first-entry scale, matched logo, staggered
entrances, spotlight and marquee animation remain intact.

This policy is scoped to launch and authentication surfaces. It does not disable
animations across the entire app shell or control system-owned authentication UI.

## Repeatable checks

From the repository root:

```sh
ios/bin/test-sim LaughTrackTests/ContentViewNavigationTests
ios/bin/test-sim LaughTrackUITests/LaunchReadinessUITests
```

- All 34 ContentViewNavigationTests passed, including actual hosted artwork
  snapshots taken while enabling Reduce Motion during the delayed entrance.
  Static samples remain stable across the original bloom deadline; disabling the
  preference resumes visible animation, and re-enabling returns to the same image.
  A nonblank-image assertion prevents empty captures from passing.
- The three existing native launch tests passed: withheld home feed, first-entry
  guest handoff, and failed-feed retry. Search remains usable during loading.
- The new native test passed twice with the final code. It changes the real iOS
  Settings preference, launches into first entry, starts and cancels sign-in,
  enters the guest home shell with its feed withheld, opens Search, then toggles
  Reduce Motion off and on while the app remains alive. Search remains selected
  and the launch loading screen does not return. The original preference is restored.
- The full iOS build-for-testing commit gate passed.

The hosted test supplies the artwork preference directly; it does not claim to
simulate the read-only SwiftUI accessibility environment. The native test covers
real preference propagation and parent routing. Together these checks cover the
parent boundary, child artwork, cancellation, and live changes.

## Recording and visual review

Local artifacts are under `apps/screenshot-comparisons/task-3992/` in the primary
checkout; generated media is not committed:

- `native-verified.mp4`: complete passing native flow, including Settings.
  Relevant app sequence is approximately 188–208 seconds.
- `native-contact.png`: overview sampled every two seconds.
- `native-detail-contact.png`: sign-in, cancellation and guest handoff sampled at
  100 ms intervals, from 194–204 seconds.
- `native-final/manifest.json`: six named native screenshots from the first
  successful run.
- `hosted-after/`: six rendered artwork captures from the passing unit test.

Visual inspection confirms static branded artwork and direct surface changes,
without intermediate logo travel or scaling during sign-in, cancellation and
guest entry. The destination home skeleton has its own shimmer; that ongoing
content-loading animation is outside this launch-transition change. The system
sign-in consent alert also owns its presentation animation.

The normal-motion artwork is nonblank and visibly resumes animation in the hosted
captures; its production timing and styling are retained. No successful signed-in
account or physical-device verification is claimed. Physical-device release
verification remains tracked separately in TASK-3995.

Successful native result bundles (under the worktree DerivedData Logs/Test):

- `Test-LaughTrack-2026.09.13_15-21-24--0400.xcresult`
- `Test-LaughTrack-2026.09.13_15-27-04--0400.xcresult` (recorded run)

Earlier failed runs exposed test-harness issues (read-only environment injection,
wrong snapshot window and system-alert ownership). They are not evidence of a
production regression or a valid before/after comparison.
