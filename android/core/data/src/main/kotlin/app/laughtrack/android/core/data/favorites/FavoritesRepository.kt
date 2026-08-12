package app.laughtrack.android.core.data.favorites

import app.laughtrack.android.core.data.auth.LoginPromptController
import app.laughtrack.android.core.data.runCatchingCancellable
import app.laughtrack.android.core.network.auth.AuthSessionManager
import app.laughtrack.android.core.network.generated.api.FavoritesApi
import app.laughtrack.android.core.network.generated.model.AddFavoriteClubRequest
import app.laughtrack.android.core.network.generated.model.AddFavoritePodcastRequest
import app.laughtrack.android.core.network.generated.model.AddFavoriteRequest
import app.laughtrack.android.core.network.generated.model.ComedianSearchItem
import app.laughtrack.android.core.network.generated.model.FavoriteClubItem
import app.laughtrack.android.core.network.generated.model.FavoritePodcastItem
import app.laughtrack.android.core.network.generated.model.FavoriteResponse
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import retrofit2.Response
import java.io.IOException
import javax.inject.Inject
import javax.inject.Singleton

data class FavoritesSnapshot(
    val comedians: List<ComedianSearchItem> = emptyList(),
    val clubs: List<FavoriteClubItem> = emptyList(),
    val podcasts: List<FavoritePodcastItem> = emptyList(),
    val comedianValues: Map<String, Boolean> = emptyMap(),
    val clubValues: Map<Int, Boolean> = emptyMap(),
    val podcastValues: Map<Int, Boolean> = emptyMap(),
    val pending: Set<String> = emptySet(),
    val isLoading: Boolean = false,
    val errorMessage: String? = null,
)

sealed interface FavoriteToggleResult {
    data class Updated(val isFavorite: Boolean) : FavoriteToggleResult

    data class Queued(val isFavorite: Boolean) : FavoriteToggleResult

    data class Failure(val message: String) : FavoriteToggleResult

    /** The user is signed out; the sign-in prompt was requested instead of toggling. */
    data object SignInRequired : FavoriteToggleResult
}

