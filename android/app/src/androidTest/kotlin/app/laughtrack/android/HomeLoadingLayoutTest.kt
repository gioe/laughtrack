package app.laughtrack.android

import android.graphics.Bitmap
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.ui.geometry.Rect
import androidx.compose.ui.graphics.asAndroidBitmap
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.captureToImage
import androidx.compose.ui.test.junit4.createAndroidComposeRule
import androidx.compose.ui.test.onAllNodesWithTag
import androidx.compose.ui.test.onAllNodesWithText
import androidx.compose.ui.test.onNodeWithContentDescription
import androidx.compose.ui.test.onNodeWithTag
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.onRoot
import androidx.compose.ui.test.performClick
import androidx.lifecycle.ViewModelStore
import androidx.test.espresso.Espresso
import androidx.test.platform.app.InstrumentationRegistry
import app.laughtrack.android.core.analytics.AnalyticsManager
import app.laughtrack.android.core.data.location.HomeLocationState
import app.laughtrack.android.core.network.generated.model.HomeFeed
import app.laughtrack.android.core.network.generated.model.HomeFeedHero
import app.laughtrack.android.core.network.generated.model.Show
import app.laughtrack.android.core.ui.UiState
import app.laughtrack.android.core.ui.components.RemoteImageFallback
import app.laughtrack.android.core.ui.components.RemoteImageTestTags
import app.laughtrack.android.core.ui.theme.LaughTrackTheme
import app.laughtrack.android.feature.home.HomeScreen
import app.laughtrack.android.feature.home.data.HomeFeedCache
import app.laughtrack.android.feature.home.data.HomeFeedRepository
import app.laughtrack.android.feature.home.location.HomeLocationResolver
import app.laughtrack.android.feature.home.ui.HomeViewModel
import dagger.hilt.android.testing.HiltAndroidRule
import dagger.hilt.android.testing.HiltAndroidTest
import kotlinx.coroutines.CompletableDeferred
import kotlinx.coroutines.channels.Channel
import okhttp3.mockwebserver.Dispatcher
import okhttp3.mockwebserver.MockResponse
import okhttp3.mockwebserver.MockWebServer
import okhttp3.mockwebserver.RecordedRequest
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Rule
import org.junit.Test
import java.io.File
import java.io.IOException
import java.util.concurrent.CountDownLatch
import java.util.concurrent.TimeUnit

/** Holds network completion explicitly so the real loading and recovery layouts can be measured. */
@HiltAndroidTest
class HomeLoadingLayoutTest {
    @get:Rule(order = 0)
    val hiltRule = HiltAndroidRule(this)

    @get:Rule(order = 1)
    val composeRule = createAndroidComposeRule<HiltTestActivity>()

    private val viewModelStore = ViewModelStore()

    @After
    fun clearViewModel() {
        composeRule.runOnIdle { viewModelStore.clear() }
    }

    @Test
    fun uncached_feed_and_missing_artwork_preserve_home_geometry() {
        val response = CompletableDeferred<HomeFeed>()
        val viewModel = showHome(HeldRepository(response))
        val loadingBounds = homeBounds()
        capture("loading")
        assertLocationEditorWorks()

        composeRule.runOnIdle { response.complete(feed(withShow = true)) }
        composeRule.waitUntil { viewModel.state.value.feed is UiState.Success }
        composeRule.onNodeWithText(SHOW_TITLE).assertIsDisplayed()
        assertEquals(loadingBounds, homeBounds())
        capture("populated-missing-artwork")
    }

