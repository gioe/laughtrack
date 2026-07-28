package app.laughtrack.android.core.data.savedshows

import app.laughtrack.android.core.data.auth.LoginPromptController
import app.laughtrack.android.core.network.auth.AuthSessionManager
import app.laughtrack.android.core.network.auth.SessionTokens
import app.laughtrack.android.core.network.auth.TokenStore
import app.laughtrack.android.core.network.generated.api.AuthApi
import app.laughtrack.android.core.network.generated.api.SavedShowsApi
import app.laughtrack.android.core.network.generated.model.SavedShowListResponse
import app.laughtrack.android.core.network.generated.model.SavedShowState
import app.laughtrack.android.core.network.generated.model.SavedShowStateResponse
import app.laughtrack.android.core.network.generated.model.Show
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
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test
import retrofit2.Response
import java.io.IOException
import java.time.Clock

@OptIn(ExperimentalCoroutinesApi::class)
class SavedShowsRepositoryTest {
    @Test
    fun loads_per_show_state_and_distinct_paginated_upcoming_and_past_collections() =
        runTest {
            val api =
                ProgrammableSavedShowsApi(
                    stateBehavior = { stateResponse(true) },
                    listBehavior = { period, page, _ ->
                        when (period) {
                            SavedShowsApi.PeriodGetSavedShows.UPCOMING ->
                                listResponse(
                                    shows = listOf(show(page ?: 1)),
                                    page = page ?: 1,
                                    total = 2,
                                    totalPages = 2,
                                )
                            SavedShowsApi.PeriodGetSavedShows.PAST ->
                                listResponse(
                                    shows = listOf(show(30)),
                                    page = 1,
                                    total = 1,
                                    totalPages = 1,
                                )
                            null -> error("Period is required")
                        }
                    },
                )
            val repository = repository(api, signedIn = true)

            assertEquals(true, repository.loadState(99))
            assertTrue(repository.refresh(SavedShowPeriod.UPCOMING))
            assertTrue(repository.loadNextPage(SavedShowPeriod.UPCOMING))
            assertTrue(repository.refresh(SavedShowPeriod.PAST))

            val snapshot = repository.snapshot.value
            assertEquals(listOf(1, 2), snapshot.upcoming.shows.map(Show::id))
            assertEquals(2, snapshot.upcoming.page)
            assertEquals(2, snapshot.upcoming.total)
            assertEquals(listOf(30), snapshot.past.shows.map(Show::id))
            assertEquals(1, snapshot.past.page)
            assertEquals(true, snapshot.values[99])
            assertEquals(true, snapshot.values[1])
            assertEquals(true, snapshot.values[2])
            assertEquals(true, snapshot.values[30])
            assertEquals(
                listOf(
                    Triple(SavedShowsApi.PeriodGetSavedShows.UPCOMING, 1, 20),
                    Triple(SavedShowsApi.PeriodGetSavedShows.UPCOMING, 2, 20),
                    Triple(SavedShowsApi.PeriodGetSavedShows.PAST, 1, 20),
                ),
                api.listCalls,
            )
        }

    @Test
    fun next_page_does_not_fetch_past_the_last_page() =
        runTest {
            val api =
                ProgrammableSavedShowsApi(
                    listBehavior = { _, _, _ ->
                        listResponse(
                            shows = listOf(show(1)),
                            page = 1,
                            total = 1,
                            totalPages = 1,
                        )
                    },
                )
            val repository = repository(api, signedIn = true)

            assertTrue(repository.refresh(SavedShowPeriod.UPCOMING))
            assertFalse(repository.loadNextPage(SavedShowPeriod.UPCOMING))
            assertEquals(1, api.listCalls.size)
        }

