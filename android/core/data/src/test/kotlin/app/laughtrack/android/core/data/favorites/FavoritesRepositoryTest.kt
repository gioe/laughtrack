package app.laughtrack.android.core.data.favorites

import app.laughtrack.android.core.data.auth.LoginPromptController
import app.laughtrack.android.core.network.auth.AuthSessionManager
import app.laughtrack.android.core.network.auth.SessionTokens
import app.laughtrack.android.core.network.auth.TokenStore
import app.laughtrack.android.core.network.generated.api.AuthApi
import app.laughtrack.android.core.network.generated.api.FavoritesApi
import app.laughtrack.android.core.network.generated.model.AddFavoriteClubRequest
import app.laughtrack.android.core.network.generated.model.AddFavoritePodcastRequest
import app.laughtrack.android.core.network.generated.model.AddFavoriteRequest
import app.laughtrack.android.core.network.generated.model.FavoriteClubListResponse
import app.laughtrack.android.core.network.generated.model.FavoriteListResponse
import app.laughtrack.android.core.network.generated.model.FavoritePodcastListResponse
import app.laughtrack.android.core.network.generated.model.FavoriteResponse
import app.laughtrack.android.core.network.generated.model.FavoriteResponseData
import app.laughtrack.android.core.network.generated.model.FavoriteShowListResponse
import app.laughtrack.android.core.testing.throwingApi
import kotlinx.coroutines.test.runTest
import okhttp3.ResponseBody.Companion.toResponseBody
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test
import retrofit2.Response
import java.io.IOException
import java.time.Clock

class FavoritesRepositoryTest {
    // -- toggle: server success -----------------------------------------------

    @Test
    fun successful_toggle_reports_updated_and_keeps_optimistic_value() =
        runTest {
            val api = ProgrammableFavoritesApi()
            val repository = repository(api, signedIn = true)

            val result = repository.toggleComedian("comedian-1")

            assertEquals(FavoriteToggleResult.Updated(isFavorite = false), result)
            assertEquals(false, repository.snapshot.value.comedianValues["comedian-1"])
            assertTrue(repository.snapshot.value.pending.isEmpty())
        }

    // -- toggle: transport failure queues offline ------------------------------

    @Test
    fun io_exception_queues_the_toggle_and_keeps_the_optimistic_value() =
        runTest {
            val api = ProgrammableFavoritesApi(comedianBehavior = { throw IOException("offline") })
            val queue = RecordingOfflineQueue()
            val repository = repository(api, signedIn = true, queue = queue)

            val result = repository.toggleComedian("comedian-1")

            assertEquals(FavoriteToggleResult.Queued(isFavorite = false), result)
            // Optimistic value survives — the queue will replay it later.
            assertEquals(false, repository.snapshot.value.comedianValues["comedian-1"])
            assertEquals(
                listOf(Triple(FavoriteEntity.COMEDIAN, "comedian-1", false)),
                queue.enqueued,
            )
            assertTrue(repository.snapshot.value.pending.isEmpty())
        }

    // -- toggle: 5xx queues, 4xx reverts ---------------------------------------

    @Test
    fun server_5xx_queues_the_toggle() =
        runTest {
            val api = ProgrammableFavoritesApi(comedianBehavior = { errorResponse(503) })
            val queue = RecordingOfflineQueue()
            val repository = repository(api, signedIn = true, queue = queue)

            val result = repository.toggleComedian("comedian-1")

            assertEquals(FavoriteToggleResult.Queued(isFavorite = false), result)
            assertEquals(1, queue.enqueued.size)
        }

    @Test
    fun client_4xx_reverts_the_optimistic_value_and_reports_failure() =
        runTest {
            val api = ProgrammableFavoritesApi(comedianBehavior = { errorResponse(404) })
            val queue = RecordingOfflineQueue()
            val repository = repository(api, signedIn = true, queue = queue)

            val result = repository.toggleComedian("comedian-1")

            assertTrue(result is FavoriteToggleResult.Failure)
            // Reverted to the pre-toggle default (true for an unknown comedian).
            assertEquals(true, repository.snapshot.value.comedianValues["comedian-1"])
            assertTrue(queue.enqueued.isEmpty())
            assertTrue(repository.snapshot.value.pending.isEmpty())
        }

