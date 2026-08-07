# Tusk Configuration

`test_command_timeout_sec` is set to 600 seconds because the iOS domain gate
builds the `LaughTrack` test bundle for iOS Simulator, and cold Xcode builds in
task worktrees can exceed the old 240 second limit before completing
compilation.

The iOS gate uses `xcodebuild build-for-testing` instead of
`swift build --build-tests` because the test bundle includes UIKit coverage,
which must compile against an iOS SDK rather than SwiftPM's default macOS
destination.

Before building, both the iOS domain gate and the `ios/**` path gate run
`ios/bin/check-pbxproj-sync.sh`. This fails fast when a Swift source or test
file is missing from `LaughTrack.xcodeproj/project.pbxproj`, rather than
allowing an unregistered test file to be silently omitted from verification.

The timeout remains finite so `tusk commit` still fails genuinely hung test
commands instead of waiting indefinitely.
