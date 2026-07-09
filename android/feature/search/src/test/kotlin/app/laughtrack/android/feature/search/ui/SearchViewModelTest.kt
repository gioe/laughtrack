package app.laughtrack.android.feature.search.ui

import app.laughtrack.android.core.analytics.AnalyticsManager
import app.laughtrack.android.core.data.location.HomeLocation
import app.laughtrack.android.core.data.location.HomeLocationState
import app.laughtrack.android.core.network.generated.api.ShowsApi
import app.laughtrack.android.core.network.generated.model.ShowDetailResponse
import app.laughtrack.android.core.network.generated.model.ShowListResponse
import app.laughtrack.android.core.network.generated.model.ShowSearchResponse
import app.laughtrack.android.feature.search.data.SearchRepository
import app.laughtrack.android.feature.search.model.DEFAULT_DISTANCE_MILES
import app.laughtrack.android.feature.search.model.SearchPivot
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
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test
import retrofit2.Response
import java.lang.reflect.Proxy

@OptIn(ExperimentalCoroutinesApi::class)
class SearchViewModelTest {
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
    fun cancelled_previous_query_does_not_write_failed_state() =
        runTest {
            val showsApi = SuspendingShowsApi()
            val viewModel = viewModel(showsApi)
            advanceUntilIdle()

            viewModel.updateQuery { it.copy(text = "new search") }
            advanceUntilIdle()

            assertEquals(2, showsApi.searchCalls)
            assertTrue(viewModel.state.value.current.results.isLoading)
            assertNull(viewModel.state.value.current.results.error)

            showsApi.completeLatestSearch()
            advanceUntilIdle()
        }

    @Test
    fun search_seeds_shows_pivot_from_home_location() =
        runTest {
            val showsApi = SuspendingShowsApi()
            val viewModel = viewModel(showsApi, homeLocation = HomeLocation("60614", 50))
            advanceUntilIdle()

            val query = viewModel.state.value.states.getValue(SearchPivot.SHOWS).query
            assertEquals("60614", query.zip)
            assertEquals(50, query.distance)
            // Non-geo pivots stay nationwide.
            assertNull(viewModel.state.value.states.getValue(SearchPivot.COMEDIANS).query.zip)

            showsApi.completeLatestSearch()
            advanceUntilIdle()
        }

    @Test
    fun search_stays_global_without_home_location() =
        runTest {
            val showsApi = SuspendingShowsApi()
            val viewModel = viewModel(showsApi)
            advanceUntilIdle()

            val query = viewModel.state.value.states.getValue(SearchPivot.SHOWS).query
            assertNull(query.zip)
            assertEquals(DEFAULT_DISTANCE_MILES, query.distance)

            showsApi.completeLatestSearch()
            advanceUntilIdle()
        }

    private fun viewModel(
        showsApi: ShowsApi,
        homeLocation: HomeLocation? = null,
    ): SearchViewModel =
        SearchViewModel(
            repository =
                SearchRepository(
                    showsApi = showsApi,
                    comediansApi = throwingApi(),
                    clubsApi = throwingApi(),
                    podcastsApi = throwingApi(),
                ),
            analytics = AnalyticsManager(emptyList()),
            homeLocationState =
                HomeLocationState().apply {
                    homeLocation?.let { update(it.zip, it.distanceMiles) }
                },
        )

    private class SuspendingShowsApi : ShowsApi {
        var searchCalls = 0
        private val pendingSearches = mutableListOf<CompletableDeferred<Response<ShowSearchResponse>>>()

        override suspend fun searchShows(
            zip: String?,
            from: String?,
            to: String?,
            page: Int?,
            size: Int?,
            comedian: String?,
            club: String?,
            filters: String?,
            distance: Int?,
            sort: String?,
            xTimezone: String?,
        ): Response<ShowSearchResponse> {
            searchCalls += 1
            val pending = CompletableDeferred<Response<ShowSearchResponse>>()
            pendingSearches += pending
            return pending.await()
        }

        fun completeLatestSearch() {
            pendingSearches
                .last()
                .complete(
                    Response.success(
                        ShowSearchResponse(
                            data = emptyList(),
                            total = 0,
                            filters = emptyList(),
                            zipCapTriggered = false,
                        ),
                    ),
                )
        }

        override suspend fun getShow(id: Int): Response<ShowDetailResponse> = error("Unexpected getShow call")

        override suspend fun getShowsDensity(
            zip: String?,
            from: String?,
            to: String?,
            distance: Int?,
            comedian: String?,
            club: String?,
            xTimezone: String?,
        ): Response<Map<String, Int>> = error("Unexpected getShowsDensity call")

        override suspend fun listShows(
            zip: String,
            from: String?,
            to: String?,
            page: Int?,
            size: Int?,
            comedian: String?,
            filters: String?,
            distance: Int?,
            xTimezone: String?,
        ): Response<ShowListResponse> = error("Unexpected listShows call")
    }

    private inline fun <reified T : Any> throwingApi(): T =
        Proxy.newProxyInstance(T::class.java.classLoader, arrayOf(T::class.java)) { _, method, _ ->
            error("Unexpected ${method.name} call")
        } as T
}
