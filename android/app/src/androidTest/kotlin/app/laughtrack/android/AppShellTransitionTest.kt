package app.laughtrack.android

import android.graphics.Bitmap
import android.os.SystemClock
import android.provider.Settings
import androidx.activity.BackEventCompat
import androidx.compose.runtime.mutableStateOf
import androidx.compose.ui.geometry.Rect
import androidx.compose.ui.semantics.SemanticsProperties
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.hasText
import androidx.compose.ui.test.isSelected
import androidx.compose.ui.test.junit4.createAndroidComposeRule
import androidx.compose.ui.test.onAllNodesWithTag
import androidx.compose.ui.test.onNodeWithContentDescription
import androidx.compose.ui.test.onNodeWithTag
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.onRoot
import androidx.compose.ui.test.performClick
import androidx.compose.ui.test.performScrollTo
import androidx.compose.ui.test.performScrollToIndex
import androidx.compose.ui.test.printToString
import androidx.navigation.NavDestination.Companion.hasRoute
import androidx.navigation.NavHostController
import androidx.navigation.compose.rememberNavController
import androidx.test.platform.app.InstrumentationRegistry
import app.laughtrack.android.core.navigation.AppRoute
import app.laughtrack.android.core.navigation.AppTab
import app.laughtrack.android.core.network.ApiClientModule
import app.laughtrack.android.core.network.generated.infrastructure.ApiClient
import app.laughtrack.android.core.playback.PodcastPlaybackController
import app.laughtrack.android.core.playback.PodcastPlaybackItem
import app.laughtrack.android.core.ui.theme.LaughTrackTheme
import app.laughtrack.android.feature.home.HOME_DISCOVER_LIST_TEST_TAG
import dagger.hilt.android.testing.BindValue
import dagger.hilt.android.testing.HiltAndroidRule
import dagger.hilt.android.testing.HiltAndroidTest
import dagger.hilt.android.testing.UninstallModules
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Protocol
import okhttp3.Response
import okhttp3.ResponseBody.Companion.toResponseBody
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Rule
import org.junit.Test
import java.io.File

/** Exercises shipping NavHost/chrome while the animation clock and native back progress move. */
@HiltAndroidTest
@UninstallModules(ApiClientModule::class)
class AppShellTransitionTest {
    // Deterministic offline destinations; transition tests must not depend on production data.
    @BindValue
    @JvmField
    val fixtureApiClient =
        ApiClient(
            baseUrl = "https://navigation-test.invalid/api/v1/",
            okHttpClientBuilder =
                OkHttpClient.Builder().addInterceptor { chain ->
                    Response.Builder().request(chain.request()).protocol(Protocol.HTTP_1_1)
                        .code(
                            if (chain.request().url.encodedPath.endsWith("home/feed")) 200 else 503,
                        ).message("Offline fixture")
                        .body(
                            (
                                if (chain.request().url.encodedPath.endsWith(
                                        "home/feed",
                                    )
                                ) {
                                    HOME_FEED
                                } else {
                                    "{}"
                                }
                            ).toResponseBody("application/json".toMediaType()),
                        ).build()
                },
        )

    @BindValue
    @JvmField
    @javax.inject.Named("apiBaseUrl")
    val fixtureApiBaseUrl = "https://navigation-test.invalid/api/v1/"

    @get:Rule(order = 0)
    val hiltRule = HiltAndroidRule(this)

    @get:Rule(order = 1)
    val composeRule = createAndroidComposeRule<HiltTestActivity>()

    private lateinit var navController: NavHostController

