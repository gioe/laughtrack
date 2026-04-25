.PHONY: check-pbxproj

## Verify every Swift file under Sources/ is wired into LaughTrack.xcodeproj/project.pbxproj.
## Run before pushing to catch the "added a .swift file but forgot to run xcodegen" footgun
## that broke main in TASK-1764. CI runs the same check via .github/workflows/ios-pbxproj-sync.yml.
check-pbxproj:
	@bin/check-pbxproj-sync.sh
