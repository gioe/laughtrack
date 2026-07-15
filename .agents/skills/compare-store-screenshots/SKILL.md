---
name: compare-store-screenshots
description: Regenerate the nine iOS App Store and Android Google Play screenshots, validate a fresh one-to-one capture set, visually compare every matched screen, and report qualitative product-polish differences. Use when asked to run, audit, review, compare, or assess the mobile store screenshots across iOS and Android.
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

Record a freshness boundary immediately before capture:

```bash
CAPTURE_STARTED_AT=$(date +%s)
```

## 2. Run both capture lanes

Run the capture-only lanes sequentially so two UI-test workloads do not compete for host resources:

```bash
ios/bin/lane screenshots
(cd android && bundle exec fastlane screenshots)
```

Do not run `screenshots_and_upload`, `upload_screenshots`, `upload_metadata`, `release`, or any other upload/release lane. If either capture lane fails, report its failure and stop before qualitative analysis.

The expected outputs are:

- iOS: `ios/fastlane/screenshots/en-US/`
- Android: `android/fastlane/metadata/android/en-US/images/phoneScreenshots/`

## 3. Validate the capture set

Run the bundled validator with the recorded epoch:

```bash
python3 .agents/skills/compare-store-screenshots/scripts/validate_pairs.py \
  --repo-root . \
  --fresh-since "$CAPTURE_STARTED_AT"
```

Require exactly one fresh iOS and Android image for each canonical key:

1. `01_NearMe`
2. `02_SearchShows`
3. `03_SearchComedians`
4. `04_SearchClubs`
5. `05_ClubDetail`
6. `06_ShowDetail`
7. `07_ComedianDetail`
8. `08_SearchPodcasts`
9. `09_PodcastDetail`

Stop on missing, duplicate, stale, unreadable, or unexpected captures. Do not silently select among duplicates.

## 4. Inspect every pair

Open all 18 images at high or original detail, keeping each iOS image adjacent to its Android match. Do not infer visual quality from source code or filenames.

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
2. a nine-row table with the screen name, meaningful differences, stronger capture, and severity;
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
