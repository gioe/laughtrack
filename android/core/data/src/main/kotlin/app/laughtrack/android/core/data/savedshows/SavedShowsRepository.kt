package app.laughtrack.android.core.data.savedshows

import app.laughtrack.android.core.data.auth.LoginPromptController
import app.laughtrack.android.core.data.runCatchingCancellable
import app.laughtrack.android.core.network.auth.AuthSessionManager
import app.laughtrack.android.core.network.generated.api.SavedShowsApi
import app.laughtrack.android.core.network.generated.infrastructure.ApiClient
import app.laughtrack.android.core.network.generated.model.SavedShowStateResponse
import app.laughtrack.android.core.network.generated.model.Show
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import retrofit2.Response
import java.io.IOException
import java.time.OffsetDateTime
import javax.inject.Inject
import javax.inject.Singleton

enum class SavedShowPeriod(
    internal val apiValue: SavedShowsApi.PeriodGetSavedShows,
) {
    UPCOMING(SavedShowsApi.PeriodGetSavedShows.UPCOMING),
    PAST(SavedShowsApi.PeriodGetSavedShows.PAST),
}

data class SavedShowsCollection(
    val shows: List<Show> = emptyList(),
    val page: Int = 0,
    val total: Int = 0,
    val totalPages: Int = 0,
    val isLoading: Boolean = false,
    val errorMessage: String? = null,
)

data class SavedShowsSnapshot(
    val values: Map<Int, Boolean> = emptyMap(),
    val upcoming: SavedShowsCollection = SavedShowsCollection(),
    val past: SavedShowsCollection = SavedShowsCollection(),
    val pending: Set<Int> = emptySet(),
)

sealed interface SavedShowMutationResult {
    data class Updated(val isSaved: Boolean) : SavedShowMutationResult

    data class Queued(val isSaved: Boolean) : SavedShowMutationResult

    data class Failure(val message: String) : SavedShowMutationResult

    data object SignInRequired : SavedShowMutationResult
}

