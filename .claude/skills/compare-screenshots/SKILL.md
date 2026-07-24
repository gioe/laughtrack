---
name: compare-screenshots
description: Regenerate the complete iOS and Android screenshot matrices, validate fresh run manifests, compare selected phone and tablet profiles side by side, and report qualitative product-polish differences. Use when asked to run, audit, review, compare, or assess the mobile store screenshots across iOS and Android.
---

# Compare Screenshots

Capture both native store-listing sets and evaluate the resulting images pair by pair. Treat this as a local capture and read-only product audit: never upload screenshots or invoke release lanes.

## 1. Confirm the environment

Run from the repository root. Confirm these prerequisites before starting:

```bash
test -x ios/bin/lane
test -f android/Gemfile
test -x scripts/screenshots/regenerate-comparisons
xcrun simctl list devices booted
adb devices
```

Require at least one booted iOS simulator and one authorized Android emulator/device. If either is missing, stop and tell the user exactly what must be started. Do not analyze an existing set as though it were newly generated.

Create persistent run directories and record an RFC 3339 freshness boundary immediately before capture:

```bash
SCREENSHOT_RUN_ROOT=$(mktemp -d "${TMPDIR:-/tmp}/laughtrack-screenshot-compare.XXXXXX")
IOS_RUN_ROOT="$SCREENSHOT_RUN_ROOT/runs/ios"
ANDROID_RUN_ROOT="$SCREENSHOT_RUN_ROOT/runs/android"
CAPTURE_STARTED_AT=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
```

Keep this directory until the audit is complete. The regeneration command writes
normalized manifests and their declared images below the corresponding run roots,
plus 17 labeled cross-platform sheets under `scenario-sheets/` and the
delta-aware `comparison.json` at the comparison root.

## 2. Regenerate the comparison matrix

Use the repository's single capture-only entry point. It runs the iOS and Android
lanes sequentially, supplies the resilient Xcode build-settings timeout, validates
both manifests, generates all 17 scenario sheets, and compares decoded pixels
with the persistent reviewed baseline:

```bash
scripts/screenshots/regenerate-comparisons \
  --output-root "$SCREENSHOT_RUN_ROOT" \
  --no-open
```

Do not run `screenshots_and_upload`, `upload_screenshots`, `upload_metadata`, `release`, or any other upload/release lane. If either capture lane fails, report its failure and stop before qualitative analysis.

The wrapper invokes only capture lanes. The explicit output root preserves the
validated raw runs for comparison; it does not upload anything. The expected
manifests are:

- iOS: `$IOS_RUN_ROOT/manifest.json`
- Android: `$ANDROID_RUN_ROOT/manifest.json`

## 3. Validate the capture set and audit delta

Run the bundled validator with both manifests, the recorded freshness boundary,
and the persistent reviewed baseline. It hashes ImageMagick-decoded RGBA pixels,
not encoded PNG bytes, so metadata and compression changes do not create false
deltas. The canonical order is iOS phone, Android phone, comparison-only iPad,
Android 10-inch, then Android 7-inch. The iPad profile renders native geometry
for comparison but is not a shipping target; the production iOS app is
iPhone-only.

```bash
REVIEWED_BASELINE="apps/screenshot-comparisons/reviewed-baseline.json"
python3 .claude/skills/compare-screenshots/scripts/validate_pairs.py \
  --ios-manifest "$IOS_RUN_ROOT/manifest.json" \
  --android-manifest "$ANDROID_RUN_ROOT/manifest.json" \
  --fresh-since "$CAPTURE_STARTED_AT" \
  --baseline "$REVIEWED_BASELINE" \
  --sheet-dir "$SCREENSHOT_RUN_ROOT/scenario-sheets" \
  > "$SCREENSHOT_RUN_ROOT/comparison.json"
```

Add a canonical scenario such as `--scenario 05_ClubDetail` only for diagnosis;
a partial comparison cannot be approved as the reviewed baseline.

Require the manifests to contain exactly one fresh, declared, readable image
for every selected platform profile and every scenario in
`screenshots/catalog.json`. This includes guest, authenticated-persona,
protected-action auth-prompt, and first-entry auth-choice states; do not treat
those authentication surfaces as interchangeable.

Stop on missing, duplicate, stale, unreadable, or unexpected captures, mismatched
Git revisions, or undeclared image files in either run. Do not silently select
among duplicates.

## 4. Inspect required scenario sheets

Read `comparison.json` in group order. On the first audit, a missing baseline
marks all 17 groups `review_required`; open every scenario sheet at high detail.
On later audits, open only sheets whose group has `review_required: true`.
Changed pixels, a missing capture record, or invalid baseline catalog/source/order
provenance must always require review. Never override those safeguards.

Read the root-level `profiles` metadata before judging device support. Treat any
profile with `comparison_only: true` and `shipping: false` as a diagnostic
comparison surface, not as evidence of a production tablet experience. The
scenario-sheet label repeats this status so it remains visible during review.

Use each sheet as the primary review surface. Open an original image at high or
original detail only when the sheet exposes a suspected defect that needs closer
inspection. Do not infer visual quality from source code, filenames, or metadata.

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

## 5. Approve the reviewed baseline and report

Only after every required sheet and any suspect originals have been reviewed,
write the complete current corpus as the next reviewed baseline:

```bash
python3 .claude/skills/compare-screenshots/scripts/validate_pairs.py \
  --ios-manifest "$IOS_RUN_ROOT/manifest.json" \
  --android-manifest "$ANDROID_RUN_ROOT/manifest.json" \
  --fresh-since "$CAPTURE_STARTED_AT" \
  --write-baseline "$REVIEWED_BASELINE" \
  --reviewed-by "<reviewer identity>" \
  > /dev/null
```

Never write or refresh the baseline before the visual review is complete.

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

The caveat section must explicitly state that the iPad images use native iPad
geometry enabled only for comparison captures and that the shipping iOS target
is iPhone-only. Do not score or describe those images as production iPad or
App Store tablet support.

Do not modify app code or create tasks unless the user separately asks for remediation or task creation.
