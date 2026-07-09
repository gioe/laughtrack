package app.laughtrack.android.feature.home

import app.laughtrack.android.core.network.generated.model.ClubListItem
import app.laughtrack.android.core.network.generated.model.ComedianListItem
import app.laughtrack.android.core.network.generated.model.HomeFeed
import app.laughtrack.android.core.network.generated.model.HomeFeedHero
import app.laughtrack.android.core.network.generated.model.HomeFeedPodcast
import app.laughtrack.android.core.network.generated.model.Show
import app.laughtrack.android.core.network.generated.model.SocialData
import app.laughtrack.android.core.ui.UiState
import app.laughtrack.android.feature.home.data.HomeFeedCache
import app.laughtrack.android.feature.home.data.HomeFeedRepository
import app.laughtrack.android.feature.home.location.HomeLocationResolver
import app.laughtrack.android.feature.home.ui.HomeViewModel
import kotlinx.coroutines.CompletableDeferred
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.test.StandardTestDispatcher
import kotlinx.coroutines.test.advanceUntilIdle
import kotlinx.coroutines.test.resetMain
import kotlinx.coroutines.test.runTest
import kotlinx.coroutines.test.setMain
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test
import java.io.IOException

@OptIn(ExperimentalCoroutinesApi::class)
class HomeViewModelTest {
    private val dispatcher = StandardTestDispatcher()

    @Before
    fun setUp() {
        Dispatchers.setMain(dispatcher)
    }

    @After
    fun tearDown() {
        Dispatchers.resetMain()
    }

    @Test
    fun load_replaces_skeleton_state_with_feed_content() =
        runTest {
            val repository = FakeHomeFeedRepository(feed = homeFeed())
            val viewModel = viewModel(repository)

            assertEquals(UiState.Loading, viewModel.state.value.feed)
            advanceUntilIdle()

            val state = viewModel.state.value
            assertTrue(state.feed is UiState.Success)
            assertEquals("Near New York, NY", state.locationTitle)
            assertEquals(2, state.showsTonight.size)
            assertEquals(1, state.trendingThisWeek.size)
            assertEquals(1, state.comedians.size)
            assertEquals(1, state.clubs.size)
            assertEquals(1, state.podcasts.size)
            assertEquals(1, repository.loads)
        }

    @Test
    fun retry_recovers_from_user_visible_error_state() =
        runTest {
            val repository =
                FakeHomeFeedRepository(
                    failuresBeforeSuccess = 1,
                    feed = homeFeed(),
                )
            val viewModel = viewModel(repository)
            advanceUntilIdle()

            assertTrue(viewModel.state.value.feed is UiState.Failure)

            viewModel.retry()
            advanceUntilIdle()

            assertTrue(viewModel.state.value.feed is UiState.Success)
            assertEquals(2, repository.loads)
        }

    @Test
    fun cached_feed_survives_network_failure() =
        runTest {
            // Cache holds a prior snapshot; the network always fails. The user keeps
            // seeing the cached feed instead of an error (criterion: re-render from cache).
            val repository = FakeHomeFeedRepository(failuresBeforeSuccess = Int.MAX_VALUE, feed = homeFeed())
            val cache = FakeHomeFeedCache(stored = homeFeed())
            val viewModel = viewModel(repository, cache)
            advanceUntilIdle()

            assertTrue(viewModel.state.value.feed is UiState.Success)
        }

    @Test
    fun successful_load_writes_through_to_cache() =
        runTest {
            val cache = FakeHomeFeedCache()
            val viewModel = viewModel(FakeHomeFeedRepository(feed = homeFeed()), cache)
            advanceUntilIdle()

            assertEquals(1, cache.sets)
        }

    @Test
    fun manual_zip_reloads_feed_scoped_to_that_zip() =
        runTest {
            val repository = FakeHomeFeedRepository(feed = homeFeed())
            val viewModel = viewModel(repository)
            advanceUntilIdle()

            viewModel.setManualZip("90210")
            advanceUntilIdle()

            assertEquals("90210", repository.lastZip)
            assertEquals(2, repository.loads)
        }

    @Test
    fun use_device_location_reloads_with_resolved_zip() =
        runTest {
            val repository = FakeHomeFeedRepository(feed = homeFeed())
            val resolver = FakeLocationResolver(zip = "60614")
            val viewModel = viewModel(repository, resolver = resolver)
            advanceUntilIdle()

            viewModel.useDeviceLocation()
            advanceUntilIdle()

            assertEquals("60614", repository.lastZip)
            assertTrue(repository.loads >= 2)
        }

