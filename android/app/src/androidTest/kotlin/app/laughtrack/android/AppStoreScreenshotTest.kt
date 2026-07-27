package app.laughtrack.android

import android.Manifest
import android.os.SystemClock
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.compose.ui.semantics.SemanticsProperties
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
import androidx.navigation.NavHostController
import androidx.navigation.compose.rememberNavController
import androidx.test.espresso.Espresso.closeSoftKeyboard
import androidx.test.platform.app.InstrumentationRegistry
import app.laughtrack.android.core.navigation.AppRoute
import app.laughtrack.android.core.network.ApiClientModule
import app.laughtrack.android.core.network.generated.infrastructure.ApiClient
import app.laughtrack.android.core.playback.PodcastPlaybackController
import app.laughtrack.android.core.playback.PodcastPlaybackItem
import app.laughtrack.android.core.ui.components.RemoteImageTestTags
import app.laughtrack.android.core.ui.theme.LaughTrackTheme
import app.laughtrack.android.feature.detail.ui.CLUB_SHOW_ROW_TEST_TAG
import app.laughtrack.android.feature.detail.ui.components.DETAIL_LOADING_TEST_TAG
import app.laughtrack.android.feature.search.ui.SEARCH_RESULT_ROW_TEST_TAG
import app.laughtrack.android.screenshots.AuthenticatedScreenshotPersona
import app.laughtrack.android.screenshots.ScreenshotImageTracker
import coil.Coil
import coil.ImageLoader
import dagger.hilt.android.testing.BindValue
import dagger.hilt.android.testing.HiltAndroidRule
import dagger.hilt.android.testing.HiltAndroidTest
import dagger.hilt.android.testing.UninstallModules
import okhttp3.OkHttpClient
import okhttp3.Request
import org.json.JSONObject
import org.junit.Before
import org.junit.Rule
import org.junit.Test
import tools.fastlane.screengrab.Screengrab
import tools.fastlane.screengrab.UiAutomatorScreenshotStrategy
import tools.fastlane.screengrab.locale.LocaleTestRule

/**
 * Captures the complete comparison screenshot set, mirroring the iOS
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
 * Result data and artwork come from the same host-side fixture backend as iOS,
 * while location resolution remains test-side and fixed to Hollywood (90028).
 */
@HiltAndroidTest
@UninstallModules(ApiClientModule::class)
class AppStoreScreenshotTest {
    private val screenshotExecutionOrder =
        listOf(
            "01_NearMe",
            "02_SearchShows",
            "03_SearchComedians",
            "04_SearchClubs",
            "05_ClubDetail",
            "06_ShowDetail",
            "07_ComedianDetail",
            "08_SearchPodcasts",
            "09_PodcastDetail",
            "11_Profile",
            "18_AuthPrompt",
            "13_Onboarding",
            "14_NowPlaying",
            "15_AuthenticatedFavorites",
            "16_AuthenticatedProfile",
            "17_AuthenticatedNotifications",
            "19_FirstEntryAuthChoice",
        )
    private val selectedScenarioIds: List<String>? by lazy {
        InstrumentationRegistry.getArguments().getString("screenshotScenarios")
            ?.split(",")
            ?.filter(String::isNotBlank)
    }
    private val lastSelectedScenarioId: String? by lazy {
        val selected = selectedScenarioIds ?: return@lazy null
        screenshotExecutionOrder.lastOrNull { it in selected }
    }

    @BindValue
    @JvmField
    val screenshotApiClient =
        ApiClient(
            baseUrl = "http://10.0.2.2:8765/api/v1/",
            okHttpClientBuilder = OkHttpClient.Builder(),
        )

    @BindValue
    @JvmField
    @javax.inject.Named("apiBaseUrl")
    val screenshotApiBaseUrl = "http://10.0.2.2:8765/api/v1/"

