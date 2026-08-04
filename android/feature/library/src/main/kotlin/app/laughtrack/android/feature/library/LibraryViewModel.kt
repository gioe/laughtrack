package app.laughtrack.android.feature.library

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import app.laughtrack.android.core.data.favorites.FavoriteToggleResult
import app.laughtrack.android.core.data.favorites.FavoritesRepository
import app.laughtrack.android.core.data.favorites.FavoritesSnapshot
import app.laughtrack.android.core.data.savedshows.SavedShowPeriod
import app.laughtrack.android.core.data.savedshows.SavedShowsRepository
import app.laughtrack.android.core.data.savedshows.SavedShowsSnapshot
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch
import kotlinx.coroutines.supervisorScope
import javax.inject.Inject

internal interface LibrarySavedShowsSource {
    val snapshot: StateFlow<SavedShowsSnapshot>

    suspend fun refresh(period: SavedShowPeriod): Boolean

    fun resetSignedOut()
}

private class RepositoryLibrarySavedShowsSource(
    private val repository: SavedShowsRepository,
) : LibrarySavedShowsSource {
    override val snapshot: StateFlow<SavedShowsSnapshot> = repository.snapshot

    override suspend fun refresh(period: SavedShowPeriod): Boolean = repository.refresh(period)

    override fun resetSignedOut() {
        repository.resetSignedOut()
    }
}

private class EmptyLibrarySavedShowsSource : LibrarySavedShowsSource {
    override val snapshot = MutableStateFlow(SavedShowsSnapshot())

    override suspend fun refresh(period: SavedShowPeriod): Boolean = false

    override fun resetSignedOut() {
        snapshot.value = SavedShowsSnapshot()
    }
}

@HiltViewModel
class LibraryViewModel internal constructor(
    private val favoritesRepository: FavoritesRepository,
    private val savedShowsSource: LibrarySavedShowsSource,
) : ViewModel() {
    @Inject
    constructor(
        favoritesRepository: FavoritesRepository,
        savedShowsRepository: SavedShowsRepository,
    ) : this(
        favoritesRepository = favoritesRepository,
        savedShowsSource = RepositoryLibrarySavedShowsSource(savedShowsRepository),
    )

    /** Keeps the favorites-only seam used by the existing focused ViewModel tests. */
    internal constructor(favoritesRepository: FavoritesRepository) :
        this(favoritesRepository, EmptyLibrarySavedShowsSource())

    val snapshot: StateFlow<FavoritesSnapshot> =
        favoritesRepository.snapshot
            .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), FavoritesSnapshot())

    val savedShowsSnapshot: StateFlow<SavedShowsSnapshot> = savedShowsSource.snapshot

    private val _initialRefreshComplete = MutableStateFlow(false)
    val initialRefreshComplete: StateFlow<Boolean> = _initialRefreshComplete.asStateFlow()

    private val _message = MutableStateFlow<String?>(null)
    val message: StateFlow<String?> = _message.asStateFlow()

    fun refresh(signedIn: Boolean) {
        viewModelScope.launch {
            if (!signedIn) {
                favoritesRepository.resetSignedOut()
                savedShowsSource.resetSignedOut()
                _initialRefreshComplete.value = true
                return@launch
            }
            _initialRefreshComplete.value = false
            try {
                supervisorScope {
                    launch { savedShowsSource.refresh(SavedShowPeriod.UPCOMING) }
                    launch { favoritesRepository.refreshSignedInFavorites() }
                    launch { savedShowsSource.refresh(SavedShowPeriod.PAST) }
                }
            } finally {
                _initialRefreshComplete.value = true
            }
        }
    }

    fun refreshSavedShows(period: SavedShowPeriod) {
        viewModelScope.launch {
            savedShowsSource.refresh(period)
        }
    }

    fun toggleComedian(uuid: String) {
        viewModelScope.launch {
            publish(favoritesRepository.toggleComedian(uuid))
        }
    }

    fun toggleClub(id: Int) {
        viewModelScope.launch {
            publish(favoritesRepository.toggleClub(id))
        }
    }

    fun togglePodcast(id: Int) {
        viewModelScope.launch {
            publish(favoritesRepository.togglePodcast(id))
        }
    }

    fun clearMessage() {
        _message.value = null
    }

    private fun publish(result: FavoriteToggleResult) {
        _message.value =
            when (result) {
                is FavoriteToggleResult.Updated -> null
                is FavoriteToggleResult.Queued ->
                    "Saved offline. LaughTrack will sync this when you're connected."
                is FavoriteToggleResult.Failure -> result.message
                // The shared login prompt is the user-facing signal here, so no snackbar.
                FavoriteToggleResult.SignInRequired -> null
            }
    }
}
