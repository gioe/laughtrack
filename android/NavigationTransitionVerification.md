# Android navigation transitions — TASK-3993

## Policy

Each NavHost entry owns its background, Scaffold, bars, mini-player and content
insets. The outgoing screen and a predictive-back preview retain their original
geometry, even when the destination has different chrome. The former outer
Scaffold resized both screens as soon as navigation changed.

| Navigation | Motion |
| --- | --- |
| Discover / Search / Library | 140 ms crossfade; no directional push |
| Detail, Profile, Notifications, onboarding | 260 ms fade and restrained horizontal travel (12% incoming, 4% outgoing); reversed on back and mirrored in RTL |
| Expanded player | 260 ms vertical expansion/collapse with the underlying destination fading |
| Sign-in sheet | Material sheet gesture, back and hide animation; opens fully; scrolls when larger text needs more room |

NavHost still owns back progress, cancellation and interruption. No custom back
handler or duration-scale override was introduced. Android predictive callbacks
are explicitly enabled in the application manifest. Tab navigation retains
saveState, restoreState and launchSingleTop; destination deduplication is unchanged.

The player has an accessible Collapse player button outside its scrolling content
and respects system safe areas. The sign-in sheet's Not now action awaits its
native hide animation before removing the sheet. Its provider buttons can grow
with text size.

## Verification

Device: Android API 35 emulator, 390 × 844 logical viewport at density 160,
gesture navigation. Tests use a deterministic local interceptor for an empty Home
feed and offline detail responses, plus seeded paused playback. No production
account, network-dependent media playback or physical-device performance is claimed.

Reproduction commands from the repository root (JDK 17 and Android SDK required):

```sh
android/gradlew -p android :app:testDebugUnitTest \
  --tests app.laughtrack.android.AppShellTabsTest \
  --tests app.laughtrack.android.AppShellChromeTest
android/gradlew -p android :app:connectedDebugAndroidTest \
  -Pandroid.testInstrumentationRunnerArguments.class=app.laughtrack.android.AppShellTransitionTest,app.laughtrack.android.AppShellTest
```

AppShellTransitionTest checks rendered content bounds during tab/detail motion,
immediate selected-tab semantics, rapid repeated switching, restoration of a
nonzero Discover scroll position, native back start/progress/cancel/commit,
player expansion/collapse and sign-in dismissal. The predictive test calls the
activity's native OnBackPressedDispatcher and checks that the previous screen is
actually composed during the preview; it does not replace the back implementation.

System animation scale zero intentionally removes intermediate frames; settled
navigation and state restoration still must pass. Screenshot assertions query
Material's tab label because its icon description is cleared from merged semantics.

Physical release-build frame pacing and hardware gesture review remain part of
TASK-3995. Emulator recordings demonstrate geometry and behavior, not release latency.

## Results — September 13, 2026

- Full Android JVM gate: 436 tests, zero failures/errors.
- Existing AppShellTest: six scenarios passed.
- AppShellTransitionTest: all three scenarios passed at animation scales 1/1/1,
  at 0/0/0, and at 1/1/1 with font scale 1.5.
- Player/sheet scenario passed again after improving capture synchronization.
- App and profile ktlint checks and debug app/test APK builds passed.

Local artifacts in the primary checkout's `apps/screenshot-comparisons/`:

- `task-3993-verified.mp4`: normal-scale transition run; app scenarios begin around
  30 seconds. The clock is deliberately held at intermediate frames for geometry
  assertions. White activity-launch frames between test cases belong to the test
  host, not a transition between app destinations.
- `task-3993-zero.mp4` and `task-3993-large.mp4`: disabled-animation and large-text runs.
- `task-3993-dialog.mp4` and `task-3993-dialog-sheet.png`: focused native sheet
  recording and settled screenshot. Dialog captures explicitly advance the Compose
  clock through the entrance, because semantics can exist before the sheet renders.
- `task-3993-verified/`, `task-3993-zero/`, `task-3993-large/`: named case screenshots.
- `task-3993-video-contact.png`: normal-run overview sampled once per second.

Visual review confirms that the player collapse control clears the status bar,
large titles wrap, and standard-size sign-in actions are visible on first opening.
Bounds assertions confirm stable outgoing and predictive-return screen geometry.
The initial rapid-tab failure was a test matcher querying an icon description
cleared by Material semantics; the label-based assertion passes with the standard
navigation state observer. It was not proof of a production tab-selection defect.

The emulator's original animation and font settings were restored after testing.
