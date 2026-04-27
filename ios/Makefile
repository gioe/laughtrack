.PHONY: check-pbxproj check-ios-libs-pin

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
