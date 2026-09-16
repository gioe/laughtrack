# Search entity row polish — TASK-4004

## Reproduce the visual comparison

Start the local artwork fixture server from the repo root:

```sh
python3 scripts/screenshots/fixture_server.py --host 127.0.0.1 --port 8765
```

Run the shared-row capture suite on both devices:

```sh
ios/bin/test-sim LaughTrackTests/SearchEntityRowVisualCaptureTests
ios/bin/test-sim --model 'iPad Pro 11-inch (M4)' LaughTrackTests/SearchEntityRowVisualCaptureTests
```

The suite records PNG attachments and prints their temporary paths. Copy these
before another test launch reinstalls the app. Each run covers comedian, club,
and podcast artwork, missing artwork, saved/unsaved/pending favorites, standard
text, and AX5. Separate AX5 pending captures make the spinner visible even when
long rows extend below the scroll viewport.

## Visual findings

Captured on iPhone 16 Pro and iPad Pro 11-inch (M4), iOS 18.3.1. The shipping app
targets iPhone; the iPad captures exercise its 375-point compatibility canvas,
not a native tablet layout.

- Removed ornate artwork frames, glowing dotted borders, row outlines, and
  shadows. Circular portraits, rounded club logos, and square podcast covers
  retain distinct identities. Club images remain fitted rather than cropped.
- Removed chevrons beside favorite controls. Rows without a favorite, including
  Search clubs, retain their disclosure indicator.
- At standard text sizes, the smaller artwork and heart leave more room for
  names. Hearts retain independent 44 × 44 point targets.
- At AX5, artwork moves above the text and names expand without a line limit.
  The baseline truncated “Good One: A Podcast About Jokes”; the new row displays
  the whole title. Long rows scroll normally, and long words can wrap on narrow
  canvases. Metadata also expands at accessibility sizes.
- Saved, unsaved, and pending states retain row geometry. The compact spinner
  stays at its standard visual size even at AX5.
- Library uses the same shared row and accessory presentation. Standalone
  onboarding favorite controls retain their existing treatment.

## Verification

The focused layout suite measures actual rendered geometry at a narrow 288-point
row width for every entity type, standard/AX5, and all three favorite states.
It verifies separate targets, minimum target sizes, row containment, stable state
geometry, and increasing row height for titles well beyond two lines.

Native navigation tests exercise guest favorite → sign-in → cancel, followed by
independent detail navigation. The accessibility case checks complete title and
metadata labels, visible targets, and screenshots inside the actual Search tab.

Run the behavioral suites with:

```sh
ios/bin/test-sim LaughTrackTests/SearchFavoriteRowLayoutTests LaughTrackTests/ClubRowTests LaughTrackTests/LibraryFavoritesViewTests
caffeinate -dimsu ios/bin/test-sim LaughTrackUITests/NavigationTransitionUITests/testSearchEntityFavoritesKeepLoginAndDetailActionsSeparate LaughTrackUITests/NavigationTransitionUITests/testAccessibilitySearchEntityRowsRetainLabelsAndSeparateTargets
```

Keep the Mac awake during native interaction tests. In this session, macOS sleep
interrupted event generation and produced multi-minute tap/swipe timeouts;
power logs confirmed those runs were interrupted by sleep.

Session artifacts are in `/tmp/task4004-{before,after}-{phone,ipad}-*.png`;
the capture suite provides a durable way to regenerate the current design.
