package app.laughtrack.android.feature.search.ui

import app.laughtrack.android.core.analytics.AnalyticsManager
import app.laughtrack.android.core.data.location.HomeLocation
import app.laughtrack.android.core.data.location.HomeLocationState
import app.laughtrack.android.core.network.generated.api.ShowsApi
import app.laughtrack.android.core.network.generated.model.Show
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
import kotlinx.coroutines.test.advanceTimeBy
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

    @Test
    fun search_created_before_home_location_resolves_reseeds_when_home_location_arrives() =
        runTest {
            val showsApi = SuspendingShowsApi()
            val homeLocationState = HomeLocationState()
            val viewModel = viewModel(showsApi, homeLocationState = homeLocationState)
            advanceUntilIdle()
            assertNull(showsApi.lastZip)
            assertEquals(DEFAULT_DISTANCE_MILES, showsApi.lastDistance)

            homeLocationState.update("60614", 50)
            advanceUntilIdle()

            val query = viewModel.state.value.states.getValue(SearchPivot.SHOWS).query
            assertEquals("60614", query.zip)
            assertEquals(50, query.distance)
            assertEquals(2, showsApi.searchCalls)
            assertEquals("60614", showsApi.lastZip)
            assertEquals(50, showsApi.lastDistance)

            showsApi.completeLatestSearch()
            advanceUntilIdle()
        }

    @Test
    fun home_location_change_updates_untouched_search_seed() =
        runTest {
            val showsApi = SuspendingShowsApi()
            val homeLocationState = HomeLocationState().apply { update("60614", 50) }
            val viewModel = viewModel(showsApi, homeLocationState = homeLocationState)
            advanceUntilIdle()
            showsApi.completeLatestSearch()
            advanceUntilIdle()

            homeLocationState.update("10001", 100)
            advanceUntilIdle()

            val query = viewModel.state.value.states.getValue(SearchPivot.SHOWS).query
            assertEquals("10001", query.zip)
            assertEquals(100, query.distance)
            assertEquals(2, showsApi.searchCalls)
            assertEquals("10001", showsApi.lastZip)
            assertEquals(100, showsApi.lastDistance)

            showsApi.completeLatestSearch()
            advanceUntilIdle()
        }

    @Test
    fun user_edited_search_location_stops_home_location_sync() =
        runTest {
            val showsApi = SuspendingShowsApi()
            val homeLocationState = HomeLocationState().apply { update("60614", 50) }
            val viewModel = viewModel(showsApi, homeLocationState = homeLocationState)
            advanceUntilIdle()

            viewModel.setZip("90210")
            advanceUntilIdle()
            homeLocationState.update("10001", 100)
            advanceUntilIdle()

            val query = viewModel.state.value.states.getValue(SearchPivot.SHOWS).query
            assertEquals("90210", query.zip)
            assertEquals(50, query.distance)
            assertEquals(2, showsApi.searchCalls)
            assertEquals("90210", showsApi.lastZip)
            assertEquals(50, showsApi.lastDistance)

            showsApi.completeLatestSearch()
            advanceUntilIdle()
        }

    @Test
    fun text_edits_are_debounced_into_a_single_reload() =
        runTest {
            val showsApi = SuspendingShowsApi()
            val viewModel = viewModel(showsApi)
            advanceUntilIdle()
            showsApi.completeLatestSearch()
            advanceUntilIdle()
            check(showsApi.searchCalls == 1)

            viewModel.onTextChange("st")
            viewModel.onTextChange("stand")
            viewModel.onTextChange("stand up")
            advanceTimeBy(299)

            // Still inside the debounce window: no reload has fired yet.
            assertEquals(1, showsApi.searchCalls)

            advanceUntilIdle()

            // One settled query, one reload — not one per keystroke.
            assertEquals(2, showsApi.searchCalls)
            showsApi.completeLatestSearch()
            advanceUntilIdle()
        }

    @Test
    fun reselecting_a_loaded_pivot_does_not_reload_it() =
        runTest {
            val showsApi = SuspendingShowsApi()
            val viewModel = viewModel(showsApi)
            advanceUntilIdle()
            showsApi.completeLatestSearch()
            advanceUntilIdle()
            check(showsApi.searchCalls == 1)

            viewModel.selectPivot(SearchPivot.SHOWS)
            advanceUntilIdle()

            // Per-pivot state is retained; a loaded pivot is not refetched on select.
            assertEquals(1, showsApi.searchCalls)
        }

    @Test
    fun load_more_requests_the_next_page() =
        runTest {
            val showsApi = SuspendingShowsApi()
            val viewModel = viewModel(showsApi)
            advanceUntilIdle()
            // Page 1 returns 1 of 30 results, so more pages exist.
            showsApi.completeLatestSearch(data = listOf(show(1)), total = 30)
            advanceUntilIdle()
            check(showsApi.lastPage == 1)

            viewModel.loadMore()
            advanceUntilIdle()

            assertEquals(2, showsApi.searchCalls)
            assertEquals(2, showsApi.lastPage)
            showsApi.completeLatestSearch(data = listOf(show(2)), total = 30)
            advanceUntilIdle()

            // Both pages accumulated in the pivot state.
            assertEquals(2, viewModel.state.value.current.results.items.size)
        }

    private fun show(id: Int) =
        Show(
            id = id,
            clubId = 10 + id,
            date = "2026-06-25T20:00:00-04:00",
            imageUrl = "https://example.com/show-$id.jpg",
            clubName = "Comedy Room",
            name = "Show $id",
        )

    private fun viewModel(
        showsApi: ShowsApi,
        homeLocation: HomeLocation? = null,
        homeLocationState: HomeLocationState =
            HomeLocationState().apply {
                homeLocation?.let { update(it.zip, it.distanceMiles) }
            },
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
            homeLocationState = homeLocationState,
        )

    private class SuspendingShowsApi : ShowsApi {
        var searchCalls = 0
        var lastPage: Int? = null
        var lastZip: String? = null
        var lastDistance: Int? = null
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
            lastPage = page
            lastZip = zip
            lastDistance = distance
            val pending = CompletableDeferred<Response<ShowSearchResponse>>()
            pendingSearches += pending
            return pending.await()
        }

        fun completeLatestSearch(
            data: List<Show> = emptyList(),
            total: Int = data.size,
        ) {
            pendingSearches
                .last()
                .complete(
                    Response.success(
                        ShowSearchResponse(
                            data = data,
                            total = total,
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
