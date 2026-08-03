package app.laughtrack.android.feature.detail.ui

import app.laughtrack.android.core.network.generated.api.ComediansApi
import app.laughtrack.android.core.network.generated.api.ShowsApi
import app.laughtrack.android.core.network.generated.model.ComedianDetail
import app.laughtrack.android.core.network.generated.model.GetComedian200Response
import app.laughtrack.android.core.network.generated.model.GetComedianCoBill200Response
import app.laughtrack.android.core.network.generated.model.GetComedianPastShows200Response
import app.laughtrack.android.core.network.generated.model.Show
import app.laughtrack.android.core.network.generated.model.ShowSearchResponse
import app.laughtrack.android.core.network.generated.model.SocialData
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
import org.junit.Assert.assertNull
import org.junit.Before
import org.junit.Test
import retrofit2.Response

@OptIn(ExperimentalCoroutinesApi::class)
class ComedianDetailLocationTest {
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
    fun initial_apply_radius_and_clear_requests_use_the_expected_location() =
        runTest {
            val showsApi = RecordingShowsApi()
            val viewModel = viewModel(showsApi)

            viewModel.load(COMEDIAN_ID)
            advanceUntilIdle()
            assertEquals(ShowRequest(zip = null, distance = null, page = 0), showsApi.requests.last())

            viewModel.setLocation("60614")
            advanceUntilIdle()
            assertEquals(ShowRequest(zip = "60614", distance = 25, page = 0), showsApi.requests.last())

            viewModel.setDistance(50)
            advanceUntilIdle()
            assertEquals(ShowRequest(zip = "60614", distance = 50, page = 0), showsApi.requests.last())

            viewModel.clearLocation()
            advanceUntilIdle()
            assertEquals(ShowRequest(zip = null, distance = null, page = 0), showsApi.requests.last())

            val ui = (viewModel.state.value as UiState.Success).value
            assertNull(ui.activeZip)
            assertEquals(0, ui.currentPinnedShowsPage)
        }

    @Test
    fun location_change_resets_pagination_and_replaces_the_previous_request_results() =
        runTest {
            val showsApi = RecordingShowsApi()
            val viewModel = viewModel(showsApi)
            viewModel.load(COMEDIAN_ID)
            advanceUntilIdle()

            viewModel.loadMoreShows()
            advanceUntilIdle()
            val globalPage = (viewModel.state.value as UiState.Success).value
            assertEquals(1, globalPage.currentPinnedShowsPage)
            assertEquals(listOf(100, 101), globalPage.pinnedShows.map { it.id })

            viewModel.setLocation("60614")
            advanceUntilIdle()

            val localPage = (viewModel.state.value as UiState.Success).value
            assertEquals(0, localPage.currentPinnedShowsPage)
            assertEquals(listOf(200), localPage.pinnedShows.map { it.id })
            assertEquals(
                listOf(
                    ShowRequest(zip = null, distance = null, page = 0),
                    ShowRequest(zip = null, distance = null, page = 1),
                    ShowRequest(zip = "60614", distance = 25, page = 0),
                ),
                showsApi.requests,
            )
        }

    private fun viewModel(showsApi: ShowsApi): ComedianDetailViewModel =
        ComedianDetailViewModel(
            repository = ComedianDetailRepository(FakeComediansApi(), showsApi),
            favoritesRepository = signedOutFavoritesRepository(),
        )

    private class RecordingShowsApi : ShowsApi by throwingApi() {
        val requests = mutableListOf<ShowRequest>()

        override suspend fun searchShows(
            zip: String?,
            from: String?,
            to: String?,
            page: Int?,
            size: Int?,
            comedian: String?,
            club: String?,
            clubId: Int?,
            filters: String?,
            distance: Int?,
            sort: String?,
            xTimezone: String?,
        ): Response<ShowSearchResponse> {
            val request = ShowRequest(zip = zip, distance = distance, page = page ?: 0)
            requests += request
            val id = (if (zip == null) 100 else 200) + request.page
            return Response.success(
                ShowSearchResponse(
                    data = listOf(show(id)),
                    total = 3,
                    filters = emptyList(),
                    zipCapTriggered = false,
                ),
            )
        }
    }

    private class FakeComediansApi : ComediansApi by throwingApi() {
        override suspend fun getComedian(id: Int): Response<GetComedian200Response> =
            Response.success(
                GetComedian200Response(
                    ComedianDetail(
                        id = id,
                        uuid = "comedian-$id",
                        name = "Comedian $id",
                        imageUrl = "https://example.com/comedian-$id.jpg",
                        socialData = SocialData(id = id),
                        podcastAppearances = emptyList(),
                    ),
                ),
            )

        override suspend fun getComedianUpcomingRuns(
            id: Int,
            club: String?,
            location: String?,
            date: String?,
            xTimezone: String?,
        ): Response<UpcomingRunResponse> = Response.success(UpcomingRunResponse(emptyList()))

        override suspend fun getComedianCoBill(id: Int): Response<GetComedianCoBill200Response> =
            Response.success(GetComedianCoBill200Response(emptyList()))

        override suspend fun getComedianPastShows(
            comedian: String,
            page: Int?,
            size: Int?,
            xTimezone: String?,
        ): Response<GetComedianPastShows200Response> =
            Response.success(GetComedianPastShows200Response(data = emptyList(), total = 0))
    }

    private data class ShowRequest(
        val zip: String?,
        val distance: Int?,
        val page: Int,
    )

    private companion object {
        const val COMEDIAN_ID = 5

        fun show(id: Int) =
            Show(
                id = id,
                clubId = id + 10,
                date = "2026-08-20T20:00:00-04:00",
                imageUrl = "https://example.com/show-$id.jpg",
                clubName = "Comedy Room",
                name = "Show $id",
            )
    }
}
