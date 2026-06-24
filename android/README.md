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
│   ├── ui/             # Design system: theme tokens (mirrors iOS), Compose theme
│   ├── navigation/     # AppRoute model + LaughTrackDeepLink (laughtrack:// + FCM routing)
│   ├── network/        # OkHttp/Retrofit, generated OpenAPI client, AuthSessionManager
│   ├── data/           # Repositories, stores, offline queue, shared UiState
│   └── playback/       # Media3/ExoPlayer podcast playback controller
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

> The Android SDK is a separate prerequisite for `assembleDebug` and the
> `*UnitTest` tasks (`SDK location not found` if missing) — set `ANDROID_HOME`
> or `sdk.dir` in `local.properties`. The JDK setup above is what lets Gradle
> start at all; the OpenAPI drift check (`bin/check-openapi-regen-drift.sh`)
> needs only the JDK, no Android SDK.

```sh
cd android
./gradlew assembleDebug        # build the debug APK
./gradlew test                 # JVM unit tests
./gradlew ktlintCheck detekt   # lint + static analysis
./gradlew connectedCheck       # instrumented tests (needs an emulator/device)
```

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
its App Store Connect key out of the repo. Store/Play setup is TASK-3268; the
Fastlane release lane is TASK-3269.

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
