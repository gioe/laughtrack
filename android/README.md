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

Requires JDK 17+ and the Android SDK (set `ANDROID_HOME` / `local.properties`).

```sh
cd android
./gradlew assembleDebug        # build the debug APK
./gradlew test                 # JVM unit tests
./gradlew ktlintCheck detekt   # lint + static analysis
./gradlew connectedCheck       # instrumented tests (needs an emulator/device)
```

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
