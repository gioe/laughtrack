package app.laughtrack.android

import android.Manifest
import android.os.SystemClock
import androidx.compose.ui.test.SemanticsMatcher
import androidx.compose.ui.test.hasContentDescription
import androidx.compose.ui.test.hasSetTextAction
import androidx.compose.ui.test.hasTestTag
import androidx.compose.ui.test.hasText
import androidx.compose.ui.test.junit4.createAndroidComposeRule
import androidx.compose.ui.test.onFirst
import androidx.compose.ui.test.onNodeWithContentDescription
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import androidx.compose.ui.test.performScrollTo
import androidx.compose.ui.test.performTextInput
import androidx.test.platform.app.InstrumentationRegistry
import app.laughtrack.android.core.ui.components.RemoteImageTestTags
import app.laughtrack.android.core.ui.theme.LaughTrackTheme
import app.laughtrack.android.feature.detail.ui.CLUB_SHOW_ROW_TEST_TAG
import app.laughtrack.android.feature.detail.ui.components.DETAIL_LOADING_TEST_TAG
import app.laughtrack.android.feature.search.ui.SEARCH_RESULT_ROW_TEST_TAG
import app.laughtrack.android.screenshots.ScreenshotImageTracker
import coil.Coil
import coil.ImageLoader
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
 * Result data and artwork come from the production API, matching the iOS store
 * screenshot lane. Only location resolution is faked so both platforms request
 * Hollywood (90028) without depending on emulator GPS or runner geo-IP.
 */
@HiltAndroidTest
class AppStoreScreenshotTest {
    private val imageTracker = ScreenshotImageTracker()

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
        // Pre-grant location so tapping "Use my location" calls the ViewModel directly
        // instead of launching the system permission dialog (which would destroy the
        // test activity). The FakeHomeLocationResolver still short-circuits GPS and
        // returns 90028 — the grant only keeps the in-app permission check happy.
        val instrumentation = InstrumentationRegistry.getInstrumentation()
        // Screengrab enters demo mode after the fastlane preflight. Reset it once
        // here before applying the canonical chrome: Android 15 otherwise adds a
        // duplicate Wi-Fi slot each time the network demo command is repeated.
        instrumentation.uiAutomation
            .executeShellCommand("am broadcast -a com.android.systemui.demo -e command exit")
            .close()
        // SystemUI handles demo broadcasts asynchronously. Let the exit finish before
        // sending the canonical state or its reset can win the race and restore real
        // time/notification icons while screenshots are being captured.
        SystemClock.sleep(500)
        listOf(
            "am broadcast -a com.android.systemui.demo -e command clock -e hhmm 0941",
            "am broadcast -a com.android.systemui.demo -e command notifications -e visible false",
            "am broadcast -a com.android.systemui.demo -e command network -e mobile hide",
            "am broadcast -a com.android.systemui.demo -e command network -e wifi show -e level 4 -e fully true",
            "am broadcast -a com.android.systemui.demo -e command battery -e level 100 -e plugged false",
        ).forEach { command -> instrumentation.uiAutomation.executeShellCommand(command).close() }
        SystemClock.sleep(300)
        Coil.setImageLoader(
            ImageLoader.Builder(instrumentation.targetContext)
                .crossfade(false)
                .eventListener(imageTracker)
                .build(),
        )
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

        // 01 — Near Me. The location controls live behind the header row's bottom
        // sheet (TASK-3624): open it via the chevron's stable contentDescription
        // (the row title varies with the server-inferred area), trigger
        // use-device-location so the fake resolver (90028) drives the Discover
        // feed, then wait for the LA feed.
        waitFor(hasContentDescription("Edit location"))
        composeRule.onNodeWithContentDescription("Edit location").performClick()
        waitFor(hasText("Use my location"))
        composeRule.onNodeWithText("Use my location").performClick()
        waitFor(
            hasText("Near Los Angeles", substring = true) or hasText("90028", substring = true),
            timeoutMs = 30_000,
        )
        capture("01_NearMe")

        // 02 — Search / Shows (the default pivot). The Search tab's contentDescription
        // lives on the icon, which NavigationBarItem merges under its label Text — so
        // it only resolves in the unmerged tree. Clicking the icon node still triggers
        // the item's onClick.
        composeRule.onNode(hasContentDescription("Search"), useUnmergedTree = true).performClick()
        waitFor(hasText("Search nearby comedy"), timeoutMs = 30_000)
        waitForResults()
        capture("02_SearchShows")

