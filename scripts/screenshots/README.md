# Mobile screenshot tooling

Regenerate the complete cross-platform comparison matrix with one command:

```bash
scripts/screenshots/regenerate-comparisons
```

The command runs the capture-only iOS and Android Fastlane lanes sequentially,
persists validated manifests for all catalog scenarios and five device profiles,
generates five contact sheets, and opens them. It never uploads screenshots or
metadata to App Store Connect or Google Play.

Android capture is resumable by profile. If an emulator or instrumentation run
fails after a profile completes, rerun the same command with the same output
root. The lane reuses only profile directories whose canonical filenames and
PNG dimensions still validate, captures the remaining profiles, and retains the
resume cache until the final 51-image Android manifest and Play projection both
succeed. A changed Git revision, screenshot catalog, or profile configuration
invalidates the cache automatically.

By default, output is written to
`apps/screenshot-comparisons/YYYY-MM-DD-current-catalog/`. Use `--output-root`
to select another directory or `--no-open` for a headless run.

The command requires a booted iOS simulator, an authorized Android emulator or
device, Homebrew Ruby, Python 3, and ImageMagick.

iOS build-settings discovery uses a 30-second timeout by default. Override it
for slower environments by prefixing the command, for example:

```bash
FASTLANE_XCODEBUILD_SETTINGS_TIMEOUT=60 scripts/screenshots/regenerate-comparisons
```
