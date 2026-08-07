.PHONY: check-pbxproj check-ios-libs-pin check-bundle-version test-test-sim-destination test-test-sim-runner test-test-sim

## Verify every Swift file under Sources/ is wired into LaughTrack.xcodeproj/project.pbxproj.
## Run before pushing to catch the "added a .swift file but forgot to run xcodegen" footgun
## that broke main in TASK-1764. CI runs the same check via .github/workflows/ios-pbxproj-sync.yml.
check-pbxproj:
	@bin/check-pbxproj-sync.sh

## Verify the ios-libs revision in project.yml matches both Package.resolved files.
## Catches the drift that broke main in TASK-1807 → TASK-1819, where project.yml stayed on
## an old commit while both Package.resolved files moved forward and xcodebuild silently
## resolved a different revision than `swift build`. CI runs the same check via
## .github/workflows/ios-libs-pin-sync.yml.
check-ios-libs-pin:
	@bin/check-ios-libs-pin.sh

## Verify ios/project.yml's CURRENT_PROJECT_VERSION (the LaughTrack app target's build number)
## has not decreased relative to the base ref (defaults to origin/main). Catches the
## regression class from TASK-1902 — TestFlight rejects uploads whose CFBundleVersion is not
## strictly greater than the last accepted build, so a silent decrease breaks releases.
## CI runs the same check via .github/workflows/ios-bundle-version.yml.
check-bundle-version:
	@bin/check-bundle-version.sh

## Verify deterministic iOS simulator destination selection without requiring Xcode runtimes.
test-test-sim-destination:
	@PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s bin/tests -p 'test_test_sim_destination.py' -v

## Verify focused-run output handling without requiring Xcode or a simulator.
test-test-sim-runner:
	@PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s bin/tests -p 'test_test_sim.py' -v

test-test-sim: test-test-sim-destination test-test-sim-runner
