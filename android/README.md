# LaughTrack — Android client

Native Android app mirroring the iOS app (`ios/`). Both clients render the same
domain (shows, clubs, comedians, podcasts) and consume the same Next.js
`/api/v1` backend. This directory is the Android sibling of `ios/`.

## Stack

- **Language / UI:** Kotlin + Jetpack Compose (Material 3), dark-only theme
- **DI:** Hilt
- **Networking:** OkHttp + Retrofit, with a Kotlin client generated from the
  shared OpenAPI spec (`ios/Sources/LaughTrackAPIClient/openapi.json`) — wired in
  TASK-3256
- **Images:** Coil · **Playback:** Media3/ExoPlayer · **Storage:** DataStore +
  EncryptedSharedPreferences · **Background:** WorkManager
- **Analytics/crash:** Firebase Analytics + FCM, Sentry
- **Build:** Gradle (KTS) + version catalog (`gradle/libs.versions.toml`)
- **minSdk 26, compileSdk/targetSdk 35**

## Module layout

```
android/
├── app/                # Application + MainActivity (intent dispatch), AppShell, DI host
├── core/
│   ├── ui/             # Design system: theme tokens (mirrors iOS), Compose theme, shared UiState
│   ├── navigation/     # AppRoute model + LaughTrackDeepLink (laughtrack:// + FCM routing)
│   ├── network/        # OkHttp/Retrofit, generated OpenAPI client, AuthSessionManager
│   ├── data/           # Repositories, stores, offline queue, runCatchingCancellable
│   ├── playback/       # Media3/ExoPlayer podcast playback controller
│   ├── analytics/      # Analytics events + AnalyticsManager
│   └── testing/        # Shared JVM test fixtures (throwingApi, signed-out FavoritesRepository)
└── feature/
    ├── home/           # Discover/Home rails + location header
    ├── search/         # Search across shows, clubs, comedians
    ├── library/        # Favorites / saved entities
    ├── detail/         # Show / club / comedian / podcast detail
    ├── onboarding/     # First-run onboarding
    ├── notifications/  # Notification center
    └── profile/        # Profile + settings (location, toggles, sign-out)
```

These `:core:*` and `:feature:*` modules are all included in
`settings.gradle.kts` and ship today; individual feature surfaces continue to be
built out under their own tasks (e.g. Home rails in TASK-3259, Profile in
TASK-3266).

### API-provider pattern

Each feature module owns a Hilt `@Module` that provides the generated API
services it needs from `core:network`'s configured `ApiClient` via
`apiClient.createService(...)`. The `ApiClient` (with its auth interceptor) is the
single shared, configured client — feature modules never construct their own
Retrofit/OkHttp stack. Example — `feature/search`'s `SearchApiModule`:

```kotlin
@Module
@InstallIn(SingletonComponent::class)
object SearchApiModule {
    @Provides @Singleton
    fun provideShowsApi(apiClient: ApiClient): ShowsApi =
        apiClient.createService(ShowsApi::class.java)
}
```

## Auth & deep links

`MainActivity.handleIntent` dispatches every launch / `onNewIntent` intent two
ways:

- A `laughtrack://auth/callback` OAuth redirect (matched by
  `AuthSessionManager.isAuthCallback`) is consumed by **`AuthSessionManager`**
  (`core:network`) to complete sign-in.
- Any other `laughtrack://…` VIEW link, or an FCM push data payload, is parsed
  into an `AppRoute` by **`LaughTrackDeepLink`** (`core:navigation`) and handed to
  `AppShell` to navigate.

Auth callbacks are handled fresh-start only (a config-change recreation
re-delivers the launch intent and must not re-navigate).

## Design tokens

`core/ui` theme tokens are mirrored 1:1 from the iOS design system
(`ios/Sources/LaughTrackBridge/LaughTrackTheme.swift`) and `apps/web`
(`tailwind.config.ts`): canvas `#121212`, surface scale, copper `accent-strong`
`#CD6837`. A color change in any one client must be reflected in the other two.

## Building

### Prerequisites: JDK 17

This client builds and tests on **JDK 17** — every module pins
`sourceCompatibility`/`targetCompatibility = VERSION_17` and `jvmTarget = "17"`,
and CI (`.github/workflows/android.yml`) provisions **Temurin 17** for the
assemble/test/lint and OpenAPI-drift jobs. Use a JDK 17 distribution locally;
newer JDKs are not validated against AGP 8.7.3 / Gradle 8.11.1 and may break the
build.

