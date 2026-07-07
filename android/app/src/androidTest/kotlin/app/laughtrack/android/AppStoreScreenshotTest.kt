package app.laughtrack.android

import android.Manifest
import androidx.compose.ui.test.SemanticsMatcher
import androidx.compose.ui.test.hasContentDescription
import androidx.compose.ui.test.hasTestTag
import androidx.compose.ui.test.hasText
import androidx.compose.ui.test.junit4.createAndroidComposeRule
import androidx.compose.ui.test.onFirst
import androidx.compose.ui.test.onNodeWithContentDescription
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import androidx.test.platform.app.InstrumentationRegistry
import app.laughtrack.android.core.ui.theme.LaughTrackTheme
import app.laughtrack.android.feature.detail.ui.components.DETAIL_LOADING_TEST_TAG
import app.laughtrack.android.feature.search.ui.SEARCH_RESULT_ROW_TEST_TAG
import dagger.hilt.android.testing.HiltAndroidRule
import dagger.hilt.android.testing.HiltAndroidTest
import org.junit.Before
import org.junit.Rule
import org.junit.Test
import tools.fastlane.screengrab.Screengrab
import tools.fastlane.screengrab.UiAutomatorScreenshotStrategy
import tools.fastlane.screengrab.locale.LocaleTestRule

/**
 * Captures the nine Google Play listing screenshots, mirroring the iOS
 * AppStoreScreenshotTests.swift set (ios/Tests/LaughTrackUITests). Driven by
 * fastlane screengrab via the `screenshots` lane (wired in TASK-3617); run it on a
 * booted emulator/device.
 *
 * Navigation is driven by Compose semantics (tab contentDescriptions, pivot-chip
 * text, and the SEARCH_RESULT_ROW_TEST_TAG on result rows), NOT hardcoded screen
 * coordinates like the iOS test — the Android accessibility tree is queryable, so
 * this survives layout changes.
 *
 * Determinism: the Near Me rail is pinned to Hollywood (90028) by tapping "Use
 * location", which routes through the FakeHomeLocationResolver installed by
 * FakeHomeLocationModule (TASK-3615). The fake returns 90028 unconditionally, so
 * this does not depend on the emulator's GPS/permission/geo-IP. (The resolver is
 * only consulted from useDeviceLocation(), never on the initial zip=null load —
 * hence the explicit tap.)
 *
 * Result data comes from the production /api/v1 backend, so the exact shows/clubs
 * shown vary run to run; the flow only assumes at least one result exists per pivot.
 */
@HiltAndroidTest
class AppStoreScreenshotTest {
    @get:Rule(order = 0)
    val hiltRule = HiltAndroidRule(this)

    @get:Rule(order = 1)
    val localeRule = LocaleTestRule()

    // Renders the real AppShell under the empty HiltTestActivity rather than launching
    // MainActivity — the proven Compose-UI-test harness (AppShellTest / TASK-3280).
    // MainActivity's own setContent path is not reliably surfaced to the test's Compose
    // hierarchy (auth/deeplink launch logic), which yields "No compose hierarchies found".
    @get:Rule(order = 2)
    val composeRule = createAndroidComposeRule<HiltTestActivity>()

    @Before
    fun setUp() {
        hiltRule.inject()
        Screengrab.setDefaultScreenshotStrategy(UiAutomatorScreenshotStrategy())
        // Pre-grant location so tapping "Use location" calls the ViewModel directly
        // instead of launching the system permission dialog (which would destroy the
        // test activity). The FakeHomeLocationResolver still short-circuits GPS and
        // returns 90028 — the grant only keeps the in-app permission check happy.
        val instrumentation = InstrumentationRegistry.getInstrumentation()
        val pkg = instrumentation.targetContext.packageName
        listOf(
            Manifest.permission.ACCESS_FINE_LOCATION,
            Manifest.permission.ACCESS_COARSE_LOCATION,
        ).forEach { instrumentation.uiAutomation.grantRuntimePermission(pkg, it) }
    }