@Singleton
class SavedShowsRepository
    internal constructor(
        private val savedShowsApi: SavedShowsApi,
        private val offlineQueue: SavedShowQueue,
        private val authSessionManager: AuthSessionManager,
        private val loginPromptController: LoginPromptController,
    ) {
        @Inject
        constructor(
            apiClient: ApiClient,
            offlineQueue: SavedShowOfflineQueue,
            authSessionManager: AuthSessionManager,
            loginPromptController: LoginPromptController,
        ) : this(
            savedShowsApi = apiClient.createService(SavedShowsApi::class.java),
            offlineQueue = offlineQueue,
            authSessionManager = authSessionManager,
            loginPromptController = loginPromptController,
        )

        private val _snapshot = MutableStateFlow(SavedShowsSnapshot())
        val snapshot: StateFlow<SavedShowsSnapshot> = _snapshot.asStateFlow()

        private val stateLock = Any()
        private var sessionGeneration = 0L
        private val mutationGenerations = mutableMapOf<Int, Long>()
        private val mutationMutexes = mutableMapOf<Int, Mutex>()
        private val loadGenerations = mutableMapOf<SavedShowPeriod, Long>()

        suspend fun loadState(showId: Int): Boolean? {
            if (!authSessionManager.signedIn.value) return null
            val request =
                synchronized(stateLock) {
                    StateLoadStart(
                        session = sessionGeneration,
                        mutationGeneration = mutationGenerations[showId],
                    )
                }

            val isSaved =
                savedShowsApi
                    .getSavedShowState(showId)
                    .bodyOrThrow()
                    .data
                    .isSaved
            return synchronized(stateLock) {
                if (!isCurrentSession(request.session) ||
                    mutationGenerations[showId] != request.mutationGeneration
                ) {
                    return@synchronized null
                }
                setValue(showId, isSaved)
                isSaved
            }
        }

        suspend fun refresh(
            period: SavedShowPeriod,
            size: Int = DEFAULT_PAGE_SIZE,
        ): Boolean = loadPage(period = period, page = 1, size = size, append = false)

        suspend fun loadNextPage(
            period: SavedShowPeriod,
            size: Int = DEFAULT_PAGE_SIZE,
        ): Boolean {
            val current = collection(period)
            if (current.isLoading) return false
            if (current.page > 0 && current.page >= current.totalPages) return false
            val nextPage = if (current.page == 0) 1 else current.page + 1
            return loadPage(period = period, page = nextPage, size = size, append = current.page > 0)
        }

        suspend fun toggleSaved(showId: Int): SavedShowMutationResult =
            setSaved(
                showId = showId,
                isSaved = !(_snapshot.value.values[showId] ?: false),
            )

        suspend fun setSaved(
            showId: Int,
            isSaved: Boolean,
        ): SavedShowMutationResult {
            if (!authSessionManager.signedIn.value) {
                loginPromptController.request()
                return SavedShowMutationResult.SignInRequired
            }

            val mutation =
                synchronized(stateLock) {
                    if (!authSessionManager.signedIn.value) return@synchronized null
                    if (_snapshot.value.values[showId] == isSaved) {
                        return@synchronized MutationStart.AlreadyCurrent
                    }

                    val before = _snapshot.value
                    val generation = (mutationGenerations[showId] ?: 0L) + 1L
                    mutationGenerations[showId] = generation
                    _snapshot.value = optimisticSnapshot(before, showId, isSaved)
                    MutationStart.Started(
                        session = sessionGeneration,
                        generation = generation,
                        beforeValue = before.values[showId],
                        beforeUpcoming = before.upcoming,
                        beforePast = before.past,
                    )
                }
            if (mutation == null) {
                loginPromptController.request()
                return SavedShowMutationResult.SignInRequired
            }
            if (mutation === MutationStart.AlreadyCurrent) return SavedShowMutationResult.Updated(isSaved)
            mutation as MutationStart.Started

            return try {
                mutationMutex(showId).withLock {
                    performMutation(showId, isSaved, mutation)
                }
            } catch (error: CancellationException) {
                synchronized(stateLock) {
                    if (isCurrentMutation(showId, mutation)) {
                        rollbackMutation(showId, mutation)
                    }
                }
                throw error
            }
        }

        private suspend fun performMutation(
            showId: Int,
            isSaved: Boolean,
            mutation: MutationStart.Started,
        ): SavedShowMutationResult {
            val responseResult =
                runCatchingCancellable {
                    if (isSaved) {
                        savedShowsApi.saveShow(showId)
                    } else {
                        savedShowsApi.unsaveShow(showId)
                    }
                }
            val response =
                responseResult.getOrElse { error ->
                    return handleMutationError(showId, isSaved, mutation, error)
                }

            return handleMutationResponse(showId, isSaved, mutation, response)
        }

        private fun handleMutationError(
            showId: Int,
            isSaved: Boolean,
            mutation: MutationStart.Started,
            error: Throwable,
        ): SavedShowMutationResult =
            synchronized(stateLock) {
                if (!isCurrentMutation(showId, mutation)) {
                    return@synchronized currentMutationResult(showId, isSaved)
                }
                if (error !is IOException) {
                    rollbackMutation(showId, mutation)
                    return@synchronized SavedShowMutationResult.Failure(MUTATION_FAILURE_MESSAGE)
                }
                offlineQueue.enqueue(showId, isSaved)
                clearPending(showId)
                SavedShowMutationResult.Queued(isSaved)
            }

        private fun handleMutationResponse(
            showId: Int,
            isSaved: Boolean,
            mutation: MutationStart.Started,
            response: Response<SavedShowStateResponse>,
        ): SavedShowMutationResult =
            synchronized(stateLock) {
                if (!isCurrentMutation(showId, mutation)) {
                    return@synchronized currentMutationResult(showId, isSaved)
                }
                when {
                    response.isSuccessful && response.body() != null -> {
                        val serverValue = response.body()!!.data.isSaved
                        offlineQueue.cancel(showId)
                        applyConfirmedValue(showId, serverValue)
                        clearPending(showId)
                        SavedShowMutationResult.Updated(serverValue)
                    }
                    response.code() >= 500 -> {
                        offlineQueue.enqueue(showId, isSaved)
                        clearPending(showId)
                        SavedShowMutationResult.Queued(isSaved)
                    }
                    else -> {
                        rollbackMutation(showId, mutation)
                        SavedShowMutationResult.Failure(MUTATION_FAILURE_MESSAGE)
                    }
                }
            }

        fun resetSignedOut() {
            synchronized(stateLock) {
                sessionGeneration += 1
                mutationGenerations.clear()
                loadGenerations.clear()
                _snapshot.value = SavedShowsSnapshot()
                offlineQueue.cancelAll()
            }
        }

        private suspend fun loadPage(
            period: SavedShowPeriod,
            page: Int,
            size: Int,
            append: Boolean,
        ): Boolean {
            if (!authSessionManager.signedIn.value) return false
            val request =
                synchronized(stateLock) {
                    if (!authSessionManager.signedIn.value) return@synchronized null
                    val current = collection(period)
                    if (append &&
                        (current.isLoading ||
                            current.page == 0 ||
                            current.page >= current.totalPages ||
                            page != current.page + 1)
                    ) {
                        return@synchronized null
                    }
                    val generation = (loadGenerations[period] ?: 0L) + 1L
                    loadGenerations[period] = generation
                    updateCollection(period) { it.copy(isLoading = true, errorMessage = null) }
                    LoadStart(
                        session = sessionGeneration,
                        generation = generation,
                        mutationGenerations = mutationGenerations.toMap(),
                    )
                } ?: return false

            val result =
                try {
                    runCatchingCancellable {
                        savedShowsApi
                            .getSavedShows(period = period.apiValue, page = page, size = size)
                            .bodyOrThrow()
                    }
                } catch (error: CancellationException) {
                    clearLoadingAfterCancellation(period, request)
                    throw error
                }

            return result.fold(
                onSuccess = { body ->
                    synchronized(stateLock) {
                        if (!isCurrentLoad(period, request)) return@synchronized false
                        val currentSnapshot = _snapshot.value
                        val effectiveData =
                            body.data.filterNot { show ->
                                val changedDuringLoad =
                                    mutationGenerations[show.id] != request.mutationGenerations[show.id]
                                val pendingUnsave =
                                    show.id in currentSnapshot.pending &&
                                        currentSnapshot.values[show.id] == false
                                (changedDuringLoad || pendingUnsave) &&
                                    currentSnapshot.values[show.id] == false
                            }
                        val current = collection(period)
                        val shows =
                            if (append) {
                                orderShows(
                                    shows = (current.shows + effectiveData).distinctBy(Show::id),
                                    period = period,
                                )
                            } else {
                                orderShows(effectiveData, period)
                            }
                        updateCollection(period) {
                            SavedShowsCollection(
                                shows = shows,
                                page = body.page,
                                total = (body.total - (body.data.size - effectiveData.size)).coerceAtLeast(shows.size),
                                totalPages = body.totalPages,
                                isLoading = false,
                                errorMessage = null,
                            )
                        }
                        val pageValues = effectiveData.associate { it.id to true }
                        _snapshot.value =
                            _snapshot.value.copy(
                                values = _snapshot.value.values + pageValues,
                            )
                        true
                    }
                },
                onFailure = {
                    synchronized(stateLock) {
                        if (!isCurrentLoad(period, request)) return@synchronized false
                        updateCollection(period) {
                            it.copy(
                                isLoading = false,
                                errorMessage = COLLECTION_FAILURE_MESSAGE,
                            )
                        }
                        false
                    }
                },
            )
        }

        private fun clearLoadingAfterCancellation(
            period: SavedShowPeriod,
            request: LoadStart,
        ) {
            synchronized(stateLock) {
                if (isCurrentLoad(period, request)) {
                    updateCollection(period) { it.copy(isLoading = false) }
                }
            }
        }

        private fun orderShows(
            shows: List<Show>,
            period: SavedShowPeriod,
        ): List<Show> =
            shows.sortedWith { left, right ->
                val leftInstant = runCatching { OffsetDateTime.parse(left.date).toInstant() }.getOrNull()
                val rightInstant = runCatching { OffsetDateTime.parse(right.date).toInstant() }.getOrNull()
                val dateComparison =
                    if (leftInstant != null && rightInstant != null) {
                        leftInstant.compareTo(rightInstant)
                    } else {
                        left.date.compareTo(right.date)
                    }
                val orderedDateComparison =
                    when (period) {
                        SavedShowPeriod.UPCOMING -> dateComparison
                        SavedShowPeriod.PAST -> -dateComparison
                    }
                if (orderedDateComparison != 0) {
                    orderedDateComparison
                } else {
                    when (period) {
                        SavedShowPeriod.UPCOMING -> left.id.compareTo(right.id)
                        SavedShowPeriod.PAST -> right.id.compareTo(left.id)
                    }
                }
            }

        private fun optimisticSnapshot(
            snapshot: SavedShowsSnapshot,
            showId: Int,
            isSaved: Boolean,
        ): SavedShowsSnapshot =
            snapshot.copy(
                values = snapshot.values + (showId to isSaved),
                upcoming = if (isSaved) snapshot.upcoming else snapshot.upcoming.without(showId),
                past = if (isSaved) snapshot.past else snapshot.past.without(showId),
                pending = snapshot.pending + showId,
            )

        private fun SavedShowsCollection.without(showId: Int): SavedShowsCollection {
            val filtered = shows.filterNot { it.id == showId }
            val removed = shows.size - filtered.size
            return copy(
                shows = filtered,
                total = (total - removed).coerceAtLeast(0),
            )
        }

        private fun setValue(
            showId: Int,
            isSaved: Boolean,
        ) {
            _snapshot.value =
                _snapshot.value.copy(
                    values = _snapshot.value.values + (showId to isSaved),
                )
        }

        private fun applyConfirmedValue(
            showId: Int,
            isSaved: Boolean,
        ) {
            val current = _snapshot.value
            _snapshot.value =
                current.copy(
                    values = current.values + (showId to isSaved),
                    upcoming = if (isSaved) current.upcoming else current.upcoming.without(showId),
                    past = if (isSaved) current.past else current.past.without(showId),
                )
        }

        private fun rollbackMutation(
            showId: Int,
            mutation: MutationStart.Started,
        ) {
            val current = _snapshot.value
            val values =
                if (mutation.beforeValue == null) {
                    current.values - showId
                } else {
                    current.values + (showId to mutation.beforeValue)
                }
            _snapshot.value =
                current.copy(
                    values = values,
                    upcoming = current.upcoming.restoreShowFrom(mutation.beforeUpcoming, showId),
                    past = current.past.restoreShowFrom(mutation.beforePast, showId),
                    pending = current.pending - showId,
                )
        }

        private fun SavedShowsCollection.restoreShowFrom(
            before: SavedShowsCollection,
            showId: Int,
        ): SavedShowsCollection {
            val previousIndex = before.shows.indexOfFirst { it.id == showId }
            val currentIndex = shows.indexOfFirst { it.id == showId }
            if (previousIndex < 0 || currentIndex >= 0) return this

            val restored = shows.toMutableList()
            restored.add(previousIndex.coerceAtMost(restored.size), before.shows[previousIndex])
            return copy(
                shows = restored,
                total = (total + 1).coerceAtLeast(before.total),
            )
        }

        private fun isCurrentSession(generation: Long): Boolean =
            generation == sessionGeneration && authSessionManager.signedIn.value

        private fun isCurrentMutation(
            showId: Int,
            mutation: MutationStart.Started,
        ): Boolean =
            isCurrentSession(mutation.session) &&
                mutationGenerations[showId] == mutation.generation

        private fun isCurrentLoad(
            period: SavedShowPeriod,
            load: LoadStart,
        ): Boolean =
            isCurrentSession(load.session) &&
                loadGenerations[period] == load.generation

        private fun currentMutationResult(
            showId: Int,
            fallback: Boolean,
        ): SavedShowMutationResult = SavedShowMutationResult.Updated(_snapshot.value.values[showId] ?: fallback)

        private fun mutationMutex(showId: Int): Mutex =
            synchronized(stateLock) {
                mutationMutexes.getOrPut(showId) { Mutex() }
            }

        private fun clearPending(showId: Int) {
            _snapshot.value =
                _snapshot.value.copy(
                    pending = _snapshot.value.pending - showId,
                )
        }

        private fun collection(period: SavedShowPeriod): SavedShowsCollection =
            when (period) {
                SavedShowPeriod.UPCOMING -> _snapshot.value.upcoming
                SavedShowPeriod.PAST -> _snapshot.value.past
            }

        private fun updateCollection(
            period: SavedShowPeriod,
            transform: (SavedShowsCollection) -> SavedShowsCollection,
        ) {
            val current = _snapshot.value
            _snapshot.value =
                when (period) {
                    SavedShowPeriod.UPCOMING -> current.copy(upcoming = transform(current.upcoming))
                    SavedShowPeriod.PAST -> current.copy(past = transform(current.past))
                }
        }

        private fun <T> Response<T>.bodyOrThrow(): T {
            if (!isSuccessful) throw IOException("HTTP ${code()}")
            return body() ?: throw IOException("Empty response body")
        }

        private companion object {
            const val DEFAULT_PAGE_SIZE = 20
            const val MUTATION_FAILURE_MESSAGE = "LaughTrack couldn't update that saved show."
            const val COLLECTION_FAILURE_MESSAGE =
                "Saved shows are still available offline, but the latest sync did not finish."
        }

        private sealed interface MutationStart {
            data object AlreadyCurrent : MutationStart

            data class Started(
                val session: Long,
                val generation: Long,
                val beforeValue: Boolean?,
                val beforeUpcoming: SavedShowsCollection,
                val beforePast: SavedShowsCollection,
            ) : MutationStart
        }

        private data class LoadStart(
            val session: Long,
            val generation: Long,
            val mutationGenerations: Map<Int, Long>,
        )

        private data class StateLoadStart(
            val session: Long,
            val mutationGeneration: Long?,
        )
    }
