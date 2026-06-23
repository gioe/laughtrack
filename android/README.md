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
├── app/                # Application + MainActivity, manifest, launcher, DI host
├── core/
│   ├── ui/             # Design system: theme tokens (mirrors iOS), Compose theme
│   ├── network/        # OkHttp/Retrofit + generated OpenAPI client (later tasks)
│   └── data/           # Repositories, stores, offline queue, shared UiState
└── feature/
    └── home/           # Discover/Home (placeholder; real rails in TASK-3259)
```

Feature surfaces (search, favorites, detail, playback, notifications, onboarding,
profile) land as additional `:feature:*` modules in their own tasks.

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

## Cross-client parity

Per the repo convention: any `/api/v1` change must regenerate **both** the iOS and
Android generated clients in the same PR (see convention #220). The OpenAPI spec
in `ios/Sources/LaughTrackAPIClient/openapi.json` is the single source of truth.
