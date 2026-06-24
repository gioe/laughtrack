package app.laughtrack.android

import androidx.activity.ComponentActivity
import dagger.hilt.android.AndroidEntryPoint

/**
 * Empty `@AndroidEntryPoint` host activity for `@HiltAndroidTest` Compose UI
 * tests. `createAndroidComposeRule<HiltTestActivity>()` launches it and the test
 * calls `setContent { ... }` on it, so Hilt-backed composables resolve their
 * `hiltViewModel()` against the test graph. Declared in the androidTest manifest.
 */
@AndroidEntryPoint
class HiltTestActivity : ComponentActivity()