`JAVA_HOME` must point at a real JDK 17 home before you run `./gradlew`. The
macOS system stub at `/usr/bin/java` is **not** a JDK — Gradle (and the
OpenAPI regen scripts) fail at Java-runtime discovery with "Unable to locate a
Java Runtime" if `JAVA_HOME` is unset and no JDK is on `PATH`. Fresh task
worktrees inherit the shell environment, not any project-local Java config, so
`JAVA_HOME` has to be exported in the shell that runs Gradle.

**macOS (Homebrew):**

```sh
brew install openjdk@17
# openjdk@17 is keg-only, so export JAVA_HOME at the brew-managed home:
export JAVA_HOME="$(brew --prefix openjdk@17)/libexec/openjdk.jdk/Contents/Home"
# (optional) make /usr/libexec/java_home -v 17 resolve it too:
sudo ln -sfn "$(brew --prefix openjdk@17)/libexec/openjdk.jdk" \
  /Library/Java/JavaVirtualMachines/openjdk-17.jdk
```

Add the `export JAVA_HOME=…` line to your shell profile (or set it per-session)
so every worktree picks it up. Verify with `java -version` (should report
`17.x`) before building.

### Prerequisites: Android SDK

Gradle also needs an Android SDK for `assembleDebug` and `*UnitTest` tasks. A
missing SDK fails before tests run with `SDK location not found`. CI provisions
the SDK with `android-actions/setup-android@v3`; local checkouts should use the
same command-line SDK layout.

**macOS command-line setup:**

```sh
mkdir -p "$HOME/Library/Android/sdk/cmdline-tools"
cd "$HOME/Library/Android/sdk/cmdline-tools"
curl -L -o commandlinetools-mac.zip \
  https://dl.google.com/android/repository/commandlinetools-mac-14742923_latest.zip
unzip commandlinetools-mac.zip
rm commandlinetools-mac.zip
mv cmdline-tools latest

export ANDROID_HOME="$HOME/Library/Android/sdk"
export PATH="$ANDROID_HOME/cmdline-tools/latest/bin:$ANDROID_HOME/platform-tools:$PATH"
yes | sdkmanager --licenses
sdkmanager "platform-tools" "platforms;android-35" "build-tools;35.0.0"
```

Add the `ANDROID_HOME` and `PATH` exports to your shell profile so fresh task
worktrees inherit them. Alternatively, keep SDK discovery project-local by
creating `android/local.properties` in each worktree:

```properties
sdk.dir=/Users/<you>/Library/Android/sdk
```

`local.properties` is ignored and must not be committed. The project targets
`compileSdk`/`targetSdk` **35**, requires Android build-tools **35.0.0**, and
keeps `minSdk` **26**. `connectedCheck` additionally needs a running emulator or
physical device; JVM unit tests such as `:core:network:testDebugUnitTest` do not.

The JDK setup above is what lets Gradle start at all; the OpenAPI drift check
(`bin/check-openapi-regen-drift.sh`) needs only the JDK, no Android SDK.

```sh
cd android
./gradlew assembleDebug        # build the debug APK
./gradlew test                 # JVM unit tests
./gradlew ktlintCheck detekt   # lint + static analysis
./gradlew connectedCheck       # instrumented tests (needs an emulator/device)
```

CI (`.github/workflows/android.yml`, path-gated on `android/**`) runs the
instrumented suites on every push/PR via `reactivecircus/android-emulator-runner`
(API 34, x86_64, KVM-accelerated `ubuntu-latest`): the job targets
`:core:ui:connectedDebugAndroidTest` (RemoteImageFallbackTest) and then
`:app:connectedDebugAndroidTest` explicitly — never project-wide, because
runner-less modules crash the legacy instrumentation runner. Whole-job runtime
is **~7 minutes** (≈2 min emulator boot + ≈5 min build-and-test); add new
modules to the job's `script` as they gain androidTest sources. Note the jobs
run post-merge (main merges bypass required checks), so a red run alerts
Discord rather than blocking the push.

### Tusk commit/merge test gate for `android/**`

Commits that touch **only** `android/**` resolve to an Android-specific Tusk
test gate (`path_test_commands["android/**"]` in `tusk/config.json`) instead of
the global scraper/web `test_command` — it runs `./gradlew testDebugUnitTest`
from `android/`. A commit that mixes `android/**` with another subtree (e.g. a
web or `apps/**` file) matches no single pattern and falls through to the global
command, so split Android-only changes into their own commit to get the Android
gate.

The gate **degrades gracefully** instead of failing with a cryptic Gradle error
when prerequisites are missing — it prints a `[tusk android gate] SKIPPED: …`
message pointing back here and exits 0:

