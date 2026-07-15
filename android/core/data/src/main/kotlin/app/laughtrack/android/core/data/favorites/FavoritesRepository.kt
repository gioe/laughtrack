package app.laughtrack.android.core.data.favorites

import app.laughtrack.android.core.data.auth.LoginPromptController
import app.laughtrack.android.core.network.auth.AuthSessionManager
import app.laughtrack.android.core.network.generated.api.FavoritesApi
import app.laughtrack.android.core.network.generated.model.AddFavoriteClubRequest
import app.laughtrack.android.core.network.generated.model.AddFavoritePodcastRequest
import app.laughtrack.android.core.network.generated.model.AddFavoriteRequest
import app.laughtrack.android.core.network.generated.model.ComedianSearchItem
import app.laughtrack.android.core.network.generated.model.FavoriteClubItem
import app.laughtrack.android.core.network.generated.model.FavoritePodcastItem
import app.laughtrack.android.core.network.generated.model.Show
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import retrofit2.Response
import java.io.IOException
import javax.inject.Inject
import javax.inject.Singleton

data class FavoritesSnapshot(
    val comedians: List<ComedianSearchItem> = emptyList(),
    val shows: List<Show> = emptyList(),
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

        suspend fun refreshSignedInFavorites() {
            _snapshot.value = _snapshot.value.copy(isLoading = true, errorMessage = null)

            runCatching {
                val comedians = favoritesApi.getFavorites().bodyOrThrow().data
                val shows = favoritesApi.getFavoriteShows(page = 1, size = 20).bodyOrThrow().data
                val clubs = favoritesApi.getFavoriteClubs().bodyOrThrow().data
                val podcasts = favoritesApi.getFavoritePodcasts().bodyOrThrow().data

                _snapshot.value =
                    _snapshot.value.copy(
                        comedians = comedians,
                        shows = shows,
                        clubs = clubs,
                        podcasts = podcasts,
                        comedianValues = comedians.associate { it.uuid to true },
                        clubValues = clubs.associate { it.id to true },
                        podcastValues = podcasts.associate { it.id to true },
                        isLoading = false,
                        errorMessage = null,
                    )
            }.onFailure {
                _snapshot.value =
                    _snapshot.value.copy(
                        isLoading = false,
                        errorMessage = "Favorites are still available offline, but the latest sync did not finish.",
                    )
            }
        }

        fun resetSignedOut() {
            _snapshot.value = FavoritesSnapshot()
        }

        suspend fun toggleComedian(uuid: String): FavoriteToggleResult =
            toggle(
                key = FavoriteEntity.COMEDIAN.name + uuid,
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
        ): FavoriteToggleResult {
            val currentValue = _snapshot.value.comedianValues[uuid] ?: false
            if (currentValue == isFavorite) return FavoriteToggleResult.Updated(isFavorite)
            return toggle(
                key = FavoriteEntity.COMEDIAN.name + uuid,
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
                key = FavoriteEntity.CLUB.name + id,
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
                key = FavoriteEntity.CLUB.name + id,
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
                key = FavoriteEntity.PODCAST.name + id,
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
        ): FavoriteToggleResult {
            val currentValue = _snapshot.value.podcastValues[id] ?: false
            if (currentValue == isFavorite) return FavoriteToggleResult.Updated(isFavorite)
            return toggle(
                key = FavoriteEntity.PODCAST.name + id,
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

        private suspend fun toggle(
            key: String,
            currentValue: Boolean,
            optimistic: (Boolean) -> Unit,
            serverCall: suspend (Boolean) -> Response<*>,
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

            val nextValue = !currentValue
            setPending(key, true)
            optimistic(nextValue)

            val response =
                runCatching { serverCall(nextValue) }
                    .getOrElse { error ->
                        if (error is IOException) {
                            queue(nextValue)
                            setPending(key, false)
                            return FavoriteToggleResult.Queued(nextValue)
                        }
                        optimistic(currentValue)
                        setPending(key, false)
                        return FavoriteToggleResult.Failure("LaughTrack couldn't update that favorite.")
                    }

            setPending(key, false)
            return when {
                response.isSuccessful -> FavoriteToggleResult.Updated(nextValue)
                response.code() >= 500 -> {
                    queue(nextValue)
                    FavoriteToggleResult.Queued(nextValue)
                }
                else -> {
                    optimistic(currentValue)
                    FavoriteToggleResult.Failure("LaughTrack couldn't update that favorite.")
                }
            }
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

        private fun <T> Response<T>.bodyOrThrow(): T {
            if (!isSuccessful) {
                throw IOException("HTTP ${code()}")
            }
            return body() ?: throw IOException("Empty response body")
        }
    }
