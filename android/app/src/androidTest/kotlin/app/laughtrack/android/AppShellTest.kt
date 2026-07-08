package app.laughtrack.android

import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.junit4.createAndroidComposeRule
import androidx.compose.ui.test.onNodeWithContentDescription
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import app.laughtrack.android.core.ui.theme.LaughTrackTheme
import dagger.hilt.android.testing.HiltAndroidRule
import dagger.hilt.android.testing.HiltAndroidTest
import org.junit.Rule
import org.junit.Test

/**
 * Instrumented test for the app shell chrome, asserting the chrome the
 * shipping [AppShellChrome] NavDestination predicates actually produce:
 * root tabs hide the shell top bar (the "LaughTrack" title bar only appears
 * on topAppBarRoutes members like Favorites), and the Favorites tab is gated
 * on signedIn + hasFavorites (TASK-3302, mirroring iOS showFavoritesTab).
 * This is the only coverage of the AppShellChrome.hasRoute adapters — unit
 * tests pin the canonical route sets but cannot build typed NavDestinations
 * without Robolectric — so keep both the bar-shown (Favorites) and
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
            LaughTrackTheme { AppShell(signedIn = true, hasFavorites = true) }
        }

        // Root-tab chrome on the Discover start screen: the bottom bar shows
        // Search and Favorites (signed-in with favorites, so the gated tab is
        // present); the Discover tab label is intentionally not asserted
        // because the Discover/Home screen also renders a "Discover" headline,
        // so onNodeWithText would match two nodes. The shell top bar must be
        // ABSENT here — Discover owns its own chrome (not in topAppBarRoutes).
        composeRule.onNodeWithText("Search").assertIsDisplayed()
        composeRule.onNodeWithText("Favorites").assertIsDisplayed()
        composeRule.onNodeWithText("LaughTrack").assertDoesNotExist()

        // Navigate to Favorites — a topAppBarRoutes member — via its tab. The
        // shell top bar appears (the shipping showsTopAppBar hasRoute path)
        // and exposes the Profile + Notifications actions (dropdown labels,
        // not navigated screens, so no extra destination is rendered).
        composeRule.onNodeWithText("Favorites").performClick()
        composeRule.onNodeWithText("LaughTrack").assertIsDisplayed()
        composeRule.onNodeWithContentDescription("Profile menu").performClick()
        composeRule.onNodeWithText("Profile").assertIsDisplayed()
        composeRule.onNodeWithText("Notifications").assertIsDisplayed()
    }

    @Test
    fun favorites_tab_is_hidden_for_signed_out_users() {
        hiltRule.inject()
        composeRule.setContent {
            LaughTrackTheme { AppShell() }
        }

        // Default params are signed-out with no favorites: the Favorites tab
        // must not exist anywhere in the tree (TASK-3302 gating), while the
        // ungated Search tab renders normally.
        composeRule.onNodeWithText("Search").assertIsDisplayed()
        composeRule.onNodeWithText("Favorites").assertDoesNotExist()
    }
}