@Singleton
class FavoritesRepository
    @Inject
    constructor(
        private val favoritesApi: FavoritesApi,
        private val offlineQueue: FavoriteQueue,
        private val authSessionManager: AuthSessionManager,
        private val loginPromptController: LoginPromptController,
    ) {
        private val _snapshot = MutableStateFlow(FavoritesSnapshot())
        val snapshot: StateFlow<FavoritesSnapshot> = _snapshot.asStateFlow()

        private val stateLock = Any()
        private var sessionGeneration = 0L
        private var refreshGeneration = 0L
        private val mutationGenerations = mutableMapOf<MutationKey, Long>()
        private val mutationMutexes = mutableMapOf<MutationKey, Mutex>()

        suspend fun refreshSignedInFavorites() {
            val request =
                synchronized(stateLock) {
                    refreshGeneration += 1
                    _snapshot.value = _snapshot.value.copy(isLoading = true, errorMessage = null)
                    RefreshStart(
                        session = sessionGeneration,
                        generation = refreshGeneration,
                        mutationGenerations = mutationGenerations.toMap(),
                    )
                }

            val result =
                try {
                    runCatchingCancellable {
                        RefreshData(
                            comedians = favoritesApi.getFavorites().bodyOrThrow().data,
                            clubs = favoritesApi.getFavoriteClubs().bodyOrThrow().data,
                            podcasts = favoritesApi.getFavoritePodcasts().bodyOrThrow().data,
                        )
                    }
                } catch (error: CancellationException) {
                    synchronized(stateLock) {
                        if (isCurrentRefresh(request)) {
                            _snapshot.value = _snapshot.value.copy(isLoading = false)
                        }
                    }
                    throw error
                }

            result.fold(
                onSuccess = { data ->
                    synchronized(stateLock) {
                        if (!isCurrentRefresh(request)) return@synchronized
                        applyRefresh(data, request)
                    }
                },
                onFailure = {
                    synchronized(stateLock) {
                        if (!isCurrentRefresh(request)) return@synchronized
                        _snapshot.value =
                            _snapshot.value.copy(
                                isLoading = false,
                                errorMessage = REFRESH_FAILURE_MESSAGE,
                            )
                    }
                },
            )
        }

        fun resetSignedOut() {
            synchronized(stateLock) {
                sessionGeneration += 1
                refreshGeneration += 1
                mutationGenerations.clear()
                _snapshot.value = FavoritesSnapshot()
                offlineQueue.cancelAll()
            }
        }

        suspend fun toggleComedian(uuid: String): FavoriteToggleResult =
            toggle(
                entity = FavoriteEntity.COMEDIAN,
                id = uuid,
                currentValue = _snapshot.value.comedianValues[uuid] ?: true,
                optimistic = { next ->
                    val current = _snapshot.value
                    _snapshot.value =
                        current.copy(
                            comedianValues = current.comedianValues + (uuid to next),
                            comedians =
                                if (next) {
                                    current.comedians
                                } else {
                                    current.comedians.filterNot { it.uuid == uuid }
                                },
                        )
                },
                serverCall = { next ->
                    if (next) {
                        favoritesApi.addFavorite(AddFavoriteRequest(uuid))
                    } else {
                        favoritesApi.removeFavorite(uuid)
                    }
                },
                queue = { next -> offlineQueue.enqueue(FavoriteEntity.COMEDIAN, uuid, next) },
            )

        suspend fun setComedianFavorite(
            uuid: String,
            isFavorite: Boolean,
            knownCurrentValue: Boolean? = null,
        ): FavoriteToggleResult {
            val currentValue = knownCurrentValue ?: _snapshot.value.comedianValues[uuid] ?: false
            if (currentValue == isFavorite) return FavoriteToggleResult.Updated(isFavorite)
            return toggle(
                entity = FavoriteEntity.COMEDIAN,
                id = uuid,
                currentValue = currentValue,
                optimistic = { next ->
                    val current = _snapshot.value
                    _snapshot.value =
                        current.copy(
                            comedianValues = current.comedianValues + (uuid to next),
                            comedians =
                                if (next) current.comedians else current.comedians.filterNot { it.uuid == uuid },
                        )
                },
                serverCall = { next ->
                    if (next) {
                        favoritesApi.addFavorite(AddFavoriteRequest(uuid))
                    } else {
                        favoritesApi.removeFavorite(uuid)
                    }
                },
                queue = { next -> offlineQueue.enqueue(FavoriteEntity.COMEDIAN, uuid, next) },
            )
        }

        suspend fun toggleClub(id: Int): FavoriteToggleResult =
            toggle(
                entity = FavoriteEntity.CLUB,
                id = id.toString(),
                currentValue = _snapshot.value.clubValues[id] ?: true,
                optimistic = { next ->
                    val current = _snapshot.value
                    _snapshot.value =
                        current.copy(
                            clubValues = current.clubValues + (id to next),
                            clubs = if (next) current.clubs else current.clubs.filterNot { it.id == id },
                        )
                },
                serverCall = { next ->
                    if (next) {
                        favoritesApi.addFavoriteClub(AddFavoriteClubRequest(id))
                    } else {
                        favoritesApi.removeFavoriteClub(id)
                    }
                },
                queue = { next -> offlineQueue.enqueue(FavoriteEntity.CLUB, id.toString(), next) },
            )

        suspend fun setClubFavorite(
            id: Int,
            isFavorite: Boolean,
        ): FavoriteToggleResult {
            val currentValue = _snapshot.value.clubValues[id] ?: false
            if (currentValue == isFavorite) return FavoriteToggleResult.Updated(isFavorite)
            return toggle(
                entity = FavoriteEntity.CLUB,
                id = id.toString(),
                currentValue = currentValue,
                optimistic = { next ->
                    val current = _snapshot.value
                    _snapshot.value =
                        current.copy(
                            clubValues = current.clubValues + (id to next),
                            clubs = if (next) current.clubs else current.clubs.filterNot { it.id == id },
                        )
                },
                serverCall = { next ->
                    if (next) {
                        favoritesApi.addFavoriteClub(AddFavoriteClubRequest(id))
                    } else {
                        favoritesApi.removeFavoriteClub(id)
                    }
                },
                queue = { next -> offlineQueue.enqueue(FavoriteEntity.CLUB, id.toString(), next) },
            )
        }

        suspend fun togglePodcast(id: Int): FavoriteToggleResult =
            toggle(
                entity = FavoriteEntity.PODCAST,
                id = id.toString(),
                currentValue = _snapshot.value.podcastValues[id] ?: true,
                optimistic = { next ->
                    val current = _snapshot.value
                    _snapshot.value =
                        current.copy(
                            podcastValues = current.podcastValues + (id to next),
                            podcasts = if (next) current.podcasts else current.podcasts.filterNot { it.id == id },
                        )
                },
                serverCall = { next ->
                    if (next) {
                        favoritesApi.addFavoritePodcast(AddFavoritePodcastRequest(id))
                    } else {
                        favoritesApi.removeFavoritePodcast(id)
                    }
                },
                queue = { next -> offlineQueue.enqueue(FavoriteEntity.PODCAST, id.toString(), next) },
            )

        suspend fun setPodcastFavorite(
            id: Int,
            isFavorite: Boolean,
            knownCurrentValue: Boolean? = null,
        ): FavoriteToggleResult {
            val currentValue = knownCurrentValue ?: _snapshot.value.podcastValues[id] ?: false
            if (currentValue == isFavorite) return FavoriteToggleResult.Updated(isFavorite)
            return toggle(
                entity = FavoriteEntity.PODCAST,
                id = id.toString(),
                currentValue = currentValue,
                optimistic = { next ->
                    val current = _snapshot.value
                    _snapshot.value =
                        current.copy(
                            podcastValues = current.podcastValues + (id to next),
                            podcasts = if (next) current.podcasts else current.podcasts.filterNot { it.id == id },
                        )
                },
                serverCall = { next ->
                    if (next) {
                        favoritesApi.addFavoritePodcast(AddFavoritePodcastRequest(id))
                    } else {
                        favoritesApi.removeFavoritePodcast(id)
                    }
                },
                queue = { next -> offlineQueue.enqueue(FavoriteEntity.PODCAST, id.toString(), next) },
            )
        }

        @Suppress("LongParameterList")
        private suspend fun toggle(
            entity: FavoriteEntity,
            id: String,
            currentValue: Boolean,
            optimistic: (Boolean) -> Unit,
            serverCall: suspend (Boolean) -> Response<FavoriteResponse>,
            queue: (Boolean) -> Unit,
        ): FavoriteToggleResult {
            // Gate favoriting on sign-in (mirrors iOS): a guest tap requests the
            // sign-in prompt rather than optimistically toggling and firing a
            // doomed 401 (which would revert with a misleading "couldn't update"
            // error). Favorites are a per-account concept, so there is nothing to
            // persist offline for a signed-out user.
            if (!authSessionManager.signedIn.value) {
                loginPromptController.request()
                return FavoriteToggleResult.SignInRequired
            }

            val mutationKey = MutationKey(entity, id)
            val nextValue = !currentValue
            val mutation =
                synchronized(stateLock) {
                    if (!authSessionManager.signedIn.value) return@synchronized null
                    val generation = (mutationGenerations[mutationKey] ?: 0L) + 1L
                    mutationGenerations[mutationKey] = generation
                    val before = _snapshot.value
                    setPending(mutationKey.pendingKey, true)
                    optimistic(nextValue)
                    MutationStart(
                        session = sessionGeneration,
                        generation = generation,
                        before = before,
                        beforeValue = currentValue,
                    )
                }
            if (mutation == null) {
                loginPromptController.request()
                return FavoriteToggleResult.SignInRequired
            }

            return try {
                mutationMutex(mutationKey).withLock {
                    synchronized(stateLock) {
                        if (!isCurrentMutation(mutationKey, mutation)) {
                            return@withLock currentMutationResult(mutationKey, nextValue)
                        }
                    }
                    val responseResult = runCatchingCancellable { serverCall(nextValue) }
                    val response =
                        responseResult.getOrElse { error ->
                            return@withLock handleMutationError(
                                key = mutationKey,
                                nextValue = nextValue,
                                mutation = mutation,
                                error = error,
                                queue = queue,
                            )
                        }

                    synchronized(stateLock) {
                        if (!isCurrentMutation(mutationKey, mutation)) {
                            return@synchronized currentMutationResult(mutationKey, nextValue)
                        }
                        when {
                            response.isSuccessful && response.body() != null -> {
                                offlineQueue.cancel(entity, id)
                                optimistic(nextValue)
                                setPending(mutationKey.pendingKey, false)
                                FavoriteToggleResult.Updated(nextValue)
                            }
                            response.code() >= 500 -> {
                                queue(nextValue)
                                setPending(mutationKey.pendingKey, false)
                                FavoriteToggleResult.Queued(nextValue)
                            }
                            else -> {
                                rollbackMutation(mutationKey, mutation)
                                FavoriteToggleResult.Failure(MUTATION_FAILURE_MESSAGE)
                            }
                        }
                    }
                }
            } catch (error: CancellationException) {
                synchronized(stateLock) {
                    if (isCurrentMutation(mutationKey, mutation)) {
                        rollbackMutation(mutationKey, mutation)
                    }
                }
                throw error
            }
        }

        private fun handleMutationError(
            key: MutationKey,
            nextValue: Boolean,
            mutation: MutationStart,
            error: Throwable,
            queue: (Boolean) -> Unit,
        ): FavoriteToggleResult =
            synchronized(stateLock) {
                if (!isCurrentMutation(key, mutation)) {
                    return@synchronized currentMutationResult(key, nextValue)
                }
                if (error !is IOException) {
                    rollbackMutation(key, mutation)
                    return@synchronized FavoriteToggleResult.Failure(MUTATION_FAILURE_MESSAGE)
                }
                queue(nextValue)
                setPending(key.pendingKey, false)
                FavoriteToggleResult.Queued(nextValue)
            }

        private fun setPending(
            key: String,
            isPending: Boolean,
        ) {
            val current = _snapshot.value
            _snapshot.value =
                current.copy(
                    pending = if (isPending) current.pending + key else current.pending - key,
                )
        }

        private fun mutationMutex(key: MutationKey): Mutex =
            synchronized(stateLock) {
                mutationMutexes.getOrPut(key) { Mutex() }
            }

        private fun isCurrentSession(generation: Long): Boolean =
            generation == sessionGeneration && authSessionManager.signedIn.value

        private fun isCurrentMutation(
            key: MutationKey,
            mutation: MutationStart,
        ): Boolean =
            isCurrentSession(mutation.session) &&
                mutationGenerations[key] == mutation.generation

        private fun isCurrentRefresh(refresh: RefreshStart): Boolean =
            refresh.session == sessionGeneration &&
                refreshGeneration == refresh.generation

        private fun currentMutationResult(
            key: MutationKey,
            fallback: Boolean,
        ): FavoriteToggleResult {
            val value =
                when (key.entity) {
                    FavoriteEntity.COMEDIAN -> _snapshot.value.comedianValues[key.id]
                    FavoriteEntity.CLUB -> key.id.toIntOrNull()?.let(_snapshot.value.clubValues::get)
                    FavoriteEntity.PODCAST -> key.id.toIntOrNull()?.let(_snapshot.value.podcastValues::get)
                }
            return FavoriteToggleResult.Updated(value ?: fallback)
        }

        private fun rollbackMutation(
            key: MutationKey,
            mutation: MutationStart,
        ) {
            val current = _snapshot.value
            _snapshot.value =
                when (key.entity) {
                    FavoriteEntity.COMEDIAN ->
                        current.copy(
                            comedians =
                                restoreItem(
                                    current = current.comedians,
                                    before = mutation.before.comedians,
                                    id = key.id,
                                    itemId = ComedianSearchItem::uuid,
                                ),
                            comedianValues =
                                current.comedianValues + (key.id to mutation.beforeValue),
                            pending = current.pending - key.pendingKey,
                        )
                    FavoriteEntity.CLUB -> {
                        val id = key.id.toInt()
                        current.copy(
                            clubs =
                                restoreItem(
                                    current = current.clubs,
                                    before = mutation.before.clubs,
                                    id = id,
                                    itemId = FavoriteClubItem::id,
                                ),
                            clubValues = current.clubValues + (id to mutation.beforeValue),
                            pending = current.pending - key.pendingKey,
                        )
                    }
                    FavoriteEntity.PODCAST -> {
                        val id = key.id.toInt()
                        current.copy(
                            podcasts =
                                restoreItem(
                                    current = current.podcasts,
                                    before = mutation.before.podcasts,
                                    id = id,
                                    itemId = FavoritePodcastItem::id,
                                ),
                            podcastValues =
                                current.podcastValues + (id to mutation.beforeValue),
                            pending = current.pending - key.pendingKey,
                        )
                    }
                }
        }

        private fun <T, K> restoreItem(
            current: List<T>,
            before: List<T>,
            id: K,
            itemId: (T) -> K,
        ): List<T> {
            val beforeIndex = before.indexOfFirst { itemId(it) == id }
            val without = current.filterNot { itemId(it) == id }.toMutableList()
            if (beforeIndex < 0) return without
            without.add(beforeIndex.coerceAtMost(without.size), before[beforeIndex])
            return without
        }

        private fun applyRefresh(
            data: RefreshData,
            request: RefreshStart,
        ) {
            val current = _snapshot.value
            val comedians =
                mergeRefreshedItems(
                    server = data.comedians,
                    current = current.comedians,
                    entity = FavoriteEntity.COMEDIAN,
                    itemId = ComedianSearchItem::uuid,
                    currentValues = current.comedianValues,
                    request = request,
                )
            val clubs =
                mergeRefreshedItems(
                    server = data.clubs,
                    current = current.clubs,
                    entity = FavoriteEntity.CLUB,
                    itemId = { it.id.toString() },
                    currentValues = current.clubValues.mapKeys { it.key.toString() },
                    request = request,
                )
            val podcasts =
                mergeRefreshedItems(
                    server = data.podcasts,
                    current = current.podcasts,
                    entity = FavoriteEntity.PODCAST,
                    itemId = { it.id.toString() },
                    currentValues = current.podcastValues.mapKeys { it.key.toString() },
                    request = request,
                )
            _snapshot.value =
                current.copy(
                    comedians = comedians,
                    clubs = clubs,
                    podcasts = podcasts,
                    comedianValues =
                        mergedRefreshedValues(
                            serverIds = data.comedians.map(ComedianSearchItem::uuid),
                            currentValues = current.comedianValues,
                            entity = FavoriteEntity.COMEDIAN,
                            request = request,
                        ),
                    clubValues =
                        mergedRefreshedValues(
                            serverIds = data.clubs.map(FavoriteClubItem::id),
                            currentValues = current.clubValues,
                            entity = FavoriteEntity.CLUB,
                            request = request,
                            keyToId = Int::toString,
                        ),
                    podcastValues =
                        mergedRefreshedValues(
                            serverIds = data.podcasts.map(FavoritePodcastItem::id),
                            currentValues = current.podcastValues,
                            entity = FavoriteEntity.PODCAST,
                            request = request,
                            keyToId = Int::toString,
                        ),
                    isLoading = false,
                    errorMessage = null,
                )
        }

        @Suppress("LongParameterList")
        private fun <T> mergeRefreshedItems(
            server: List<T>,
            current: List<T>,
            entity: FavoriteEntity,
            itemId: (T) -> String,
            currentValues: Map<String, Boolean>,
            request: RefreshStart,
        ): List<T> {
            val retainedServer =
                server.filterNot { item ->
                    val id = itemId(item)
                    changedSince(request, entity, id) && currentValues[id] == false
                }
            val retainedCurrent =
                current.filter { item ->
                    val id = itemId(item)
                    changedSince(request, entity, id) &&
                        currentValues[id] == true &&
                        retainedServer.none { itemId(it) == id }
                }
            return retainedServer + retainedCurrent
        }

        private fun <K> mergedRefreshedValues(
            serverIds: List<K>,
            currentValues: Map<K, Boolean>,
            entity: FavoriteEntity,
            request: RefreshStart,
            keyToId: (K) -> String = { it.toString() },
        ): Map<K, Boolean> {
            val merged = serverIds.associateWith { true }.toMutableMap()
            currentValues.forEach { (key, value) ->
                if (changedSince(request, entity, keyToId(key))) {
                    merged[key] = value
                }
            }
            return merged
        }

        private fun changedSince(
            request: RefreshStart,
            entity: FavoriteEntity,
            id: String,
        ): Boolean {
            val key = MutationKey(entity, id)
            return mutationGenerations[key] != request.mutationGenerations[key]
        }

        private fun <T> Response<T>.bodyOrThrow(): T {
            if (!isSuccessful) {
                throw IOException("HTTP ${code()}")
            }
            return body() ?: throw IOException("Empty response body")
        }

        private data class MutationKey(
            val entity: FavoriteEntity,
            val id: String,
        ) {
            val pendingKey: String = entity.name + id
        }

        private data class MutationStart(
            val session: Long,
            val generation: Long,
            val before: FavoritesSnapshot,
            val beforeValue: Boolean,
        )

        private data class RefreshStart(
            val session: Long,
            val generation: Long,
            val mutationGenerations: Map<MutationKey, Long>,
        )

        private data class RefreshData(
            val comedians: List<ComedianSearchItem>,
            val clubs: List<FavoriteClubItem>,
            val podcasts: List<FavoritePodcastItem>,
        )

        private companion object {
            const val MUTATION_FAILURE_MESSAGE = "LaughTrack couldn't update that favorite."
            const val REFRESH_FAILURE_MESSAGE =
                "Favorites are still available offline, but the latest sync did not finish."
        }
    }
