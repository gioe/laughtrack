# LaughTrack Full-Repo Audit — Execution Plan

**Date:** 2026-07-07
**Produced by:** Claude Fable 5 (five parallel audit agents: apps/web, apps/scraper, ios/, android/, cross-cutting infra)
**Intended executor:** a capable but less-context-rich model (e.g. Claude Opus) working one task at a time.

This document is self-contained. You do not need the audit session's context. Every task lists the files, the exact change, the traps, and the verification command. **Read the Global Guardrails before doing anything.**

---

## How to use this plan

1. Work **one task per commit** (or per tusk task). Never batch unrelated tasks.
2. Before starting a task, run `tusk dupes check` / `tusk task-list` — some of these may already be filed. File new ones via `/create-task` referencing this doc's task IDs.
3. Tiers are priority order. Within a tier, respect the stated dependencies; otherwise tasks are independent.
4. After each task, run the task's **Verification** exactly. If it fails, fix or revert — do not leave a task half-done.
5. `git add` **specific file paths only** — never `git add -A` / `commit -a`. This repo runs parallel agent sessions; the working tree routinely contains other sessions' edits. Diff every file before staging it.
6. Effort key: S = under ~1h, M = a session, L = multiple sessions (split it).

## Status

- **TASK 0 (done 2026-07-07):** 53 tracked files had been deleted from the primary checkout's working tree (shipped scrapers, 3 applied scraper migrations, 6 applied Prisma migrations, `apps/web/public/.well-known/assetlinks.json`). All were restored via `git checkout -- <path>`. If you ever see unexplained ` D` entries in `git status` for shipped files, restore them the same way (list with `git status --porcelain | awk '/^ D / {print $2}'`) — likely a parallel worktree-finalize sweep hitting the wrong checkout. Never `git reset --hard` or `git stash` to "clean up".

---

## Global Guardrails (apply to every task)

