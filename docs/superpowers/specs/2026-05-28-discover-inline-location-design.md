# Discover Inline Location Design

## Goal

Make location setup and correction part of the Discover tab so nearby recommendations are immediately understandable and adjustable.

## User Experience

Discover shows an inline location prompt directly under the `Discover` title. When no location is saved, it says `Set your location` with short supporting copy. When a location exists, it says `Near City, ST - 25 mi` when city/state are known, or `ZIP 10012 - 25 mi` as a fallback. Tapping the prompt opens a focused sheet with ZIP entry, distance, current-location, clear, validation, and permission-recovery actions.

## Architecture

The prompt uses the existing shared `NearbyLocationController` and `SettingsNearbyPreferenceModel`. This avoids a second location state path: saving, clearing, or geolocating from Discover updates the same nearby preference used by Profile, Search, and home rails. Home rails already observe the nearby preference store by ZIP, so they reload after changes without new feed plumbing.

## Error Handling

Invalid ZIP input stays in the sheet and shows the existing validation copy. Location denial or lookup failure shows the existing controller status message and offers Settings when permission is denied.

## Testing

Add source-level home tests that ensure the Discover header is wired to `NearbyLocationController`, presents the inline prompt, uses `SettingsNearbyPreferenceModel`, and keeps home rail reload behavior tied to the shared preference.