        // 03 — Search / Comedians. Pivot chips render their label uppercased.
        selectPivot("COMEDIANS")
        capture("03_SearchComedians")

        // 04 — Search / Clubs.
        selectPivot("CLUBS")
        capture("04_SearchClubs")

        // 05 — Match iOS's curated live club selection.
        searchFor("New York Comedy Club Midtown")
        openFirstResult()
        capture("05_ClubDetail")

        // 06 — Show detail. Match iOS by opening the first upcoming show from
        // the selected club's calendar rather than returning to global Shows.
        waitFor(hasTestTag(CLUB_SHOW_ROW_TEST_TAG), timeoutMs = 30_000)
        composeRule.onAllNodes(hasTestTag(CLUB_SHOW_ROW_TEST_TAG)).onFirst().performScrollTo().performClick()
        waitFor(hasContentDescription("Home"), timeoutMs = 20_000)
        waitForDetail()
        capture("06_ShowDetail")
        goBackToClubDetail()
        goBack()

        // 07 — Comedian detail.
        selectPivot("COMEDIANS")
        searchFor("Andrew Schulz")
        openFirstResult()
        capture("07_ComedianDetail")
        goBack()

        // 08 — Search / Podcasts.
        selectPivot("PODCASTS")
        capture("08_SearchPodcasts")

        // 09 — Match iOS's curated live podcast selection.
        searchFor("The D.L. Hughley Show")
        openFirstResult()
        capture("09_PodcastDetail")
    }

    /** Select a search pivot by its uppercased chip label and wait for its results. */
    private fun selectPivot(label: String) {
        composeRule.onNodeWithText(label).performScrollTo().performClick()
        waitForResults()
    }

    /** Narrow the active live endpoint to the entity curated by the iOS flow. */
    private fun searchFor(query: String) {
        composeRule.onAllNodes(hasSetTextAction()).onFirst().performTextInput(query)
        waitForResults()
    }

    /** Tap the first search result row and wait for the detail screen to finish loading. */
    private fun openFirstResult() {
        waitFor(hasTestTag(SEARCH_RESULT_ROW_TEST_TAG), timeoutMs = 30_000)
        composeRule.onAllNodes(hasTestTag(SEARCH_RESULT_ROW_TEST_TAG)).onFirst().performClick()
        waitForDetail()
    }

    private fun waitForDetail() {
        waitFor(hasContentDescription("Back"), timeoutMs = 20_000)
        waitUntilGone(hasTestTag(DETAIL_LOADING_TEST_TAG), timeoutMs = 30_000)
        settle()
    }

    private fun goBackToClubDetail() {
        composeRule.onNodeWithContentDescription("Back").performClick()
        waitFor(hasTestTag(CLUB_SHOW_ROW_TEST_TAG), timeoutMs = 20_000)
        waitUntilGone(hasTestTag(DETAIL_LOADING_TEST_TAG), timeoutMs = 30_000)
    }

    /** Return from a detail screen to the search list. */
    private fun goBack() {
        composeRule.onNodeWithContentDescription("Back").performScrollTo().performClick()
        waitForResults()
    }

    /** Wait until at least one search result row is present. */
    private fun waitForResults() = waitForStable(hasTestTag(SEARCH_RESULT_ROW_TEST_TAG), timeoutMs = 30_000)

    /** Require a node to remain present across recompositions, not merely flash during navigation. */
    private fun waitForStable(
        matcher: SemanticsMatcher,
        timeoutMs: Long,
        stableMs: Long = 750,
    ) {
        var presentSince = 0L
        composeRule.waitUntil(timeoutMillis = timeoutMs) {
            val now = android.os.SystemClock.uptimeMillis()
            if (composeRule.onAllNodes(matcher).fetchSemanticsNodes().isEmpty()) {
                presentSince = 0L
                false
            } else {
                if (presentSince == 0L) presentSince = now
                now - presentSince >= stableMs
            }
        }
    }

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

    /** Wait for live artwork requests and Coil decode before capture. */
    private fun capture(name: String) {
        settle()
        imageTracker.awaitIdle(timeoutMs = 30_000)
        waitUntilGone(hasTestTag(RemoteImageTestTags.SKELETON))
        // Coil can report success just before Compose commits the decoded bitmap.
        // Give that final frame time to land before asking screengrab to capture.
        android.os.SystemClock.sleep(250)
        settle()
        Screengrab.screenshot(name)
    }
}