    @Test
    fun collection_failure_preserves_cached_items_and_exposes_an_error() =
        runTest {
            var shouldFail = false
            val api =
                ProgrammableSavedShowsApi(
                    listBehavior = { _, _, _ ->
                        if (shouldFail) {
                            throw IOException("offline")
                        }
                        listResponse(listOf(show(1)), page = 1, total = 1, totalPages = 1)
                    },
                )
            val repository = repository(api, signedIn = true)
            assertTrue(repository.refresh(SavedShowPeriod.UPCOMING))

            shouldFail = true
            assertFalse(repository.refresh(SavedShowPeriod.UPCOMING))

            assertEquals(listOf(1), repository.snapshot.value.upcoming.shows.map(Show::id))
            assertFalse(repository.snapshot.value.upcoming.isLoading)
            assertTrue(repository.snapshot.value.upcoming.errorMessage != null)
        }

    @Test
    fun save_is_optimistic_then_reports_server_success() =
        runTest {
            val response = CompletableDeferred<Response<SavedShowStateResponse>>()
            val api =
                ProgrammableSavedShowsApi(
                    saveBehavior = { response.await() },
                )
            val repository = repository(api, signedIn = true)

            val mutation = async { repository.setSaved(showId = 42, isSaved = true) }
            runCurrent()

            assertEquals(true, repository.snapshot.value.values[42])
            assertTrue(42 in repository.snapshot.value.pending)

            response.complete(stateResponse(true))
            assertEquals(SavedShowMutationResult.Updated(true), mutation.await())
            assertTrue(repository.snapshot.value.pending.isEmpty())
        }

    @Test
    fun later_online_success_cancels_older_replay_for_the_same_show() =
        runTest {
            val queue = RecordingSavedShowQueue()
            val repository =
                repository(
                    ProgrammableSavedShowsApi(
                        saveBehavior = { throw IOException("offline") },
                        unsaveBehavior = { stateResponse(false) },
                    ),
                    signedIn = true,
                    queue = queue,
                )

            assertEquals(
                SavedShowMutationResult.Queued(true),
                repository.setSaved(showId = 42, isSaved = true),
            )
            assertEquals(
                SavedShowMutationResult.Updated(false),
                repository.setSaved(showId = 42, isSaved = false),
            )

            assertEquals(listOf(42 to true), queue.enqueued)
            assertEquals(listOf(42), queue.cancelled)
            assertEquals(false, repository.snapshot.value.values[42])
        }

    @Test
    fun unsave_is_optimistic_and_removes_the_show_from_loaded_collections() =
        runTest {
            val api =
                ProgrammableSavedShowsApi(
                    listBehavior = { _, _, _ ->
                        listResponse(listOf(show(42)), page = 1, total = 1, totalPages = 1)
                    },
                    unsaveBehavior = { stateResponse(false) },
                )
            val repository = repository(api, signedIn = true)
            repository.refresh(SavedShowPeriod.UPCOMING)

            val result = repository.setSaved(showId = 42, isSaved = false)

            assertEquals(SavedShowMutationResult.Updated(false), result)
            assertEquals(false, repository.snapshot.value.values[42])
            assertTrue(repository.snapshot.value.upcoming.shows.isEmpty())
            assertEquals(0, repository.snapshot.value.upcoming.total)
        }

    @Test
    fun io_failure_queues_replay_and_keeps_the_optimistic_value() =
        runTest {
            val queue = RecordingSavedShowQueue()
            val repository =
                repository(
                    ProgrammableSavedShowsApi(saveBehavior = { throw IOException("offline") }),
                    signedIn = true,
                    queue = queue,
                )

            val result = repository.setSaved(showId = 42, isSaved = true)

            assertEquals(SavedShowMutationResult.Queued(true), result)
            assertEquals(true, repository.snapshot.value.values[42])
            assertEquals(listOf(42 to true), queue.enqueued)
            assertTrue(repository.snapshot.value.pending.isEmpty())
        }

    @Test
    fun server_5xx_queues_replay_and_keeps_the_optimistic_value() =
        runTest {
            val queue = RecordingSavedShowQueue()
            val repository =
                repository(
                    ProgrammableSavedShowsApi(saveBehavior = { errorResponse(503) }),
                    signedIn = true,
                    queue = queue,
                )

            val result = repository.setSaved(showId = 7, isSaved = true)

            assertEquals(SavedShowMutationResult.Queued(true), result)
            assertEquals(true, repository.snapshot.value.values[7])
            assertEquals(listOf(7 to true), queue.enqueued)
        }