    @Test
    fun rapid_tabs_preserve_scroll_and_each_destinations_content_bounds() {
        showShell()
        composeRule.waitUntil(10_000) {
            composeRule.onNodeWithTag(HOME_DISCOVER_LIST_TEST_TAG).fetchSemanticsNode()
                .config[SemanticsProperties.VerticalScrollAxisRange].maxValue() > 0f
        }
        composeRule.onNodeWithTag(HOME_DISCOVER_LIST_TEST_TAG).performScrollToIndex(2)
        val scrollBefore = homeScroll()
        assertTrue("Discover must actually be scrolled", scrollBefore > 0f)
        composeRule.runOnIdle { navController.switchTab(AppTab.FAVORITES) }
        val libraryId = currentId()
        val libraryBounds = contentBounds(libraryId)
        capture("library-before-tabs")

        composeRule.mainClock.autoAdvance = false
        composeRule.runOnIdle { navController.switchTab(AppTab.SEARCH) }
        composeRule.mainClock.advanceTimeBy(32)
        val searchId = currentId()
        if (animationsEnabled()) {
            assertEquals(
                "Outgoing Library retains its own insets",
                libraryBounds,
                contentBounds(libraryId),
            )
        }
        val searchBounds = contentBounds(searchId)
        assertTrue("Search owns its top edge", searchBounds.top < libraryBounds.top)
        assertTrue(navController.currentDestination?.hasRoute<AppRoute.Search>() == true)
        capture("tab-crossfade")
        val semantics = composeRule.onRoot(useUnmergedTree = true).printToString()
        assertTrue(
            "Tab selection updates during the transition: $semantics",
            composeRule.onAllNodes(
                hasText("Search") and isSelected(),
            ).fetchSemanticsNodes().isNotEmpty(),
        )
        repeat(3) {
            composeRule.runOnIdle { navController.switchTab(AppTab.FAVORITES) }
            composeRule.mainClock.advanceTimeBy(32)
            composeRule.runOnIdle { navController.switchTab(AppTab.SEARCH) }
            composeRule.mainClock.advanceTimeBy(32)
        }
        composeRule.mainClock.autoAdvance = true
        composeRule.waitForIdle()
        assertEquals(searchBounds, contentBounds(searchId))
        composeRule.onNodeWithText("Search").assertIsDisplayed()
        capture("rapid-tabs-settled")
        composeRule.runOnIdle { navController.switchTab(AppTab.DISCOVER) }
        assertEquals(scrollBefore, homeScroll(), 0.01f)
        capture("discover-scroll-restored")
    }

    @Test
    fun detail_push_and_cancelled_predictive_back_keep_route_owned_insets() {
        showShell()
        composeRule.runOnIdle { navController.switchTab(AppTab.FAVORITES) }
        val libraryId = currentId()
        val libraryBounds = contentBounds(libraryId)
        composeRule.mainClock.autoAdvance = false
        composeRule.runOnIdle { navController.openEntity(AppRoute.ShowDetail(-3993)) }
        composeRule.mainClock.advanceTimeBy(80)
        // Horizontal motion may change x, but must not resize or move the content vertically.
        if (animationsEnabled()) {
            val outgoing = contentBounds(libraryId)
            assertEquals(libraryBounds.top, outgoing.top, 0.5f)
            assertEquals(libraryBounds.bottom, outgoing.bottom, 0.5f)
        }
        capture("detail-push")
        composeRule.mainClock.autoAdvance = true
        composeRule.waitForIdle()
        val detailId = currentId()
        val detailBounds = contentBounds(detailId)
        assertTrue(detailBounds.height > libraryBounds.height)
        composeRule.mainClock.autoAdvance = false
        composeRule.runOnIdle {
            composeRule.activity.onBackPressedDispatcher.dispatchOnBackStarted(backEvent(0f))
        }
        composeRule.mainClock.advanceTimeByFrame()
        composeRule.runOnIdle {
            composeRule.activity.onBackPressedDispatcher.dispatchOnBackProgressed(backEvent(0.45f))
        }
        composeRule.mainClock.advanceTimeBy(48)
        assertTrue(
            "Back must reveal the return destination",
            composeRule.onAllNodesWithTag(contentTag(libraryId)).fetchSemanticsNodes().isNotEmpty(),
        )
        val preview = contentBounds(libraryId)
        assertEquals(libraryBounds.top, preview.top, 0.5f)
        assertEquals(libraryBounds.bottom, preview.bottom, 0.5f)
        capture("predictive-back-preview")
        composeRule.runOnIdle { composeRule.activity.onBackPressedDispatcher.dispatchOnBackCancelled() }
        composeRule.mainClock.autoAdvance = true
        composeRule.waitForIdle()
        assertTrue(navController.currentDestination?.hasRoute<AppRoute.ShowDetail>() == true)
        assertEquals(detailBounds, contentBounds(detailId))
        capture("predictive-back-cancelled")
        composeRule.runOnIdle { composeRule.activity.onBackPressedDispatcher.onBackPressed() }
        composeRule.waitForIdle()
        assertTrue(navController.currentDestination?.hasRoute<AppRoute.Favorites>() == true)
        assertEquals(libraryBounds, contentBounds(libraryId))
        capture("back-restored-library")
    }

