package app.laughtrack.android

import android.Manifest
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.SystemBarStyle
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.Surface
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.core.content.ContextCompat
import androidx.lifecycle.lifecycleScope
import app.laughtrack.android.core.analytics.AnalyticsEvents
import app.laughtrack.android.core.analytics.AnalyticsManager
import app.laughtrack.android.core.data.auth.CurrentUserState
import app.laughtrack.android.core.data.auth.LoginPromptController
import app.laughtrack.android.core.data.favorites.FavoritesRepository
import app.laughtrack.android.core.navigation.AppRoute
import app.laughtrack.android.core.navigation.LaughTrackDeepLink
import app.laughtrack.android.core.network.auth.AuthCallbackResult
import app.laughtrack.android.core.network.auth.AuthSessionManager
import app.laughtrack.android.core.playback.PodcastPlaybackController
import app.laughtrack.android.core.ui.theme.LaughTrackTheme
import app.laughtrack.android.push.PushNotifications
import app.laughtrack.android.push.PushTokenManager
import dagger.hilt.android.AndroidEntryPoint
import kotlinx.coroutines.flow.collectLatest
import kotlinx.coroutines.launch
import javax.inject.Inject

/**
 * Single-Activity host for the Compose app shell. The launching/`onNewIntent`
 * intent is dispatched two ways: a `laughtrack://auth/callback` OAuth redirect is
 * consumed by [AuthSessionManager]; any other `laughtrack://…` VIEW link (or FCM
 * push payload) is parsed into an [AppRoute] and handed to [AppShell] to navigate.
 * Sign-in controls are surfaced on the Profile destination of the shell.
 */
@AndroidEntryPoint
class MainActivity : ComponentActivity() {
    @Inject
    lateinit var authSessionManager: AuthSessionManager

    @Inject
    lateinit var playbackController: PodcastPlaybackController

    @Inject
    lateinit var pushTokenManager: PushTokenManager

    @Inject
    lateinit var analytics: AnalyticsManager

    @Inject
    lateinit var favoritesRepository: FavoritesRepository

    @Inject
    lateinit var loginPromptController: LoginPromptController

    @Inject
    lateinit var currentUserState: CurrentUserState

    private var pendingRoute by mutableStateOf<AppRoute?>(null)
    private val signedIn = mutableStateOf(false)
    private val showLoginPrompt = mutableStateOf(false)
    private val sessionRestoreCompleted = mutableStateOf(false)
    private val hasResolvedFirstEntryChoice = mutableStateOf(false)
    private lateinit var firstEntryAuthChoiceStore: FirstEntryAuthChoiceStore