    @Test
    fun delayed_artwork_keeps_its_frame_when_the_image_request_fails() {
        val requested = CountDownLatch(1)
        val release = CountDownLatch(1)
        val server = MockWebServer()
        server.dispatcher =
            object : Dispatcher() {
                override fun dispatch(request: RecordedRequest): MockResponse {
                    requested.countDown()
                    release.await(30, TimeUnit.SECONDS)
                    return MockResponse().setResponseCode(404)
                }
            }
        server.start()
        try {
            val artworkUrl = server.url("/held-artwork.jpg").toString()
            val response = CompletableDeferred<HomeFeed>()
            showHome(HeldRepository(response))
            val initialBounds = homeBounds()
            composeRule.runOnIdle {
                response.complete(feed(withShow = true, artworkUrl = artworkUrl))
            }
            composeRule.onNodeWithText(SHOW_TITLE).assertIsDisplayed()
            assertTrue("The hero requests its artwork", requested.await(10, TimeUnit.SECONDS))
            composeRule.onNodeWithTag(RemoteImageTestTags.SKELETON, useUnmergedTree = true).assertIsDisplayed()
            assertEquals(initialBounds, homeBounds())
            capture("delayed-artwork")

            release.countDown()
            val fallbackTag = RemoteImageTestTags.fallback(RemoteImageFallback.Show)
            composeRule.waitUntil(timeoutMillis = 10_000) {
                composeRule.onAllNodesWithTag(fallbackTag, useUnmergedTree = true).fetchSemanticsNodes().isNotEmpty()
            }
            composeRule.onNodeWithTag(fallbackTag, useUnmergedTree = true).assertIsDisplayed()
            assertEquals(initialBounds, homeBounds())
            capture("failed-artwork")
        } finally {
            release.countDown()
            server.shutdown()
        }
    }

    @Test
    fun failure_retry_and_empty_feed_preserve_geometry_and_location_access() {
        val initialResponse = CompletableDeferred<HomeFeed>()
        val retryResponse = CompletableDeferred<HomeFeed>()
        val viewModel = showHome(HeldRepository(initialResponse, retryResponse))
        val loadingBounds = homeBounds()

        composeRule.runOnIdle { initialResponse.completeExceptionally(IOException("Offline fixture")) }
        composeRule.waitUntil { viewModel.state.value.feed is UiState.Failure }
        composeRule.onNodeWithText("Retry").assertIsDisplayed()
        assertEquals(loadingBounds, homeBounds())
        capture("offline")
        assertLocationEditorWorks()

        composeRule.onNodeWithText("Retry").performClick()
        composeRule.waitUntil { viewModel.state.value.feed is UiState.Loading }
        assertEquals(loadingBounds, homeBounds())
        capture("retry-loading")

        composeRule.runOnIdle { retryResponse.complete(feed(withShow = false)) }
        composeRule.waitUntil { viewModel.state.value.feed is UiState.Success }
        composeRule.onNodeWithText("More laughs soon").assertIsDisplayed()
        assertEquals(loadingBounds, homeBounds())
        capture("empty")
        assertLocationEditorWorks()
    }

    @Test
    fun cached_content_remains_visible_through_failed_refresh_and_retry() {
        val refreshResponse = CompletableDeferred<HomeFeed>()
        val retryResponse = CompletableDeferred<HomeFeed>()
        val viewModel = showHome(HeldRepository(refreshResponse, retryResponse), feed(withShow = true))
        composeRule.onNodeWithText(SHOW_TITLE).assertIsDisplayed()
        val cachedBounds = homeBounds()
        capture("cached-refresh")

        composeRule.runOnIdle { refreshResponse.completeExceptionally(IOException("Offline fixture")) }
        composeRule.onNodeWithText("Retry").assertIsDisplayed()
        composeRule.onNodeWithText(SHOW_TITLE).assertIsDisplayed()
        assertEquals(cachedBounds, homeBounds())
        capture("cached-offline")

        composeRule.onNodeWithText("Retry").performClick()
        composeRule.onNodeWithText(SHOW_TITLE).assertIsDisplayed()
        assertEquals(cachedBounds, homeBounds())
        composeRule.runOnIdle { retryResponse.complete(feed(withShow = true)) }
        composeRule.waitUntil { viewModel.state.value.feed is UiState.Success }
        assertEquals(cachedBounds, homeBounds())
    }

