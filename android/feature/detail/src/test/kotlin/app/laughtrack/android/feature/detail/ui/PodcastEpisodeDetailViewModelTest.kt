package app.laughtrack.android.feature.detail.ui

import app.laughtrack.android.core.network.generated.api.PodcastsApi
import app.laughtrack.android.core.network.generated.model.PodcastDetailEpisode
import app.laughtrack.android.core.network.generated.model.PodcastDetailPodcast
import app.laughtrack.android.core.network.generated.model.PodcastEpisodeDetailResponse
import app.laughtrack.android.core.playback.PodcastPlaybackItem
import app.laughtrack.android.core.testing.throwingApi
import app.laughtrack.android.core.ui.UiState
import app.laughtrack.android.feature.detail.data.PodcastEpisodeDetailRepository
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
class PodcastEpisodeDetailViewModelTest {
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
    fun load_publishes_loading_then_episode_success_for_requested_id() =
        runTest {
            val api = FakePodcastsApi()
            val viewModel = viewModel(api)

            viewModel.load(501)
            assertEquals(UiState.Loading, viewModel.state.value)
            advanceUntilIdle()

            val state = viewModel.state.value
            assertTrue(state is UiState.Success)
            assertEquals(501, (state as UiState.Success).value.episode.id)
            assertEquals(listOf(501), api.requestedIds)
        }

    @Test
    fun retry_reloads_the_same_id_after_a_retryable_failure() =
        runTest {
            val api = FakePodcastsApi(failuresRemaining = 1)
            val viewModel = viewModel(api)

            viewModel.load(501)
            advanceUntilIdle()
            val failed = viewModel.state.value
            assertTrue(failed is UiState.Failure)
            assertTrue((failed as UiState.Failure).error is IOException)

            viewModel.retry()
            assertEquals(UiState.Loading, viewModel.state.value)
            advanceUntilIdle()

            assertTrue(viewModel.state.value is UiState.Success)
            assertEquals(listOf(501, 501), api.requestedIds)
        }

    @Test
    fun play_forwards_the_resolved_episode_to_the_playback_handler() =
        runTest {
            val played = mutableListOf<PodcastPlaybackItem>()
            val viewModel =
                PodcastEpisodeDetailViewModel(
                    repository = PodcastEpisodeDetailRepository(FakePodcastsApi()),
                    onPlay = played::add,
                )
            val item =
                PodcastPlaybackItem(
                    episodeId = 501,
                    podcastId = 42,
                    podcastTitle = "The Laugh Track Pod",
                    episodeTitle = "Comedy Cellar Stories",
                    audioUrl = "https://cdn.example.com/cellar.mp3",
                    artworkUrl = null,
                )

            viewModel.play(item)

            assertEquals(listOf(item), played)
        }

    private fun viewModel(api: PodcastsApi): PodcastEpisodeDetailViewModel =
        PodcastEpisodeDetailViewModel(
            repository = PodcastEpisodeDetailRepository(api),
            onPlay = {},
        )

    private class FakePodcastsApi(
        private var failuresRemaining: Int = 0,
    ) : PodcastsApi by throwingApi() {
        val requestedIds = mutableListOf<Int>()

        override suspend fun getPodcastEpisode(id: Int): Response<PodcastEpisodeDetailResponse> {
            requestedIds += id
            if (failuresRemaining > 0) {
                failuresRemaining -= 1
                throw IOException("network down")
            }
            return Response.success(response(id))
        }
    }

    private companion object {
        fun response(id: Int): PodcastEpisodeDetailResponse =
            PodcastEpisodeDetailResponse(
                podcast =
                    PodcastDetailPodcast(
                        id = 42,
                        slug = "the-laugh-track-pod",
                        title = "The Laugh Track Pod",
                        episodeCount = 75,
                        hosts = emptyList(),
                    ),
                episode =
                    PodcastDetailEpisode(
                        id = id,
                        title = "Episode $id",
                        description = "Full episode description.",
                        releaseDate = "2026-03-01T00:00:00Z",
                        durationSeconds = 3_720,
                        episodeUrl = "https://podcasts.example.com/$id",
                        audioUrl = "https://cdn.example.com/$id.mp3",
                        appearances = emptyList(),
                    ),
            )
    }
}
