package app.laughtrack.android

import android.content.Intent
import android.net.Uri
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.browser.customtabs.CustomTabsIntent
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.Surface
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.lifecycle.lifecycleScope
import app.laughtrack.android.core.navigation.AppRoute
import app.laughtrack.android.core.navigation.LaughTrackDeepLink
import app.laughtrack.android.core.network.auth.AuthCallbackResult
import app.laughtrack.android.core.network.auth.AuthProvider
import app.laughtrack.android.core.network.auth.AuthSessionManager
import app.laughtrack.android.core.ui.theme.LaughTrackTheme
import dagger.hilt.android.AndroidEntryPoint
import kotlinx.coroutines.launch
import javax.inject.Inject

/**
 * Single-Activity host for the Compose app shell. The launching/`onNewIntent`
 * intent is dispatched two ways: a `laughtrack://auth/callback` OAuth redirect is
 * consumed by [AuthSessionManager]; any other `laughtrack://…` VIEW link (or FCM
 * push payload) is parsed into an [AppRoute] and handed to [AppShell] to navigate.
 * Sign-in/out controls are surfaced on the Profile destination of the shell.
 */
@AndroidEntryPoint
class MainActivity : ComponentActivity() {
    @Inject
    lateinit var authSessionManager: AuthSessionManager

    private var pendingRoute by mutableStateOf<AppRoute?>(null)
    private val authStatus = mutableStateOf("Signed out")

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        // Seed deep-link routing / auth-callback handling only on a fresh start; a
        // config-change recreation re-delivers the launch Intent and must not
        // re-navigate or re-handle the original link (3258). onNewIntent covers
        // links arriving while running.
        if (savedInstanceState == null) {
            handleIntent(intent)
        }
        restoreSession()
        setContent {
            LaughTrackTheme {
                Surface(modifier = Modifier.fillMaxSize()) {
                    AppShell(
                        pendingRoute = pendingRoute,
                        onRouteConsumed = { pendingRoute = null },
                        authStatus = authStatus.value,
                        onGoogleSignIn = { launchAuth(AuthProvider.GOOGLE) },
                        onAppleSignIn = { launchAuth(AuthProvider.APPLE) },
                        onSignOut = { signOut() },
                        onDeleteAccount = { deleteAccount() },
                    )
                }
            }
        }
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        setIntent(intent)
        handleIntent(intent)
    }

    /** Route an OAuth callback to the session manager, otherwise a nav deep-link to the shell. */
    private fun handleIntent(intent: Intent?) {
        val dataString = intent?.dataString
        if (dataString != null && AuthSessionManager.isAuthCallback(dataString)) {
            handleAuthRedirect(dataString)
        } else {
            routeFromIntent(intent)?.let { pendingRoute = it }
        }
    }

    /** Resolve a nav route from a `laughtrack://` VIEW link or an FCM data payload in extras. */
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

    private fun restoreSession() {
        lifecycleScope.launch {
            authSessionManager.restoreSession()
            refreshSignedInUser()
        }
    }

    private fun launchAuth(provider: AuthProvider) {
        CustomTabsIntent.Builder()
            .build()
            .launchUrl(this, Uri.parse(authSessionManager.buildSignInUrl(provider)))
    }

    private fun handleAuthRedirect(callbackUrl: String) {
        lifecycleScope.launch {
            when (val result = authSessionManager.handleCallback(callbackUrl)) {
                is AuthCallbackResult.Authenticated -> refreshSignedInUser()
                is AuthCallbackResult.Error -> authStatus.value = "Sign-in failed: ${result.code}"
                AuthCallbackResult.Ignored -> Unit
            }
        }
    }

    private suspend fun refreshSignedInUser() {
        authStatus.value = authSessionManager.getMe()
            .fold(
                onSuccess = { response -> "Signed in as ${response.data.email}" },
                onFailure = { "Signed out" },
            )
    }

    private fun signOut() {
        lifecycleScope.launch {
            val revoked = authSessionManager.signOut()
            authStatus.value = if (revoked) "Signed out" else "Signed out locally"
        }
    }

    private fun deleteAccount() {
        lifecycleScope.launch {
            val deleted = authSessionManager.deleteAccount()
            authStatus.value = if (deleted) "Account deleted" else "Delete failed"
        }
    }
}
