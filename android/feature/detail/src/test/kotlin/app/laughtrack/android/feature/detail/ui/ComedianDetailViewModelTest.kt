package app.laughtrack.android.feature.detail.ui

import app.laughtrack.android.core.network.generated.api.ComediansApi
import app.laughtrack.android.core.network.generated.model.ComedianDetail
import app.laughtrack.android.core.network.generated.model.GetComedian200Response
import app.laughtrack.android.core.network.generated.model.GetComedianCoBill200Response
import app.laughtrack.android.core.network.generated.model.GetComedianPastShows200Response
import app.laughtrack.android.core.network.generated.model.SocialData
import app.laughtrack.android.core.network.generated.model.UpcomingRun
import app.laughtrack.android.core.network.generated.model.UpcomingRunResponse
import app.laughtrack.android.core.testing.signedOutFavoritesRepository
import app.laughtrack.android.core.testing.throwingApi
import app.laughtrack.android.core.ui.UiState
import app.laughtrack.android.feature.detail.data.ComedianDetailRepository
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
class ComedianDetailViewModelTest {
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
    fun load_publishes_success_with_tab_data() =
        runTest {
            val viewModel = viewModel(FakeComediansApi())

            viewModel.load(5)
            assertEquals(UiState.Loading, viewModel.state.value)
            advanceUntilIdle()

            val state = viewModel.state.value
            assertTrue(state is UiState.Success)
            val ui = (state as UiState.Success).value
            assertEquals(5, ui.detail.id)
            assertEquals("Comedian 5", ui.detail.name)
            assertEquals(listOf(upcomingRun()), ui.upcomingRuns)
        }

    @Test
    fun secondary_endpoint_failures_degrade_to_empty_lists() =
        runTest {
            // Upcoming runs / past shows / co-bill all throw; the screen still loads.
            val viewModel = viewModel(FakeComediansApi(secondaryCallsFail = true))

            viewModel.load(5)
            advanceUntilIdle()

            val state = viewModel.state.value
            assertTrue(state is UiState.Success)
            val ui = (state as UiState.Success).value
            assertTrue(ui.upcomingRuns.isEmpty())
            assertTrue(ui.pastShows.isEmpty())
            assertTrue(ui.coBill.isEmpty())
        }

    @Test
    fun load_failure_publishes_failure_state() =
        runTest {
            val viewModel = viewModel(FakeComediansApi(detailFails = true))

            viewModel.load(5)
            advanceUntilIdle()

            val state = viewModel.state.value
            assertTrue(state is UiState.Failure)
            assertTrue((state as UiState.Failure).error is IOException)
        }

    private fun viewModel(comediansApi: ComediansApi): ComedianDetailViewModel =
        ComedianDetailViewModel(
            repository = ComedianDetailRepository(comediansApi),
            favoritesRepository = signedOutFavoritesRepository(),
        )

    private class FakeComediansApi(
        private val detailFails: Boolean = false,
        private val secondaryCallsFail: Boolean = false,
    ) : ComediansApi by throwingApi() {
        override suspend fun getComedian(id: Int): Response<GetComedian200Response> {
            if (detailFails) throw IOException("network down")
            return Response.success(GetComedian200Response(comedianDetail(id)))
        }

        override suspend fun getComedianUpcomingRuns(
            id: Int,
            club: String?,
            location: String?,
            date: String?,
            xTimezone: String?,
        ): Response<UpcomingRunResponse> {
            if (secondaryCallsFail) throw IOException("network down")
            return Response.success(UpcomingRunResponse(listOf(upcomingRun())))
        }

        override suspend fun getComedianCoBill(id: Int): Response<GetComedianCoBill200Response> {
            if (secondaryCallsFail) throw IOException("network down")
            return Response.success(GetComedianCoBill200Response(emptyList()))
        }

        override suspend fun getComedianPastShows(
            comedian: String,
            page: Int?,
            size: Int?,
            xTimezone: String?,
        ): Response<GetComedianPastShows200Response> {
            if (secondaryCallsFail) throw IOException("network down")
            return Response.success(GetComedianPastShows200Response(data = emptyList(), total = 0))
        }
    }

    private companion object {
        fun comedianDetail(id: Int) =
            ComedianDetail(
                id = id,
                uuid = "comedian-$id",
                name = "Comedian $id",
                imageUrl = "https://example.com/comedian-$id.jpg",
                socialData = SocialData(id = id),
                podcastAppearances = emptyList(),
            )

        fun upcomingRun() =
            UpcomingRun(
                clubId = 42,
                clubName = "Comedy Room",
                clubImageUrl = "https://example.com/club-42.jpg",
                shows = emptyList(),
            )
    }
}