- **No working JDK 17** — `JAVA_HOME` is unset (or points at the macOS
  `/usr/bin/java` stub) and no real JDK is on `PATH`. Set `JAVA_HOME` per
  *Prerequisites: JDK 17* above.
- **No Android SDK** — none of `android/local.properties`, `ANDROID_HOME`, or
  `ANDROID_SDK_ROOT` is configured (`testDebugUnitTest` would otherwise fail with
  `SDK location not found`).

With both prerequisites present the gate runs the unit tests for real. CI
(`.github/workflows/android.yml`) provisions JDK 17 + SDK and is the
authoritative gate; the local skip only keeps a missing local toolchain from
blocking an unrelated Android commit.

> **Gradle wrapper jar:** `gradle/wrapper/gradle-wrapper.jar` is a binary and is
> generated, not authored. On first checkout run `gradle wrapper` once (or open
> the project in Android Studio, which generates it automatically) so `./gradlew`
> can bootstrap. Everything else (wrapper scripts, properties pinned to Gradle
> 8.11.1) is committed.

## Secrets & signing

Never commit signing material or `google-services.json` (see `.gitignore`).
Play upload key + service-account JSON live in CI secrets, mirroring how iOS keeps
its App Store Connect key out of the repo. Store/Play setup is TASK-3268.

## Release (Fastlane + Play)