1. **OpenAPI lockstep (convention #220).** The single source of truth for `/api/v1` is `ios/Sources/LaughTrackAPIClient/openapi.json`. Any spec edit must regenerate **both** clients in the same commit: iOS `GeneratedSources/` (pinned generator 1.9.0, recipe in `ios/CLAUDE.md`) and Android via `android/bin/regen-openapi.sh` (needs `/opt/homebrew/opt/openjdk@17/bin` on PATH). Blocking CI drift gates exist on both sides and will catch you.
2. **Never hand-edit generated code**: `ios/Sources/LaughTrackAPIClient/GeneratedSources/` and `android/core/network/.../generated/`.
3. **Never change `/api/v1` response shapes** unless the task explicitly says so — iOS and Android consume them via generated clients.
4. **Never rename scraper `scraper_key` strings or class registrations** — they are referenced by `scraping_sources` rows in the production DB.
5. **Scraper Makefile traps:** `make lint` **auto-formats the whole tree** (black+isort) — never run it for a scoped change; invoke `.venv/bin/flake8` / `.venv/bin/mypy` directly. In GitHub Actions, `make` targets fail ("No virtual environment found") — CI must call `python -m scripts.core.<module>` / `python bin/migrate` / pytest directly.
6. **Never rename existing applied migration files** (either system) — ledgers key on filename. Scraper migrations re-run nightly and must be idempotent.
7. **Tickets are access records:** every show must emit ≥1 ticket (even free/RSVP). All three clients hide shows with zero tickets. Never "fix" this by dropping ticketless shows.
8. **Don't rebuild scraper health alerting** — it exists in `apps/web/monitoring/grafana/` over `scraper_run_clubs` matviews.
9. **iOS test runs:** HostedView test suites must run on an **iOS 18.x** simulator; iOS 26.x sims fail ~18 tests due to an OS accessibility regression (not your bug). `swift test --filter X` can match zero tests and still exit 0 — confirm nonzero test count in output.
10. **iOS project file:** new Swift files are wired via `ios/project.yml` + `xcodegen generate` — never hand-edit pbxproj hex IDs. Run `make -C ios check-pbxproj` before pushing.
11. **Android builds need** brew JDK 17 on PATH and `android/local.properties` with `sdk.dir`. If unavailable locally, rely on CI (`.github/workflows/android.yml` runs `testDebugUnitTest`, ktlint, detekt).
12. **Merges go directly to main** (no PRs unless asked) — EXCEPT any change adding a file under `apps/web/prisma/migrations/`: validate it first (PR or `workflow_dispatch` web-ci and wait for the `migrations` job), because Vercel applies Prisma migrations to prod on push (see Task INF-6).
13. **main is force-push protected.** No history rewrites.
14. Commit messages end with `Co-Authored-By:` trailer per house style; reference this doc + task ID.

---

## TIER 1 — Correctness & security bugs

### T1.1 (WEB-1) Open redirect via `/api/v1/tickets/out?url=` — **medium/high severity**
- **Files:** `apps/web/app/api/v1/tickets/out/route.ts` (lines ~62–140), `apps/web/lib/affiliate/affiliateRouting.ts`.
- **Bug:** any non-provider host resolves to `provider: "direct_venue"` with `routedUrl = originalUrl`, then 302-redirects. Only `http:`/`https:` is enforced ⇒ `?url=https://evil.example` is a working open redirect off the apex domain. `showId`/`clubId` are enumerable, so the show/club-match guard doesn't help.
- **Fix:** before redirecting, fetch the show's real ticket URLs (`db.ticket.findMany({ where: { showId }, select: { purchaseUrl: true } })`) and require `new URL(destination.originalUrl).origin` to match one of their origins; otherwise return 400. Keep the affiliate rewrite after that check.
- **Gotchas:** this is an OpenAPI-contract route used by iOS/Android. Do NOT change the 302 behavior for valid URLs, the `lt_anon_visitor_id` cookie, or the `TicketPurchaseClickEvent` write. Affiliate rewrites (e.g. Ticketmaster) change the URL but keep the host — validate the *original* URL's origin, not the rewritten one.
- **Effort:** M
- **Verify:** route test asserting evil-host → 400 and real venue URL → 302. `npx vitest run app/api/v1/tickets`; manual: `curl -sI "http://localhost:3000/api/v1/tickets/out?showId=<real>&clubId=<real>&surface=show_card&url=https://evil.com"` → 400.

### T1.2 (WEB-2) Unbounded zip `IN (...)` on the home feed — **high severity (cheap unauth DoS)**
- **Files:** `apps/web/lib/data/home/` — `getTrendingComedians.ts`, `getShowsNearZip.ts`, `getComediansByZip.ts`, `getClubsByZip.ts`, `getTrendingShowsThisWeek.ts`, `getShowsTonight.ts`, `getTrendingPodcasts.ts`; `apps/web/app/api/v1/home/feed/route.ts` (accepts `distance` ≤ 500).
- **Bug:** each file re-declares `resolveZipCodes` with **no cap**; `zipcodes.radius('10001', 500)` = 13,254 zips inlined into SQL `IN` lists across ~7 parallel queries per request. The search path already caps at `QueryHelper.ZIP_CAP = 500` (`apps/web/objects/class/query/QueryHelper.ts:198,568-574`); the home path does not.
- **Fix:** (a) create one shared helper, e.g. `apps/web/util/location/resolveNearbyZips.ts`, applying the same 500-zip cap; import it in all 7 files. (b) Lower home-feed `MAX_DISTANCE_MILES` to 100.
- **Gotchas:** the 7 copies differ subtly (string vs `ZipCode` object returns) — unify carefully. Keep the fallback-to-`[zipCode]` when radius is invalid. Do not change the feed's JSON shape (OpenAPI contract).
- **Effort:** M
- **Verify:** `npx vitest run lib/data/home`; unit test `resolveNearbyZips('10001', 500).length <= 500`; curl the feed with `distance=500` and confirm fast response.

### T1.3 (SCR-1) Yearless-date year inference: 25+ divergent copies; etix path with NO Dec→Jan rollover — **high severity (silent seasonal data loss)**
- **[Progress — TASK-3670, 2026-07-09]** Squarespace's products-path `_infer_year` is now venue-tz-aware (it keeps its intentional skip-recently-past-products policy, distinct from `DateTimeUtils.infer_year`). New hazard found in this class: **machine-local clocks** — squarespace used `date.today()` and only failed between 20:00–24:00 Eastern (UTC/venue calendar divergence); `csz_philadelphia/transformer.py:88` still uses naive `datetime.now()` (month-boundary wrong on UTC runners, tracked as TASK-3693). When migrating copies, always derive `today` from the **venue timezone**, per the tixologi/comedy_mothership idiom.
- **Bug:** five different private `_infer_year` implementations (`src/laughtrack/core/entities/event/tixologi.py:25`, `comedy_mothership.py:23`, `multipass.py:45`, `scrapers/implementations/tempo_tickets/extractor.py:145`, `venues/csz_philadelphia/transformer.py:88`) plus ~24 hand-rolled `year + 1` heuristics. Worst: `scrapers/implementations/api/etix/scraper.py:839` does `year = title_year or date.today().year` with no rollover — a January show scraped in December resolves to *past* January and is silently dropped.
- **Fix (incremental, one scraper per commit):**
  1. Add `DateTimeUtils.infer_year(month, day, *, today, horizon_days=2, weekday_abbr=None) -> int` in `apps/scraper/src/laughtrack/foundation/utilities/datetime/utils.py`. Pure function; clock always injected — never call `date.today()` inside it. Port the weekday-disambiguation logic from `core/entities/event/multipass.py:45` (the richest variant). Add frozen-clock unit tests at 2026-12-28 and 2027-01-02.
  2. Fix the unguarded etix fallback first: `title_year or infer_year(month, day, today=date.today())`.
  3. Migrate the identical twins `tixologi.py`/`comedy_mothership.py`, then others opportunistically.
- **Gotchas:** only replace the *fallback* branch in scrapers whose pages sometimes print explicit years. TASK-3586 just converted test fixtures to frozen-clock-safe forms — don't reintroduce yearless literals in tests. A `scraper-frozen-clock.yml` CI workflow will catch fixture rot. Etix cannot be verified live locally (DataDome) — rely on fixture tests.
- **Effort:** M (helper S; migration incremental)
- **Verify:** `.venv/bin/python -m pytest tests/scrapers/implementations/api/etix tests/scrapers/implementations/api/multipass tests/scrapers/implementations/tempo_tickets -q` from `apps/scraper/`, then `make test`.

### T1.4 (SCR-2) "Every show emits ≥1 ticket" invariant enforced nowhere; pipeline validator hook is dead code — **high severity (invisible-show regressions)**
- **Files:** `apps/scraper/src/laughtrack/utilities/infrastructure/pipeline/pipeline.py` (lines 33, 39-41: `validators`/`register_validator` exist but `transform()` at 43-92 never applies them; zero callers), `core/entities/ticket/handler.py:47-49`, `foundation/infrastructure/http/diagnostics.py`.
- **Fix:** in `ShowTransformationPipeline.transform()`, when a produced show has no tickets, `Logger.warn(...)` and record via the existing `ScrapeDiagnostics` (e.g. a `shows_without_tickets` counter) so it reaches `scraper_run_clubs`/Grafana. Either wire `self.validators` into the loop or delete the dead attribute + method (deleting is fine).
- **Gotchas:** WARN + metric only — do **not** raise or drop ticketless shows; some scrapers attach tickets later via `scrapers/utils/ticket_enrichment.py`. A persisted new column needs a guarded SQL migration; Grafana provisioning is a separate surface (`apps/web/monitoring/grafana/`) — don't rebuild alerting.
- **Effort:** S (warn + diagnostic) / M (persisted metric)
- **Verify:** `.venv/bin/python -m pytest tests -q -k "pipeline or transformer_registration"`, then `make test`.

### T1.5 (AND-1 + AND-2) Android: `runCatching` swallows `CancellationException`; Home load race — do together
- **Part A (all ViewModels):** add to `core:data` (next to `UiState`):
  ```kotlin
  suspend fun <T> runCatchingCancellable(block: suspend () -> T): Result<T> =
      try { Result.success(block()) }
      catch (e: kotlinx.coroutines.CancellationException) { throw e }
      catch (e: Throwable) { Result.failure(e) }
  ```
  Replace every `runCatching { <suspend repository/api call> }` inside `viewModelScope.launch` with it: `SearchViewModel.kt:211` (the actively-cancelling one — currently a cancelled search can flash "Search failed"), `HomeViewModel.kt:141`, `ComedianDetailViewModel.kt:40`, `ShowDetailViewModel.kt:37`, `PodcastDetailViewModel.kt:34`, `ClubDetailViewModel.kt:40`, `NotificationCenterViewModel.kt:34`, `ComedianOnboardingViewModel.kt:61/76/101/186/205`, and repository-internal sites like `ComedianDetailRepository.kt:34-42`.
  **Do NOT** touch synchronous uses (`runCatching { URI(uri) }` in `LaughTrackDeepLink.kt:30`, `DetailFormatting.kt`, `SearchScreen.kt:635`).
- **Part B (`feature/home/.../HomeViewModel.kt:130-154`):** `load(zip)` has no in-flight cancellation — rapid `setManualZip` → `useDeviceLocation` lets the *older* zip's response win. Add `private var loadJob: Job?`; `loadJob?.cancel()` at the top of `load()` **before** the cached render. Requires Part A first (else the cancellation is swallowed).
- **Effort:** S
- **Verify:** `cd android && ./gradlew testDebugUnitTest` (or defer to CI). Add a `SearchViewModelTest`: two rapid query changes with a fake repository whose first call suspends forever → state never `failed`. Extend `HomeViewModelTest.kt` (276 lines, don't rewrite).

### T1.6 (IOS-1) iOS: six classes bypass the generated client (and token refresh); three endpoints missing from the spec — **high severity**
- **Evidence:** hand-rolled `URLRequest`+`JSONSerialization` against our own `/api/v1` in: `ios/Sources/LaughTrackCore/NearbyPreferenceStore.swift:194-237` (PATCH `me/location`), `NotificationPreferenceStore.swift:17-67` (PATCH `me/notifications`), `PushDeviceTokenManager.swift:14-90` (POST/DELETE `me/push-tokens`), `LaughTrackApp/Search/Models/PodcastSearchModel.swift:103`, `Detail/Views/PodcastDetailView.swift:635`, `PodcastTonightNearYouCard.swift:98`. These skip `TokenRefreshMiddleware` — after access-token expiry they silently fail until an unrelated generated-client call refreshes. The three `me/*` endpoints are **absent from `openapi.json`** entirely.
- **Fix (ordered):**
  1. Add the three missing operations to `ios/Sources/LaughTrackAPIClient/openapi.json`. The location PATCH sends explicit JSON `null` to clear fields — mark those fields `nullable` or the clear-zip flow breaks.
  2. Regenerate **both** clients (Guardrail 1) in the same commit. Verify web handlers actually match what you specify (check `apps/web/app/api/v1/me/...` routes first; the spec must describe reality, not aspiration).
  3. Swap each hand-rolled fetcher to a generated-client call through `APIClientFactory` (carries Authentication + TokenRefresh middleware). Keep every `*Syncing`/`*Fetching` protocol — swap only implementations, so the 66 existing test files keep compiling. One client per commit, suite green before the next.
  4. Podcast fetchers need no spec change — `Client.searchPodcasts` (`GeneratedSources/Client.swift:3708`) and `Client.getPodcast` (`:3857`) already exist; map to the existing `PodcastSearchResult`/`PodcastDetailResponse` structs.
- **Effort:** L (split into ≥3 commits)
- **Verify:** `cd ios && swift build && swift test`; `ios/bin/check-openapi-regen-drift.sh`; Android drift check per `android/README.md`.
- **Follow-on:** after this lands, do **IOS-5**: delete the duplicated HTTP-status→failure switches in `PodcastSearchModel.swift:150-170` / `PodcastDetailView.swift:658-676` in favor of `LoadFailure.classifyUndocumented` (`LaughTrackCore/LoadFailure.swift:83-97`). Grep tests for the literal error strings before changing copy.

### T1.7 (INF-2) Spec-only `openapi.json` edits never trigger web CI
- **File:** `.github/workflows/web-ci.yml`.
- **Fix:** add `- "ios/Sources/LaughTrackAPIClient/openapi.json"` to both `push.paths` and `pull_request.paths`. Then add a `dorny/paths-filter` `changes` job (copy the pattern from `scraper-ci.yml:22-39`) so a spec-only trigger runs only the `test` job (the route tests import the spec via `apps/web/test/openapiResponseValidator.ts`), not lint/build/e2e-visual (expensive).
- **Effort:** S
- **Verify:** `grep -n 'openapi.json' .github/workflows/web-ci.yml`; push a whitespace-only spec change on a branch → `Web CI/CD / Test` runs.

### T1.8 Small type-safety fixes (batchable in one commit each)
- **(WEB-5)** `apps/web/app/api/v1/tickets/out/route.ts:107-124`: remove the outer `as any` on the whole `db.ticketPurchaseClickEvent.create({ data: ... })`; if the JSON field complains, cast only `deviceMetadata` as `Prisma.InputJsonValue`. Verify `npx tsc --noEmit` clean.
- **(AND-7)** `feature/detail/.../PodcastDetailScreen.kt:60` and `ComedianDetailScreen.kt:97`: replace `when (state)` + separate nullable `data!!` with `when (val s = state) { is UiState.Success -> Body(s.value, ...) }`. In `ComedianDetailScreen`, the `isFavorite`/`onFavorite` lambdas (lines 99-101) also use `ui` — move them inside the branch. The `data?.let` for `onShare` outside the `when` is fine; keep it.
- **(SCR-3 part)** `apps/scraper/scripts/core/scrape_shows.py:166`: mypy-confirmed None-deref (`Item "None" of "Club | None" has no attribute "id"`) — add the None guard.

---

## TIER 2 — CI/ops guardrails & repo hygiene (small, high leverage)

### T2.1 (SCR-3) Add a ratcheting lint/typecheck gate to scraper CI
- **Current state:** `.venv/bin/flake8 src/ scripts/ --count -qq` → 971 (E402×275, C901×193, W191×127, F401×77); `.venv/bin/mypy src/ scripts/` → 729 errors in 297 files. `scraper-ci.yml` runs pytest only.
- **Fix:** (a) burn down the 31 `[unused-ignore]` mypy errors (mechanical). (b) Add a scraper-ci job that fails if counts *increase* over a checked-in baseline (simple: store baseline counts in a file, compare), or enforce a small clean subset first (`flake8 --select F821,F811,F401 src/`). Exclude `scripts/` initially (see T3.5).
- **Gotchas:** Guardrail 5 (no `make lint`, no `make` in CI). Don't attempt to fix all 971 — ratchet only.
- **Effort:** M
- **Verify:** counts strictly decrease: `.venv/bin/flake8 src/ scripts/ --count -qq`; `.venv/bin/mypy src/ scripts/ | tail -1`.

### T2.2 (INF-10) `scraper-schedule.yml` has no concurrency group
- **Fix:** add top-level:
  ```yaml
  concurrency:
    group: scraper-pipeline
    cancel-in-progress: false
  ```
  **Never** `cancel-in-progress: true` — cancelling mid-run leaves a partially persisted run that dropped-to-zero alerts misread. Don't serialize `scraper-verify.yml` with it (verify runs are excluded from alert baselines).
- **Effort:** S. **Verify:** dispatch twice quickly → second run queues.

### T2.3 (INF-7) `vercel.json` hardening — **verify with a preview deploy before merging**
- **Fix:** (a) `installCommand`: `npm install --prefix apps/web` → `npm ci --prefix apps/web` (fall back to `npm ci --legacy-peer-deps --prefix apps/web` if peer-dep resolution fails — next-auth beta historically needed it). (b) Replace the silent `DIRECT_URL:-$DATABASE_URL` fallback with fail-fast: `: "${DIRECT_URL:?DIRECT_URL must be set (non-pooled Neon URL)}"` — the pooled URL breaks migrate advisory locks with hard-to-diagnose hangs. (c) Check in the Vercel dashboard that Preview environments don't share prod `DATABASE_URL` (else a preview build can migrate prod) — report, don't guess.
- **Effort:** S. **Verify:** trigger a preview deploy; build logs show `npm ci` and `prisma migrate deploy` succeeding.

### T2.4 (INF-3) Untrack `.claude/bin`; reconcile `.claude/skills` modifications
- `.gitignore` lists `.claude/bin/` but ~40+ files are tracked anyway (gitignore never untracks) — every tusk upgrade dirties 17+ files, masking real problems (Task 0's 53 deletions hid in this noise).
- **Fix:** `git rm -r --cached .claude/bin && git commit`. For the 4 modified `.claude/skills/*/SKILL.md`: diff each; per the "tusk-issues go upstream" rule they're likely upgrade artifacts — revert them (`git checkout --`) rather than committing, unless the diff shows intentional project-specific content.
- **Gotchas:** files stay on disk after `rm --cached`. `AGENTS.md` invokes `./.claude/bin/tusk` at runtime — unaffected by untracking.
- **Effort:** S. **Verify:** `git status --porcelain | grep -c '.claude/'` → 0; `git ls-files .claude/bin | wc -l` → 0.

### T2.5 (INF-4 tier 1 + SCR-11) Untrack scratch data; delete stale task docs
- **Fix:** `git rm --cached apps/scraper/tmp/*.csv apps/scraper/tmp/*.jsonl`; add `tmp/` to `apps/scraper/.gitignore`. Delete `apps/scraper/TICKETMASTER_NATIONAL_SHARDING_TASK.md` (shipped 2026-06-14; history preserves it). Keep `apps/scraper/web/seatengine_api_tool/` (a `make seatengine-api-tool` target uses it).
- **Ask the user first (do not act unilaterally):** `logs/main/app.log` is *intentionally* tracked per a `.gitignore` comment — confirm why before untracking. `screenshots/` (~20 MB) references a `/refresh-screenshots` skill that no longer exists — ask keep/delete. Any git-history rewrite (600 MiB pack, old `client/.next` blobs) is **blocked by force-push protection** and is a user decision — do not attempt.
- **Effort:** S. **Verify:** `git ls-files apps/scraper/tmp | wc -l` → 0.

### T2.6 (INF-5 + SCR-10) Document the dual-migration-system rules; add migration lint
- **Fix (docs):** create `apps/scraper/migrations/README.md`: (1) Prisma owns table DDL; scraper SQL owns data fixes + scraper-only objects (matviews, `migrations_log`); (2) scraper migrations re-run nightly → must be idempotent (guarded inserts / `ON CONFLICT` / `IF NOT EXISTS`); (3) ordering: Vercel applies Prisma on merge, nightly applies scraper SQL at 21:00 UTC — scraper migrations must not depend on undeployed Prisma migrations; (4) matview definition changes = new migration with DROP+recreate, never edit-in-place (rule already in the `scraper-health-alerts.yaml` header — read it first, don't paraphrase from memory); (5) new filenames MUST use full `YYYYMMDDHHMMSS_` prefixes (existing date-only files: leave them — ledger keys on filename). Cross-link from `apps/web/DEPLOYMENT.md`.
- **Fix (optional lint):** a `check-migrations` script failing on *new* date-only names or unguarded `INSERT INTO` (compare against `git merge-base` — never lint pre-existing files).
- **Effort:** S. **Verify:** file exists; `make migrate-dry-run` still clean.

### T2.7 (INF-6) Document post-merge-CI reality; verify the Neon guardrail is real
- **Fix:** add a "CI is post-merge by design" section to `apps/web/DEPLOYMENT.md` (or `AGENTS.md`): direct pushes to main bypass checks and Vercel deploys+migrates immediately; therefore any change adding `apps/web/prisma/migrations/` files must be validated pre-push (PR, or `workflow_dispatch` web-ci and wait for the `migrations` job). Also run `gh variable list | grep NEON_PROJECT_ID` — the ephemeral-branch migration-validation job silently skips if unset; if it's missing, tell the user (the guardrail is imaginary until provisioned).
- **Do NOT** enable branch protection or change the merge workflow — direct-push is an explicit user preference.
- **Effort:** S.

### T2.8 (INF-11) `grafana-provision.yml`: add failure notification + monthly dry-run
- **Fix:** copy the Discord notify-failure step from `scraper-ci.yml:90-104` (it's the only workflow missing one). Add a monthly `schedule:` trigger running the provision script with `--dry-run` so token rot surfaces within a month instead of at the next alert edit. Read `provision_alert_rules.py`'s docstring before changing invocation flags; scheduled dry-run must not write.
- **Effort:** S. **Verify:** `gh workflow run grafana-provision.yml -f dry_run=true` succeeds.

### T2.9 (INF-8 + WEB-11 + INF-12) Docs drift sweep (one commit)
- `README.md`: says "three apps" — add `android/` to the table and structure diagram (it shipped; has CI and Play releases).
- `ONBOARDING.md`: prune skills that no longer exist (`/refresh-screenshots`, `/tour-date-club-onboarding`, `/fastlane-beta`, `/fastlane-release`, `/fastlane-submit-review`) — replace from the live `.claude/skills/` listing. **Preserve the embedded "INSTRUCTION FOR CLAUDE" block at the bottom.**
- `apps/web/DEPLOYMENT.md:478`: "three unified-alerting rules" is stale (yaml has 1, 2, 2b, 3, 4, 5) — say "see the yaml" instead of a number.
- `web-ci.yml` build-job comment claims secrets that the step doesn't use; `web-ci.yml`/`scraper-ci.yml` notify conditions test `event_name == 'schedule'` but have no cron — fix or annotate.
- **Stack-description corrections** (repo docs + any place that claims otherwise): apps/web uses Tailwind + `@tailwindcss/forms`, Headless UI (4 files) + Radix primitives (7 files), lucide-react icons, date-fns/date-fns-tz. There is **no** DaisyUI, HeroUI, Material Tailwind, or moment-timezone. `tsc --noEmit` is clean; only 3 `as any` in non-test code.
- **Effort:** S.

### T2.10 (INF-9) Prune stale worktrees — **inspect before deleting**
- `git worktree prune`. `~/.tusk/worktrees/laughtrack/` contains unregistered orphan dirs `TASK-2758-ios-gilroy-font-swap` and `TASK-3374-onboard-comedy-bar-detroit` — **look inside for uncommitted work before `rm -rf`**; note the Gilroy swap DID ship (Urbanist is in `ios/Resources/Fonts/`), so 2758's dir is probably safe, but verify. Check `.worktrees/fix-vercel-youtube-live-push-lint`: `git log main..fix/vercel-youtube-live-push-lint --oneline` — if empty, remove worktree + branch. When in doubt, leave it and report.
- **Effort:** S.

---

## TIER 3 — Mechanical refactors (no behavior change)

### T3.1 (IOS-2) Split the 2,729-line `HomeView.swift`
- **File:** `ios/Sources/LaughTrackApp/Home/Views/HomeView.swift` — contains `HomeView`, 15+ card/rail/skeleton views, **five** `@MainActor` models (`HomeShowsTonightModel` L1385, `HomeFavoriteShowsModel` L1520, `HomeTrendingComediansModel` L1834, `HomePopularClubsModel` L2141, `HomeTrendingPodcastsModel` L2660), `MainPageCache` (L2212), `actor HomeFeedRequestCoalescer` (L2286).
- **Fix:** create `Home/Models/` (move the 5 models + coalescer + `MainPageCache`); move each rail bundle to `Home/Views/Rails/<Name>Rail.swift`. Pure moves; adjust `private`→`internal` only where cross-file access requires.
- **Gotchas:** Guardrail 10 (xcodegen). Keep `HomeFeedRequestCoalescer.shared` semantics and the default `.shared` param on `refresh(coalescer:)` — tests pass fresh instances deliberately. HostedView suites verify on iOS 18.x only (Guardrail 9).
- **Effort:** M. **Verify:** `swift build && swift test`; `make -C ios check-pbxproj`; `test_sim` (iOS 18.x) for `HomeFavoriteShowsRailTests`, `HomeHeroHeaderTests`, `MainPageCacheTests`.

### T3.2 (IOS-3) Fix thread-unsafe shared DateFormatter mutation
- **Files:** `ios/Sources/LaughTrackApp/Components/ShowFormatting.swift:54-59` and `ShowRow.swift:481-492` mutate `static let` formatters' `timeZone` per call (data race + wrong-timezone renders); `ShowFormatting.listDate` (L40), `ShowsListView.swift:571`, `MonthCalendarView.swift:286-298,471` allocate fresh formatters in scroll paths (slow).
- **Fix:** make `ShowFormatting` `@MainActor` (all call sites are views) or use `Date.FormatStyle` (value type). Cache formatters keyed by timezone id in a `@MainActor` static dictionary for hot paths.
- **Gotchas:** `ShowRowTests`/`ShowsListViewPresentationTests` assert exact output strings — `FormatStyle` output differs subtly from `DateFormatter` patterns; match exactly. Don't touch `apiFormatter` (it's a parser, `en_US_POSIX`).
- **Effort:** S. **Verify:** `swift test --filter ShowRowTests` and `--filter ShowsListViewPresentationTests` — confirm nonzero test counts.

### T3.3 (IOS-6) One ISO8601 parse helper instead of four
- **[Executed — TASK-3643, 2026-07-08]** `Date.laughTrackISO8601(_:)` added in `LaughTrackAPIConfiguration.swift`, backed by a shared lock-guarded formatter cache (`LaughTrackISO8601Formatters`); the transcoder delegates to the same cache and all three inline copies are deleted. Both verify suites pass (12 + 3 tests).
- Duplicates: `ComedianDetailView.swift:617-619`, `PodcastDetailView.swift:403-405`, `NotificationCenterModel.swift:218-223`; canonical: `LaughTrackAPIClient/LaughTrackAPIConfiguration.swift:10-25` (`LaughTrackFlexibleISO8601DateTranscoder`). Add `Date.laughTrackISO8601(_:)` in `LaughTrackAPIClient` (hand-written file — safe; NOT `GeneratedSources/`), backed by cached static formatters; delete the three inline copies. `ISO8601DateFormatter` options are set-at-init only.
- **Effort:** S. **Verify:** `swift test --filter NotificationCenterModelTests` + `--filter APIClientConfigurationTests` (nonzero counts).

### T3.4 (SCR-4) Extract `ScrapingService` out of the 1,518-line package `__init__.py`
- **File:** `apps/scraper/src/laughtrack/core/services/scraping/__init__.py`. Move the class(es) to `service.py`; keep `__init__.py` re-exporting **every public name** (grep import sites first). Split `_scrape_clubs_concurrently` (complexity 33) into named phases. **Leave the `loop._default_executor = None` hack** (line ~984) — it dodges a real shutdown hang; just isolate it in `_detach_default_executor(loop)` with its comment.
- **Gotchas:** grep `tests/` for `core.services.scraping` monkeypatch targets before moving.
- **Effort:** M. **Verify:** `make test`; `.venv/bin/python -c "from laughtrack.core.services.scraping import ScrapingService"`.

### T3.5 (SCR-5) Archive the `scripts/core` graveyard (116 modules)
- **[Executed — TASK-3645, 2026-07-08]** 51 dated one-offs moved to `scripts/archive/` (git renames; 8 referencing test files repointed); mypy override + flake8 exclude added; mypy errors 756 → 695. Keep-list verified: zero workflow/Makefile references to moved modules. Remaining undated one-offs (`fold_task_1984_dup_pairs.py` etc.) need individual triage — tracked as TASK-3690; naming convention #325 requires date suffixes on new one-offs.
- Move every dated one-off (`*_20XX_XX_XX.py`) and completed disposition to `scripts/archive/`; exclude the archive from mypy (`[[tool.mypy.overrides]]`) and flake8 (`.flake8 exclude`).
- **CRITICAL:** first build the keep-list: `grep -rn "scripts.core" .github/workflows/ Makefile` — the nightly and six other workflows invoke `python -m scripts.core.<module>` directly (`scrape_shows`, `update_popularity`, and modules in `scraper-schedule.yml`, `scraper-verify.yml`, `cdn-image-audit.yml`, `discover-clubs-from-comedian-show-pages.yml`, `check-comedian-website-health.yml`, `podcast-episode-sync.yml`, `social-follower-refresh.yml`). Moving a referenced module breaks production.
- **Effort:** S/M. **Verify:** the grep shows no reference to moved files; `make test`; mypy error count drops.

### T3.6 (SCR-6) Delete the unused `domain/` facade; stop the layering bleed
- `src/laughtrack/domain/` is a re-export facade used by only 10 files (vs 697 importing `laughtrack.core` directly). Codemod those 10 to core imports, delete `domain/`, add an import-linter contract forbidding `laughtrack.domain`. Do **NOT** move the 114 venue modules in `core/entities/event/` (test module-loading and patch paths depend on their locations) — instead record the convention that *new* venue entities live with their scraper (`scrapers/implementations/<x>/entity.py`, as holdmyticket already does): `tusk conventions add --topics "scraper,architecture" "..."`.
- **Effort:** S. **Verify:** `make arch-lint`; `grep -rln "from laughtrack.domain" src scripts` → 0; `make test`.

### T3.7 (SCR-7) Shared price parser + wall-clock→UTC helper
- 15 duplicated price parsers (`core/entities/event/{kellars,philly_improv,timely}.py`; `api/{booktix,modern_events_calendar,tixr,vbo_tickets,woocommerce_store_api}`; `venues/{academy_of_music,go_bananas,laugh_boston,new_york_comedy_club,the_auricle,the_comedy_shoppe}`; `utilities/domain/show/enhancement.py`) and 43 files calling `pytz.timezone(...)` by hand.
- **Fix:** add `foundation/utilities/number/price.py` `parse_price_text(text) -> Optional[float]` ($ ranges→min, "free"→0.0, commas) and `DateTimeUtils.venue_wall_clock_to_utc(naive_dt, tz_name)`. Migrate price sites first, one scraper per commit with its tests.
- **Gotchas:** platforms that parse **cents ints** (dojour, 1234ticket) must NOT route through the text parser. Preserve `None` = unknown vs `0` = free (documented in `scrapers/utils/ticket_enrichment.py:26-28`).
- **Effort:** M. **Verify:** per-scraper pytest, then `make test`.

### T3.8 (SCR-8) Extract Funny Bone/Rockhouse special-casing from the 890-line etix scraper
- Move `_extract_funny_bone_events` (L618), `_funny_bone_single_event` (L663), `_funny_bone_series_events` from `api/etix/scraper.py` into `api/etix/rockhouse.py` as pure functions `(html, today) -> List[EtixEvent]`. Do this **after** T1.3's etix fix. Guardrail 4 (never rename `etix` key). No live verification possible (DataDome) — fixtures only.
- **Effort:** M. **Verify:** `.venv/bin/python -m pytest tests/scrapers/implementations/api/etix -q`.

### T3.9 (AND-3 + AND-4) Split Android god-screens and dedupe the ticket-stub UI
- **Split:** `HomeScreen.kt` (1,269 lines) → `HomeScreen.kt` (scaffold), `HomeRails.kt`, `TonightCarousel.kt`, `ShowTicketRow.kt`, `ShowPresentation.kt` (pure helpers → unit-testable). `SearchScreen.kt` (1,032) → `SearchFilterPills.kt`, `SearchResultRows.kt`, `SearchPresentation.kt`. Keep everything `internal`, same package — no call-site changes.
- **Dedupe:** `showDateParts` (HomeScreen:1182-1199 vs SearchScreen:911-925 — allocates 4 `DateTimeFormatter.ofPattern` per row per recomposition; hoist to top-level `private val` constants, they're thread-safe), `TicketDashedDivider` (989-1000 vs 841-852), `ShowTicketStub` vs `ShowResultStub`, `PrimitiveChip` (273 vs 232) → `core/ui/.../components/TicketStub.kt` with a `TicketStubData` param + colors variant (dark / paper).
- **Gotchas:** the two stubs are **intentionally different colorways** (Home dark, Search cream — Play Store screenshots) — parameterize, don't unify the look. `SEARCH_RESULT_ROW_TEST_TAG` (SearchScreen:721) and home skeleton test tags are load-bearing for `AppStoreScreenshotTest` — keep values/visibility identical. `dateRangeLabel` is tested by `DateRangeLabelTest` — keep its package. Never touch token values in `core/ui/theme/Color.kt` (they're verified 1:1 with iOS/web).
- **Effort:** M. **Verify:** `./gradlew :feature:home:testDebugUnitTest :feature:search:testDebugUnitTest ktlintCheck detekt`; screenshot test on CI.

### T3.10 (AND-5) Single source of truth for AppShell chrome routing
- **[Executed — TASK-3650, 2026-07-08]** Canonical `topAppBarRoutes`/`bottomBarRoutes`/`fullScreenRoutes` KClass sets in `AppShellChrome`; the shipping `NavDestination` predicates read them and the `when(AppRoute)` overloads are deleted. `AppShellChromeTest` pins the sets and adds a kotlin-reflect `sealedSubclasses` exhaustiveness test (replaces the lost compile-time forcing function). Note: the `hasRoute` adapter sliver is covered only by instrumented `AppShellTest` (red on CI — TASK-3679, risk atom attached).
- **File:** `android/app/src/main/kotlin/app/laughtrack/android/AppShell.kt:317-372`. `showsTopAppBar`/`showsBottomBar` exist twice (exhaustive `when(AppRoute)` vs hand-maintained `NavDestination.hasRoute` list); production uses the `NavDestination` versions, tests test the `AppRoute` versions — a new route can pass tests while shipping wrong chrome. Derive both from one canonical route-class set (e.g. `private val TOP_BAR_ROUTES = setOf(AppRoute.Favorites::class, ...)`); point `AppShellChromeTest.kt` at the shipping path. Don't rename `AppShell`'s public params (androidTest `AppShellTest.kt` uses them).
- **Effort:** S. **Verify:** `./gradlew :app:testDebugUnitTest`.

### T3.11 (AND-6) Gate the podcast playback ticker; lazy ExoPlayer
- **File:** `android/core/playback/.../PodcastPlaybackController.kt:34-67`. A `while(true) { publishState(); delay(500) }` wakes the main dispatcher every 500ms for process lifetime even if no podcast ever plays; ExoPlayer+MediaSession are built eagerly at `@Singleton` injection during `MainActivity.onCreate`.
- **Fix:** start the polling job in `play()`, cancel on `stop()`/`onIsPlayingChanged(false)` after a final publish. Make `player`/`mediaSession` `by lazy` — but first grep `PodcastPlaybackService`, `NowPlayingScreen`, `PodcastMiniPlayer` for direct `controller.player` access (`by lazy` keeps them source-compatible).
- **Gotchas:** ExoPlayer is thread-confined — the ticker must stay on `Dispatchers.Main.immediate`. Keep 500ms cadence *during* playback (mini-player seekbar).
- **Effort:** S–M. **Verify:** `./gradlew :core:playback:testDebugUnitTest`; manual: play podcast, background app, mini-player still updates.

### T3.12 (AND-8) Add LazyColumn item keys
- Keyless `items(...)`: `SearchScreen.kt:683` (paginated results — worst case), `HomeScreen.kt:499/519/539`, `ShowDetailScreen.kt:476`, `PodcastDetailScreen.kt:123`, `ComedianDetailScreen.kt:669`. Use `key = { it.id }` (clubs/podcasts/lineup) / `{ it.uuid }` (comedians) — **verify the field exists on the generated model in `core/network/.../generated/model/` first**; never edit generated models. Don't key the header/footer `item {}` blocks.
- **Effort:** S. **Verify:** compile + existing tests.

### T3.13 (WEB-6) Deduplicate `SHOW_SELECT` + DTO mappers
- **[Executed — TASK-3653, 2026-07-08]** Extracted `PUBLIC_SHOW_SELECT` + `buildShowSelect` + `mapShowRowToDTO` into `apps/web/lib/data/show/showSelect.ts`; search (`findShowsWithCount.ts`) and home (`findShowsForHome.ts`) now import it. Per-path DTO field parity preserved exactly (223 data-layer tests + tsc green). The still-duplicated `AVAILABLE_SHOW_WHERE` where-clause and the show-detail `findShowById` select were out of this task's scope — tracked as follow-ups.
- Near-identical select+map logic in `apps/web/lib/data/show/search/findShowsWithCount.ts:27-97,296-328` and `lib/data/home/findShowsForHome.ts:20-85,131-168` (plus the zip helper from T1.2). Extract `PUBLIC_SHOW_SELECT` + `mapShowRowToDTO` into `lib/data/show/showSelect.ts`; parameterize the real differences (search adds `favoriteComedians` when `profileId` present + `description`; home adds `getBestLineupImageUrl`). Field parity is consumed by iOS/Android — keep DTO shapes exact.
- **Effort:** M. **Verify:** `npx vitest run lib/data/show lib/data/home`.

### T3.14 (WEB-7 + WEB-10) Dead code + icon-dep pruning
- **[Partially executed — TASK-3654, 2026-07-08]** `ui/components/google/` deleted. **`ui/components/divider/` was NOT dead and is retained**: the zero-import-sites claim missed a relative import (`cards/show/index.tsx` imports `../../divider` and renders it) — do not re-attempt that deletion. Icon-dep pruning below is tracked as TASK-3688.
- Delete `apps/web/ui/components/divider/` and `ui/components/google/` (zero import sites; `GoogleAdsense` is an ad-script component with no callers). Scope the pre-delete grep to import paths, not the word "Divider"; check for `next/dynamic` string refs. Then replace the 3 `react-icons` + 3 `@radix-ui/react-icons` usages with lucide equivalents (match glyphs visually — names differ) and drop both deps; first confirm `@radix-ui/react-icons` isn't a peer of another radix package.
- **Effort:** S. **Verify:** `npx tsc --noEmit`; `npm run build`; `grep -rn "react-icons\|@radix-ui/react-icons" ui app` → nothing.

### T3.15 (AND-12) Move `UiState` from `core:data` to `core:ui`
- `core/data/.../UiState.kt` is a pure UI type forcing the design-system module to depend on the data layer (`core/ui/build.gradle.kts` declares `implementation(project(":core:data"))` solely for `UiStateContent.kt:15`). Move `UiState.kt`+`UiStateTest.kt` to `core:ui` (or new `core:model`), update ~20 imports, drop the module edge. One commit, nothing else in it (wide mechanical diff).
- **Effort:** S. **Verify:** `./gradlew assembleDebug testDebugUnitTest`.

---

## TIER 4 — Higher-risk or long-horizon work (needs care; some need user input)

### T4.1 (WEB-3) Rewrite `getTrendingComedians` correlated subqueries — **L, correctness-subtle**
- `apps/web/lib/data/home/getTrendingComedians.ts:71-153`: per-comedian correlated `COUNT`/`SUM`/`EXISTS` over `lineup_items ⋈ shows` with the zip `IN` list inlined 4×. Rewrite as one grouped join (`GROUP BY c.id`, `HAVING count > MIN_UPCOMING_SHOWS`), folding the alias-comedian rollup via `parent_comedian_id`.
- **Do T1.2 first** (shrinks the zip lists). **Before replacing:** add a fixture test (PGlite) asserting identical `show_count` per comedian old-vs-new — the alias rollup is easy to double-count or drop. Keep `Prisma.sql`/`Prisma.join` parameterization. `EXPLAIN ANALYZE` old vs new.

### T4.2 (WEB-4) Detail-page cache fragmentation — **L, design decision**
- Detail pages (`app/(entities)/(detail)/club/[name]/page.tsx:83-105` + comedian/show/podcast siblings) key `unstable_cache` on `userId`+`profileId`+raw `searchParams` JSON → per-user per-param 1-hour entries. Split into an anonymous param-whitelisted cached read + a per-user favorites overlay computed outside the cache.
- **Gotchas:** keep the coarse tag (e.g. `"club-detail-data"`) in `tags` — the scraper's `/api/revalidate` purges by it. Verify signed-in favorite markers still render. This changes SEO-surface caching — test signed-out and signed-in.

### T4.3 (WEB-12) Test the untested auth spine
- Per `apps/web/TEST_COVERAGE_AUDIT.md`: `auth.ts` 0%, `lib/auth/resolveAuth.ts` 0%, `app/actions/favorite.ts` 0%, `middleware.ts` auth branches untested, `app/api/unsubscribe/route.ts` 0%. Add in that order. Suite is mock-isolation-fragile (TASK-2534): `beforeEach` stubbing only, never module-level; never leave `global.fetch` stubbed; follow `apps/web/CONTRIBUTING.md` route-test patterns.
- **Verify:** `npx vitest run --coverage` — named files leave 0%.

### T4.4 (AND-9) Android ViewModel/repository tests
- Priority: (1) `SearchViewModelTest` (debounce, pivot switch, load-more, T1.5 cancellation), (2) `FavoritesRepositoryTest` (toggle→IOException→queued; 5xx→queued; 4xx→revert; `FavoritesRepository.kt:220-260`), (3) `ProfileViewModelTest`, (4) detail VMs. JVM tests only (fakes + `StandardTestDispatcher`, style of `HomeViewModelTest.kt` / `ComedianOnboardingViewModelTest.kt`); no Robolectric. `kotlinx-coroutines-test` 1.9.0 is in the catalog.

### T4.5 (AND-10) Replace deprecated `security-crypto` alpha token store
- `gradle/libs.versions.toml:22` pins `1.1.0-alpha06` (deprecated by Google, known Tink keyset-corruption crash reports); `EncryptedSharedPreferencesTokenStore.kt:12-21` constructs it eagerly on the main thread and a corrupted keyset **throws in the constructor** → crash loop.
- **Short-term (S):** wrap prefs init in `by lazy` + `runCatching`; on corruption, delete the prefs file and recreate (signs user out instead of crash-looping). **Long-term (M):** migrate to DataStore (already a dep) + Keystore AES cipher, with a read-then-write-then-delete migration. The `TokenStore` interface boundary keeps `AuthSessionManagerTest`/`RefreshTokenAuthenticatorTest` fakes valid.

### T4.6 (IOS-8) Swift 6 strict-concurrency, staged
- `Package.swift` is tools 5.9, no strict concurrency; 6 `@unchecked Sendable` classes (5 are T1.6's hand-rolled clients — **do T1.6 and T3.2 first**, most diagnostics then vanish). Enable per-target starting with `LaughTrackCore`; don't go repo-wide; don't bump the ios-libs pin as part of this (pin bumps need the 4-file recipe + `make -C ios check-ios-libs-pin`).

### T4.7 (IOS-9) HostedView skip-guard for iOS 26 sims — **read carefully**
- Zero skip markers exist; iOS 26.x sims silently fail 18 tests. Add a runtime probe in `HostedViewTestSupport.swift` (host a probe view; if the accessibility tree is empty → the regression) that skips with a clear message — **but gate it behind an env var** (e.g. `LAUGHTRACK_SKIP_HOSTEDVIEW_ON_BROKEN_WIRING=1`, local-only).
- **CRITICAL:** the `sim-tests-ios-26-watch` CI job (`.github/workflows/ios.yml:148`) is *designed to fail loudly*; its going green is the signal to drop the iOS 18 pin. An unconditional skip would blind that watcher. Never set the env var in the watch job.

### T4.8 (IOS-7 + WEB-9) Design-token sweeps (visual-risk, low urgency)
- iOS: `Color(red: 1.0, green: 0.78, blue: 0.24)` (marquee bulb) duplicated at `ClubsDiscoveryView.swift:164`, `HomeView.swift:2071`, `MarqueeHero.swift:540` → one token on `LaughTrackTokens` (`LaughTrackBridge/LaughTrackTheme.swift:245-257`); name the recurring ShowRow "ticket-stub" palette. Identical resolved values — don't "improve" colors; `LaughTrackThemeTests` asserts token values (extend, don't rename).
- Web: 73 raw `gray-*/neutral-*` utilities in 20 files; fix the user-facing ones first (`ui/pages/home/hero/`, `ui/pages/home/footer/`, `ui/components/cards/show/`, `ui/components/lineup/`, search calendar display), mapping each to the semantically right token (`border-subtle`, `surface`/`canvas`) — NOT a mechanical find-replace. Skip admin managers.

### T4.9 (SCR-9) Guard `sys.modules`-mutating tests (44 files)
- Add an autouse conftest fixture snapshotting `sys.modules` keys per test module and removing additions on teardown, or convert files to `monkeypatch.setitem`. Some stubs are deliberate session-scoped perf hacks (skipping playwright imports) — check intent per file; follow `apps/scraper/CONTRIBUTING.md`. Prove no order-dependence: run the suite twice.

### T4.10 (SCR-12) Import-layering ratchet
- 275 E402 late imports, many masking cycles; import-linter contracts intentionally loose. Add one contract at a time (first: `laughtrack.foundation` must not import `core`/`scrapers`), `make arch-lint`, fix, repeat. Moving imports to top level can change import-time side effects (dotenv/Logger) — smoke with `python -c "import laughtrack.app.cli"`.

### T4.11 Small remainders
- **(AND-11)** `android/app/.../push/PushNotifications.kt:122-135`: replace hand-rolled `HttpURLConnection` bitmap fetch with Coil (already a dep) + ~1024px size cap; keep 5s timeouts (FCM ~10s budget); it fetches CDN images — do NOT route through the generated client.
- **(IOS-11)** `HomeView.swift:1026` `UIScreen.main.bounds.width` → use the enclosing `GeometryReader` proxy; verify carousel page-snap on-sim (values differ in sheets).
- **(IOS-12)** `PodcastVisualEffects.swift:70`: `CADisplayLink(target: self)` retains the driver — use the weak-proxy pattern; preserve the Reduce Motion branch. **Don't touch** `AppBootstrap.swift:206` (intentional Sentry test-crash seam).
- **(IOS-10)** Optional: add a String Catalog (`Localizable.xcstrings`; `SWIFT_EMIT_LOC_STRINGS` is already YES). Tests assert exact copy — pure moves, no rewording; don't convert `accessibilityIdentifier` constants.
- **(WEB-8)** Admin managers (`AdminComedianManager.tsx` 3,037 lines etc.): split **only when a task touches them** — no speculative big-bang; tests are timeout/mock-sensitive; preserve asserted DOM structure.
- **(WEB-13)** `lib/rateLimit.ts:128-143` rightmost-XFF is correct **on Vercel** (x-real-ip preferred). No change unless self-hosting; never switch to leftmost XFF (spoofable).

---

## Do NOT touch (verified healthy — wasted effort or regression risk)

- **Web:** CSP/security headers in `middleware.ts`; Upstash rate limiting; refresh-token rotation with reuse-detection; admin auth + Zod `.strict()` + audit writes; Prisma indexing (129 declarations, hot paths covered); all raw SQL is parameterized; `lib/httpCache.ts` personalized-vs-shared CDN logic (carefully reasoned — leave it).
- **Scraper:** `ScrapeDiagnostics` contextvar side-channel and everything feeding `scraper_run_clubs`/Grafana; `BaseScraper` retry/rate-limit pipeline; `BrowserProfile` UA bundles, proxy pool; `app/cli.py` (clean 61-line dispatcher); migration guarding is mostly good already.
- **iOS:** force-unwrap hygiene (3 total, all constant URLs); `@MainActor` discipline on all 28 models; weak-self sink discipline; the generated-client CI gates; fonts (Gilroy already replaced by Urbanist).
- **Android:** generated-client boundary (drift check passes); auth/session stack (single-flight refresh, CSRF-nonced OAuth, fail-closed) — all tested; module graph (except T3.15); design-token values (verified 1:1 with iOS/web); deep-link dispatch (structured, tested); `runBlocking` in OkHttp interceptor/authenticator (standard pattern — leave).
- **Infra:** workflow path-gating; iOS 26 watcher design; Discord notify coverage (except grafana-provision); secrets hygiene; `python -m scripts.core.*` convention (consistently honored).

## Sequencing summary

- T1.6 (iOS client swap) → then IOS-5 cleanup → then T4.6 (Swift 6).
- T1.5 Part A → Part B (same commit is fine).
- T1.2 → T4.1. T1.3 (etix fix) → T3.8 (etix extraction).
- T2.4/T2.5 (untracking) after confirming the tree is otherwise clean (Task 0 done).
- Everything else is independent; keep one task per commit.