    @Test
    fun permanent_failure_rolls_back_the_optimistic_value_and_does_not_queue() =
        runTest {
            val queue = RecordingSavedShowQueue()
            val repository =
                repository(
                    ProgrammableSavedShowsApi(saveBehavior = { errorResponse(409) }),
                    signedIn = true,
                    queue = queue,
                )

            val result = repository.setSaved(showId = 7, isSaved = true)

            assertTrue(result is SavedShowMutationResult.Failure)
            assertFalse(repository.snapshot.value.values.containsKey(7))
            assertTrue(repository.snapshot.value.pending.isEmpty())
            assertTrue(queue.enqueued.isEmpty())
        }

    @Test
    fun failed_mutation_rolls_back_only_its_show_without_erasing_another_success() =
        runTest {
            val first = CompletableDeferred<Response<SavedShowStateResponse>>()
            val second = CompletableDeferred<Response<SavedShowStateResponse>>()
            val api =
                ProgrammableSavedShowsApi(
                    saveBehavior = { showId ->
                        when (showId) {
                            1 -> first.await()
                            2 -> second.await()
                            else -> error("Unexpected show")
                        }
                    },
                )
            val repository = repository(api, signedIn = true)

            val failed = async { repository.setSaved(showId = 1, isSaved = true) }
            val succeeded = async { repository.setSaved(showId = 2, isSaved = true) }
            runCurrent()
            second.complete(stateResponse(true))
            assertEquals(SavedShowMutationResult.Updated(true), succeeded.await())
            first.complete(errorResponse(409))
            assertTrue(failed.await() is SavedShowMutationResult.Failure)

            assertFalse(repository.snapshot.value.values.containsKey(1))
            assertEquals(true, repository.snapshot.value.values[2])
        }

    @Test
    fun newer_same_show_intent_wins_when_responses_complete_in_reverse_order() =
        runTest {
            val finishSave = CompletableDeferred<Unit>()
            val finishUnsave = CompletableDeferred<Unit>()
            val unsaveStarted = CompletableDeferred<Unit>()
            var serverSaved = false
            val api =
                ProgrammableSavedShowsApi(
                    saveBehavior = {
                        finishSave.await()
                        serverSaved = true
                        stateResponse(serverSaved)
                    },
                    unsaveBehavior = {
                        unsaveStarted.complete(Unit)
                        finishUnsave.await()
                        serverSaved = false
                        stateResponse(serverSaved)
                    },
                )
            val repository = repository(api, signedIn = true)

            val older = async { repository.setSaved(showId = 42, isSaved = true) }
            runCurrent()
            val newer = async { repository.setSaved(showId = 42, isSaved = false) }
            runCurrent()
            assertFalse(unsaveStarted.isCompleted)
            finishSave.complete(Unit)
            older.await()
            runCurrent()
            assertTrue(unsaveStarted.isCompleted)
            finishUnsave.complete(Unit)
            assertEquals(SavedShowMutationResult.Updated(false), newer.await())

            assertEquals(false, repository.snapshot.value.values[42])
            assertTrue(repository.snapshot.value.pending.isEmpty())
            assertFalse(serverSaved)
        }

    @Test
    fun stale_per_show_state_read_cannot_overwrite_a_newer_mutation() =
        runTest {
            val state = CompletableDeferred<Response<SavedShowStateResponse>>()
            val api =
                ProgrammableSavedShowsApi(
                    stateBehavior = { state.await() },
                    unsaveBehavior = { stateResponse(false) },
                )
            val repository = repository(api, signedIn = true)

            val staleState = async { repository.loadState(42) }
            runCurrent()
            assertEquals(
                SavedShowMutationResult.Updated(false),
                repository.setSaved(showId = 42, isSaved = false),
            )
            state.complete(stateResponse(true))

            assertNull(staleState.await())
            assertEquals(false, repository.snapshot.value.values[42])
        }

