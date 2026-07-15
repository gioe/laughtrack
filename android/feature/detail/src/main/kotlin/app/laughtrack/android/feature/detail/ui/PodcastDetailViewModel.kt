package app.laughtrack.android.feature.detail.ui

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import app.laughtrack.android.core.data.favorites.FavoriteEntity
import app.laughtrack.android.core.data.favorites.FavoritesRepository
import app.laughtrack.android.core.data.favorites.FavoritesSnapshot
import app.laughtrack.android.core.data.runCatchingCancellable
import app.laughtrack.android.core.network.generated.model.PodcastDetailResponse
import app.laughtrack.android.core.playback.PodcastPlaybackController
import app.laughtrack.android.core.playback.PodcastPlaybackItem
import app.laughtrack.android.core.ui.UiState
import app.laughtrack.android.feature.detail.data.PodcastDetailRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch
import javax.inject.Inject

@HiltViewModel
class PodcastDetailViewModel(
    private val repository: PodcastDetailRepository,
    private val onPlay: (PodcastPlaybackItem) -> Unit,
    private val favoritesRepository: FavoritesRepository? = null,
) : ViewModel() {
    /**
     * Hilt path: delegates play requests to the app-wide [PodcastPlaybackController].
     * The primary constructor takes the play handler directly because the controller
     * needs an Android [android.content.Context] (ExoPlayer), which JVM unit tests
     * cannot provide.
     */
    @Inject
    constructor(
        repository: PodcastDetailRepository,
        playbackController: PodcastPlaybackController,
        favoritesRepository: FavoritesRepository,
    ) : this(repository, playbackController::play, favoritesRepository)

    private val _state = MutableStateFlow<UiState<PodcastDetailResponse>>(UiState.Idle)
    val state: StateFlow<UiState<PodcastDetailResponse>> = _state.asStateFlow()
    val favoritesSnapshot: StateFlow<FavoritesSnapshot> =
        favoritesRepository?.snapshot?.stateIn(
            viewModelScope,
            SharingStarted.WhileSubscribed(5_000),
            FavoritesSnapshot(),
        ) ?: MutableStateFlow(FavoritesSnapshot())

    private var loadedId: Int? = null

    fun load(id: Int) {
        if (loadedId == id && _state.value is UiState.Success) return
        loadedId = id
        _state.value = UiState.Loading
        viewModelScope.launch {
            runCatchingCancellable { repository.getPodcast(id) }
                .onSuccess { _state.value = UiState.Success(it) }
                .onFailure { _state.value = UiState.Failure(it) }
        }
    }

    fun retry() {
        val id = loadedId ?: return
        loadedId = null
        load(id)
    }

    fun play(item: PodcastPlaybackItem) {
        onPlay(item)
    }

    fun toggleFavorite(
        id: Int,
        currentValue: Boolean,
    ) {
        val repository = favoritesRepository ?: return
        viewModelScope.launch {
            repository.setPodcastFavorite(id, !currentValue)
        }
    }

    fun isFavoritePending(id: Int): Boolean = favoritesSnapshot.value.pending.contains(FavoriteEntity.PODCAST.name + id)
}
