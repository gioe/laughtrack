package app.laughtrack.android

import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onNodeWithContentDescription
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import app.laughtrack.android.core.ui.theme.LaughTrackTheme
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import androidx.test.ext.junit.runners.AndroidJUnit4

/**
 * Instrumented test for the app shell: the three tabs render and profile-menu
 * actions are discoverable. Search/Favorites/Profile/Notifications host
 * DI-backed screens (hiltViewModel), which can't render under the Hilt-free
 * AppShell() harness. Route parsing remains unit-tested in :core:navigation.
 */
@RunWith(AndroidJUnit4::class)
class AppShellTest {
    @get:Rule
    val composeRule = createComposeRule()

    @Test
    fun renders_tabs_and_profile_menu_actions() {
        composeRule.setContent {
            LaughTrackTheme { AppShell() }
        }

        // Discover is the start tab; its content and the other tab labels render.
        composeRule.onNodeWithText("Comedy near you").assertIsDisplayed()
        composeRule.onNodeWithText("Search").assertIsDisplayed()
        composeRule.onNodeWithText("Favorites").assertIsDisplayed()

        // Keep the Hilt-free shell harness focused on chrome/menu behavior.
        composeRule.onNodeWithContentDescription("Profile menu").performClick()
        composeRule.onNodeWithText("Profile").assertIsDisplayed()
        composeRule.onNodeWithText("Notifications").assertIsDisplayed()
    }
}
