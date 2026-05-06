---
name: fastlane-beta
description: Build and upload the iOS app to TestFlight with metadata and screenshots. Runs generate_release_notes, bump_build_number, build, upload_app_store, and tag_release.
---

# Fastlane Beta Skill

This skill runs the fastlane `beta` lane to build and upload the LaughTrack iOS app to App Store Connect (TestFlight + metadata + screenshots in one shot).

## What it does

1. Generates release notes from commits since the last tag (writes `release_notes.txt`)
2. Bumps the build number (fetches latest from App Store Connect + 1)
3. Builds the IPA with App Store signing
4. Uploads IPA + metadata + screenshots to ASC via `deliver` (creates the version record, pushes to TestFlight)
5. Tags the commit `vX.Y.Z-N`

## Usage

```bash
cd "$(git rev-parse --show-toplevel)/ios" && export PATH="/opt/homebrew/opt/ruby/bin:/opt/homebrew/lib/ruby/gems/4.0.0/bin:$PATH" && bundle exec fastlane beta 2>&1
```

**Timeout:** This command takes 3–5 minutes. Use a 600000ms timeout.

## Interpreting results

- Look for `fastlane.tools finished successfully` at the end
- The build number and TestFlight upload status will be in the output
- Precheck warnings about "broken urls" or competitor mentions are non-blocking — review them but they don't fail the upload
- If it fails, check for signing issues, API key problems, or App Store Connect errors

## Prerequisites

- App Store Connect API key at `~/Desktop/keys/AuthKey_UCV7S354H2.p8`
- Homebrew Ruby with bundler 4.0.8
- Gems installed via `bundle install` in the `ios/` directory
