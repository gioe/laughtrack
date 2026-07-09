package app.laughtrack.android.feature.library

import app.laughtrack.android.core.data.auth.LoginPromptController
import app.laughtrack.android.core.data.favorites.FavoriteEntity
import app.laughtrack.android.core.data.favorites.FavoriteQueue
import app.laughtrack.android.core.data.favorites.FavoritesRepository
import app.laughtrack.android.core.network.auth.AuthSessionManager
import app.laughtrack.android.core.network.auth.SessionTokens
import app.laughtrack.android.core.network.auth.TokenStore
import app.laughtrack.android.core.network.generated.api.AuthApi
import app.laughtrack.android.core.network.generated.api.FavoritesApi
import app.laughtrack.android.core.network.generated.model.ComedianSearchItem
import app.laughtrack.android.core.network.generated.model.FavoriteClubItem
import app.laughtrack.android.core.network.generated.model.FavoriteClubListResponse
import app.laughtrack.android.core.network.generated.model.FavoriteListResponse
import app.laughtrack.android.core.network.generated.model.FavoritePodcastItem
import app.laughtrack.android.core.network.generated.model.FavoritePodcastListResponse
import app.laughtrack.android.core.network.generated.model.FavoriteShowListResponse
import app.laughtrack.android.core.network.generated.model.SocialData
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.launch
import kotlinx.coroutines.test.StandardTestDispatcher
import kotlinx.coroutines.test.TestScope
import kotlinx.coroutines.test.advanceUntilIdle
import kotlinx.coroutines.test.resetMain
import kotlinx.coroutines.test.runTest
import kotlinx.coroutines.test.setMain
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test
import retrofit2.Response
import java.io.IOException
import java.lang.reflect.Proxy
import java.time.Clock

@OptIn(ExperimentalCoroutinesApi::class)
class LibraryViewModelTest {
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
    fun signed_in_refresh_populates_snapshot() =
        runTest {
            val viewModel = LibraryViewModel(favoritesRepository(FakeFavoritesApi()))
            collectSnapshot(viewModel)

            viewModel.refresh(signedIn = true)
            advanceUntilIdle()

            val snapshot = viewModel.snapshot.value
            assertEquals(1, snapshot.comedians.size)
            assertEquals(1, snapshot.clubs.size)
            assertEquals(1, snapshot.podcasts.size)
            assertTrue(snapshot.comedianValues.getValue("comedian-1"))
            assertNull(snapshot.errorMessage)
            assertTrue(!snapshot.isLoading)
        }

    @Test
    fun failed_refresh_publishes_error_message_and_stops_loading() =
        runTest {
            val viewModel = LibraryViewModel(favoritesRepository(FakeFavoritesApi(refreshFails = true)))
            collectSnapshot(viewModel)

            viewModel.refresh(signedIn = true)
            advanceUntilIdle()

            val snapshot = viewModel.snapshot.value
            assertNotNull(snapshot.errorMessage)
            assertTrue(!snapshot.isLoading)
            assertTrue(snapshot.comedians.isEmpty())
        }

    @Test
    fun signed_out_refresh_resets_snapshot() =
        runTest {
            val api = FakeFavoritesApi()
            val viewModel = LibraryViewModel(favoritesRepository(api))
            collectSnapshot(viewModel)

            viewModel.refresh(signedIn = true)
            advanceUntilIdle()
            assertEquals(1, viewModel.snapshot.value.comedians.size)

            viewModel.refresh(signedIn = false)
            advanceUntilIdle()

            assertTrue(viewModel.snapshot.value.comedians.isEmpty())
            assertTrue(viewModel.snapshot.value.comedianValues.isEmpty())
        }

    /** Activates the WhileSubscribed stateIn so the ViewModel mirrors the repository. */
    private fun TestScope.collectSnapshot(viewModel: LibraryViewModel) {
        backgroundScope.launch { viewModel.snapshot.collect {} }
    }

    private class FakeFavoritesApi(
        private val refreshFails: Boolean = false,
    ) : FavoritesApi by throwingApi() {
        override suspend fun getFavorites(): Response<FavoriteListResponse> {
            if (refreshFails) throw IOException("network down")
            return Response.success(FavoriteListResponse(listOf(comedian())))
        }

        override suspend fun getFavoriteShows(
            page: Int?,
            size: Int?,
        ): Response<FavoriteShowListResponse> =
            Response.success(
                FavoriteShowListResponse(data = emptyList(), total = 0, page = 1, propertySize = 20, totalPages = 0),
            )

        override suspend fun getFavoriteClubs(): Response<FavoriteClubListResponse> =
            Response.success(
                FavoriteClubListResponse(
                    listOf(FavoriteClubItem(id = 7, name = "Comedy Room", imageUrl = "", isFavorite = true)),
                ),
            )

        override suspend fun getFavoritePodcasts(): Response<FavoritePodcastListResponse> =
            Response.success(
                FavoritePodcastListResponse(
                    listOf(FavoritePodcastItem(id = 3, title = "Podcast 3", episodeCount = 0, isFavorite = true)),
                ),
            )
    }

    private companion object {
        fun comedian() =
            ComedianSearchItem(
                id = 1,
                uuid = "comedian-1",
                name = "Comedian 1",
                imageUrl = "https://example.com/comedian-1.jpg",
                socialData = SocialData(id = 1),
                showCount = 12,
            )

        fun favoritesRepository(api: FavoritesApi): FavoritesRepository =
            FavoritesRepository(
                favoritesApi = api,
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
