package app.laughtrack.android.feature.home

import app.laughtrack.android.core.data.UiState
import app.laughtrack.android.core.network.generated.model.ClubListItem
import app.laughtrack.android.core.network.generated.model.ComedianListItem
import app.laughtrack.android.core.network.generated.model.HomeFeed
import app.laughtrack.android.core.network.generated.model.HomeFeedHero
import app.laughtrack.android.core.network.generated.model.HomeFeedPodcast
import app.laughtrack.android.core.network.generated.model.Show
import app.laughtrack.android.core.network.generated.model.SocialData
import app.laughtrack.android.feature.home.data.HomeFeedRepository
import app.laughtrack.android.feature.home.ui.HomeViewModel
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
            val viewModel = HomeViewModel(repository)

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
            val viewModel = HomeViewModel(repository)
            advanceUntilIdle()

            assertTrue(viewModel.state.value.feed is UiState.Failure)

            viewModel.retry()
            advanceUntilIdle()

            assertTrue(viewModel.state.value.feed is UiState.Success)
            assertEquals(2, repository.loads)
        }

    private class FakeHomeFeedRepository(
        private val failuresBeforeSuccess: Int = 0,
        private val feed: HomeFeed,
    ) : HomeFeedRepository {
        var loads = 0

        override suspend fun getHomeFeed(
            zip: String?,
            distance: Int?,
        ): HomeFeed {
            loads += 1
            if (loads <= failuresBeforeSuccess) {
                throw IOException("Home feed failed")
            }
            return feed
        }
    }

    private fun homeFeed(): HomeFeed {
        val heroShow = show(1, "Friday Night Laughs")
        val tonightShow = show(2, "Late Show")
        val weekShow = show(3, "Weekend Showcase")
        return HomeFeed(
            hero =
                HomeFeedHero(
                    shows = listOf(heroShow),
                    zipCode = "10001",
                    city = "New York",
                    state = "NY",
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