    @Test
    fun cancelled_collection_load_clears_loading_state() =
        runTest {
            val response = CompletableDeferred<Response<SavedShowListResponse>>()
            val repository =
                repository(
                    ProgrammableSavedShowsApi(listBehavior = { _, _, _ -> response.await() }),
                    signedIn = true,
                )

            val load = launch { repository.refresh(SavedShowPeriod.UPCOMING) }
            runCurrent()
            assertTrue(repository.snapshot.value.upcoming.isLoading)
            load.cancelAndJoin()

            assertFalse(repository.snapshot.value.upcoming.isLoading)
        }

    @Test
    fun stale_refresh_cannot_readd_a_show_unsaved_while_it_was_in_flight() =
        runTest {
            val refresh = CompletableDeferred<Response<SavedShowListResponse>>()
            var listCall = 0
            val api =
                ProgrammableSavedShowsApi(
                    listBehavior = { _, _, _ ->
                        listCall += 1
                        if (listCall == 1) {
                            listResponse(listOf(show(42)), page = 1, total = 1, totalPages = 1)
                        } else {
                            refresh.await()
                        }
                    },
                    unsaveBehavior = { stateResponse(false) },
                )
            val repository = repository(api, signedIn = true)
            assertTrue(repository.refresh(SavedShowPeriod.UPCOMING))

            val staleRefresh = async { repository.refresh(SavedShowPeriod.UPCOMING) }
            runCurrent()
            assertEquals(
                SavedShowMutationResult.Updated(false),
                repository.setSaved(showId = 42, isSaved = false),
            )
            refresh.complete(listResponse(listOf(show(42)), page = 1, total = 1, totalPages = 1))
            assertTrue(staleRefresh.await())

            assertEquals(false, repository.snapshot.value.values[42])
            assertTrue(repository.snapshot.value.upcoming.shows.isEmpty())
        }

    @Test
    fun signed_out_mutation_requests_login_without_state_api_or_queue_writes() =
        runTest {
            val api = ProgrammableSavedShowsApi()
            val queue = RecordingSavedShowQueue()
            val prompt = LoginPromptController()
            val repository =
                repository(
                    api = api,
                    signedIn = false,
                    queue = queue,
                    loginPromptController = prompt,
                )

            val result = repository.setSaved(showId = 42, isSaved = true)

            assertEquals(SavedShowMutationResult.SignInRequired, result)
            assertTrue(prompt.visible.value)
            assertTrue(api.mutationCalls.isEmpty())
            assertTrue(queue.enqueued.isEmpty())
            assertFalse(repository.snapshot.value.values.containsKey(42))
            assertNull(repository.loadState(42))
            assertEquals(0, api.stateCalls)
        }

    @Test
    fun sign_out_reset_clears_all_account_bound_state() =
        runTest {
            val queue = RecordingSavedShowQueue()
            val api =
                ProgrammableSavedShowsApi(
                    stateBehavior = { stateResponse(true) },
                    listBehavior = { _, _, _ ->
                        listResponse(listOf(show(42)), page = 1, total = 1, totalPages = 1)
                    },
                )
            val repository = repository(api, signedIn = true, queue = queue)
            repository.loadState(42)
            repository.refresh(SavedShowPeriod.UPCOMING)

            repository.resetSignedOut()

            assertEquals(SavedShowsSnapshot(), repository.snapshot.value)
            assertEquals(1, queue.cancelCount)
        }

    @Test
    fun sign_out_invalidates_in_flight_responses_and_prevents_replay_enqueue() =
        runTest {
            val mutation = CompletableDeferred<Response<SavedShowStateResponse>>()
            val refresh = CompletableDeferred<Response<SavedShowListResponse>>()
            val queue = RecordingSavedShowQueue()
            val api =
                ProgrammableSavedShowsApi(
                    listBehavior = { _, _, _ -> refresh.await() },
                    saveBehavior = { mutation.await() },
                )
            val repository = repository(api, signedIn = true, queue = queue)

            val save = async { repository.setSaved(showId = 42, isSaved = true) }
            val load = async { repository.refresh(SavedShowPeriod.UPCOMING) }
            runCurrent()
            repository.resetSignedOut()
            mutation.completeExceptionally(IOException("offline"))
            refresh.complete(listResponse(listOf(show(42)), page = 1, total = 1, totalPages = 1))
            save.await()
            assertFalse(load.await())

            assertEquals(SavedShowsSnapshot(), repository.snapshot.value)
            assertTrue(queue.enqueued.isEmpty())
            assertEquals(1, queue.cancelCount)
        }

