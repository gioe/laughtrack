package app.laughtrack.android.feature.detail.ui

import app.laughtrack.android.core.data.auth.LoginPromptController
import app.laughtrack.android.core.data.favorites.FavoriteEntity
import app.laughtrack.android.core.data.favorites.FavoriteQueue
import app.laughtrack.android.core.data.favorites.FavoritesRepository
import app.laughtrack.android.core.network.auth.AuthSessionManager
import app.laughtrack.android.core.network.auth.SessionTokens
import app.laughtrack.android.core.network.auth.TokenStore
import app.laughtrack.android.core.network.generated.api.AuthApi
import app.laughtrack.android.core.network.generated.api.ClubsApi
import app.laughtrack.android.core.network.generated.api.FavoritesApi
import app.laughtrack.android.core.network.generated.model.ClubDetail
import app.laughtrack.android.core.network.generated.model.ClubShowsResponse
import app.laughtrack.android.core.network.generated.model.GetClub200Response
import app.laughtrack.android.core.network.generated.model.Show
import app.laughtrack.android.core.ui.UiState
import app.laughtrack.android.feature.detail.data.ClubDetailRepository
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
import java.lang.reflect.Proxy
import java.time.Clock

@OptIn(ExperimentalCoroutinesApi::class)
class ClubDetailViewModelTest {
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
    fun load_publishes_success_with_upcoming_shows() =
        runTest {
            val viewModel = viewModel(FakeClubsApi())

            viewModel.load(42)
            assertEquals(UiState.Loading, viewModel.state.value)
            advanceUntilIdle()

            val state = viewModel.state.value
            assertTrue(state is UiState.Success)
            val ui = (state as UiState.Success).value
            assertEquals(42, ui.detail.id)
            assertEquals(1, ui.upcomingShows.size)
        }

    @Test
    fun shows_endpoint_failure_degrades_to_empty_list() =
        runTest {
            val viewModel = viewModel(FakeClubsApi(showsFail = true))

            viewModel.load(42)
            advanceUntilIdle()

            val state = viewModel.state.value
            assertTrue(state is UiState.Success)
            assertTrue((state as UiState.Success).value.upcomingShows.isEmpty())
        }

    @Test
    fun load_failure_publishes_failure_state() =
        runTest {
            val viewModel = viewModel(FakeClubsApi(detailFails = true))

            viewModel.load(42)
            advanceUntilIdle()

            val state = viewModel.state.value
            assertTrue(state is UiState.Failure)
            assertTrue((state as UiState.Failure).error is IOException)
        }

    private fun viewModel(clubsApi: ClubsApi): ClubDetailViewModel =
        ClubDetailViewModel(
            repository = ClubDetailRepository(clubsApi),
            favoritesRepository = signedOutFavoritesRepository(),
        )

    private class FakeClubsApi(
        private val detailFails: Boolean = false,
        private val showsFail: Boolean = false,
    ) : ClubsApi by throwingApi() {
        override suspend fun getClub(id: Int): Response<GetClub200Response> {
            if (detailFails) throw IOException("network down")
            return Response.success(GetClub200Response(clubDetail(id)))
        }

        override suspend fun getClubShows(
            id: Int,
            page: Int?,
            size: Int?,
        ): Response<ClubShowsResponse> {
            if (showsFail) throw IOException("network down")
            return Response.success(ClubShowsResponse(data = listOf(show(1, clubId = id)), total = 1))
        }
    }

    private companion object {
        fun clubDetail(id: Int) =
            ClubDetail(
                id = id,
                name = "Comedy Room",
                imageUrl = "https://example.com/club-$id.jpg",
                heroImageUrl = "https://example.com/club-$id-hero.jpg",
                website = "https://example.com/club-$id",
                address = "1 Main St, New York, NY",
            )

        fun show(
            id: Int,
            clubId: Int,
        ) = Show(
            id = id,
            clubId = clubId,
            date = "2026-07-09T20:00:00-04:00",
            imageUrl = "https://example.com/show-$id.jpg",
            clubName = "Comedy Room",
            name = "Show $id",
        )

        fun signedOutFavoritesRepository(): FavoritesRepository =
            FavoritesRepository(
                favoritesApi = throwingApi<FavoritesApi>(),
                offlineQueue = NoOpQueue,
                authSessionManager =
                    AuthSessionManager(
                        tokenStore = NullTokenStore,
                        authApi = throwingApi<AuthApi>(),
                        websiteBaseUrl = "https://www.laugh-track.com",
                        clock = Clock.systemUTC(),
                    ),
                loginPromptController = LoginPromptController(),
            )

        object NoOpQueue : FavoriteQueue {
            override fun enqueue(
                entity: FavoriteEntity,
                id: String,
                isFavorite: Boolean,
            ) = Unit
        }

        object NullTokenStore : TokenStore {
            override suspend fun read(): SessionTokens? = null

            override suspend fun save(tokens: SessionTokens) = Unit

            override suspend fun clear() = Unit
        }

        inline fun <reified T : Any> throwingApi(): T =
            Proxy.newProxyInstance(T::class.java.classLoader, arrayOf(T::class.java)) { _, method, _ ->
                error("Unexpected ${method.name} call")
            } as T
    }
}
