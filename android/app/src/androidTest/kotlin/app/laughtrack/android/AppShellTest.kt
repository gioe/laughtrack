package app.laughtrack.android

import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import app.laughtrack.android.core.ui.theme.LaughTrackTheme
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import androidx.test.ext.junit.runners.AndroidJUnit4

/**
 * Instrumented test for the app shell: the three tabs render and switching tabs
 * works. Switches to Favorites (a Hilt-free placeholder); the Search tab now hosts
 * the DI-backed real screen, so it's exercised by its own feature tests rather
 * than here. Cycle-dedup + deep-link parsing are unit-tested in :core:navigation.
 */
@RunWith(AndroidJUnit4::class)
class AppShellTest {
    @get:Rule
    val composeRule = createComposeRule()

    @Test
    fun renders_tabs_and_switches_to_a_placeholder_tab() {
        composeRule.setContent {
            LaughTrackTheme { AppShell() }
        }

        // Discover is the start tab; its content and the other tab labels render.
        composeRule.onNodeWithText("Comedy near you").assertIsDisplayed()
        composeRule.onNodeWithText("Search").assertIsDisplayed()
        composeRule.onNodeWithText("Favorites").assertIsDisplayed()

        // Switching to the Favorites placeholder tab renders its body.
        composeRule.onNodeWithText("Favorites").performClick()
        composeRule.onNodeWithText("Coming soon.").assertIsDisplayed()
    }
}