    // -- toggle: signed-out gate ------------------------------------------------

    @Test
    fun signed_out_toggle_requests_the_sign_in_prompt_and_never_calls_the_api() =
        runTest {
            val api = ProgrammableFavoritesApi()
            val prompt = LoginPromptController()
            val repository = repository(api, signedIn = false, loginPromptController = prompt)

            val result = repository.toggleComedian("comedian-1")

            assertEquals(FavoriteToggleResult.SignInRequired, result)
            assertTrue(prompt.visible.value)
            assertEquals(0, api.comedianCalls)
            // No optimistic write happened for the guest.
            assertFalse(repository.snapshot.value.comedianValues.containsKey("comedian-1"))
        }

    // -- club/podcast variants ride the same core path --------------------------

    @Test
    fun club_io_exception_queues_with_the_club_entity_key() =
        runTest {
            val api = ProgrammableFavoritesApi(clubBehavior = { throw IOException("offline") })
            val queue = RecordingOfflineQueue()
            val repository = repository(api, signedIn = true, queue = queue)

            val result = repository.toggleClub(42)

            assertEquals(FavoriteToggleResult.Queued(isFavorite = false), result)
            assertEquals(listOf(Triple(FavoriteEntity.CLUB, "42", false)), queue.enqueued)
        }

    @Test
    fun podcast_4xx_reverts() =
        runTest {
            val api = ProgrammableFavoritesApi(podcastBehavior = { errorResponse(400) })
            val repository = repository(api, signedIn = true)

            val result = repository.togglePodcast(7)

            assertTrue(result is FavoriteToggleResult.Failure)
            assertEquals(true, repository.snapshot.value.podcastValues[7])
        }

    // -- set-style API (no-op when already at the requested value) --------------

    @Test
    fun set_comedian_favorite_is_a_no_op_when_already_at_the_requested_value() =
        runTest {
            val api = ProgrammableFavoritesApi()
            val repository = repository(api, signedIn = true)

            val result = repository.setComedianFavorite("comedian-1", isFavorite = false)

            // Unknown comedians default to false for the set-style API.
            assertEquals(FavoriteToggleResult.Updated(isFavorite = false), result)
            assertEquals(0, api.comedianCalls)
        }

    @Test
    fun set_podcast_favorite_uses_the_explicit_current_value_contract() =
        runTest {
            val repository = repository(ProgrammableFavoritesApi(), signedIn = true)

            val result = repository.setPodcastFavorite(7, isFavorite = true)

            assertEquals(FavoriteToggleResult.Updated(isFavorite = true), result)
            assertEquals(true, repository.snapshot.value.podcastValues[7])
        }

    @Test
    fun set_podcast_favorite_can_remove_a_server_favorite_before_snapshot_hydration() =
        runTest {
            val api = ProgrammableFavoritesApi()
            val repository = repository(api, signedIn = true)

            val result =
                repository.setPodcastFavorite(
                    id = 7,
                    isFavorite = false,
                    knownCurrentValue = true,
                )

            assertEquals(FavoriteToggleResult.Updated(isFavorite = false), result)
            assertEquals(false, repository.snapshot.value.podcastValues[7])
            assertEquals(1, api.podcastCalls)
        }

    // -- helpers ----------------------------------------------------------------

