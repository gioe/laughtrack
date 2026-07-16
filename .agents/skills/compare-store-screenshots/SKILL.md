---
name: compare-store-screenshots
description: Regenerate the complete iOS and Android screenshot matrices, validate fresh run manifests, compare selected phone and tablet profiles side by side, and report qualitative product-polish differences. Use when asked to run, audit, review, compare, or assess the mobile store screenshots across iOS and Android.
---

# Compare Store Screenshots

Capture both native store-listing sets and evaluate the resulting images pair by pair. Treat this as a local capture and read-only product audit: never upload screenshots or invoke release lanes.

## 1. Confirm the environment

Run from the repository root. Confirm these prerequisites before starting:

```bash
test -x ios/bin/lane
test -f android/Gemfile
xcrun simctl list devices booted
adb devices
```

Require at least one booted iOS simulator and one authorized Android emulator/device. If either is missing, stop and tell the user exactly what must be started. Do not analyze an existing set as though it were newly generated.

Create persistent run directories and record an RFC 3339 freshness boundary immediately before capture:

```bash
SCREENSHOT_RUN_ROOT=$(mktemp -d "${TMPDIR:-/tmp}/laughtrack-screenshot-compare.XXXXXX")
IOS_RUN_ROOT="$SCREENSHOT_RUN_ROOT/ios"
ANDROID_RUN_ROOT="$SCREENSHOT_RUN_ROOT/android"
CAPTURE_STARTED_AT=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
```

Keep this directory until the audit is complete. Each lane writes a normalized
`manifest.json` and its declared images below the corresponding run root.

## 2. Run both capture lanes

Run the capture-only lanes sequentially so two UI-test workloads do not compete for host resources:

```bash
ios/bin/lane screenshots run_root:"$IOS_RUN_ROOT"
(cd android && bundle exec fastlane screenshots run_root:"$ANDROID_RUN_ROOT")
```

Do not run `screenshots_and_upload`, `upload_screenshots`, `upload_metadata`, `release`, or any other upload/release lane. If either capture lane fails, report its failure and stop before qualitative analysis.

These are capture-only lanes. The explicit `run_root` options preserve the
validated raw runs for comparison; they do not change the normal storefront
projections or upload anything. The expected manifests are:

- iOS: `$IOS_RUN_ROOT/manifest.json`
- Android: `$ANDROID_RUN_ROOT/manifest.json`

## 3. Validate the capture set

Run the bundled validator with both manifests and the recorded freshness boundary.
Choose the comparison view that fits the audit:

- `phone` — iOS phone adjacent to Android phone;
- `tablet` — iPad adjacent to Android 10-inch, followed by Android 7-inch;
- `all` — phone pair, large-tablet pair, then Android 7-inch.

```bash
python3 .agents/skills/compare-store-screenshots/scripts/validate_pairs.py \
  --ios-manifest "$IOS_RUN_ROOT/manifest.json" \
  --android-manifest "$ANDROID_RUN_ROOT/manifest.json" \
  --fresh-since "$CAPTURE_STARTED_AT" \
  --view phone \
  > "$SCREENSHOT_RUN_ROOT/comparison.json"
```

Use `--view tablet` or `--view all` for the other profile sets. Add a canonical
scenario such as `--scenario 05_ClubDetail` to emit only that scenario across
the selected profiles.

Require the manifests to contain exactly one fresh, declared, readable image
for every selected platform profile and every scenario in
`screenshots/catalog.json`. This includes guest, authenticated-persona,
protected-action auth-prompt, and first-entry auth-choice states; do not treat
those authentication surfaces as interchangeable.

Stop on missing, duplicate, stale, unreadable, or unexpected captures, mismatched
Git revisions, or undeclared image files in either run. Do not silently select
among duplicates.

## 4. Inspect every pair

Read `comparison.json` in group order. Open every listed image at high or
original detail, keeping each group's images adjacent in the emitted order. Do
not infer visual quality from source code, filenames, or manifest metadata.

For each pair, assess:

- narrative parity: whether both screenshots communicate the same product capability;
- content curation: recognizable and appealing entities, plausible dates/prices, useful populated states;
- asset completeness: portraits, club logos, podcast art, hero art, and intentional fallbacks;
- information hierarchy: focal point, scan order, typography, spacing, density, and truncation;
- brand expression: color, motifs, component consistency, and platform-appropriate polish;
- capture quality: status bar, clipping, loading/skeleton states, empty states, transient UI, and stale data;
- storefront effectiveness: whether the image makes the app feel trustworthy, useful, and finished.

Distinguish three causes when possible:

1. capture/data curation problems;
2. missing-asset or loading problems;
3. actual UI/layout implementation gaps.

Do not penalize normal iOS-versus-Android platform conventions. Call out different locations, dates, records, filters, or device aspect ratios when they prevent a clean comparison.

## 5. Report the audit

Lead with an honest overall judgment. Include:

1. a caveat section for data/device differences that affect comparability;
2. one row per inspected scenario with the screen name, meaningful differences, stronger capture, and severity;
3. systematic findings that recur across multiple screens;
4. separate qualitative scores for the iOS set, Android set, and—when capture data materially distorts it—the Android UI independent of capture quality;
5. prioritized remediation ordered by storefront impact.

Use severity labels:

- **Critical** — looks broken, empty, or unsuitable for store submission;
- **High** — substantially reduces trust or perceived completeness;
- **Medium** — noticeable hierarchy, density, or consistency gap;
- **Low** — minor polish difference or normal platform variation.

Be specific about visible evidence. Avoid vague statements such as “iOS feels better.” Explain which asset, spacing decision, record selection, hierarchy, or artifact creates the difference.

Do not modify app code or create tasks unless the user separately asks for remediation or task creation.
