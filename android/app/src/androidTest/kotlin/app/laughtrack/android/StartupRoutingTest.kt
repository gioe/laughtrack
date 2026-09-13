package app.laughtrack.android

import android.graphics.Bitmap
import androidx.compose.material3.Button
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.ui.graphics.asAndroidBitmap
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.captureToImage
import androidx.compose.ui.test.junit4.createAndroidComposeRule
import androidx.compose.ui.test.onNodeWithTag
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.onRoot
import androidx.compose.ui.test.performClick
import androidx.navigation.NavDestination.Companion.hasRoute
import androidx.navigation.NavHostController
import androidx.navigation.compose.rememberNavController
import androidx.test.platform.app.InstrumentationRegistry
import app.laughtrack.android.core.navigation.AppRoute
import app.laughtrack.android.core.network.generated.model.MeData
import app.laughtrack.android.core.network.generated.model.MeResponse
import app.laughtrack.android.core.ui.theme.LaughTrackTheme
import dagger.hilt.android.testing.HiltAndroidRule
import dagger.hilt.android.testing.HiltAndroidTest
import kotlinx.coroutines.CompletableDeferred
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Rule
import org.junit.Test
import java.io.File
import java.io.IOException

/** Exercises the production root selector while explicitly holding the destination-bearing response. */
@HiltAndroidTest
class StartupRoutingTest {
    @get:Rule(order = 0)
    val hiltRule = HiltAndroidRule(this)

    @get:Rule(order = 1)
    val composeRule = createAndroidComposeRule<HiltTestActivity>()

    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.Main.immediate)
    private var shellMounts = 0
    private val pendingRoute = mutableStateOf<AppRoute?>(null)
    private lateinit var navController: NavHostController

    @After
    fun cancelResolution() {
        composeRule.runOnIdle { scope.cancel() }
    }

    @Test
    fun delayed_onboarding_never_mounts_shell_and_preserves_pending_deep_link() {
        val response = CompletableDeferred<Result<MeResponse>>()
        pendingRoute.value = AppRoute.ShowDetail(1)
        val resolver = showRoot(getMe = { response.await() })
        assertShellNeverMounted()
        capture("delayed-current-user")

        composeRule.runOnIdle { response.complete(Result.success(me(onboarded = false))) }
        composeRule.onNodeWithText("Complete onboarding").assertIsDisplayed()
        assertShellNeverMounted()
        composeRule.runOnIdle { assertEquals(AppRoute.ShowDetail(1), pendingRoute.value) }

        composeRule.onNodeWithText("Complete onboarding").performClick()
        composeRule.runOnIdle {
            assertTrue(
                (resolver.state.value as StartupSessionState.Authenticated).response.data.comedianOnboardingCompleted,
            )
            assertEquals(1, shellMounts)
            assertNull(pendingRoute.value)
            assertTrue(navController.currentDestination?.hasRoute<AppRoute.ShowDetail>() == true)
            assertTrue(navController.popBackStack())
        }
        composeRule.onNodeWithText("Search").assertIsDisplayed()
        composeRule.onNodeWithText("Library").assertIsDisplayed()
    }

    @Test
    fun delayed_completed_account_reveals_home_only_after_current_user_resolves() {
        val response = CompletableDeferred<Result<MeResponse>>()
        showRoot(getMe = { response.await() })
        assertShellNeverMounted()
        composeRule.onNodeWithTag("startup-loading").assertIsDisplayed()
        composeRule.runOnIdle { response.complete(Result.success(me(onboarded = true))) }
        composeRule.onNodeWithText("Search").assertIsDisplayed()
        composeRule.onNodeWithText("Library").assertIsDisplayed()
        composeRule.runOnIdle { assertEquals(1, shellMounts) }
        capture("resolved-home")
    }

    @Test
    fun signed_out_first_entry_opens_shell_only_after_guest_choice() {
        showRoot(restoreSession = { false }, getMe = { error("Signed-out users must not request current user") })
        composeRule.onNodeWithText("Continue as guest").assertIsDisplayed()
        assertShellNeverMounted()
        composeRule.onNodeWithText("Continue as guest").performClick()
        composeRule.onNodeWithText("Search").assertIsDisplayed()
        composeRule.runOnIdle { assertEquals(1, shellMounts) }
    }

    @Test
    fun failed_current_user_keeps_shell_hidden_and_retry_resolves_destination() {
        val response = CompletableDeferred<Result<MeResponse>>()
        var requests = 0
        showRoot(getMe = {
            requests++
            if (requests == 1) Result.failure(IOException("Offline")) else response.await()
        })
        composeRule.onNodeWithTag("startup-recovery").assertIsDisplayed()
        assertShellNeverMounted()
        capture("recoverable-current-user-failure")
        composeRule.onNodeWithText("Retry").performClick()
        composeRule.onNodeWithTag("startup-loading").assertIsDisplayed()
        assertShellNeverMounted()
        composeRule.runOnIdle { response.complete(Result.success(me(onboarded = false))) }
        composeRule.onNodeWithText("Complete onboarding").assertIsDisplayed()
        assertShellNeverMounted()
        composeRule.runOnIdle { assertEquals(2, requests) }
    }

    private fun showRoot(
        restoreSession: suspend () -> Boolean = { true },
        getMe: suspend () -> Result<MeResponse>,
    ): StartupSessionResolver {
        hiltRule.inject()
        val resolver = StartupSessionResolver(scope, restoreSession, getMe)
        val guestChoice = mutableStateOf(false)
        composeRule.runOnIdle { resolver.resolve() }
        composeRule.setContent {
            val session by resolver.state.collectAsState()
            LaughTrackTheme {
                Surface {
                    FirstEntryRootContent(
                        surface = firstEntryRootSurface(session, guestChoice.value),
                        onRetry = resolver::resolve,
                        authChoice = {
                            Button(onClick = { guestChoice.value = true }) { Text("Continue as guest") }
                        },
                        onboarding = {
                            Button(onClick = resolver::completeOnboarding) { Text("Complete onboarding") }
                        },
                        appShell = {
                            DisposableEffect(Unit) {
                                shellMounts++
                                onDispose { }
                            }
                            navController = rememberNavController()
                            AppShell(
                                navController = navController,
                                signedIn = session is StartupSessionState.Authenticated,
                                pendingRoute = pendingRoute.value,
                                onRouteConsumed = { pendingRoute.value = null },
                            )
                        },
                    )
                }
            }
        }
        return resolver
    }

    private fun assertShellNeverMounted() {
        composeRule.onNodeWithText("Search").assertDoesNotExist()
        composeRule.onNodeWithText("Library").assertDoesNotExist()
        composeRule.runOnIdle { assertEquals(0, shellMounts) }
    }

    private fun capture(name: String) {
        val context = InstrumentationRegistry.getInstrumentation().targetContext
        val directory = File(context.filesDir, "startup-routing").apply { mkdirs() }
        val bitmap = composeRule.onRoot().captureToImage().asAndroidBitmap()
        File(directory, "$name.png").outputStream().use { bitmap.compress(Bitmap.CompressFormat.PNG, 100, it) }
    }

    private fun me(onboarded: Boolean) =
        MeResponse(
            MeData(
                userId = "startup-routing-test",
                email = "startup@example.invalid",
                isAdmin = false,
                emailShowNotifications = false,
                pushShowNotifications = false,
                comedianOnboardingCompleted = onboarded,
                zipCode = null,
                nearbyDistanceMiles = null,
            ),
        )
}
