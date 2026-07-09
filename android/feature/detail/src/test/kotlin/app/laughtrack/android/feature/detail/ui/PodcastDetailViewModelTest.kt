package app.laughtrack.android.feature.detail.ui

import app.laughtrack.android.core.network.generated.api.PodcastsApi
import app.laughtrack.android.core.network.generated.model.PodcastDetailPodcast
import app.laughtrack.android.core.network.generated.model.PodcastDetailResponse
import app.laughtrack.android.core.playback.PodcastPlaybackItem
import app.laughtrack.android.core.testing.throwingApi
import app.laughtrack.android.core.ui.UiState
import app.laughtrack.android.feature.detail.data.PodcastDetailRepository
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
import retrofit2.Response
import java.io.IOException

@OptIn(ExperimentalCoroutinesApi::class)
class PodcastDetailViewModelTest {
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
    fun load_publishes_success_with_podcast_payload() =
        runTest {
            val viewModel = viewModel(FakePodcastsApi())

            viewModel.load(3)
            assertEquals(UiState.Loading, viewModel.state.value)
            advanceUntilIdle()

            val state = viewModel.state.value
            assertTrue(state is UiState.Success)
            assertEquals("Podcast 3", (state as UiState.Success).value.podcast.title)
        }

    @Test
    fun load_failure_publishes_failure_state() =
        runTest {
            val viewModel = viewModel(FakePodcastsApi(detailFails = true))

            viewModel.load(3)
            advanceUntilIdle()

            val state = viewModel.state.value
            assertTrue(state is UiState.Failure)
            assertTrue((state as UiState.Failure).error is IOException)
        }

    @Test
    fun play_forwards_item_to_playback_handler() =
        runTest {
            val played = mutableListOf<PodcastPlaybackItem>()
            val viewModel =
                PodcastDetailViewModel(
                    repository = PodcastDetailRepository(FakePodcastsApi()),
                    onPlay = played::add,
                )
            val item =
                PodcastPlaybackItem(
                    episodeId = 11,
                    podcastId = 3,
                    podcastTitle = "Podcast 3",
                    episodeTitle = "Episode 11",
                    audioUrl = "https://example.com/episode-11.mp3",
                    artworkUrl = null,
                )

            viewModel.play(item)

            assertEquals(listOf(item), played)
        }

    private fun viewModel(podcastsApi: PodcastsApi): PodcastDetailViewModel =
        PodcastDetailViewModel(
            repository = PodcastDetailRepository(podcastsApi),
            onPlay = {},
        )

    private class FakePodcastsApi(
        private val detailFails: Boolean = false,
    ) : PodcastsApi by throwingApi() {
        override suspend fun getPodcast(id: Int): Response<PodcastDetailResponse> {
            if (detailFails) throw IOException("network down")
            return Response.success(
                PodcastDetailResponse(
                    podcast =
                        PodcastDetailPodcast(
                            id = id,
                            slug = "podcast-$id",
                            title = "Podcast $id",
                            episodeCount = 0,
                            hosts = emptyList(),
                        ),
                    episodes = emptyList(),
                    relatedComedians = emptyList(),
                ),
            )
        }
    }
}