    private val imageTracker = ScreenshotImageTracker()
    private lateinit var fixtureMode: String
    private var fixtureResultCount = 5

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
        fixtureMode =
            if (instrumentation.targetContext.resources.configuration.smallestScreenWidthDp >= 600) {
                "asset-rich"
            } else {
                "fallback-focused"
            }
        fixtureResultCount = configureFixture(fixtureMode)
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
        lateinit var navController: NavHostController
        var screenshotPersona by mutableStateOf<AuthenticatedScreenshotPersona?>(null)
        var showLoginPrompt by mutableStateOf(false)
        var showFirstEntryAuthChoice by mutableStateOf(false)
        val playbackController = PodcastPlaybackController(InstrumentationRegistry.getInstrumentation().targetContext)
        composeRule.setContent {
            navController = rememberNavController()
            LaughTrackTheme {
                if (showFirstEntryAuthChoice) {
                    FirstEntryAuthChoiceScreen(onContinueAsGuest = {})
                } else {
                    AppShell(
                        navController = navController,
                        signedIn = screenshotPersona != null,
                        hasFavorites = screenshotPersona != null,
                        playbackController = playbackController,
                        showLoginPrompt = showLoginPrompt,
                        onLoginPromptDismiss = { showLoginPrompt = false },
                        screenshotPersona = screenshotPersona,
                    )
                }
            }
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
        if (capture("01_NearMe")) return

        // 02 — Search / Shows (the default pivot). The Search tab's contentDescription
        // lives on the icon, which NavigationBarItem merges under its label Text — so
        // it only resolves in the unmerged tree. Clicking the icon node still triggers
        // the item's onClick.
        composeRule.onNode(hasContentDescription("Search"), useUnmergedTree = true).performClick()
        waitFor(hasText("Search nearby comedy"), timeoutMs = 30_000)
        waitForResults()
        assertFixtureResultCount()
        if (capture("02_SearchShows")) return

        // 03 — Search / Comedians. Pivot chips render their label uppercased.
        selectPivot("COMEDIANS")
        assertFixtureResultCount()
        if (capture("03_SearchComedians")) return

        // 04 — Search / Clubs.
        selectPivot("CLUBS")
        assertFixtureResultCount()
        if (capture("04_SearchClubs")) return

        // 05 — Open the catalog's fixed club fixture.
        searchFor("The Comedy Store")
        openFirstResult()
        if (capture("05_ClubDetail")) return

        // 06 — Show detail. Match iOS by opening the first upcoming show from
        // the selected club's calendar rather than returning to global Shows.
        waitFor(hasTestTag(CLUB_SHOW_ROW_TEST_TAG), timeoutMs = 30_000)
        composeRule.onAllNodes(hasTestTag(CLUB_SHOW_ROW_TEST_TAG)).onFirst().performScrollTo().performClick()
        waitFor(hasContentDescription("Home"), timeoutMs = 20_000)
        waitForDetail()
        if (capture("06_ShowDetail")) return
        goBackToClubDetail()
        goBack()

        // 07 — Comedian detail.
        selectPivot("COMEDIANS")
        searchFor("Ali Wong")
        openFirstResult()
        if (capture("07_ComedianDetail")) return

        goBack()

        // 08 — Search / Podcasts.
        selectPivot("PODCASTS")
        assertFixtureResultCount()
        if (capture("08_SearchPodcasts")) return

        // 09 — Open the catalog's fixed podcast fixture.
        searchFor("The Joe Rogan Experience")
        openFirstResult()
        if (capture("09_PodcastDetail")) return

        navigate(navController, AppRoute.Profile)
        waitFor(hasText("Guest mode"))
        if (capture("11_Profile")) return

        // Present the protected-action prompt over a neutral app destination instead
        // of making the guest Profile hierarchy compete with the modal. No provider
        // is clicked, so Custom Tabs / external OAuth never launches.
        navigate(navController, AppRoute.Discover)
        waitFor(hasContentDescription("Edit location"), timeoutMs = 20_000)
        composeRule.runOnIdle { showLoginPrompt = true }
        waitFor(hasText("Sign in to save favorites"))
        listOf("Continue with Google", "Continue with Apple", "Email me a sign-in link").forEach { option ->
            waitFor(hasText(option))
        }
        if (capture("18_AuthPrompt", dismissKeyboard = false)) return
        composeRule.runOnIdle { showLoginPrompt = false }

        navigate(navController, AppRoute.ComedianOnboarding)
        waitForPopulatedOnboarding()
        if (capture("13_Onboarding")) return

        composeRule.runOnIdle {
            playbackController.seedForScreenshot(
                PodcastPlaybackItem(
                    episodeId = -1,
                    podcastId = -1,
                    podcastTitle = "LaughTrack",
                    episodeTitle = "The LaughTrack Comedy Roundup",
                    audioUrl = "https://example.invalid/demo.mp3",
                    artworkUrl = null,
                ),
            )
            navController.navigate(AppRoute.NowPlaying)
        }
        waitFor(hasText("The LaughTrack Comedy Roundup"))
        // Intentional background override: this immersive media destination is
        // the sole AppShell route that replaces the atmosphere with opaque Canvas.
        if (capture("14_NowPlaying")) return

        // Opt into the credentials-free persona explicitly for the populated
        // authenticated screens, including the only valid Favorites state.
        composeRule.runOnIdle {
            playbackController.stop()
            screenshotPersona = AuthenticatedScreenshotPersona
        }

        navigate(navController, AppRoute.Favorites())
        waitFor(hasText("Taylor Tomlinson"))
        if (capture("15_AuthenticatedFavorites")) return

        navigate(navController, AppRoute.Profile)
        waitFor(hasText("Jordan Rivera"))
        if (capture("16_AuthenticatedProfile")) return

        navigate(navController, AppRoute.NotificationCenter)
        waitFor(hasText("Taylor Tomlinson has a show near you"))
        if (capture("17_AuthenticatedNotifications")) return

        // Render the production root-level gate, distinct from the protected-action
        // LoginPromptSheet captured above. Provider buttons are asserted but untouched.
        composeRule.runOnIdle {
            screenshotPersona = null
            showFirstEntryAuthChoice = true
        }
        waitFor(hasTestTag(FIRST_ENTRY_AUTH_CHOICE_TEST_TAG))
        waitFor(hasContentDescription(FIRST_ENTRY_BRAND_LOGO_CONTENT_DESCRIPTION))
        listOf(
            "Continue as guest",
            "Continue with Google",
            "Continue with Apple",
            "Email me a sign-in link",
        ).forEach { option -> waitFor(hasText(option)) }
        // Specialized root owner: the first-entry gate lives outside AppShell
        // and renders its own branded atmosphere and authentication treatments.
        if (capture("19_FirstEntryAuthChoice", dismissKeyboard = false)) return
    }