    @Test
    fun captureAppStoreScreenshots() {
        composeRule.setContent {
            LaughTrackTheme { AppShell() }
        }

        // 01 — Near Me. Trigger use-device-location so the fake resolver (90028)
        // drives the Discover feed, then wait for the LA feed to resolve.
        waitFor(hasText("Use location"))
        composeRule.onNodeWithText("Use location").performClick()
        waitFor(
            hasText("Near ", substring = true) or hasText("90028", substring = true),
            timeoutMs = 30_000,
        )
        settle()
        Screengrab.screenshot("01_NearMe")

        // 02 — Search / Shows (the default pivot). The Search tab's contentDescription
        // lives on the icon, which NavigationBarItem merges under its label Text — so
        // it only resolves in the unmerged tree. Clicking the icon node still triggers
        // the item's onClick.
        composeRule.onNode(hasContentDescription("Search"), useUnmergedTree = true).performClick()
        waitForResults()
        settle()
        Screengrab.screenshot("02_SearchShows")

        // 03 — Search / Comedians. Pivot chips render their label uppercased.
        selectPivot("COMEDIANS")
        settle()
        Screengrab.screenshot("03_SearchComedians")

        // 04 — Search / Clubs.
        selectPivot("CLUBS")
        settle()
        Screengrab.screenshot("04_SearchClubs")

        // 05 — Club detail (open the first Clubs result, capture, return).
        openFirstResult()
        Screengrab.screenshot("05_ClubDetail")
        goBack()

        // 06 — Show detail (Shows pivot → first result).
        selectPivot("SHOWS")
        openFirstResult()
        Screengrab.screenshot("06_ShowDetail")
        goBack()

        // 07 — Comedian detail.
        selectPivot("COMEDIANS")
        openFirstResult()
        Screengrab.screenshot("07_ComedianDetail")
        goBack()

        // 08 — Search / Podcasts.
        selectPivot("PODCASTS")
        settle()
        Screengrab.screenshot("08_SearchPodcasts")

        // 09 — Podcast detail.
        openFirstResult()
        Screengrab.screenshot("09_PodcastDetail")
    }

    /** Select a search pivot by its uppercased chip label and wait for its results. */
    private fun selectPivot(label: String) {
        composeRule.onNodeWithText(label).performClick()
        waitForResults()
    }

    /** Tap the first search result row and wait for the detail screen to finish loading. */
    private fun openFirstResult() {
        waitFor(hasTestTag(SEARCH_RESULT_ROW_TEST_TAG), timeoutMs = 30_000)
        composeRule.onAllNodes(hasTestTag(SEARCH_RESULT_ROW_TEST_TAG)).onFirst().performClick()
        waitFor(hasContentDescription("Back"), timeoutMs = 20_000)
        // The detail scaffold (Back arrow) renders immediately; wait for the loading
        // skeleton to disappear so the capture shows real content, not placeholders.
        waitUntilGone(hasTestTag(DETAIL_LOADING_TEST_TAG), timeoutMs = 30_000)
        settle()
    }

    /** Return from a detail screen to the search list. */
    private fun goBack() {
        composeRule.onNodeWithContentDescription("Back").performClick()
        waitForResults()
    }

    /** Wait until at least one search result row is present. */
    private fun waitForResults() = waitFor(hasTestTag(SEARCH_RESULT_ROW_TEST_TAG), timeoutMs = 30_000)

    /** Block until at least one node matches [matcher], or the timeout elapses. */
    private fun waitFor(
        matcher: SemanticsMatcher,
        timeoutMs: Long = 15_000,
    ) {
        composeRule.waitUntil(timeoutMillis = timeoutMs) {
            composeRule.onAllNodes(matcher).fetchSemanticsNodes().isNotEmpty()
        }
    }

    /** Block until no node matches [matcher] (e.g. a loading skeleton has cleared). */
    private fun waitUntilGone(
        matcher: SemanticsMatcher,
        timeoutMs: Long = 15_000,
    ) {
        composeRule.waitUntil(timeoutMillis = timeoutMs) {
            composeRule.onAllNodes(matcher).fetchSemanticsNodes().isEmpty()
        }
    }

    /** Let animations/recomposition quiesce before capturing a frame. */
    private fun settle() {
        composeRule.waitForIdle()
    }
}
