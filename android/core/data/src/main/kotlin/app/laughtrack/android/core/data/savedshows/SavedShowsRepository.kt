package app.laughtrack.android.core.data.savedshows

import app.laughtrack.android.core.data.auth.LoginPromptController
import app.laughtrack.android.core.data.runCatchingCancellable
import app.laughtrack.android.core.network.auth.AuthSessionManager
import app.laughtrack.android.core.network.generated.api.SavedShowsApi
import app.laughtrack.android.core.network.generated.infrastructure.ApiClient
import app.laughtrack.android.core.network.generated.model.Show
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import retrofit2.Response
import java.io.IOException
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

        suspend fun loadState(showId: Int): Boolean? {
            if (!authSessionManager.signedIn.value) return null

            val isSaved =
                savedShowsApi
                    .getSavedShowState(showId)
                    .bodyOrThrow()
                    .data
                    .isSaved
            _snapshot.value =
                _snapshot.value.copy(
                    values = _snapshot.value.values + (showId to isSaved),
                )
            return isSaved
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

            if (_snapshot.value.values[showId] == isSaved) {
                return SavedShowMutationResult.Updated(isSaved)
            }

            val before = _snapshot.value
            _snapshot.value = optimisticSnapshot(before, showId, isSaved)

            val responseResult =
                try {
                    runCatchingCancellable {
                        if (isSaved) {
                            savedShowsApi.saveShow(showId)
                        } else {
                            savedShowsApi.unsaveShow(showId)
                        }
                    }
                } catch (error: CancellationException) {
                    _snapshot.value = before
                    throw error
                }
            val response =
                responseResult.getOrElse { error ->
                    if (error !is IOException) {
                        _snapshot.value = before
                        return SavedShowMutationResult.Failure(MUTATION_FAILURE_MESSAGE)
                    }
                    offlineQueue.enqueue(showId, isSaved)
                    clearPending(showId)
                    return SavedShowMutationResult.Queued(isSaved)
                }

            return when {
                response.isSuccessful && response.body() != null -> {
                    val serverValue = response.body()!!.data.isSaved
                    setValue(showId, serverValue)
                    clearPending(showId)
                    SavedShowMutationResult.Updated(serverValue)
                }
                response.code() >= 500 -> {
                    offlineQueue.enqueue(showId, isSaved)
                    clearPending(showId)
                    SavedShowMutationResult.Queued(isSaved)
                }
                else -> {
                    _snapshot.value = before
                    SavedShowMutationResult.Failure(MUTATION_FAILURE_MESSAGE)
                }
            }
        }

        fun resetSignedOut() {
            _snapshot.value = SavedShowsSnapshot()
        }

        private suspend fun loadPage(
            period: SavedShowPeriod,
            page: Int,
            size: Int,
            append: Boolean,
        ): Boolean {
            if (!authSessionManager.signedIn.value) return false
            updateCollection(period) { it.copy(isLoading = true, errorMessage = null) }

            return runCatchingCancellable {
                savedShowsApi
                    .getSavedShows(period = period.apiValue, page = page, size = size)
                    .bodyOrThrow()
            }.fold(
                onSuccess = { body ->
                    val current = collection(period)
                    val shows =
                        if (append) {
                            (current.shows + body.data).distinctBy(Show::id)
                        } else {
                            body.data
                        }
                    updateCollection(period) {
                        SavedShowsCollection(
                            shows = shows,
                            page = body.page,
                            total = body.total,
                            totalPages = body.totalPages,
                            isLoading = false,
                            errorMessage = null,
                        )
                    }
                    val pageValues = body.data.associate { it.id to true }
                    _snapshot.value =
                        _snapshot.value.copy(
                            values = _snapshot.value.values + pageValues,
                        )
                    true
                },
                onFailure = {
                    updateCollection(period) {
                        it.copy(
                            isLoading = false,
                            errorMessage = COLLECTION_FAILURE_MESSAGE,
                        )
                    }
                    false
                },
            )
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
    }