Distribution to Google Play is automated with [Fastlane](https://fastlane.tools)
`supply`, mirroring the iOS setup. The config lives in `android/fastlane/`
(`Fastfile`, `Appfile`) and runs through bundler (`android/Gemfile`).

**Versioning.** `gradle.properties` is the single source of truth, splitting the
user-facing marketing version from the Play build number (the same split as
`ios/project.yml`'s `MARKETING_VERSION` / `CURRENT_PROJECT_VERSION`):

- `VERSION_NAME` — semantic `MAJOR.MINOR.PATCH` shown to users.
- `VERSION_CODE` — monotonically-increasing integer Play requires per upload.

`app/build.gradle.kts` reads both and honours `-PVERSION_CODE=…` / `-PVERSION_NAME=…`
overrides. The `bump_build_number` lane sets `VERSION_CODE` to
`max(highest code already on Play, current) + 1`, so the build number can never
collide with or regress below what Play has seen.

**Lanes** (run from `android/`):

```sh
bundle install                              # one-time: install fastlane
bundle exec fastlane internal               # bump code, build signed AAB, upload to the internal track
bundle exec fastlane internal bump:minor    # also raise VERSION_NAME (patch|minor|major)
bundle exec fastlane production rollout:0.1  # refresh the full listing, then promote (staged 10%)
bundle exec fastlane test                   # unit tests + ktlint + detekt (parity with iOS `test`)
```

**Store-listing metadata.** The English Play listing is version-controlled under
`fastlane/metadata/android/en-US/`: `title.txt`, `short_description.txt`, and
`full_description.txt`. Release notes are collected from commit subjects formatted as
`[release] Customer-facing change`, then written to the version-code-specific
`changelogs/<versionCode>.txt` file that `supply` expects. When a release has no marked
commits, the lane uses a safe bug-fixes-and-performance fallback instead of exposing
task IDs or implementation details.

```sh
bundle exec fastlane generate_release_notes version_code:42 # generate only
bundle exec fastlane upload_metadata version_code:42        # generate + upload text/changelog
```

The `production` lane performs both automatically before promotion. The `internal`
lane intentionally skips all listing metadata for a fast test-track upload.

**Store-listing screenshots.** The nine canonical scenarios are captured for phone,
7-inch tablet, and 10-inch tablet profiles the same way iOS generates its App Store
set — an instrumented UI test captures them and `supply` uploads curated Play-safe
subsets, rather than managing them by hand in the Play Console:

```sh
bundle exec fastlane screenshots            # starts an available AVD if needed, then builds/captures
bundle exec fastlane upload_screenshots     # supply pushes the captured images (no binary)
bundle exec fastlane screenshots_and_upload # both in one step (mirrors the iOS lane)
```

The `production` lane regenerates the complete 27-image matrix and uploads the curated
Play-safe subsets together with the listing text and release notes before promoting the
validated internal build, matching the iOS `beta` / `release` split.

- **Capture** uses a connected Android device when one is available; otherwise the
  lane starts the first local `LaughTrack*` AVD (or the first available AVD) and waits
  for it to boot. It still requires Android SDK tooling and at least one configured AVD.
  `capture_android_screenshots` (fastlane screengrab, configured by
  `fastlane/Screengrabfile`) drives
  `AppStoreScreenshotTest` (`app/src/androidTest/`), which walks the real `AppShell`
  through the nine screens (Near Me → Search {Shows,Comedians,Clubs,Podcasts} →
  Club/Show/Comedian/Podcast detail) by Compose semantics.
- **Determinism.** The Near Me rail is pinned to Hollywood (90028) by a Hilt
  `@TestInstallIn` fake `HomeLocationResolver` (`FakeHomeLocationModule`, from the
  isolated `HomeLocationModule`) that returns `90028` unconditionally; the test
  pre-grants location and taps *Use location* to route through it, so captures never
  leak the runner's geo-IP. Result data comes from the production `/api/v1` backend,
  so the exact shows vary run to run.
- **Output** lands under the `phoneScreenshots/`, `sevenInchScreenshots/`, and
  `tenInchScreenshots/` directories below
  `fastlane/metadata/android/<locale>/images/`. Every profile uses the same stable
  scenario filenames; the upload lane stages the Play-safe phone and tablet subsets
  before `supply` reads them. `internal` still skips images to keep binary uploads fast.
- **Inspecting captures locally.** `./gradlew connectedDebugAndroidTest` uninstalls
  the app afterward, wiping screengrab output. To keep the PNGs, run the instrumentation
  directly (no uninstall) and pull them, after disabling animations:
  ```sh
  adb shell settings put global window_animation_scale 0    # + transition_/animator_ variants
  adb shell am instrument -w -e class app.laughtrack.android.AppStoreScreenshotTest \
    app.laughtrack.android.debug.test/app.laughtrack.android.HiltTestRunner
  adb exec-out run-as app.laughtrack.android.debug \
    cat /data/user/0/app.laughtrack.android.debug/app_screengrab/en-US/images/screenshots/01_NearMe.png > 01_NearMe.png
  ```
  See `tusk conventions search "HiltTestActivity screengrab"` for the full set of
  Compose-instrumented-test gotchas.

**Signing.** The release build type is signed with the Play **upload key**. Locally,
provide either an `app/keystore.properties` file (`storeFile`, `storePassword`,
`keyAlias`, `keyPassword`) or the `ANDROID_KEYSTORE_PATH` / `ANDROID_KEYSTORE_PASSWORD`
/ `ANDROID_KEY_ALIAS` env vars (see `fastlane/.env.example`). When no material is
present the release build configures unsigned, so `assembleRelease` still works for
a contributor without the key.

**CI.** `.github/workflows/android-release.yml` is a `workflow_dispatch` job (pick a
track + optional marketing bump). It decodes the keystore and writes the
service-account JSON from these repo secrets (provisioned in TASK-3268), then runs
the matching lane:

| Secret | Used for |
| --- | --- |
| `PLAY_SERVICE_ACCOUNT_JSON` | `supply` auth to the Play Developer API |
| `ANDROID_UPLOAD_KEYSTORE_B64` | base64 of the upload keystore, decoded at build time |
| `ANDROID_KEYSTORE_PASSWORD` | keystore + key password |
| `ANDROID_KEY_ALIAS` | key alias (`upload`) |

## OpenAPI client regeneration

The Kotlin client under
`core/network/src/main/kotlin/app/laughtrack/android/core/network/generated/`
(`api/`, `model/`, `infrastructure/`) is **generated and committed**, produced by
openapi-generator 7.11.0 (kotlin / retrofit2 / kotlinx-serialization) from the
shared spec `ios/Sources/LaughTrackAPIClient/openapi.json`. Do not hand-edit
generated sources.

```sh
android/bin/regen-openapi.sh            # regenerate from openapi.json (JDK 17+; pins the generator jar)
android/bin/check-openapi-regen-drift.sh # CI guard: committed client must match a clean regen
```

After any `/api/v1` spec edit, run `regen-openapi.sh`, review the diff, and commit
the regenerated sources **in the same PR as the spec change**. The
drift check (the Android mirror of `ios/bin/check-openapi-regen-drift.sh`) fails
when the committed client lags the spec, so a spec edit that skips the Android
regen is caught rather than silently stranding the app behind the server
contract.

## Cross-client parity

Per the repo convention: any `/api/v1` change must regenerate **both** the iOS and
Android generated clients in the same PR (see convention #220). The OpenAPI spec
in `ios/Sources/LaughTrackAPIClient/openapi.json` is the single source of truth.

Play **store-listing screenshots** are also at parity with iOS: both clients generate
their listing screenshots from an instrumented UI test and upload them via fastlane
(`screenshots` / `upload_screenshots` here, `snapshot` / `deliver` on iOS) rather than
managing them by hand in the store console — see **Store-listing screenshots** above.