    private suspend fun repository(
        api: SavedShowsApi,
        signedIn: Boolean,
        queue: RecordingSavedShowQueue = RecordingSavedShowQueue(),
        loginPromptController: LoginPromptController = LoginPromptController(),
    ): SavedShowsRepository {
        val authSessionManager =
            AuthSessionManager(
                tokenStore = InMemoryTokenStore(if (signedIn) STORED_TOKENS else null),
                authApi = throwingApi<AuthApi>(),
                websiteBaseUrl = "https://www.laugh-track.com",
                clock = Clock.systemUTC(),
            )
        if (signedIn) authSessionManager.restoreSession()
        return SavedShowsRepository(
            savedShowsApi = api,
            offlineQueue = queue,
            authSessionManager = authSessionManager,
            loginPromptController = loginPromptController,
        )
    }

    private class RecordingSavedShowQueue : SavedShowQueue {
        val enqueued = mutableListOf<Pair<Int, Boolean>>()
        val cancelled = mutableListOf<Int>()
        var cancelCount = 0

        override fun enqueue(
            showId: Int,
            isSaved: Boolean,
        ) {
            enqueued += showId to isSaved
        }

        override fun cancelAll() {
            cancelCount += 1
        }

        override fun cancel(showId: Int) {
            cancelled += showId
        }
    }

    private class ProgrammableSavedShowsApi(
        private val stateBehavior: suspend (Int) -> Response<SavedShowStateResponse> = {
            error("Unexpected state call")
        },
        private val listBehavior:
            suspend (
                SavedShowsApi.PeriodGetSavedShows?,
                Int?,
                Int?,
            ) -> Response<SavedShowListResponse> = { _, _, _ -> error("Unexpected list call") },
        private val saveBehavior: suspend (Int) -> Response<SavedShowStateResponse> = {
            stateResponse(true)
        },
        private val unsaveBehavior: suspend (Int) -> Response<SavedShowStateResponse> = {
            stateResponse(false)
        },
    ) : SavedShowsApi {
        val listCalls =
            mutableListOf<Triple<SavedShowsApi.PeriodGetSavedShows?, Int?, Int?>>()
        val mutationCalls = mutableListOf<Pair<Int, Boolean>>()
        var stateCalls = 0
            private set

        override suspend fun getSavedShowState(showId: Int): Response<SavedShowStateResponse> {
            stateCalls += 1
            return stateBehavior(showId)
        }

        override suspend fun getSavedShows(
            period: SavedShowsApi.PeriodGetSavedShows?,
            page: Int?,
            size: Int?,
        ): Response<SavedShowListResponse> {
            listCalls += Triple(period, page, size)
            return listBehavior(period, page, size)
        }

        override suspend fun saveShow(showId: Int): Response<SavedShowStateResponse> {
            mutationCalls += showId to true
            return saveBehavior(showId)
        }

        override suspend fun unsaveShow(showId: Int): Response<SavedShowStateResponse> {
            mutationCalls += showId to false
            return unsaveBehavior(showId)
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

        fun show(id: Int) =
            Show(
                id = id,
                clubId = 10,
                date = "2026-08-01T20:00:00.000Z",
                imageUrl = "https://example.com/show-$id.jpg",
            )

        fun stateResponse(isSaved: Boolean): Response<SavedShowStateResponse> =
            Response.success(SavedShowStateResponse(SavedShowState(isSaved)))

        fun listResponse(
            shows: List<Show>,
            page: Int,
            total: Int,
            totalPages: Int,
        ): Response<SavedShowListResponse> =
            Response.success(
                SavedShowListResponse(
                    data = shows,
                    total = total,
                    page = page,
                    propertySize = 20,
                    totalPages = totalPages,
                ),
            )

        fun errorResponse(code: Int): Response<SavedShowStateResponse> = Response.error(code, "".toResponseBody())
    }
}
