# iOS navigation transition verification — TASK-3994

## Motion and state policy

Native TabView, NavigationStack and sheet presentation own selection, push/pop,
interactive reversal and dismissal. No custom animator or replacement back gesture
is introduced. A root-owned bridge restores admission to UIKit’s existing
interactive pop recognizer while the custom detail chrome hides the navigation
bar; it preserves the original touch/arbitration callbacks and guards root depth,
active transitions and presented controllers. Its delegate is restored on teardown.

Discover keeps a stable section tree independent of Search’s pivot, and the native
ScrollView owns its precise offset. Returning no longer queues a section-top jump.
The persistent mini-player remains attached to the outer navigation stack. A
contained hosting controller reserves stable space; its player view follows the
native transition coordinator between root tab clearance and detail clearance,
including interactive cancellation. Nonanimated navigation synchronizes from
completed UIKit appearance callbacks. Only app dependencies cross the hosting
boundary; size classes and accessibility traits remain native to presentation.

A mini-player drag uses gesture-scoped state so cancellation resets its position.
Completed dismissal updates playback immediately, without a delayed task that
could later dismiss a replacement episode. Reduce Motion disables its animated
settling. Native navigation and sheets continue to respect the system setting.

Expanded playback keeps Close outside scrolling content. Accessibility text uses
smaller artwork, a complete episode title and vertically stacked controls. The
account drawer keeps its header/Close visible while actions scroll. The sign-in
sheet initially opens at the large detent and scrolls, retaining native interactive
dismissal and a reachable Close button. Detail navigation hit regions are 44 points.

## Reproduce

From the task checkout, start the existing local fixture backend:

```sh
python3 scripts/screenshots/fixture_server.py --host 127.0.0.1 --port 8765
```

In another terminal, run:

```sh
ios/bin/test-sim LaughTrackUITests/NavigationTransitionUITests
ios/bin/test-sim LaughTrackTests/AppShellViewTests LaughTrackTests/ContentViewNavigationTests LaughTrackTests/DetailNavigationChromeTests LaughTrackTests/HomeContentSectionTests
```

For the additional regular-width player check, use a test-only universal build
(the shipping target intentionally remains iPhone-only):

```sh
xcodebuild -project ios/LaughTrack.xcodeproj -scheme LaughTrack \
  -destination 'platform=iOS Simulator,name=iPad Pro 13-inch (M4),OS=18.3.1' \
  CODE_SIGNING_ALLOWED=NO TARGETED_DEVICE_FAMILY=1,2 test \
  -only-testing:LaughTrackUITests/NavigationTransitionUITests/testTabletPlayerKeepsControlsAndCloseReachable
```

The UI suite uses the real app with deterministic local data and a seeded
non-streaming episode. It does not force the screenshot-only full-screen player
on phones. It checks exact Discover offset after tab changes/Search pivots and
native back, player/auth dismissal, background resume, cancelled/completed
mini-player drags, large text and native Reduce Motion. The Reduce Motion case
changes the real Settings toggle and restores its original value. Large text uses
iOS’s preferred-content-size launch argument, not fixed custom fonts.

## Evidence

Initial iPhone 16 Pro / iOS 18.3.1 verification exposed two failures: the account
drawer sign-in action was outside the viewport at accessibility XXXL, and a
completed native edge gesture could not pop a detail with the navigation bar
hidden. The normal and native Reduce Motion player/modal/resume cases passed.
Initial attachments and recording are under apps/screenshot-comparisons/
task-3994-initial and task-3994-transitions.mov in the primary checkout.

The iPhone transition rerun passed all four phone cases (the iPad-only case was
skipped) in Test-LaughTrack-2026.09.13_21-02-38--0400.xcresult. The recording
task-3994-coordinated2.mov covers tab returns, detail push, cancelled back and
completed back with the persistent player. Sampled frames were visually reviewed.

The ordinary iPad run correctly used compact layout: this project intentionally
ships TARGETED_DEVICE_FAMILY=1, so it runs in iPhone compatibility mode on iPad.
The original regular-layout assertion was therefore invalid for that build.
Regular-width coverage uses a test-only TARGETED_DEVICE_FAMILY=1,2 xcodebuild
override; no shipping configuration changes. During investigation, the host was
narrowed to forwarding app dependencies and the navigation coordinator instead
of copying the entire SwiftUI environment. The layout failure itself was not
caused by environment forwarding.

Final phone verification passed all four cases in
Test-LaughTrack-2026.09.14_07-33-39--0400.xcresult; the iPad-only case was skipped.
Attachments are in apps/screenshot-comparisons/task-3994-phone-passed. Normal
player, scrolled accessibility controls and returned Discover screenshots were
visually inspected. The phone build includes the final dependency forwarding and
podcast ID 401 seed; subsequent app changes only center the regular-width layout.

The final universal iPad check passed in
Test-LaughTrack-2026.09.14_07-57-53--0400.xcresult. The regular artwork/control row
centers in the available viewport while retaining overflow scrolling and fixed
Close. The centered rendering was visually inspected. On this simulator a
synthetic Home press sometimes left XCTest reporting foreground even while its
recording showed SpringBoard. The iPad test explicitly switches to Settings and
asserts a running or suspended background state before resuming Discover. It
does not accept app termination as successful backgrounding.

The focused simulator suites passed 78 tests: AppShellViewTests 20,
ContentViewNavigationTests 34, DetailNavigationChromeTests 4, and
HomeContentSectionTests 20. The XCTest wrapper also reports zero XCTest cases
for these Swift Testing suites; the Swift Testing totals are the relevant results.
The criterion was marked from this completed run without repeating it through
the criteria CLI. Log: /tmp/task3994-focused-final.log.

## Limits

These checks establish simulator behavior and visual continuity, not release-build
frame pacing or real audio playback. Physical iOS/Android release-build verification
is tracked separately by TASK-3995. Test-runner launch/termination gaps in a full
recording are not application navigation transitions.
