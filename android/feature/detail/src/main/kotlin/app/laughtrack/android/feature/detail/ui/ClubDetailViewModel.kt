package app.laughtrack.android.feature.detail.ui

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import app.laughtrack.android.core.data.favorites.FavoriteEntity
import app.laughtrack.android.core.data.favorites.FavoritesRepository
import app.laughtrack.android.core.data.favorites.FavoritesSnapshot
import app.laughtrack.android.core.data.runCatchingCancellable
import app.laughtrack.android.core.ui.UiState
import app.laughtrack.android.feature.detail.data.ClubDetailRepository
import app.laughtrack.android.feature.detail.model.ClubDetailUi
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch
import javax.inject.Inject

@HiltViewModel
class ClubDetailViewModel
    @Inject
    constructor(
        private val repository: ClubDetailRepository,
        private val favoritesRepository: FavoritesRepository,
    ) : ViewModel() {
        private val _state = MutableStateFlow<UiState<ClubDetailUi>>(UiState.Idle)
        val state: StateFlow<UiState<ClubDetailUi>> = _state.asStateFlow()
        private val _isLoadingMore = MutableStateFlow(false)
        val isLoadingMore: StateFlow<Boolean> = _isLoadingMore.asStateFlow()
        val favoritesSnapshot: StateFlow<FavoritesSnapshot> =
            favoritesRepository.snapshot
                .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), FavoritesSnapshot())

        private var loadedId: Int? = null

        fun load(id: Int) {
            if (loadedId == id && _state.value is UiState.Success) return
            loadedId = id
            _state.value = UiState.Loading
            viewModelScope.launch {
                runCatchingCancellable { repository.getClub(id) }
                    .onSuccess { _state.value = UiState.Success(it) }
                    .onFailure { _state.value = UiState.Failure(it) }
            }
        }

        fun retry() {
            val id = loadedId ?: return
            loadedId = null
            load(id)
        }

        fun loadMore() {
            val current = (_state.value as? UiState.Success)?.value ?: return
            if (!current.canLoadMore || _isLoadingMore.value) return

            _isLoadingMore.value = true
            viewModelScope.launch {
                runCatchingCancellable {
                    repository.getClubShows(
                        id = current.detail.id,
                        page = current.currentPage + 1,
                    )
                }.onSuccess { next ->
                    _state.value =
                        UiState.Success(
                            current.copy(
                                upcomingShows =
                                    (current.upcomingShows + next.shows)
                                        .distinctBy { it.id },
                                totalShows = next.total,
                                currentPage = next.page,
                            ),
                        )
                }
                _isLoadingMore.value = false
            }
        }

        fun toggleFavorite(id: Int) {
            val current = favoritesRepository.snapshot.value.clubValues[id] ?: false
            viewModelScope.launch {
                favoritesRepository.setClubFavorite(id, !current)
            }
        }

        fun isFavoritePending(id: Int): Boolean =
            favoritesSnapshot.value.pending.contains(FavoriteEntity.CLUB.name + id)
    }