    private suspend fun repository(
        api: FavoritesApi,
        signedIn: Boolean,
        queue: RecordingOfflineQueue = RecordingOfflineQueue(),
        loginPromptController: LoginPromptController = LoginPromptController(),
    ): FavoritesRepository {
        val authSessionManager =
            AuthSessionManager(
                tokenStore = InMemoryTokenStore(if (signedIn) STORED_TOKENS else null),
                authApi = throwingApi<AuthApi>(),
                websiteBaseUrl = "https://www.laugh-track.com",
                clock = Clock.systemUTC(),
            )
        if (signedIn) {
            // signedIn is derived from the stored session at restore time.
            authSessionManager.restoreSession()
        }
        return FavoritesRepository(
            favoritesApi = api,
            offlineQueue = queue,
            authSessionManager = authSessionManager,
            loginPromptController = loginPromptController,
        )
    }

    /** FavoritesApi fake whose add/remove behavior is programmable per entity. */
    private class ProgrammableFavoritesApi(
        private val comedianBehavior: () -> Response<FavoriteResponse> = { successResponse() },
        private val clubBehavior: () -> Response<FavoriteResponse> = { successResponse() },
        private val podcastBehavior: () -> Response<FavoriteResponse> = { successResponse() },
    ) : FavoritesApi {
        var comedianCalls = 0
            private set

        var podcastCalls = 0
            private set

        override suspend fun addFavorite(addFavoriteRequest: AddFavoriteRequest): Response<FavoriteResponse> {
            comedianCalls += 1
            return comedianBehavior()
        }

        override suspend fun removeFavorite(comedianId: String): Response<FavoriteResponse> {
            comedianCalls += 1
            return comedianBehavior()
        }

        override suspend fun addFavoriteClub(
            addFavoriteClubRequest: AddFavoriteClubRequest,
        ): Response<FavoriteResponse> = clubBehavior()

        override suspend fun removeFavoriteClub(clubId: Int): Response<FavoriteResponse> = clubBehavior()

        override suspend fun addFavoritePodcast(
            addFavoritePodcastRequest: AddFavoritePodcastRequest,
        ): Response<FavoriteResponse> {
            podcastCalls += 1
            return podcastBehavior()
        }

        override suspend fun removeFavoritePodcast(podcastId: Int): Response<FavoriteResponse> {
            podcastCalls += 1
            return podcastBehavior()
        }

        override suspend fun getFavoriteClubs(): Response<FavoriteClubListResponse> =
            error(
                "Unexpected getFavoriteClubs call",
            )

        override suspend fun getFavoritePodcasts(): Response<FavoritePodcastListResponse> =
            error(
                "Unexpected getFavoritePodcasts call",
            )

        override suspend fun getFavoriteShows(
            page: Int?,
            size: Int?,
        ): Response<FavoriteShowListResponse> = error("Unexpected getFavoriteShows call")

        override suspend fun getFavorites(): Response<FavoriteListResponse> = error("Unexpected getFavorites call")
    }

    /** Records enqueues instead of scheduling WorkManager jobs. */
    private class RecordingOfflineQueue : FavoriteQueue {
        val enqueued = mutableListOf<Triple<FavoriteEntity, String, Boolean>>()

        override fun enqueue(
            entity: FavoriteEntity,
            id: String,
            isFavorite: Boolean,
        ) {
            enqueued += Triple(entity, id, isFavorite)
        }
    }

    private class InMemoryTokenStore(
        private var tokens: SessionTokens?,
    ) : TokenStore {
        override suspend fun read(): SessionTokens? = tokens

        override suspend fun save(tokens: SessionTokens) {
            this.tokens = tokens
        }

        override suspend fun clear() {
            tokens = null
        }
    }

    private companion object {
        val STORED_TOKENS =
            SessionTokens(
                accessToken = "access-jwt",
                refreshToken = "refresh-token",
                expiresAtEpochSeconds = Long.MAX_VALUE,
            )

        fun successResponse(): Response<FavoriteResponse> =
            Response.success(
                FavoriteResponse(FavoriteResponseData(isFavorited = true)),
            )

        fun errorResponse(code: Int): Response<FavoriteResponse> = Response.error(code, "".toResponseBody())
    }
}