    @Test
    fun device_location_load_cancels_superseded_manual_zip_load() =
        runTest {
            val repository = SupersededHomeFeedRepository()
            val resolver = FakeLocationResolver(zip = "60614")
            val viewModel = viewModel(repository, resolver = resolver)
            advanceUntilIdle()

            viewModel.setManualZip("90210")
            advanceUntilIdle()
            viewModel.useDeviceLocation()
            advanceUntilIdle()

            assertEquals("60614", viewModel.state.value.zip)

            repository.completeManualZip()
            advanceUntilIdle()

            assertEquals("60614", viewModel.state.value.zip)
            assertEquals("ZIP 60614", viewModel.state.value.locationTitle)
        }

    private fun viewModel(
        repository: HomeFeedRepository,
        cache: HomeFeedCache = FakeHomeFeedCache(),
        resolver: HomeLocationResolver = FakeLocationResolver(),
    ) = HomeViewModel(repository, cache, resolver)

    private class FakeHomeFeedRepository(
        private val failuresBeforeSuccess: Int = 0,
        private val feed: HomeFeed,
    ) : HomeFeedRepository {
        var loads = 0
        var lastZip: String? = null

        override suspend fun getHomeFeed(
            zip: String?,
            distance: Int?,
        ): HomeFeed {
            loads += 1
            lastZip = zip
            if (loads <= failuresBeforeSuccess) {
                throw IOException("Home feed failed")
            }
            return feed
        }
    }

    private class FakeHomeFeedCache(
        private val stored: HomeFeed? = null,
    ) : HomeFeedCache {
        var sets = 0

        override suspend fun get(
            zip: String?,
            distance: Int?,
        ): HomeFeed? = stored

        override suspend fun set(
            zip: String?,
            distance: Int?,
            feed: HomeFeed,
        ) {
            sets += 1
        }
    }

    private class FakeLocationResolver(
        private val zip: String? = null,
    ) : HomeLocationResolver {
        override suspend fun resolveZip(): String? = zip
    }

    private inner class SupersededHomeFeedRepository : HomeFeedRepository {
        private val manualZipFeed = CompletableDeferred<HomeFeed>()

        override suspend fun getHomeFeed(
            zip: String?,
            distance: Int?,
        ): HomeFeed =
            when (zip) {
                "90210" -> manualZipFeed.await()
                "60614" -> homeFeed(zipCode = "60614", city = null, state = null)
                else -> homeFeed()
            }

        fun completeManualZip() {
            manualZipFeed.complete(homeFeed(zipCode = "90210", city = null, state = null))
        }
    }

    private fun homeFeed(
        zipCode: String = "10001",
        city: String? = "New York",
        state: String? = "NY",
    ): HomeFeed {
        val heroShow = show(1, "Friday Night Laughs")
        val tonightShow = show(2, "Late Show")
        val weekShow = show(3, "Weekend Showcase")
        return HomeFeed(
            hero =
                HomeFeedHero(
                    shows = listOf(heroShow),
                    zipCode = zipCode,
                    city = city,
                    state = state,
                ),
            trendingComedians = listOf(comedian()),
            comediansNearYou = emptyList(),
            showsTonight = listOf(heroShow, tonightShow),
            moreNearYou = emptyList(),
            trendingThisWeek = listOf(weekShow),
            trendingPodcasts = listOf(podcast()),
            popularClubs = listOf(club()),
        )
    }

    private fun show(
        id: Int,
        name: String,
    ) = Show(
        id = id,
        clubId = 10 + id,
        date = "2026-06-25T20:00:00-04:00",
        imageUrl = "https://example.com/show-$id.jpg",
        clubName = "Comedy Room",
        clubCity = "New York",
        clubState = "NY",
        name = name,
    )

    private fun comedian() =
        ComedianListItem(
            id = 7,
            uuid = "comedian-7",
            name = "Jane Comic",
            imageUrl = "https://example.com/jane.jpg",
            socialData = SocialData(id = 7),
            showCount = 4,
        )

    private fun club() =
        ClubListItem(
            id = 9,
            address = "123 Main St, New York, NY",
            name = "Comedy Room",
            imageUrl = "https://example.com/club.jpg",
            activeComedianCount = 12,
            zipCode = "10001",
        )

    private fun podcast() =
        HomeFeedPodcast(
            id = 11,
            slug = "laughs-weekly",
            title = "Laughs Weekly",
            episodeCount = 48,
            authorName = "LaughTrack",
            imageUrl = "https://example.com/podcast.jpg",
        )
}
