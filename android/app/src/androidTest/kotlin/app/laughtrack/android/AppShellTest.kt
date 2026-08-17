package app.laughtrack.android

import androidx.compose.ui.test.assertCountEquals
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.junit4.createAndroidComposeRule
import androidx.compose.ui.test.onAllNodesWithText
import androidx.compose.ui.test.onNodeWithContentDescription
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import androidx.test.platform.app.InstrumentationRegistry
import app.laughtrack.android.core.playback.PodcastPlaybackController
import app.laughtrack.android.core.playback.PodcastPlaybackItem
import app.laughtrack.android.core.ui.theme.LaughTrackTheme
import dagger.hilt.android.testing.HiltAndroidRule
import dagger.hilt.android.testing.HiltAndroidTest
import org.junit.Rule
import org.junit.Test

/**
 * Instrumented test for the app shell chrome, asserting the chrome the
 * shipping [AppShellChrome] NavDestination predicates actually produce:
 * root tabs hide the shell top bar (the "LaughTrack" title bar only appears
 * on topAppBarRoutes members like Library), and the three top-level destinations
 * remain available regardless of authentication or Library contents.
 * This is the only coverage of the AppShellChrome.hasRoute adapters — unit
 * tests pin the canonical route sets but cannot build typed NavDestinations
 * without Robolectric — so keep both the bar-shown (Library) and
 * bar-absent (Discover) assertions here.
 *
 * Runs under a Hilt test harness ([HiltAndroidTest] + [HiltAndroidRule] +
 * [HiltTestActivity] via [HiltTestRunner]) rather than a bare `AppShell()`
 * activity, so it survives any destination — including the always-rendered
 * Discover start screen — being `hiltViewModel()`-backed (TASK-3280).
 * Route parsing remains unit-tested in :core:navigation.
 */
@HiltAndroidTest
class AppShellTest {
    @get:Rule(order = 0)
    val hiltRule = HiltAndroidRule(this)

    @get:Rule(order = 1)
    val composeRule = createAndroidComposeRule<HiltTestActivity>()

    @Test
    fun renders_tabs_and_profile_menu_actions() {
        hiltRule.inject()
        composeRule.setContent {
            LaughTrackTheme { AppShell(signedIn = true) }
        }

        // Root-tab chrome on the Discover start screen: the bottom bar shows
        // Search and Library; the Discover tab label is intentionally not asserted
        // because the Discover/Home screen also renders a "Discover" headline,
        // so onNodeWithText would match two nodes. The shell top bar must be
        // ABSENT here — Discover owns its own chrome (not in topAppBarRoutes).
        composeRule.onNodeWithText("Search").assertIsDisplayed()
        composeRule.onNodeWithText("Library").assertIsDisplayed()
        composeRule.onNodeWithText("LaughTrack").assertDoesNotExist()

        // Navigate to Library — a topAppBarRoutes member — via its tab. The
        // shell top bar appears (the shipping showsTopAppBar hasRoute path)
        // and exposes the Profile + Notifications actions (dropdown labels,
        // not navigated screens, so no extra destination is rendered).
        composeRule.onNodeWithText("Library").performClick()
        composeRule.onNodeWithText("LaughTrack").assertIsDisplayed()
        composeRule.onNodeWithContentDescription("Profile menu").performClick()
        composeRule.onNodeWithText("Profile").assertIsDisplayed()
        composeRule.onNodeWithText("Notifications").assertIsDisplayed()
    }

    @Test
    fun library_tab_is_visible_for_signed_out_users() {
        hiltRule.inject()
        composeRule.setContent {
            LaughTrackTheme { AppShell() }
        }

        // Signed-out users retain the same top-level hierarchy; Library owns its
        // guest state rather than disappearing from navigation.
        composeRule.onNodeWithText("Search").assertIsDisplayed()
        composeRule.onNodeWithText("Library").assertIsDisplayed()

        // The account menu uses its authenticated-only notification slot to
        // invite guests to create an account instead.
        composeRule.onNodeWithText("Library").performClick()
        composeRule.onNodeWithContentDescription("Profile menu").performClick()
        composeRule.onNodeWithText("Sign up or sign in").assertIsDisplayed()
        composeRule.onNodeWithText("Notifications").assertDoesNotExist()
    }

    @Test
    fun expanded_now_playing_hides_shell_top_bar_and_mini_player() {
        hiltRule.inject()
        val episodeTitle = "Now Playing chrome test"
        val playbackController =
            PodcastPlaybackController(InstrumentationRegistry.getInstrumentation().targetContext)
        playbackController.seedForScreenshot(
            PodcastPlaybackItem(
                episodeId = -1,
                podcastId = -1,
                podcastTitle = "Test podcast",
                episodeTitle = episodeTitle,
                audioUrl = "https://example.invalid/test.mp3",
                artworkUrl = null,
            ),
        )
        composeRule.setContent {
            LaughTrackTheme { AppShell(playbackController = playbackController) }
        }

        composeRule.onNodeWithText(episodeTitle).assertIsDisplayed().performClick()
        composeRule.onNodeWithContentDescription("Sleep timer").assertIsDisplayed()

        composeRule.onNodeWithContentDescription("Profile menu").assertDoesNotExist()
        composeRule.onAllNodesWithText(episodeTitle).assertCountEquals(1)
        composeRule.runOnIdle { playbackController.stop() }
    }
}
