package app.laughtrack.android

import androidx.activity.ComponentActivity
import dagger.hilt.android.AndroidEntryPoint

/**
 * Empty `@AndroidEntryPoint` host activity for `@HiltAndroidTest` Compose UI
 * tests. `createAndroidComposeRule<HiltTestActivity>()` launches it and the test
 * calls `setContent { ... }` on it, so Hilt-backed composables resolve their
 * `hiltViewModel()` against the test graph.
 *
 * Lives in the **debug** source set (not androidTest) and is declared in
 * `src/debug/AndroidManifest.xml`, so it is registered under the app-under-test
 * package (`…android.debug`) rather than the test package (`…android.debug.test`).
 * The instrumentation runs in the app-under-test process; launching a test-APK
 * activity from there fails with "Intent resolved to different process" because
 * the two APKs have different package IDs/UIDs. Hosting the activity in the debug
 * APK keeps it in the same process as the instrumentation.
 */
@AndroidEntryPoint
class HiltTestActivity : ComponentActivity()
