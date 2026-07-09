package app.laughtrack.android.feature.detail.ui

import app.laughtrack.android.core.data.auth.CurrentUserState
import app.laughtrack.android.core.network.generated.api.ShowsApi
import app.laughtrack.android.core.network.generated.model.ShowDetail
import app.laughtrack.android.core.network.generated.model.ShowDetailClub
import app.laughtrack.android.core.network.generated.model.ShowDetailCta
import app.laughtrack.android.core.network.generated.model.ShowDetailResponse
import app.laughtrack.android.core.testing.throwingApi
import app.laughtrack.android.core.ui.UiState
import app.laughtrack.android.feature.detail.data.ShowDetailRepository
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
class ShowDetailViewModelTest {
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
    fun load_publishes_success_with_ticket_outbound_url() =
        runTest {
            val viewModel = viewModel(FakeShowsApi())

            viewModel.load(7)
            assertEquals(UiState.Loading, viewModel.state.value)
            advanceUntilIdle()

            val state = viewModel.state.value
            assertTrue(state is UiState.Success)
            val ui = (state as UiState.Success).value
            assertEquals(7, ui.detail.id)
            assertTrue(ui.ticketOutboundUrl!!.startsWith("https://api.example.com/tickets/out?showId=7"))
        }

    @Test
    fun load_failure_publishes_failure_state() =
        runTest {
            val viewModel = viewModel(FakeShowsApi(failuresBeforeSuccess = Int.MAX_VALUE))

            viewModel.load(7)
            advanceUntilIdle()

            val state = viewModel.state.value
            assertTrue(state is UiState.Failure)
            assertTrue((state as UiState.Failure).error is IOException)
        }

    @Test
    fun retry_recovers_from_failure() =
        runTest {
            val api = FakeShowsApi(failuresBeforeSuccess = 1)
            val viewModel = viewModel(api)

            viewModel.load(7)
            advanceUntilIdle()
            assertTrue(viewModel.state.value is UiState.Failure)

            viewModel.retry()
            advanceUntilIdle()

            assertTrue(viewModel.state.value is UiState.Success)
            assertEquals(2, api.getShowCalls)
        }

    private fun viewModel(showsApi: ShowsApi): ShowDetailViewModel =
        ShowDetailViewModel(
            repository =
                ShowDetailRepository(
                    showsApi = showsApi,
                    apiBaseUrl = "https://api.example.com",
                ),
            currentUserState = CurrentUserState(),
        )

    private class FakeShowsApi(
        private var failuresBeforeSuccess: Int = 0,
    ) : ShowsApi by throwingApi() {
        var getShowCalls = 0
            private set

        override suspend fun getShow(id: Int): Response<ShowDetailResponse> {
            getShowCalls += 1
            if (failuresBeforeSuccess > 0) {
                failuresBeforeSuccess -= 1
                throw IOException("network down")
            }
            return Response.success(
                ShowDetailResponse(
                    data = showDetail(id),
                    relatedShows = emptyList(),
                ),
            )
        }
    }

    private companion object {
        fun showDetail(id: Int) =
            ShowDetail(
                id = id,
                date = "2026-07-09T20:00:00-04:00",
                imageUrl = "https://example.com/show-$id.jpg",
                showPageUrl = "https://example.com/show/$id",
                club = ShowDetailClub(id = 42, name = "Comedy Room", imageUrl = "https://example.com/club.jpg"),
                cta = ShowDetailCta(label = "Buy tickets", isSoldOut = false, url = "https://tickets.example.com/$id"),
                name = "Show $id",
            )
    }
}
