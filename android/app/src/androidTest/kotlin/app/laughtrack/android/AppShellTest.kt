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
 * navigation works. Search/Favorites/Notifications now host DI-backed screens
 * (hiltViewModel), which can't render under the Hilt-free AppShell() harness, so
 * this navigates to the profile-menu Profile surface (ProfileAuthScreen — a plain
 * Composable). Route parsing remains unit-tested in :core:navigation.
 */
@RunWith(AndroidJUnit4::class)
class AppShellTest {
    @get:Rule
    val composeRule = createComposeRule()

    @Test
    fun renders_tabs_and_opens_profile_surface() {
        composeRule.setContent {
            LaughTrackTheme { AppShell() }
        }

        // Discover is the start tab; its content and the other tab labels render.
        composeRule.onNodeWithText("Comedy near you").assertIsDisplayed()
        composeRule.onNodeWithText("Search").assertIsDisplayed()
        composeRule.onNodeWithText("Favorites").assertIsDisplayed()

        // Open the Hilt-free Profile surface from the profile menu.
        composeRule.onNodeWithContentDescription("Profile menu").performClick()
        composeRule.onNodeWithText("Profile").performClick()
        composeRule.onNodeWithText("Account").assertIsDisplayed()
        composeRule.onNodeWithText("Continue with Google").assertIsDisplayed()
    }
}