    // POST_NOTIFICATIONS runtime prompt (Android 13+). Registered at construction
    // so it is available before the activity is STARTED. Logs the OS-prompt result
    // to the push funnel (iOS push_os_prompt_result parity).
    private val requestNotificationPermission =
        registerForActivityResult(ActivityResultContracts.RequestPermission()) { granted ->
            analytics.logEvent(
                AnalyticsEvents.Push.OS_PROMPT_RESULT,
                mapOf(AnalyticsEvents.Push.Param.GRANTED to granted),
            )
        }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge(
            statusBarStyle = SystemBarStyle.dark(android.graphics.Color.TRANSPARENT),
            navigationBarStyle = SystemBarStyle.dark(android.graphics.Color.TRANSPARENT),
        )
        PushNotifications.ensureChannel(this)
        firstEntryAuthChoiceStore = FirstEntryAuthChoiceStore.create(this)
        hasResolvedFirstEntryChoice.value = firstEntryAuthChoiceStore.hasResolvedFirstEntryChoice
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
                    when (
                        firstEntryRootSurface(
                            sessionRestoreCompleted = sessionRestoreCompleted.value,
                            signedIn = signedIn.value,
                            hasResolvedFirstEntryChoice = hasResolvedFirstEntryChoice.value,
                        )
                    ) {
                        FirstEntryRootSurface.Loading -> FirstEntryLoadingScreen()
                        FirstEntryRootSurface.AuthChoice ->
                            FirstEntryAuthChoiceScreen(
                                onContinueAsGuest = {
                                    firstEntryAuthChoiceStore.continueAsGuest()
                                    hasResolvedFirstEntryChoice.value = true
                                },
                            )
                        FirstEntryRootSurface.AppShell ->
                            AppShell(
                                pendingRoute = pendingRoute,
                                onRouteConsumed = { pendingRoute = null },
                                signedIn = signedIn.value,
                                playbackController = playbackController,
                                showLoginPrompt = showLoginPrompt.value,
                                onLoginPromptDismiss = { loginPromptController.dismiss() },
                            )
                    }
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
        val data =
            mapOf(
                "url" to intent.getStringExtra("url"),
                "showId" to intent.getStringExtra("showId"),
                "route" to intent.getStringExtra("route"),
                "showIds" to intent.getStringExtra("showIds"),
            )
        return LaughTrackDeepLink.routeFromPush(data)
    }

    private fun restoreSession() {
        // Present the sign-in prompt whenever a gated action requests it.
        lifecycleScope.launch {
            loginPromptController.visible.collectLatest { showLoginPrompt.value = it }
        }
        lifecycleScope.launch {
            authSessionManager.signedIn.collectLatest { isSignedIn ->
                signedIn.value = isSignedIn
                // A completed sign-in resolves any open prompt.
                if (isSignedIn) {
                    firstEntryAuthChoiceStore.markSignedIn()
                    hasResolvedFirstEntryChoice.value = true
                    loginPromptController.dismiss()
                }
                // Keep the shared Library snapshot aligned with auth so its content is
                // ready whenever the permanent Library destination is opened.
                if (isSignedIn) {
                    favoritesRepository.refreshSignedInFavorites()
                } else {
                    favoritesRepository.resetSignedOut()
                    currentUserState.reset()
                }
            }
        }
        lifecycleScope.launch { refreshSignedInUser() }
    }

    private fun handleAuthRedirect(callbackUrl: String) {
        lifecycleScope.launch {
            when (authSessionManager.handleCallback(callbackUrl)) {
                is AuthCallbackResult.Authenticated -> {
                    firstEntryAuthChoiceStore.markSignedIn()
                    hasResolvedFirstEntryChoice.value = true
                    refreshSignedInUser()
                }
                is AuthCallbackResult.Error -> signedIn.value = false
                AuthCallbackResult.Ignored -> Unit
            }
        }
    }

    private suspend fun refreshSignedInUser() {
        val hasSession = authSessionManager.restoreSession() != null
        signedIn.value = hasSession
        if (hasSession) {
            firstEntryAuthChoiceStore.markSignedIn()
            hasResolvedFirstEntryChoice.value = true
        }
        sessionRestoreCompleted.value = true
        if (!hasSession) return

        // Sync the FCM token while authenticated (no-ops without a Firebase
        // project), and prompt for the notification permission on Android 13+.
        maybeRequestNotificationPermission()
        pushTokenManager.syncCurrentToken()
        authSessionManager.getMe().onSuccess { response ->
            // Cache the admin role so admin-only UI (the Show-ID badge) can gate on it
            // without re-fetching /me per screen.
            currentUserState.setAdmin(response.data.isAdmin)
            // Set the analytics identity from the server-issued userId (no email-hash
            // fallback) + cross-client cohort properties.
            analytics.identify(
                userId = response.data.userId,
                onboardingCompleted = response.data.comedianOnboardingCompleted,
                hasZip = response.data.zipCode?.isNotBlank() == true,
            )
            if (!response.data.comedianOnboardingCompleted) {
                pendingRoute = AppRoute.ComedianOnboarding
            }
        }
    }

    private fun maybeRequestNotificationPermission() {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.TIRAMISU) return
        val granted =
            ContextCompat.checkSelfPermission(
                this,
                Manifest.permission.POST_NOTIFICATIONS,
            ) == PackageManager.PERMISSION_GRANTED
        if (!granted) requestNotificationPermission.launch(Manifest.permission.POST_NOTIFICATIONS)
    }
}
