# Mobile screenshot tooling

Regenerate the complete cross-platform comparison matrix with one command:

```bash
scripts/screenshots/regenerate-comparisons
```

The command runs the capture-only iOS and Android Fastlane lanes sequentially,
persists validated manifests for all catalog scenarios and five device profiles,
generates 17 labeled cross-platform scenario sheets, writes delta-aware audit
metadata, and opens them. It never uploads screenshots or
metadata to App Store Connect or Google Play.

Each native lane starts the hermetic backend in `fixture_server.py` and points
its app at that local server for the duration of the capture. The fixture pins
result counts, featured entities, dates, narrative content, and generated
artwork across both platforms. Its declared contract lives in
`screenshots/catalog.json`, and every completed run manifest records the
contract fingerprint so fixture drift is rejected during collection/export.

For focused local verification, use the separate `verify_screenshots` lane with
non-empty, comma-separated canonical profile and scenario selections:

```bash
ios/bin/lane verify_screenshots \
  profiles:ios_phone,ios_large_tablet \
  scenarios:02_SearchShows,03_SearchComedians,04_SearchClubs,08_SearchPodcasts \
  run_root:/tmp/laughtrack-ios-search-verification

android/bin/lane verify_screenshots \
  profiles:android_phone \
  scenarios:02_SearchShows,03_SearchComedians,04_SearchClubs,08_SearchPodcasts \
  run_root:/tmp/laughtrack-android-search-verification
```

Selections must be unique subsequences in catalog order. Targeted runs use the
same fixture backend and canonical filenames, write manifests with
`mode: verification`, bypass the complete-profile cache, and never export or
upload storefront assets. The native flow stops immediately after its final
selected scenario. The existing `screenshots`, `screenshots_and_upload`, and
`regenerate-comparisons` commands remain complete-matrix consumers and reject
verification manifests.

Both native lanes persist successful captures in a content-addressed cache by
profile. An unchanged run materializes every validated profile without building
or launching native tests. Cache keys hash the current contents of each
platform's render-affecting app and UI-test sources, the shared catalog and
fixture server, that profile's adapter configuration, and a normalized native
environment identity. The iOS identity records the active Xcode version/build
and the selected simulator runtime identifier/version/build. The Android
identity records the JDK version/vendor/VM/architecture, installed Build Tools
package/revision, and selected AVD system-image package/revision/API/tag/ABI.
Host-specific paths, simulator UDIDs, emulator serials, device state, and other
volatile metadata are deliberately excluded. Relevant tracked, untracked,
modified, or deleted files—or changes to that platform's native identity—
invalidate only the affected platform. Documentation, storefront projections,
and changes to the other platform do not. Cached entries are reused only when
their native identity, canonical filenames, dimensions, and recorded SHA-256
image hashes still validate.

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

The command requires an installed iOS simulator runtime, a local Android AVD,
Homebrew Ruby, Python 3, and ImageMagick. Each lane boots its selected native
target only when one or more profiles miss the cache.

iOS build-settings discovery uses a 30-second timeout by default. Override it
for slower environments by prefixing the command, for example:

```bash
FASTLANE_XCODEBUILD_SETTINGS_TIMEOUT=60 scripts/screenshots/regenerate-comparisons
```
