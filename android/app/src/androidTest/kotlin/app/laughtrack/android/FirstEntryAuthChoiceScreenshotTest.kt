package app.laughtrack.android

import android.os.SystemClock
import androidx.compose.ui.test.hasContentDescription
import androidx.compose.ui.test.hasTestTag
import androidx.compose.ui.test.hasText
import androidx.compose.ui.test.junit4.createAndroidComposeRule
import androidx.test.platform.app.InstrumentationRegistry
import app.laughtrack.android.core.ui.theme.LaughTrackTheme
import dagger.hilt.android.testing.HiltAndroidRule
import dagger.hilt.android.testing.HiltAndroidTest
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Rule
import org.junit.Test
import tools.fastlane.screengrab.Screengrab
import tools.fastlane.screengrab.UiAutomatorScreenshotStrategy
import tools.fastlane.screengrab.locale.LocaleTestRule

/** Focused, live-data-independent capture for the first-entry auth parity scenario. */
@HiltAndroidTest
class FirstEntryAuthChoiceScreenshotTest {
    @get:Rule(order = 0)
    val hiltRule = HiltAndroidRule(this)

    @get:Rule(order = 1)
    val localeRule = LocaleTestRule()

    @get:Rule(order = 2)
    val composeRule = createAndroidComposeRule<HiltTestActivity>()

    @Before
    fun setUp() {
        hiltRule.inject()
        Screengrab.setDefaultScreenshotStrategy(UiAutomatorScreenshotStrategy())
        val automation = InstrumentationRegistry.getInstrumentation().uiAutomation
        automation.executeShellCommand("am broadcast -a com.android.systemui.demo -e command exit").close()
        SystemClock.sleep(500)
        listOf(
            "am broadcast -a com.android.systemui.demo -e command clock -e hhmm 0941",
            "am broadcast -a com.android.systemui.demo -e command notifications -e visible false",
            "am broadcast -a com.android.systemui.demo -e command network -e mobile hide",
            "am broadcast -a com.android.systemui.demo -e command network -e wifi show -e level 4 -e fully true",
            "am broadcast -a com.android.systemui.demo -e command battery -e level 100 -e plugged false",
        ).forEach { command -> automation.executeShellCommand(command).close() }
        SystemClock.sleep(300)
    }

    @Test
    fun captureFirstEntryAuthChoice() {
        composeRule.setContent {
            LaughTrackTheme {
                FirstEntryAuthChoiceScreen(onContinueAsGuest = {})
            }
        }

        composeRule.waitUntil(timeoutMillis = 20_000) {
            composeRule.onAllNodes(hasTestTag(FIRST_ENTRY_AUTH_CHOICE_TEST_TAG)).fetchSemanticsNodes().isNotEmpty()
        }
        composeRule.onNode(hasContentDescription(FIRST_ENTRY_BRAND_LOGO_CONTENT_DESCRIPTION)).assertExists()

        val orderedLabels =
            listOf(
                "Continue as guest",
                "Continue with Apple",
                "Continue with Google",
                "Email me a sign-in link",
            )
        val topPositions =
            orderedLabels.map { label ->
                composeRule.onNode(hasText(label)).assertExists().fetchSemanticsNode().boundsInRoot.top
            }
        assertEquals("First-entry actions should retain the cross-platform order", topPositions.sorted(), topPositions)

        composeRule.waitForIdle()
        // Match the proven full-catalog harness: allow the committed Compose frame to reach
        // SurfaceFlinger before UiAutomator captures the whole display.
        SystemClock.sleep(250)
        composeRule.waitForIdle()
        val renderedFrame = InstrumentationRegistry.getInstrumentation().uiAutomation.takeScreenshot()
        val interiorLuminances =
            listOf(
                renderedFrame.width / 4 to renderedFrame.height / 4,
                renderedFrame.width / 2 to renderedFrame.height / 4,
                renderedFrame.width * 3 / 4 to renderedFrame.height / 4,
                renderedFrame.width / 4 to renderedFrame.height / 2,
                renderedFrame.width * 3 / 4 to renderedFrame.height / 2,
            ).map { (x, y) ->
                val pixel = renderedFrame.getPixel(x, y)
                (
                    android.graphics.Color.red(pixel) +
                        android.graphics.Color.green(pixel) +
                        android.graphics.Color.blue(pixel)
                ) / 3
            }
        assertTrue("Focused screenshot frame must contain the dark auth surface", interiorLuminances.any { it < 128 })
        Screengrab.screenshot("19_FirstEntryAuthChoice")
    }
}
