# Mobile screenshot tooling

Regenerate the complete cross-platform comparison matrix with one command:

```bash
scripts/screenshots/regenerate-comparisons
```

The command runs the capture-only iOS and Android Fastlane lanes sequentially,
persists validated manifests for all catalog scenarios and five device profiles,
generates five contact sheets, and opens them. It never uploads screenshots or
metadata to App Store Connect or Google Play.

By default, output is written to
`apps/screenshot-comparisons/YYYY-MM-DD-current-catalog/`. Use `--output-root`
to select another directory or `--no-open` for a headless run.

The command requires a booted iOS simulator, an authorized Android emulator or
device, Homebrew Ruby, Python 3, and ImageMagick.
