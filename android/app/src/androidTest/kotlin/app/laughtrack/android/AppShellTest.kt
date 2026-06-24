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
 * Instrumented test for the app shell: the three tabs render, switching tabs
 * works, and opening a detail route pushes a detail screen. Runs in the emulator
 * CI job (the cycle-dedup + deep-link parsing logic itself is unit-tested in
 * :core:navigation).
 */
@RunWith(AndroidJUnit4::class)
class AppShellTest {
    @get:Rule
    val composeRule = createComposeRule()

    @Test
    fun renders_tabs_switches_and_opens_a_detail_route() {
        composeRule.setContent {
            LaughTrackTheme { AppShell() }
        }

        // Discover is the start tab; its content and the other tab labels render.
        composeRule.onNodeWithText("Comedy near you").assertIsDisplayed()
        composeRule.onNodeWithText("Favorites").assertIsDisplayed()

        // Switch to the Search tab and open the sample detail route.
        composeRule.onNodeWithText("Search").performClick()
        composeRule.onNodeWithText("Open a sample show").performClick()

        // The detail screen pushed onto the stack.
        composeRule.onNodeWithText("Show #1").assertIsDisplayed()
        composeRule.onNodeWithText("Back").assertIsDisplayed()
    }
}
