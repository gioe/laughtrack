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
 * Instrumented test for the app shell chrome: the three tabs render and the
 * profile-menu actions are discoverable.
 *
 * Runs under a Hilt test harness ([HiltAndroidTest] + [HiltAndroidRule] +
 * [HiltTestActivity] via [HiltTestRunner]) rather than a bare `AppShell()`, so it
 * survives any destination — including the always-rendered Discover start screen —
 * becoming `hiltViewModel()`-backed. It asserts only destination-independent
 * shell chrome (tab labels, top-bar title, profile-menu items) and never depends
 * on a particular destination still being a Hilt-free "Coming soon" placeholder,
 * which is what broke the previous bare-harness version repeatedly (TASK-3280).
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
            LaughTrackTheme { AppShell() }
        }

        // Always-present shell chrome: the top-bar title and the three tab labels.
        composeRule.onNodeWithText("LaughTrack").assertIsDisplayed()
        composeRule.onNodeWithText("Discover").assertIsDisplayed()
        composeRule.onNodeWithText("Search").assertIsDisplayed()
        composeRule.onNodeWithText("Favorites").assertIsDisplayed()

        // The profile menu exposes the Profile + Notifications actions (these are
        // dropdown labels, not navigated screens, so no destination is rendered).
        composeRule.onNodeWithContentDescription("Profile menu").performClick()
        composeRule.onNodeWithText("Profile").assertIsDisplayed()
        composeRule.onNodeWithText("Notifications").assertIsDisplayed()
    }
}