    @Test
    fun player_collapse_and_native_login_sheet_dismissal_restore_the_destination() {
        val context = InstrumentationRegistry.getInstrumentation().targetContext
        val playback = PodcastPlaybackController(context)
        playback.seedForScreenshot(
            PodcastPlaybackItem(
                episodeId = -3993,
                podcastId = -3993,
                podcastTitle = "Transition test",
                episodeTitle = "A conversation worth keeping",
                audioUrl = "https://example.invalid/test.mp3",
                artworkUrl = null,
            ),
        )
        val login = mutableStateOf(false)
        hiltRule.inject()
        composeRule.setContent {
            navController = rememberNavController()
            LaughTrackTheme {
                AppShell(
                    navController = navController,
                    playbackController = playback,
                    showLoginPrompt = login.value,
                    onLoginPromptDismiss = { login.value = false },
                )
            }
        }
        try {
            composeRule.onNodeWithText("A conversation worth keeping").performClick()
            composeRule.onNodeWithContentDescription("Collapse player").assertIsDisplayed()
            capture("player-expanded")
            composeRule.onNodeWithContentDescription("Collapse player").performClick()
            composeRule.onNodeWithText("Search").assertIsDisplayed()
            composeRule.onNodeWithText("A conversation worth keeping").assertIsDisplayed()
            capture("player-collapsed")
            composeRule.runOnIdle { login.value = true }
            composeRule.onNodeWithText("Sign in to save favorites").assertIsDisplayed()
            capture("login-sheet")
            composeRule.onNodeWithText("Not now").performScrollTo().performClick()
            composeRule.onNodeWithText("Sign in to save favorites").assertDoesNotExist()
            composeRule.onNodeWithText("Search").assertIsDisplayed()
            capture("login-sheet-dismissed")
        } finally {
            composeRule.runOnIdle { playback.stop() }
        }
    }

    private fun showShell() {
        hiltRule.inject()
        composeRule.setContent {
            navController = rememberNavController()
            LaughTrackTheme { AppShell(navController = navController) }
        }
        composeRule.waitForIdle()
    }

    private fun animationsEnabled() =
        Settings.Global.getFloat(
            composeRule.activity.contentResolver, Settings.Global.ANIMATOR_DURATION_SCALE, 1f,
        ) > 0f

    private companion object {
        const val HOME_FEED = """
            {"data":{
                "hero":{"shows":[],"zipCode":"10001","city":"New York","state":"NY"},
                "trendingComedians":[],"comediansNearYou":[],"showsTonight":[],"moreNearYou":[],
                "trendingThisWeek":[],"followedComedianShows":[],"trendingPodcasts":[],"popularClubs":[]
            }}
        """
    }

    private fun currentId(): Int = navController.currentDestination!!.id

    private fun contentTag(id: Int) = "app-shell-content-$id"

    private fun contentBounds(id: Int): Rect =
        composeRule.onNodeWithTag(
            contentTag(id),
        ).fetchSemanticsNode().boundsInRoot

    private fun homeScroll(): Float =
        composeRule.onNodeWithTag(HOME_DISCOVER_LIST_TEST_TAG)
            .fetchSemanticsNode().config[SemanticsProperties.VerticalScrollAxisRange].value()

    private fun backEvent(progress: Float) = BackEventCompat(0f, 400f, progress, BackEventCompat.EDGE_LEFT)

    private fun capture(name: String) {
        if (composeRule.mainClock.autoAdvance) {
            // Dialog windows can enqueue their entrance after the first semantics pass.
            composeRule.mainClock.advanceTimeBy(600)
            composeRule.waitForIdle()
        }
        val instrumentation = InstrumentationRegistry.getInstrumentation()
        val directory = File(instrumentation.targetContext.getExternalFilesDir(null), "task3993").apply { mkdirs() }
        instrumentation.waitForIdleSync()
        // Allow the system compositor to present the frame already checked by Compose.
        SystemClock.sleep(180)
        val bitmap = instrumentation.uiAutomation.takeScreenshot()
        File(directory, "$name.png").outputStream().use { bitmap.compress(Bitmap.CompressFormat.PNG, 100, it) }
        bitmap.recycle()
    }
}