    private fun navigate(
        navController: NavHostController,
        route: AppRoute,
    ) {
        composeRule.runOnIdle { navController.navigate(route) }
        settle()
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

    private fun assertFixtureResultCount() {
        waitFor(hasText("Showing $fixtureResultCount results"), timeoutMs = 15_000)
    }

    private fun configureFixture(mode: String): Int {
        val request =
            Request.Builder()
                .url("http://10.0.2.2:8765/fixture/configure?mode=$mode")
                .build()
        return OkHttpClient().newCall(request).execute().use { response ->
            check(response.isSuccessful) {
                "Screenshot fixture mode configuration failed: HTTP ${response.code}"
            }
            val payload = JSONObject(checkNotNull(response.body).string())
            check(payload.getString("mode") == mode) {
                "Screenshot fixture selected ${payload.getString("mode")} instead of $mode"
            }
            check(payload.getString("fingerprint").length == 64) {
                "Screenshot fixture returned an invalid mode fingerprint"
            }
            check(payload.getJSONArray("required_assets").length() > 0) {
                "Screenshot fixture mode must require representative artwork"
            }
            payload.getInt("result_count").also { count ->
                check(count > 0) { "Screenshot fixture result count must be positive" }
            }
        }
    }

    /** Require the initial fixture card and its actions to remain fully rendered before capture. */
    private fun waitForPopulatedOnboarding() {
        var readySince = 0L
        composeRule.waitUntil(timeoutMillis = 30_000) {
            val now = android.os.SystemClock.uptimeMillis()
            val ready =
                isOnboardingScreenshotReady(
                    fixtureNamePresent = hasNode(hasText("Ali Wong")),
                    fixtureDetailsPresent = hasNode(hasText("28 upcoming shows")),
                    passControlPresent = hasNode(hasText("Pass")),
                    followControlPresent = hasNode(hasText("Follow")),
                    loadingPresent = hasNode(SemanticsMatcher.keyIsDefined(SemanticsProperties.ProgressBarRangeInfo)),
                    emptyStatePresent = hasNode(hasText("No more cards in this deal.")),
                )
            if (!ready) {
                readySince = 0L
                false
            } else {
                if (readySince == 0L) readySince = now
                now - readySince >= 750
            }
        }
    }

    private fun hasNode(matcher: SemanticsMatcher): Boolean =
        composeRule.onAllNodes(matcher).fetchSemanticsNodes().isNotEmpty()

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
    private fun capture(
        name: String,
        dismissKeyboard: Boolean = true,
    ): Boolean {
        if (selectedScenarioIds != null && name !in selectedScenarioIds.orEmpty()) {
            return false
        }
        // Search and profile fields can retain focus after route changes. Screengrab
        // captures the whole device, so an IME left open on one screen otherwise
        // contaminates every screenshot that follows it.
        if (dismissKeyboard) {
            closeSoftKeyboard()
        }
        settle()
        imageTracker.awaitIdle(timeoutMs = 30_000)
        waitUntilGone(hasTestTag(RemoteImageTestTags.SKELETON))
        // Coil can report success just before Compose commits the decoded bitmap.
        // Give that final frame time to land before asking screengrab to capture.
        android.os.SystemClock.sleep(250)
        settle()
        Screengrab.screenshot(name)
        return lastSelectedScenarioId == name
    }
}
