# Mobile screenshot tooling

Regenerate the complete cross-platform comparison matrix with one command:

```bash
scripts/screenshots/regenerate-comparisons
```

The command runs the capture-only iOS and Android Fastlane lanes sequentially,
persists validated manifests for all catalog scenarios and five device profiles,
generates five contact sheets, and opens them. It never uploads screenshots or
metadata to App Store Connect or Google Play.

Each native lane starts the hermetic backend in `fixture_server.py` and points
its app at that local server for the duration of the capture. The fixture pins
result counts, featured entities, dates, narrative content, and generated
artwork across both platforms. Its declared contract lives in
`screenshots/catalog.json`, and every completed run manifest records the
contract fingerprint so fixture drift is rejected during collection/export.

Both native lanes persist successful captures in a content-addressed cache by
profile. An unchanged run materializes every validated profile without building
or launching native tests. Cache keys hash the current contents of each
platform's render-affecting app and UI-test sources, the shared catalog and
fixture server, and that profile's adapter configuration. Relevant tracked,
untracked, modified, or deleted files invalidate the affected platform while
documentation, storefront projections, and changes to the other platform do
not. Cached entries are reused only when their canonical filenames, dimensions,
and recorded SHA-256 image hashes still validate.

Run `scripts/screenshots/regenerate-comparisons --force-fresh` to bypass every
profile cache for one run. Set `LAUGHTRACK_SCREENSHOT_CACHE_PATH` to relocate the
cache; by default it lives under the gitignored
`apps/screenshot-comparisons/.profile-cache/` directory.

Completed-run manifests keep physical capture provenance separate from the
current run's materialization time. Cached images therefore retain their
original capture timestamp and revision instead of appearing newly captured.

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
