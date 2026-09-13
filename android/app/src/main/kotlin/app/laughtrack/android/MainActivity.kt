package app.laughtrack.android

import android.animation.Animator
import android.animation.AnimatorListenerAdapter
import android.animation.ObjectAnimator
import android.animation.ValueAnimator
import android.content.Intent
import android.os.Bundle
import android.view.View
import android.view.animation.DecelerateInterpolator
import androidx.activity.ComponentActivity
import androidx.activity.SystemBarStyle
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.Surface
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.core.splashscreen.SplashScreen.Companion.installSplashScreen
import androidx.core.splashscreen.SplashScreenViewProvider
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
import app.laughtrack.android.core.network.generated.model.MeResponse
import app.laughtrack.android.core.playback.PodcastPlaybackController
import app.laughtrack.android.core.ui.theme.LaughTrackTheme
import app.laughtrack.android.feature.onboarding.ui.ComedianOnboardingScreen
import app.laughtrack.android.push.PushNotifications
import app.laughtrack.android.push.PushTokenManager
import dagger.hilt.android.AndroidEntryPoint
import kotlinx.coroutines.Job
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

    private val launchHandoff = LaunchHandoff()
    private var splashExitAnimator: ObjectAnimator? = null
    private var splashOverlay: SplashScreenViewProvider? = null

    private var pendingRoute by mutableStateOf<AppRoute?>(null)
    private var pendingNavigationIntent: Intent? = null
    private val signedIn = mutableStateOf(false)
    private val showLoginPrompt = mutableStateOf(false)
    private var startupSession by mutableStateOf<StartupSessionState>(StartupSessionState.Loading)
    private lateinit var startupResolver: StartupSessionResolver
    private var authenticatedEffects: Job? = null
    private val hasResolvedFirstEntryChoice = mutableStateOf(false)
    private lateinit var firstEntryAuthChoiceStore: FirstEntryAuthChoiceStore

    override fun onCreate(savedInstanceState: Bundle?) {
        val splash = installSplashScreen()
        super.onCreate(savedInstanceState)
        splash.setKeepOnScreenCondition { launchHandoff.keepSplashVisible }
        splash.setOnExitAnimationListener(::animateSplashExit)
        enableEdgeToEdge(
            statusBarStyle = SystemBarStyle.dark(android.graphics.Color.TRANSPARENT),
            navigationBarStyle = SystemBarStyle.dark(android.graphics.Color.TRANSPARENT),
        )
        PushNotifications.ensureChannel(this)
        firstEntryAuthChoiceStore = FirstEntryAuthChoiceStore.create(this)
        hasResolvedFirstEntryChoice.value = firstEntryAuthChoiceStore.hasResolvedFirstEntryChoice
        startupResolver =
            StartupSessionResolver(
                scope = lifecycleScope,
                restoreSession = { authSessionManager.restoreSession() != null },
                getMe = authSessionManager::getMe,
            )
        restoreSession()
        // Seed deep-link routing / auth-callback handling only on a fresh start; a
        // config-change recreation re-delivers the launch Intent and must not
        // re-navigate or re-handle the original link (3258). onNewIntent covers
        // links arriving while running.
        if (savedInstanceState == null) {
            handleIntent(intent)
        } else {
            @Suppress("DEPRECATION")
            val savedNavigationIntent = savedInstanceState.getParcelable<Intent>(PENDING_NAVIGATION_INTENT)
            savedNavigationIntent?.let { handleIntent(it) }
        }
        setContent {
            LaughTrackTheme {
                val rootSurface = firstEntryRootSurface(startupSession, hasResolvedFirstEntryChoice.value)
                val hasPendingRoute = pendingRoute != null
                Surface(
                    modifier =
                        Modifier.fillMaxSize().launchDestinationLayout(
                            launchHandoff,
                            rootSurface,
                            hasPendingRoute,
                        ),
                ) {
                    FirstEntryRootContent(
                        surface = rootSurface,
                        onRetry = startupResolver::resolve,
                        authChoice = {
                            FirstEntryAuthChoiceScreen(
                                onContinueAsGuest = {
                                    firstEntryAuthChoiceStore.continueAsGuest()
                                    hasResolvedFirstEntryChoice.value = true
                                },
                            )
                        },
                        onboarding = {
                            ComedianOnboardingScreen(onComplete = startupResolver::completeOnboarding)
                        },
                        appShell = {
                            AppShell(
                                pendingRoute = pendingRoute,
                                onRouteConsumed = {
                                    pendingRoute = null
                                    pendingNavigationIntent = null
                                },
                                onNotificationPermissionResult = { granted ->
                                    analytics.logEvent(
                                        AnalyticsEvents.Push.OS_PROMPT_RESULT,
                                        mapOf(AnalyticsEvents.Push.Param.GRANTED to granted),
                                    )
                                },
                                signedIn = signedIn.value,
                                playbackController = playbackController,
                                showLoginPrompt = showLoginPrompt.value,
                                onLoginPromptDismiss = { loginPromptController.dismiss() },
                            )
                        },
                    )
                }
            }
        }
    }

    private fun animateSplashExit(provider: SplashScreenViewProvider) {
        splashOverlay = provider
        if (!ValueAnimator.areAnimatorsEnabled() || isDestroyed) {
            removeSplashOverlay()
            return
        }
        splashExitAnimator =
            ObjectAnimator.ofFloat(provider.view, View.ALPHA, 1f, 0f).apply {
                duration = 240L
                interpolator = DecelerateInterpolator()
                addListener(
                    object : AnimatorListenerAdapter() {
                        override fun onAnimationEnd(animation: Animator) = removeSplashOverlay()

                        override fun onAnimationCancel(animation: Animator) = removeSplashOverlay()
                    },
                )
                start()
            }
    }

    private fun removeSplashOverlay() {
        splashOverlay?.remove()
        splashOverlay = null
        splashExitAnimator = null
    }

    override fun onDestroy() {
        splashExitAnimator?.cancel()
        removeSplashOverlay()
        super.onDestroy()
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        setIntent(intent)
        handleIntent(intent)
    }

    override fun onSaveInstanceState(outState: Bundle) {
        pendingNavigationIntent?.let { outState.putParcelable(PENDING_NAVIGATION_INTENT, it) }
        super.onSaveInstanceState(outState)
    }

    /** Route an OAuth callback to the session manager, otherwise a nav deep-link to the shell. */
    private fun handleIntent(intent: Intent?) {
        val dataString = intent?.dataString
        if (dataString != null && AuthSessionManager.isAuthCallback(dataString)) {
            handleAuthRedirect(dataString)
        } else {
            routeFromIntent(intent)?.let {
                pendingRoute = it
                pendingNavigationIntent = intent
            }
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
            var previouslySignedIn = false
            authSessionManager.signedIn.collectLatest { isSignedIn ->
                val signingOut = previouslySignedIn && !isSignedIn
                previouslySignedIn = isSignedIn
                signedIn.value = isSignedIn
                // A completed sign-in resolves any open prompt.
                if (isSignedIn) {
                    firstEntryAuthChoiceStore.markSignedIn()
                    hasResolvedFirstEntryChoice.value = true
                    loginPromptController.dismiss()
                }
                // Keep the shared Library snapshot aligned with auth so its content is
                // ready whenever the permanent Library destination is opened.
                if (!isSignedIn) {
                    authenticatedEffects?.cancel()
                    if (signingOut) startupResolver.signedOut()
                    favoritesRepository.resetSignedOut()
                    currentUserState.reset()
                }
            }
        }
        lifecycleScope.launch {
            var identifiedUserId: String? = null
            startupResolver.state.collectLatest { state ->
                startupSession = state
                when (state) {
                    is StartupSessionState.Authenticated -> {
                        signedIn.value = true
                        firstEntryAuthChoiceStore.markSignedIn()
                        hasResolvedFirstEntryChoice.value = true
                        applyCurrentUser(state.response)
                        if (identifiedUserId != state.response.data.userId) {
                            identifiedUserId = state.response.data.userId
                            // Destination resolution must not wait for push registration.
                            authenticatedEffects?.cancel()
                            authenticatedEffects =
                                lifecycleScope.launch {
                                    launch { pushTokenManager.syncCurrentToken() }
                                    launch { favoritesRepository.refreshSignedInFavorites() }
                                }
                        }
                    }
                    StartupSessionState.SignedOut -> {
                        authenticatedEffects?.cancel()
                        signedIn.value = false
                        identifiedUserId = null
                    }
                    else -> Unit
                }
            }
        }
        startupResolver.resolve()
    }

    private fun handleAuthRedirect(callbackUrl: String) {
        lifecycleScope.launch {
            when (authSessionManager.handleCallback(callbackUrl)) {
                is AuthCallbackResult.Authenticated -> {
                    firstEntryAuthChoiceStore.markSignedIn()
                    hasResolvedFirstEntryChoice.value = true
                    startupResolver.resolve()
                }
                is AuthCallbackResult.Error -> Unit
                AuthCallbackResult.Ignored -> Unit
            }
        }
    }

    private fun applyCurrentUser(response: MeResponse) {
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
    }

    private companion object {
        const val PENDING_NAVIGATION_INTENT = "pending-navigation-intent"
    }
}
