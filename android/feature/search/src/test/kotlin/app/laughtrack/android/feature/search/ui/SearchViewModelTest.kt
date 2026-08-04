package app.laughtrack.android.feature.search.ui

import app.laughtrack.android.core.analytics.AnalyticsManager
import app.laughtrack.android.core.data.location.HomeLocation
import app.laughtrack.android.core.data.location.HomeLocationState
import app.laughtrack.android.core.network.generated.api.ShowsApi
import app.laughtrack.android.core.network.generated.model.Filter
import app.laughtrack.android.core.network.generated.model.Show
import app.laughtrack.android.core.network.generated.model.ShowDetailResponse
import app.laughtrack.android.core.network.generated.model.ShowListResponse
import app.laughtrack.android.core.network.generated.model.ShowSearchResponse
import app.laughtrack.android.core.testing.throwingApi
import app.laughtrack.android.feature.search.data.SearchRepository
import app.laughtrack.android.feature.search.model.DEFAULT_DISTANCE_MILES
import app.laughtrack.android.feature.search.model.SearchPivot
import app.laughtrack.android.feature.search.model.ShowActiveConstraintKind
import app.laughtrack.android.feature.search.model.ShowDateShortcut
import app.laughtrack.android.feature.search.model.ShowMaximumPriceOption
import app.laughtrack.android.feature.search.model.ShowResultsPresentation
import app.laughtrack.android.feature.search.model.ShowSearchSeed
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
import java.math.BigDecimal
import java.time.LocalDate

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
    fun explicit_show_entity_edits_are_debounced_into_a_single_reload() =
        runTest {
            val showsApi = SuspendingShowsApi()
            val viewModel = viewModel(showsApi)
            advanceUntilIdle()
            showsApi.completeLatestSearch()
            advanceUntilIdle()
            check(showsApi.searchCalls == 1)

            viewModel.onComedianChange("at")
            viewModel.onComedianChange("atsu")
            viewModel.onComedianChange("Atsuko")
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
    fun show_entity_edit_reloads_after_switching_pivots_before_debounce() =
        runTest {
            val showsApi = SuspendingShowsApi()
            val viewModel = viewModel(showsApi)
            advanceUntilIdle()
            showsApi.completeLatestSearch()
            advanceUntilIdle()

            viewModel.onComedianChange("Atsuko")
            viewModel.selectPivot(SearchPivot.COMEDIANS)
            advanceTimeBy(301)

            // The debounce is skipped while another pivot is active, but the
            // edited Shows state remains stale and reloads on return.
            assertEquals(1, showsApi.searchCalls)
            viewModel.selectPivot(SearchPivot.SHOWS)
            advanceUntilIdle()

            assertEquals(2, showsApi.searchCalls)
            assertEquals("Atsuko", showsApi.lastComedian)
            showsApi.completeLatestSearch()
            advanceUntilIdle()
        }

    @Test
    fun shows_send_explicit_comedian_club_filters_and_maximum_price() =
        runTest {
            val showsApi = SuspendingShowsApi()
            val viewModel = viewModel(showsApi)
            advanceUntilIdle()
            showsApi.completeLatestSearch()
            advanceUntilIdle()

            viewModel.onComedianChange("Atsuko")
            viewModel.onClubChange("The Stand")
            viewModel.toggleFilter("improv")
            viewModel.setMaximumPrice(ShowMaximumPriceOption.FORTY)
            advanceUntilIdle()

            assertEquals("Atsuko", showsApi.lastComedian)
            assertEquals("The Stand", showsApi.lastClub)
            assertEquals("improv", showsApi.lastFilters)
            assertEquals(BigDecimal(40), showsApi.lastMaxPrice)
            showsApi.completeLatestSearch()
            advanceUntilIdle()
        }

    @Test
    fun show_seed_round_trips_and_constraints_remove_or_clear_together() =
        runTest {
            val showsApi = SuspendingShowsApi()
            val viewModel = viewModel(showsApi)
            advanceUntilIdle()
            showsApi.completeLatestSearch()
            advanceUntilIdle()

            val seed =
                ShowSearchSeed(
                    comedian = "Atsuko",
                    club = "The Stand",
                    zip = "10012",
                    locationLabel = "New York, NY",
                    distance = 50,
                    from = "2026-08-07",
                    to = "2026-08-09",
                    filters = setOf("free", "open_mic"),
                    maxPrice = 40,
                    resultsPresentation = ShowResultsPresentation.CALENDAR,
                )

            viewModel.applyShowSearchSeed(seed)
            assertEquals(seed, viewModel.showSearchSeed())
            val constraints = viewModel.activeShowConstraints()
            assertTrue(constraints.any { it.kind == ShowActiveConstraintKind.Location })
            assertTrue(constraints.any { it.kind == ShowActiveConstraintKind.Date })
            assertTrue(constraints.any { it.kind == ShowActiveConstraintKind.Comedian })
            assertTrue(constraints.any { it.kind == ShowActiveConstraintKind.Club })
            assertTrue(constraints.any { it.kind == ShowActiveConstraintKind.MaximumPrice })
            assertTrue(constraints.any { it.kind == ShowActiveConstraintKind.Filter("free") })

            viewModel.removeShowConstraint(ShowActiveConstraintKind.Filter("free"))
            assertTrue("free" !in viewModel.showSearchSeed().filters)

            viewModel.clearAllShowConstraints()
            val cleared = viewModel.showSearchSeed()
            assertEquals(ShowSearchSeed(), cleared)
            assertTrue(viewModel.activeShowConstraints().isEmpty())
            advanceUntilIdle()
            showsApi.completeLatestSearch()
            advanceUntilIdle()
        }

    @Test
    fun successful_density_populates_the_requested_month() =
        runTest {
            val showsApi = SuspendingShowsApi()
            val viewModel = viewModel(showsApi)
            advanceUntilIdle()
            showsApi.completeLatestSearch()
            advanceUntilIdle()

            viewModel.loadShowDensity("2026-09-19")
            advanceUntilIdle()
            showsApi.completeLatestDensity(mapOf("2026-09-12" to 4))
            advanceUntilIdle()

            val shows = viewModel.state.value.states.getValue(SearchPivot.SHOWS)
            assertEquals("2026-09-01", shows.densityMonthStart)
            assertEquals(mapOf("2026-09-12" to 4), shows.showDensity)
            assertTrue(!shows.isDensityLoading)
            assertNull(shows.densityError)
        }

    @Test
    fun calendar_selection_sets_one_exact_day_and_reloads_once() =
        runTest {
            val showsApi = SuspendingShowsApi()
            val viewModel = viewModel(showsApi)
            advanceUntilIdle()
            showsApi.completeLatestSearch()
            advanceUntilIdle()

            viewModel.setSort("price_desc")
            advanceUntilIdle()
            showsApi.completeLatestSearch()
            advanceUntilIdle()
            val callsBeforeSelection = showsApi.searchCalls

            viewModel.selectShowCalendarDate("2026-09-12")
            advanceUntilIdle()

            val query = viewModel.state.value.states.getValue(SearchPivot.SHOWS).query
            assertEquals("2026-09-12", query.from)
            assertEquals("2026-09-12", query.to)
            assertEquals("date_asc", query.sort)
            assertEquals(callsBeforeSelection + 1, showsApi.searchCalls)
            showsApi.completeLatestSearch()
            advanceUntilIdle()
        }

    @Test
    fun shortcuts_are_deterministic_and_presentation_changes_do_not_reload() =
        runTest {
            assertEquals(
                "2026-08-04" to "2026-08-04",
                showDateRangeForShortcut(ShowDateShortcut.TONIGHT, LocalDate.parse("2026-08-04")),
            )
            assertEquals(
                "2026-08-07" to "2026-08-09",
                showDateRangeForShortcut(ShowDateShortcut.THIS_WEEKEND, LocalDate.parse("2026-08-04")),
            )
            assertEquals(
                "2026-08-08" to "2026-08-09",
                showDateRangeForShortcut(ShowDateShortcut.THIS_WEEKEND, LocalDate.parse("2026-08-08")),
            )

            val showsApi = SuspendingShowsApi()
            val viewModel = viewModel(showsApi)
            advanceUntilIdle()
            assertEquals(1, showsApi.searchCalls)

            viewModel.setResultsPresentation(ShowResultsPresentation.CALENDAR)
            advanceUntilIdle()

            assertEquals(1, showsApi.searchCalls)
            assertEquals(ShowResultsPresentation.CALENDAR, viewModel.state.value.current.resultsPresentation)
            showsApi.completeLatestSearch()
            advanceUntilIdle()
        }

    @Test
    fun density_uses_explicit_scope_and_discards_a_stale_response() =
        runTest {
            val showsApi = SuspendingShowsApi()
            val viewModel = viewModel(showsApi)
            advanceUntilIdle()
            showsApi.completeLatestSearch()
            advanceUntilIdle()

            viewModel.applyShowSearchSeed(
                ShowSearchSeed(comedian = "Atsuko", zip = "10012", distance = 50),
            )
            viewModel.loadShowDensity("2026-08-15")
            advanceUntilIdle()
            assertEquals("2026-08-01", showsApi.lastDensityFrom)
            assertEquals("2026-08-31", showsApi.lastDensityTo)
            assertEquals("Atsuko", showsApi.lastDensityComedian)
            assertEquals("10012", showsApi.lastDensityZip)

            viewModel.onComedianChange("Ali Wong")
            showsApi.completeLatestDensity(mapOf("2026-08-10" to 3))
            advanceUntilIdle()

            assertTrue(viewModel.state.value.states.getValue(SearchPivot.SHOWS).showDensity.isEmpty())
            assertNull(viewModel.state.value.states.getValue(SearchPivot.SHOWS).densityMonthStart)
            showsApi.completeLatestSearch()
            advanceUntilIdle()
        }

    @Test
    fun density_falls_back_to_location_when_both_entity_constraints_are_active() =
        runTest {
            val showsApi = SuspendingShowsApi()
            val viewModel = viewModel(showsApi)
            advanceUntilIdle()
            showsApi.completeLatestSearch()
            advanceUntilIdle()

            viewModel.applyShowSearchSeed(
                ShowSearchSeed(comedian = "Atsuko", club = "The Stand", zip = "10012"),
            )
            viewModel.loadShowDensity("2026-08-01")
            advanceUntilIdle()

            assertNull(showsApi.lastDensityComedian)
            assertNull(showsApi.lastDensityClub)
            showsApi.completeLatestDensity(emptyMap())
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
            // Page 0 returns 1 of 30 results, so more pages exist.
            showsApi.completeLatestSearch(data = listOf(show(1)), total = 30)
            advanceUntilIdle()
            check(showsApi.lastPage == 0)

            viewModel.loadMore()
            advanceUntilIdle()

            assertEquals(2, showsApi.searchCalls)
            assertEquals(1, showsApi.lastPage)
            showsApi.completeLatestSearch(data = listOf(show(2)), total = 30)
            advanceUntilIdle()

            // Both pages accumulated in the pivot state.
            assertEquals(2, viewModel.state.value.current.results.items.size)
        }

    @Test
    fun initial_page_publishes_facets_for_filter_control() =
        runTest {
            val showsApi = SuspendingShowsApi()
            val viewModel = viewModel(showsApi)
            advanceUntilIdle()

            val filters = listOf(Filter(id = 1, slug = "stand-up", name = "Stand-up"))
            showsApi.completeLatestSearch(filters = filters)
            advanceUntilIdle()

            assertEquals(filters, viewModel.state.value.current.filters)
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
        var lastComedian: String? = null
        var lastClub: String? = null
        var lastFilters: String? = null
        var lastMaxPrice: BigDecimal? = null
        var lastDensityFrom: String? = null
        var lastDensityTo: String? = null
        var lastDensityZip: String? = null
        var lastDensityComedian: String? = null
        var lastDensityClub: String? = null
        private val pendingSearches = mutableListOf<CompletableDeferred<Response<ShowSearchResponse>>>()
        private val pendingDensities = mutableListOf<CompletableDeferred<Response<Map<String, Int>>>>()

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
            maxPrice: java.math.BigDecimal?,
            sort: String?,
            xTimezone: String?,
        ): Response<ShowSearchResponse> {
            searchCalls += 1
            lastPage = page
            lastZip = zip
            lastDistance = distance
            lastComedian = comedian
            lastClub = club
            lastFilters = filters
            lastMaxPrice = maxPrice
            val pending = CompletableDeferred<Response<ShowSearchResponse>>()
            pendingSearches += pending
            return pending.await()
        }

        fun completeLatestSearch(
            data: List<Show> = emptyList(),
            total: Int = data.size,
            filters: List<Filter> = emptyList(),
        ) {
            pendingSearches
                .last()
                .complete(
                    Response.success(
                        ShowSearchResponse(
                            data = data,
                            total = total,
                            filters = filters,
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
            clubId: Int?,
            xTimezone: String?,
        ): Response<Map<String, Int>> {
            lastDensityZip = zip
            lastDensityFrom = from
            lastDensityTo = to
            lastDensityComedian = comedian
            lastDensityClub = club
            val pending = CompletableDeferred<Response<Map<String, Int>>>()
            pendingDensities += pending
            return pending.await()
        }

        fun completeLatestDensity(density: Map<String, Int>) {
            pendingDensities.last().complete(Response.success(density))
        }

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
}
