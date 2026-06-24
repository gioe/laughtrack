package app.laughtrack.android.feature.library

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import app.laughtrack.android.core.data.favorites.FavoriteToggleResult
import app.laughtrack.android.core.data.favorites.FavoritesRepository
import app.laughtrack.android.core.data.favorites.FavoritesSnapshot
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch
import javax.inject.Inject

@HiltViewModel
class LibraryViewModel @Inject constructor(
    private val favoritesRepository: FavoritesRepository,
) : ViewModel() {
    val snapshot: StateFlow<FavoritesSnapshot> = favoritesRepository.snapshot
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), FavoritesSnapshot())

    private val _message = MutableStateFlow<String?>(null)
    val message: StateFlow<String?> = _message.asStateFlow()

    fun refresh(signedIn: Boolean) {
        viewModelScope.launch {
            if (!signedIn) {
                favoritesRepository.resetSignedOut()
                return@launch
            }
            favoritesRepository.refreshSignedInFavorites()
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
        _message.value = when (result) {
            is FavoriteToggleResult.Updated -> null
            is FavoriteToggleResult.Queued ->
                "Saved offline. LaughTrack will sync this when you're connected."
            is FavoriteToggleResult.Failure -> result.message
        }
    }
}
