package app.laughtrack.android.feature.detail.ui

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import app.laughtrack.android.core.data.UiState
import app.laughtrack.android.core.data.favorites.FavoriteEntity
import app.laughtrack.android.core.data.favorites.FavoritesRepository
import app.laughtrack.android.core.data.favorites.FavoritesSnapshot
import app.laughtrack.android.feature.detail.data.ComedianDetailRepository
import app.laughtrack.android.feature.detail.model.ComedianDetailUi
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch
import javax.inject.Inject

@HiltViewModel
class ComedianDetailViewModel
    @Inject
    constructor(
        private val repository: ComedianDetailRepository,
        private val favoritesRepository: FavoritesRepository,
    ) : ViewModel() {
        private val _state = MutableStateFlow<UiState<ComedianDetailUi>>(UiState.Idle)
        val state: StateFlow<UiState<ComedianDetailUi>> = _state.asStateFlow()
        val favoritesSnapshot: StateFlow<FavoritesSnapshot> =
            favoritesRepository.snapshot
                .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), FavoritesSnapshot())

        private var loadedId: Int? = null

        fun load(id: Int) {
            if (loadedId == id && _state.value is UiState.Success) return
            loadedId = id
            _state.value = UiState.Loading
            viewModelScope.launch {
                runCatching { repository.getComedian(id) }
                    .onSuccess { _state.value = UiState.Success(it) }
                    .onFailure { _state.value = UiState.Failure(it) }
            }
        }

        fun retry() {
            val id = loadedId ?: return
            loadedId = null
            load(id)
        }

        fun toggleFavorite(uuid: String) {
            val current = favoritesRepository.snapshot.value.comedianValues[uuid] ?: false
            viewModelScope.launch {
                favoritesRepository.setComedianFavorite(uuid, !current)
            }
        }

        fun isFavoritePending(uuid: String): Boolean =
            favoritesSnapshot.value.pending.contains(FavoriteEntity.COMEDIAN.name + uuid)
    }
