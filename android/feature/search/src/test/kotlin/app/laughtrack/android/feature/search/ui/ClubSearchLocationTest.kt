package app.laughtrack.android.feature.search.ui

import app.laughtrack.android.core.analytics.AnalyticsManager
import app.laughtrack.android.core.data.location.HomeLocationState
import app.laughtrack.android.core.network.generated.api.ClubsApi
import app.laughtrack.android.core.network.generated.api.ShowsApi
import app.laughtrack.android.core.network.generated.model.ClubSearchResponse
import app.laughtrack.android.core.network.generated.model.ShowSearchResponse
import app.laughtrack.android.core.testing.throwingApi
import app.laughtrack.android.feature.search.data.SearchRepository
import app.laughtrack.android.feature.search.model.SearchPivot
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
import retrofit2.http.Query
import java.lang.reflect.Proxy

@OptIn(ExperimentalCoroutinesApi::class)
class ClubSearchLocationTest {
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
    fun club_search_seeds_and_sends_home_location() =
        runTest {
            val homeLocationState =
                HomeLocationState().apply {
                    update("60614", 50, "Chicago, IL")
                }
            val clubsApi = RecordingClubsApi()
            val viewModel = viewModel(clubsApi.api, homeLocationState)
            advanceUntilIdle()

            val seeded = viewModel.state.value.states.getValue(SearchPivot.CLUBS)
            assertEquals("60614", seeded.query.zip)
            assertEquals(50, seeded.query.distance)
            assertEquals("Chicago, IL", seeded.locationLabel)

            viewModel.selectPivot(SearchPivot.CLUBS)
            advanceUntilIdle()

            assertEquals(ClubSearchRequest(zip = "60614", distance = 50), clubsApi.requests.last())
        }

    @Test
    fun club_search_supports_changing_and_clearing_location_without_blocking_show_sync() =
        runTest {
            val homeLocationState = HomeLocationState().apply { update("60614", 50) }
            val clubsApi = RecordingClubsApi()
            val viewModel = viewModel(clubsApi.api, homeLocationState)
            advanceUntilIdle()
            viewModel.selectPivot(SearchPivot.CLUBS)
            advanceUntilIdle()

            viewModel.setZip("90210")
            advanceUntilIdle()
            assertEquals(ClubSearchRequest(zip = "90210", distance = 50), clubsApi.requests.last())

            viewModel.setDistance(100)
            advanceUntilIdle()
            assertEquals(ClubSearchRequest(zip = "90210", distance = 100), clubsApi.requests.last())

            viewModel.setZip("")
            advanceUntilIdle()
            assertEquals(ClubSearchRequest(zip = null, distance = 100), clubsApi.requests.last())
            val clubRequestCountAfterClear = clubsApi.requests.size

            homeLocationState.update("10001", 25)
            advanceUntilIdle()

            val clubQuery = viewModel.state.value.states.getValue(SearchPivot.CLUBS).query
            assertNull(clubQuery.zip)
            assertEquals(100, clubQuery.distance)
            assertEquals(clubRequestCountAfterClear, clubsApi.requests.size)

            val showQuery = viewModel.state.value.states.getValue(SearchPivot.SHOWS).query
            assertEquals("10001", showQuery.zip)
            assertEquals(25, showQuery.distance)
        }

    private fun viewModel(
        clubsApi: ClubsApi,
        homeLocationState: HomeLocationState,
    ): SearchViewModel =
        SearchViewModel(
            repository =
                SearchRepository(
                    showsApi = ImmediateShowsApi(),
                    comediansApi = throwingApi(),
                    clubsApi = clubsApi,
                    podcastsApi = throwingApi(),
                ),
            analytics = AnalyticsManager(emptyList()),
            homeLocationState = homeLocationState,
        )

    private class RecordingClubsApi {
        val requests = mutableListOf<ClubSearchRequest>()

        val api: ClubsApi =
            Proxy.newProxyInstance(
                ClubsApi::class.java.classLoader,
                arrayOf(ClubsApi::class.java),
            ) { _, method, arguments ->
                check(method.name == "searchClubs") { "Unexpected ${method.name} call" }
                val queryValues =
                    method.parameterAnnotations
                        .zip(arguments.orEmpty())
                        .mapNotNull { (annotations, value) ->
                            val query = annotations.filterIsInstance<Query>().firstOrNull()
                            query?.value?.let { it to value }
                        }.toMap()
                requests +=
                    ClubSearchRequest(
                        zip = queryValues["zip"] as String?,
                        distance = queryValues["distance"] as Int?,
                    )
                Response.success(
                    ClubSearchResponse(
                        data = emptyList(),
                        total = 0,
                        filters = emptyList(),
                    ),
                )
            } as ClubsApi
    }

    private class ImmediateShowsApi : ShowsApi by throwingApi() {
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
        ): Response<ShowSearchResponse> =
            Response.success(
                ShowSearchResponse(
                    data = emptyList(),
                    total = 0,
                    filters = emptyList(),
                    zipCapTriggered = false,
                ),
            )
    }

    private data class ClubSearchRequest(
        val zip: String?,
        val distance: Int?,
    )
}
