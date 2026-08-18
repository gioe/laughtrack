package app.laughtrack.android

import android.Manifest
import android.content.Context
import android.net.Uri
import android.os.SystemClock
import android.view.inputmethod.InputMethodManager
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.compose.ui.semantics.ProgressBarRangeInfo
import androidx.compose.ui.semantics.SemanticsProperties
import androidx.compose.ui.test.ComposeTimeoutException
import androidx.compose.ui.test.SemanticsMatcher
import androidx.compose.ui.test.hasContentDescription
import androidx.compose.ui.test.hasSetTextAction
import androidx.compose.ui.test.hasTestTag
import androidx.compose.ui.test.hasText
import androidx.compose.ui.test.junit4.createAndroidComposeRule
import androidx.compose.ui.test.onFirst
import androidx.compose.ui.test.onNodeWithContentDescription
import androidx.compose.ui.test.onNodeWithTag
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import androidx.compose.ui.test.performScrollTo
import androidx.compose.ui.test.performScrollToIndex
import androidx.compose.ui.test.performScrollToNode
import androidx.compose.ui.test.performTextInput
import androidx.navigation.NavHostController
import androidx.navigation.compose.rememberNavController
import androidx.test.platform.app.InstrumentationRegistry
import app.laughtrack.android.core.data.location.HomeLocationState
import app.laughtrack.android.core.navigation.AppRoute
import app.laughtrack.android.core.network.ApiClientModule
import app.laughtrack.android.core.network.generated.infrastructure.ApiClient
import app.laughtrack.android.core.playback.PodcastPlaybackController
import app.laughtrack.android.core.playback.PodcastPlaybackItem
import app.laughtrack.android.core.ui.components.RemoteImageTestTags
import app.laughtrack.android.core.ui.theme.LaughTrackTheme
import app.laughtrack.android.feature.detail.ui.CLUB_FREQUENT_PERFORMERS_SECTION_TEST_TAG
import app.laughtrack.android.feature.detail.ui.CLUB_HIGHLIGHT_SECTION_TEST_TAG
import app.laughtrack.android.feature.detail.ui.CLUB_SHOW_ROW_TEST_TAG
import app.laughtrack.android.feature.detail.ui.components.DETAIL_LOADING_TEST_TAG
import app.laughtrack.android.feature.home.HOME_DISCOVER_LIST_TEST_TAG
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
import javax.inject.Inject

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
            "10_PodcastEpisodeDetail",
            "11_Profile",
            "18_AuthPrompt",
            "13_Onboarding",
            "14_NowPlaying",
            "15_AuthenticatedFavorites",
            "16_AuthenticatedProfile",
            "17_AuthenticatedNotifications",
            "19_FirstEntryAuthChoice",
        )
    private val podcastEpisodeRowTag = "podcastEpisodeRow-501"
    private val podcastEpisodeDetailTag = "podcastEpisodeDetail"
    private val podcastEpisodePrimaryActionTag = "podcastEpisodeDetailPrimaryAction"
    private val selectedScenarioIds: List<String>? by lazy {
        InstrumentationRegistry.getArguments().getString("screenshotScenarios")
            ?.split(",")
            ?.filter(String::isNotBlank)
    }
    private val lastSelectedScenarioId: String? by lazy {
        val selected = selectedScenarioIds ?: return@lazy null
        screenshotExecutionOrder.lastOrNull { it in selected }
    }
    private val capturesNearMe: Boolean by lazy {
        selectedScenarioIds == null || "01_NearMe" in selectedScenarioIds.orEmpty()
    }
    private val indeterminateLoadingIndicator =
        SemanticsMatcher.expectValue(
            SemanticsProperties.ProgressBarRangeInfo,
            ProgressBarRangeInfo.Indeterminate,
        )

    @Inject
    lateinit var homeLocationState: HomeLocationState

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
        // Screengrab's host-side cleanup cannot delete app-private files on
        // current Android releases. Clear the directory from inside the target
        // process so a focused run never pulls a screenshot left by an earlier
        // complete-matrix capture.
        check(instrumentation.targetContext.getDir("screengrab", Context.MODE_PRIVATE).deleteRecursively()) {
            "Unable to clear stale app-private Screengrab screenshots"
        }
        fixtureMode =
            InstrumentationRegistry.getArguments().getString("screenshotFixtureMode")
                ?.takeIf(String::isNotBlank)
                ?: "curated"
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
                        playbackController = playbackController,
                        showLoginPrompt = showLoginPrompt,
                        onLoginPromptDismiss = { showLoginPrompt = false },
                        screenshotPersona = screenshotPersona,
                    )
                }
            }
        }

        if (capturesNearMe) {
            // 01 — Near Me. The complete matrix keeps driving the real location
            // controls in canonical order before Search. Focused runs that omit
            // this scenario instead wait on the shared state below, avoiding a
            // dependency on unrelated Discover layout and semantics.
            waitFor(hasContentDescription("Edit location"))
            composeRule.onNodeWithContentDescription("Edit location").performClick()
            waitFor(hasText("Use my location"))
            composeRule.onNodeWithText("Use my location").performClick()
            waitFor(
                hasText("Near Los Angeles", substring = true) or hasText("90028", substring = true),
                timeoutMs = 30_000,
            )
            if (isCompactScreenshotProfile()) {
                waitFor(hasTestTag(HOME_DISCOVER_LIST_TEST_TAG), timeoutMs = 30_000)
                waitForDiscoverAndScrollTo(hasText("Episodes for you"))
                waitForStable(hasText("Episodes for you"), timeoutMs = 30_000)
                composeRule.onNodeWithTag("homePodcastEpisodePlay-501").performScrollTo()
                waitFor(hasContentDescription("History Hyenas"))
                waitFor(hasText("The Wildest Feuds in History"))
                waitFor(hasText(" • 71 min", substring = true))
                waitFor(hasText("Guest: Ali Wong"))
                waitFor(
                    hasContentDescription(
                        "Open The Wildest Feuds in History",
                        substring = true,
                    ),
                )
                waitFor(hasTestTag("homePodcastEpisodePlay-501"))
                waitFor(hasContentDescription("Play episode The Wildest Feuds in History"))
                composeRule
                    .onNodeWithTag(HOME_DISCOVER_LIST_TEST_TAG)
                    .performScrollToIndex(0)
                waitForStable(hasText("TONIGHT!"), timeoutMs = 30_000)
            }
            if (capture("01_NearMe")) return
        } else {
            waitForCanonicalHomeLocation()
        }

        // 02 — Search / Shows (the default pivot). The Search tab's contentDescription
        // lives on the icon, which NavigationBarItem merges under its label Text — so
        // it only resolves in the unmerged tree. Clicking the icon node still triggers
        // the item's onClick.
        composeRule.onNode(hasContentDescription("Search"), useUnmergedTree = true).performClick()
        waitFor(hasText("Start with what matters"), timeoutMs = 30_000)
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
        searchFor("Comedy Cellar")
        openFirstResult()
        waitFor(hasTestTag(CLUB_HIGHLIGHT_SECTION_TEST_TAG), timeoutMs = 30_000)
        waitFor(hasTestTag(CLUB_FREQUENT_PERFORMERS_SECTION_TEST_TAG), timeoutMs = 30_000)
        if (capture("05_ClubDetail")) return

        // 06 — Show detail. Match iOS by opening the first upcoming show from
        // the selected club's calendar rather than returning to global Shows.
        waitFor(hasTestTag(CLUB_SHOW_ROW_TEST_TAG), timeoutMs = 30_000)
        composeRule
            .onAllNodes(hasTestTag(CLUB_SHOW_ROW_TEST_TAG))
            .onFirst()
            .performScrollTo()
            .performClick()
        waitFor(hasContentDescription("Home"), timeoutMs = 20_000)
        waitForDetail()
        waitFor(hasText("TAYLOR TOMLINSON & FRIENDS"), timeoutMs = 20_000)
        waitFor(hasText("Aug 16, 2026", substring = true), timeoutMs = 20_000)
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
        searchFor("History Hyenas")
        openFirstResult()
        if (capture("09_PodcastDetail")) return

        // 10 — Open the same deterministic episode from podcast detail.
        waitFor(hasTestTag(podcastEpisodeRowTag), timeoutMs = 20_000)
        composeRule
            .onNodeWithContentDescription("Open episode The Wildest Feuds in History")
            .performScrollTo()
            .performClick()
        waitFor(hasTestTag(podcastEpisodeDetailTag), timeoutMs = 20_000)
        waitUntilGone(hasTestTag(DETAIL_LOADING_TEST_TAG), timeoutMs = 30_000)
        waitFor(hasText("The Wildest Feuds in History"), timeoutMs = 20_000)
        waitFor(hasTestTag(podcastEpisodePrimaryActionTag), timeoutMs = 20_000)
        if (capture("10_PodcastEpisodeDetail")) return

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

        // Use the upstream cover rather than the app's artwork proxy or the
        // local screenshot fixture so this capture exercises remote artwork.
        val nowPlayingArtworkUrl =
            "https://megaphone.imgix.net/podcasts/48030056-989d-11ef-a614-3bc2f8865178/" +
                "image/171a69e4231342ccae610db68861892b.jpeg?ixlib=rails-4.3.1&max-w=3000&max-h=3000&" +
                "fit=crop&auto=format%2Ccompress"
        val nowPlayingArtworkUri = Uri.parse(nowPlayingArtworkUrl)
        check(nowPlayingArtworkUri.scheme == "https") { "Now Playing artwork must use HTTPS" }
        check(nowPlayingArtworkUri.host == "megaphone.imgix.net") {
            "Now Playing artwork must use the direct upstream host"
        }
        composeRule.runOnIdle {
            playbackController.seedForScreenshot(
                PodcastPlaybackItem(
                    episodeId = -1,
                    podcastId = -1,
                    podcastTitle = "History Hyenas",
                    episodeTitle = "The Wildest Feuds in History",
                    audioUrl = "https://example.invalid/demo.mp3",
                    artworkUrl = nowPlayingArtworkUrl,
                ),
            )
            navController.navigate(AppRoute.NowPlaying)
        }
        waitFor(hasText("The Wildest Feuds in History"))
        // Intentional background override: this immersive media destination is
        // the sole AppShell route that replaces the atmosphere with opaque Canvas.
        if (capture("14_NowPlaying")) return

        // Opt into the credentials-free persona explicitly for the populated
        // authenticated screens, including the only valid Favorites state.
        composeRule.runOnIdle {
            playbackController.stop()
            screenshotPersona = AuthenticatedScreenshotPersona
        }

        navigate(navController, AppRoute.Favorites)
        waitFor(hasText(AuthenticatedScreenshotPersona.UPCOMING_SAVED_SHOW_TITLE))
        composeRule
            .onNodeWithText(AuthenticatedScreenshotPersona.UPCOMING_SAVED_SHOW_TITLE)
            .performScrollTo()
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

    private fun waitForCanonicalHomeLocation() {
        composeRule.waitUntil(timeoutMillis = 30_000) {
            homeLocationState.location.value?.let { location ->
                location.zip == "90028" &&
                    location.distanceMiles == 25 &&
                    location.locationLabel == "Los Angeles, CA"
            } == true
        }
    }

    private fun isCompactScreenshotProfile(): Boolean =
        InstrumentationRegistry.getInstrumentation()
            .targetContext
            .resources
            .displayMetrics
            .run { widthPixels * 160f / densityDpi < 600f }

    private fun waitForDiscoverAndScrollTo(
        matcher: SemanticsMatcher,
        timeoutMs: Long = 30_000,
    ) {
        composeRule.waitUntil(timeoutMillis = timeoutMs) {
            runCatching {
                composeRule
                    .onNodeWithTag(HOME_DISCOVER_LIST_TEST_TAG)
                    .performScrollToNode(matcher)
            }.isSuccess
        }
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
                    fixtureNamePresent = hasNode(hasText("ALI WONG")),
                    fixturePortraitPresent = hasNode(hasContentDescription("Ali Wong")),
                    passControlPresent = hasNode(hasContentDescription("Pass")),
                    followControlPresent = hasNode(hasContentDescription("Follow")),
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

    /** Require transient loading UI to remain absent before saving a screenshot. */
    private fun waitForCaptureLoadingToClear(
        name: String,
        timeoutMs: Long = 30_000,
        stableMs: Long = 750,
    ) {
        var clearSince = 0L
        try {
            composeRule.waitUntil(timeoutMillis = timeoutMs) {
                val now = SystemClock.uptimeMillis()
                if (indeterminateLoadingNodes().isNotEmpty()) {
                    clearSince = 0L
                    false
                } else {
                    if (clearSince == 0L) clearSince = now
                    now - clearSince >= stableMs
                }
            }
        } catch (cause: ComposeTimeoutException) {
            throw AssertionError(captureLoadingDiagnostic(name, timeoutMs), cause)
        }

        check(indeterminateLoadingNodes().isEmpty()) {
            captureLoadingDiagnostic(name, stableMs)
        }
    }

    private fun indeterminateLoadingNodes() =
        composeRule
            .onAllNodes(indeterminateLoadingIndicator, useUnmergedTree = true)
            .fetchSemanticsNodes()

    private fun captureLoadingDiagnostic(
        name: String,
        waitedMs: Long,
    ): String {
        val survivingNodes = indeterminateLoadingNodes()
        val details = survivingNodes.take(3).joinToString(separator = "\n") { it.toString() }
        return buildString {
            append("Refusing to capture '")
            append(name)
            append("': ")
            append(survivingNodes.size)
            append(" indeterminate loading indicator(s) survived the ")
            append(waitedMs)
            append(" ms readiness gate")
            if (details.isNotEmpty()) {
                append(":\n")
                append(details)
            }
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
        // contaminates every screenshot that follows it. Hide it through the
        // activity window: Espresso.closeSoftKeyboard() first requires a focused
        // root and races slow emulator window transitions before the first capture.
        if (dismissKeyboard) {
            composeRule.runOnIdle {
                val activity = composeRule.activity
                val inputMethodManager =
                    activity.getSystemService(Context.INPUT_METHOD_SERVICE) as InputMethodManager
                inputMethodManager.hideSoftInputFromWindow(activity.window.decorView.windowToken, 0)
                activity.currentFocus?.clearFocus()
            }
        }
        settle()
        imageTracker.awaitIdle(timeoutMs = 30_000)
        waitUntilGone(hasTestTag(RemoteImageTestTags.SKELETON))
        // Coil can report success just before Compose commits the decoded bitmap.
        // Give that final frame time to land before asking screengrab to capture.
        android.os.SystemClock.sleep(250)
        settle()
        waitForCaptureLoadingToClear(name)
        Screengrab.screenshot(name)
        return lastSelectedScenarioId == name
    }
}