    private fun showHome(
        repository: HomeFeedRepository,
        cachedFeed: HomeFeed? = null,
    ): HomeViewModel {
        hiltRule.inject()
        lateinit var viewModel: HomeViewModel
        composeRule.runOnUiThread {
            viewModel =
                HomeViewModel(
                    repository,
                    MemoryCache(cachedFeed),
                    object : HomeLocationResolver {
                        override suspend fun resolveZip(): String? = null
                    },
                    HomeLocationState(),
                    AnalyticsManager(emptyList()),
                )
            viewModelStore.put("home", viewModel)
        }
        composeRule.setContent {
            LaughTrackTheme {
                Surface(color = MaterialTheme.colorScheme.background) {
                    HomeScreen(onOpenEntity = {}, onPlay = {}, onOpenSearch = {}, viewModel = viewModel)
                }
            }
        }
        return viewModel
    }

    private fun homeBounds(): List<Rect> =
        listOf("homeDiscoverHeader", "homeDiscoverLocation", "homeFeaturedSurface").map { tag ->
            composeRule.onNodeWithTag(tag).assertIsDisplayed().fetchSemanticsNode().boundsInRoot
        }

    private fun assertLocationEditorWorks() {
        composeRule.onNodeWithContentDescription("Edit location").performClick()
        composeRule.onNodeWithText("Choose where Discover looks for shows, clubs, and comedians.").assertIsDisplayed()
        Espresso.pressBack()
        composeRule.waitUntil {
            composeRule.onAllNodesWithText("Choose where Discover looks for shows, clubs, and comedians.")
                .fetchSemanticsNodes().isEmpty()
        }
        composeRule.onNodeWithText("Choose where Discover looks for shows, clubs, and comedians.").assertDoesNotExist()
    }

    private fun capture(name: String) {
        composeRule.waitForIdle()
        val instrumentation = InstrumentationRegistry.getInstrumentation()
        val directory = File(instrumentation.targetContext.filesDir, "home-loading-layout").apply { mkdirs() }
        val bitmap = composeRule.onRoot().captureToImage().asAndroidBitmap()
        File(directory, "$name.png").outputStream().use { bitmap.compress(Bitmap.CompressFormat.PNG, 100, it) }
        bitmap.recycle()
    }

    private class HeldRepository(vararg responses: CompletableDeferred<HomeFeed>) : HomeFeedRepository {
        private val pending =
            Channel<CompletableDeferred<HomeFeed>>(Channel.UNLIMITED).apply {
                responses.forEach { trySend(it) }
            }

        override suspend fun getHomeFeed(
            zip: String?,
            distance: Int?,
        ): HomeFeed = pending.receive().await()
    }

    private class MemoryCache(private var feed: HomeFeed?) : HomeFeedCache {
        override suspend fun get(
            zip: String?,
            distance: Int?,
        ): HomeFeed? = feed

        override suspend fun set(
            zip: String?,
            distance: Int?,
            feed: HomeFeed,
        ) {
            this.feed = feed
        }
    }

    private fun feed(
        withShow: Boolean,
        artworkUrl: String = "",
    ): HomeFeed {
        val shows =
            if (withShow) {
                listOf(
                    Show(
                        id = 1,
                        clubId = 10,
                        date = "2026-09-12T20:00:00-04:00",
                        imageUrl = artworkUrl,
                        clubName = "Comedy Room",
                        clubCity = "New York",
                        clubState = "NY",
                        name = SHOW_TITLE,
                    ),
                )
            } else {
                emptyList()
            }
        return HomeFeed(
            hero = HomeFeedHero(shows = shows, zipCode = "10001", city = "New York", state = "NY"),
            trendingComedians = emptyList(),
            comediansNearYou = emptyList(),
            showsTonight = shows,
            moreNearYou = emptyList(),
            trendingThisWeek = emptyList(),
            followedComedianShows = emptyList(),
            trendingPodcasts = emptyList(),
            popularClubs = emptyList(),
        )
    }

    private companion object {
        const val SHOW_TITLE = "A NIGHT OF COMEDY"
    }
}
