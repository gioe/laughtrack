package app.laughtrack.android

import android.content.Intent
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.Surface
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import app.laughtrack.android.core.navigation.AppRoute
import app.laughtrack.android.core.navigation.LaughTrackDeepLink
import app.laughtrack.android.core.ui.theme.LaughTrackTheme
import dagger.hilt.android.AndroidEntryPoint

/**
 * Single-Activity host for the Compose app shell. Extracts a deep-link
 * (`laughtrack://…` VIEW intent) or push-notification target from the launching
 * intent and hands it to [AppShell] to route. Subsequent links while running are
 * delivered via [onNewIntent]; both entry points are handled here.
 */
@AndroidEntryPoint
class MainActivity : ComponentActivity() {
    private var pendingRoute by mutableStateOf<AppRoute?>(null)

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        // Seed the deep-link/push route only on a fresh start. On a config-change
        // recreation Android re-delivers the original launch Intent, so re-deriving
        // here would yank the user back to the deep link after they'd navigated away.
        // Links arriving while running are handled by onNewIntent.
        if (savedInstanceState == null) {
            pendingRoute = routeFromIntent(intent)
        }
        setContent {
            LaughTrackTheme {
                Surface(modifier = Modifier.fillMaxSize()) {
                    AppShell(
                        pendingRoute = pendingRoute,
                        onRouteConsumed = { pendingRoute = null },
                    )
                }
            }
        }
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        setIntent(intent)
        routeFromIntent(intent)?.let { pendingRoute = it }
    }

    /** Resolve a route from a `laughtrack://` VIEW link or an FCM data payload in extras. */
    private fun routeFromIntent(intent: Intent?): AppRoute? {
        if (intent == null) return null
        intent.data?.toString()?.let { LaughTrackDeepLink.route(it)?.let { route -> return route } }
        // Push (FCM data message): consult only the keys we route on, not arbitrary
        // launcher-supplied extras (the activity is exported with a VIEW filter).
        val data = mapOf(
            "url" to intent.getStringExtra("url"),
            "showId" to intent.getStringExtra("showId"),
        )
        return LaughTrackDeepLink.routeFromPush(data)
    }
}
