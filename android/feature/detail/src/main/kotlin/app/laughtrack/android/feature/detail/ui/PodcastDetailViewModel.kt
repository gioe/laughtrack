package app.laughtrack.android.feature.detail.ui

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import app.laughtrack.android.core.data.runCatchingCancellable
import app.laughtrack.android.core.network.generated.model.PodcastDetailResponse
import app.laughtrack.android.core.playback.PodcastPlaybackController
import app.laughtrack.android.core.playback.PodcastPlaybackItem
import app.laughtrack.android.core.ui.UiState
import app.laughtrack.android.feature.detail.data.PodcastDetailRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

@HiltViewModel
class PodcastDetailViewModel
    @Inject
    constructor(
        private val repository: PodcastDetailRepository,
        private val playbackController: PodcastPlaybackController,
    ) : ViewModel() {
        private val _state = MutableStateFlow<UiState<PodcastDetailResponse>>(UiState.Idle)
        val state: StateFlow<UiState<PodcastDetailResponse>> = _state.asStateFlow()

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
            playbackController.play(item)
        }
    }
