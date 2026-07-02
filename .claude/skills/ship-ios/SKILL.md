---
name: ship-ios
description: Cut an iOS beta (or App Store) release via fastlane — runs the preflight safety checklist (build-clean, apps/web typecheck-green, no racing session, ASC creds present), then drives ios/bin/lane. Use when asked to ship, release, or push an iOS beta/TestFlight build.
allowed-tools: Bash, Read, AskUserQuestion
---

# Ship iOS Skill

Cuts an iOS release through fastlane's `beta`/`release` lanes, run via the
**`ios/bin/lane`** wrapper. The lane bumps the build (and version), builds,
uploads to TestFlight / App Store Connect, and **pushes a version-bump commit
and a tag to `origin/main`** — so this is an outward-facing, hard-to-reverse
action. Never run the upload step without completing the preflight and getting
explicit go-ahead.

> The wrapper handles `cd ios` + Homebrew Ruby PATH; ASC creds load from
> `ios/fastlane/.env`. See `ios/CLAUDE.md` → "Releasing (fastlane)".

## Step 1: Preflight — the release must be safe to push

Run these checks and STOP with a clear report if any fails; do not proceed to
the upload until they pass or the user waves a specific one off.

1. **Branch + sync.** `git rev-parse --abbrev-ref HEAD` should be `main` (or the
   user's intended release branch). `git fetch -q origin main` then confirm
   local `HEAD` matches `origin/main` (no unpushed/divergent commits that the
   release would carry along unexpectedly).
2. **Working tree.** `git status --short`. A dirty tree is a yellow flag — the
   lane's `build_app` builds from the working tree, so uncommitted changes ship
   in the IPA even though only `project.yml`/`pbxproj` get committed. Surface any
   uncommitted files and confirm they're intended (or clean/commit first).
3. **HEAD builds.** `cd ios && swift build --target LaughTrackApp`. Catches the
   classic macOS-unavailable-API break (e.g. a raw `.navigationBarTitleDisplayMode`
   instead of `.modifier(InlineNavigationTitle())`). A red build here means a
   fresh checkout of `main` is broken — fix and commit before releasing.
4. **apps/web typecheck (the beta-aborting gotcha).** `cd apps/web && npm run
   type-check`. The lane's bump-commit push goes through the husky **pre-push
   hook**, which runs this exact check over the *whole working tree*. If an
   in-flight change anywhere in `apps/web` doesn't typecheck, the push — and the
   entire lane, mid-run after it already bumped the build — aborts. Must be green
   (exit 0, zero `error TS`).
5. **No racing session.** `tusk skill-run list | head` — if another session is
   active and committing to `main`, pushing the bump races it. Flag it; prefer to
   wait until it settles.
6. **ASC creds present.** Confirm `ios/fastlane/.env` exists (the wrapper's
   preflight also enforces this). Missing → `cp ios/fastlane/.env.example
   ios/fastlane/.env` and fill in the App Store Connect key.

## Step 2: Confirm scope

Ask the user (AskUserQuestion) unless they already specified:

- **Lane:** `beta` (TestFlight, default) vs `release` (full App Store submission).
- **Version bump:** default patch bump (`MARKETING_VERSION` x.y.z → x.y.(z+1) **and**
  build +1) vs **build-number-only** (`skip_marketing_bump:true`, keeps the
  marketing version, bumps just the build). "Bump the build number" usually means
  the latter.

## Step 3: Run it

Once preflight is green and scope is confirmed, run from the repo root:

```bash
ios/bin/lane beta                            # or: ios/bin/lane beta skip_marketing_bump:true
```

For a full App Store submission use `ios/bin/lane release` (adds screenshots +
`submit_review`). The wrapper prepends Homebrew Ruby and `cd`s into `ios/`; the
lane loads ASC creds from `ios/fastlane/.env`.

- This is the outward-facing step. If you (the agent) are running it rather than
  handing the command to the user, confirm explicitly first — it uploads to
  TestFlight and pushes to `main`.
- If the run dies at the bump-commit push on the pre-push typecheck, an
  `apps/web` change regressed since Step 1 — the build was already bumped locally
  (`[fastlane] Bump build to N` commit). Recover by getting the typecheck green,
  then re-pushing that commit; don't re-run the whole lane (it would double-bump).

## Step 4: Report

Report the resulting `MARKETING_VERSION` + build number, the tag
(`v{version}-{build}`), and confirm the upload reached App Store Connect /
TestFlight. Note anything skipped or waved off during preflight.
