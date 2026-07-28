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
import app.laughtrack.android.core.network.generated.model.ComedianSearchItem
import app.laughtrack.android.core.network.generated.model.FavoriteClubListResponse
import app.laughtrack.android.core.network.generated.model.FavoriteListResponse
import app.laughtrack.android.core.network.generated.model.FavoritePodcastListResponse
import app.laughtrack.android.core.network.generated.model.FavoriteResponse
import app.laughtrack.android.core.network.generated.model.FavoriteResponseData
import app.laughtrack.android.core.network.generated.model.FavoriteShowListResponse
import app.laughtrack.android.core.network.generated.model.SocialData
import app.laughtrack.android.core.testing.throwingApi
import kotlinx.coroutines.CompletableDeferred
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.async
import kotlinx.coroutines.cancelAndJoin
import kotlinx.coroutines.launch
import kotlinx.coroutines.test.runCurrent
import kotlinx.coroutines.test.runTest
import okhttp3.ResponseBody.Companion.toResponseBody
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test
import retrofit2.Response
import java.io.IOException
import java.time.Clock

@OptIn(ExperimentalCoroutinesApi::class)
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

    @Test
    fun newer_same_entity_intent_wins_locally_and_on_the_backend() =
        runTest {
            val finishAdd = CompletableDeferred<Unit>()
            val removeStarted = CompletableDeferred<Unit>()
            var serverValue = false
            val api =
                ProgrammableFavoritesApi(
                    addComedianBehavior = {
                        finishAdd.await()
                        serverValue = true
                        favoriteResponse(serverValue)
                    },
                    removeComedianBehavior = {
                        removeStarted.complete(Unit)
                        serverValue = false
                        favoriteResponse(serverValue)
                    },
                )
            val repository = repository(api, signedIn = true)

            val older = async { repository.setComedianFavorite("comedian-1", true) }
            runCurrent()
            val newer = async { repository.setComedianFavorite("comedian-1", false) }
            runCurrent()
            assertFalse(removeStarted.isCompleted)

            finishAdd.complete(Unit)
            older.await()
            runCurrent()
            assertTrue(removeStarted.isCompleted)
            assertEquals(FavoriteToggleResult.Updated(false), newer.await())

            assertFalse(serverValue)
            assertEquals(false, repository.snapshot.value.comedianValues["comedian-1"])
            assertTrue(repository.snapshot.value.pending.isEmpty())
        }

    @Test
    fun cancelled_refresh_clears_loading_state() =
        runTest {
            val favorites = CompletableDeferred<Response<FavoriteListResponse>>()
            val repository =
                repository(
                    ProgrammableFavoritesApi(favoritesBehavior = { favorites.await() }),
                    signedIn = true,
                )

            val refresh = launch { repository.refreshSignedInFavorites() }
            runCurrent()
            assertTrue(repository.snapshot.value.isLoading)
            refresh.cancelAndJoin()

            assertFalse(repository.snapshot.value.isLoading)
        }

    @Test
    fun cancelled_mutation_rolls_back_optimistic_state_and_pending_marker() =
        runTest {
            val response = CompletableDeferred<Response<FavoriteResponse>>()
            val repository =
                repository(
                    ProgrammableFavoritesApi(addComedianBehavior = { response.await() }),
                    signedIn = true,
                )

            val mutation = launch { repository.setComedianFavorite("comedian-1", true) }
            runCurrent()
            assertEquals(true, repository.snapshot.value.comedianValues["comedian-1"])
            assertTrue(repository.snapshot.value.pending.isNotEmpty())
            mutation.cancelAndJoin()

            assertEquals(false, repository.snapshot.value.comedianValues["comedian-1"])
            assertTrue(repository.snapshot.value.pending.isEmpty())
        }

    @Test
    fun stale_refresh_cannot_restore_a_comedian_unfavorited_while_it_was_in_flight() =
        runTest {
            val favorites = CompletableDeferred<Response<FavoriteListResponse>>()
            val api = ProgrammableFavoritesApi(favoritesBehavior = { favorites.await() })
            val repository = repository(api, signedIn = true)

            val refresh = async { repository.refreshSignedInFavorites() }
            runCurrent()
            assertEquals(
                FavoriteToggleResult.Updated(false),
                repository.setComedianFavorite(
                    uuid = "comedian-1",
                    isFavorite = false,
                    knownCurrentValue = true,
                ),
            )
            favorites.complete(Response.success(FavoriteListResponse(listOf(comedian("comedian-1")))))
            refresh.await()

            assertEquals(false, repository.snapshot.value.comedianValues["comedian-1"])
            assertTrue(repository.snapshot.value.comedians.isEmpty())
        }

    @Test
    fun later_online_success_cancels_older_replay_for_the_same_entity() =
        runTest {
            val queue = RecordingOfflineQueue()
            val repository =
                repository(
                    ProgrammableFavoritesApi(
                        addComedianBehavior = { throw IOException("offline") },
                        removeComedianBehavior = { favoriteResponse(false) },
                    ),
                    signedIn = true,
                    queue = queue,
                )

            assertEquals(
                FavoriteToggleResult.Queued(true),
                repository.setComedianFavorite("comedian-1", true),
            )
            assertEquals(
                FavoriteToggleResult.Updated(false),
                repository.setComedianFavorite("comedian-1", false),
            )

            assertEquals(
                listOf(Triple(FavoriteEntity.COMEDIAN, "comedian-1", true)),
                queue.enqueued,
            )
            assertEquals(listOf(FavoriteEntity.COMEDIAN to "comedian-1"), queue.cancelled)
        }

    @Test
    fun sign_out_invalidates_in_flight_mutation_and_cancels_account_replay() =
        runTest {
            val response = CompletableDeferred<Response<FavoriteResponse>>()
            val queue = RecordingOfflineQueue()
            val repository =
                repository(
                    ProgrammableFavoritesApi(addComedianBehavior = { response.await() }),
                    signedIn = true,
                    queue = queue,
                )

            val mutation = async { repository.setComedianFavorite("comedian-1", true) }
            runCurrent()
            repository.resetSignedOut()
            response.completeExceptionally(IOException("offline"))
            mutation.await()

            assertEquals(FavoritesSnapshot(), repository.snapshot.value)
            assertTrue(queue.enqueued.isEmpty())
            assertEquals(1, queue.cancelAllCount)
        }

    @Test
    fun sign_out_invalidates_in_flight_refresh() =
        runTest {
            val favorites = CompletableDeferred<Response<FavoriteListResponse>>()
            val queue = RecordingOfflineQueue()
            val repository =
                repository(
                    ProgrammableFavoritesApi(favoritesBehavior = { favorites.await() }),
                    signedIn = true,
                    queue = queue,
                )

            val refresh = async { repository.refreshSignedInFavorites() }
            runCurrent()
            repository.resetSignedOut()
            favorites.complete(Response.success(FavoriteListResponse(listOf(comedian("comedian-1")))))
            refresh.await()

            assertEquals(FavoritesSnapshot(), repository.snapshot.value)
            assertEquals(1, queue.cancelAllCount)
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
        private val comedianBehavior: suspend () -> Response<FavoriteResponse> = { successResponse() },
        private val addComedianBehavior: suspend () -> Response<FavoriteResponse> = comedianBehavior,
        private val removeComedianBehavior: suspend () -> Response<FavoriteResponse> = comedianBehavior,
        private val clubBehavior: suspend () -> Response<FavoriteResponse> = { successResponse() },
        private val podcastBehavior: suspend () -> Response<FavoriteResponse> = { successResponse() },
        private val favoritesBehavior: suspend () -> Response<FavoriteListResponse> = {
            Response.success(FavoriteListResponse(emptyList()))
        },
    ) : FavoritesApi {
        var comedianCalls = 0
            private set

        var podcastCalls = 0
            private set

        override suspend fun addFavorite(addFavoriteRequest: AddFavoriteRequest): Response<FavoriteResponse> {
            comedianCalls += 1
            return addComedianBehavior()
        }

        override suspend fun removeFavorite(comedianId: String): Response<FavoriteResponse> {
            comedianCalls += 1
            return removeComedianBehavior()
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
            Response.success(FavoriteClubListResponse(emptyList()))

        override suspend fun getFavoritePodcasts(): Response<FavoritePodcastListResponse> =
            Response.success(FavoritePodcastListResponse(emptyList()))

        override suspend fun getFavoriteShows(
            page: Int?,
            size: Int?,
        ): Response<FavoriteShowListResponse> =
            Response.success(
                FavoriteShowListResponse(
                    data = emptyList(),
                    total = 0,
                    page = 1,
                    propertySize = 20,
                    totalPages = 0,
                ),
            )

        override suspend fun getFavorites(): Response<FavoriteListResponse> = favoritesBehavior()
    }

    /** Records enqueues instead of scheduling WorkManager jobs. */
    private class RecordingOfflineQueue : FavoriteQueue {
        val enqueued = mutableListOf<Triple<FavoriteEntity, String, Boolean>>()
        val cancelled = mutableListOf<Pair<FavoriteEntity, String>>()
        var cancelAllCount = 0

        override fun enqueue(
            entity: FavoriteEntity,
            id: String,
            isFavorite: Boolean,
        ) {
            enqueued += Triple(entity, id, isFavorite)
        }

        override fun cancel(
            entity: FavoriteEntity,
            id: String,
        ) {
            cancelled += entity to id
        }

        override fun cancelAll() {
            cancelAllCount += 1
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

        fun successResponse(): Response<FavoriteResponse> = favoriteResponse(true)

        fun favoriteResponse(isFavorite: Boolean): Response<FavoriteResponse> =
            Response.success(FavoriteResponse(FavoriteResponseData(isFavorited = isFavorite)))

        fun errorResponse(code: Int): Response<FavoriteResponse> = Response.error(code, "".toResponseBody())

        fun comedian(uuid: String): ComedianSearchItem =
            ComedianSearchItem(
                id = 1,
                uuid = uuid,
                name = "Comedian",
                imageUrl = "",
                socialData = SocialData(id = 1),
                showCount = 0,
                isFavorite = true,
            )
    }
}
