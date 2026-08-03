package app.laughtrack.android.feature.detail.ui

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import app.laughtrack.android.core.data.favorites.FavoriteEntity
import app.laughtrack.android.core.data.favorites.FavoritesRepository
import app.laughtrack.android.core.data.favorites.FavoritesSnapshot
import app.laughtrack.android.core.data.runCatchingCancellable
import app.laughtrack.android.core.ui.UiState
import app.laughtrack.android.feature.detail.data.ComedianDetailRepository
import app.laughtrack.android.feature.detail.model.ComedianDetailUi
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.Job
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
        private val _isLoadingShows = MutableStateFlow(false)
        val isLoadingShows: StateFlow<Boolean> = _isLoadingShows.asStateFlow()
        val favoritesSnapshot: StateFlow<FavoritesSnapshot> =
            favoritesRepository.snapshot
                .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), FavoritesSnapshot())

        private var loadedId: Int? = null
        private var requestGeneration = 0L
        private var detailJob: Job? = null
        private var showsJob: Job? = null

        fun load(id: Int) {
            if (loadedId == id && _state.value is UiState.Success) return
            loadedId = id
            requestGeneration += 1
            val generation = requestGeneration
            detailJob?.cancel()
            showsJob?.cancel()
            _state.value = UiState.Loading
            _isLoadingShows.value = false
            detailJob =
                viewModelScope.launch {
                    runCatchingCancellable {
                        // Comedian detail is global-first. Location and distance stay
                        // absent until the user explicitly applies a ZIP filter.
                        repository.getComedian(id = id)
                    }
                        .onSuccess {
                            if (isCurrentRequest(id, generation)) _state.value = UiState.Success(it)
                        }.onFailure {
                            if (isCurrentRequest(id, generation)) _state.value = UiState.Failure(it)
                        }
                }
        }

        fun retry() {
            val id = loadedId ?: return
            loadedId = null
            load(id)
        }

        /** Apply a five-digit ZIP, or clear back to the nationwide tour with null/blank. */
        fun setLocation(zip: String?) {
            val normalized = zip?.filter(Char::isDigit)?.take(ZIP_LENGTH)?.takeIf { it.length == ZIP_LENGTH }
            if (!zip.isNullOrBlank() && normalized == null) return
            val current = (_state.value as? UiState.Success)?.value ?: return
            if (current.activeZip == normalized) return
            reloadPinnedShows(
                current = current,
                zip = normalized,
                distanceMiles = current.activeDistanceMiles,
            )
        }

        fun clearLocation() = setLocation(null)

        /** Change the selected radius; it becomes a request parameter only with an active ZIP. */
        fun setDistance(miles: Int) {
            val current = (_state.value as? UiState.Success)?.value ?: return
            if (current.activeDistanceMiles == miles) return
            if (current.activeZip == null) {
                _state.value = UiState.Success(current.copy(activeDistanceMiles = miles))
                return
            }
            reloadPinnedShows(current = current, zip = current.activeZip, distanceMiles = miles)
        }

        fun loadMoreShows() {
            val current = (_state.value as? UiState.Success)?.value ?: return
            if (!current.canLoadMorePinnedShows || _isLoadingShows.value) return

            val id = current.detail.id
            val generation = requestGeneration
            val nextPage = current.currentPinnedShowsPage + 1
            val zip = current.activeZip
            val distance = current.activeDistanceMiles.takeIf { zip != null }
            _isLoadingShows.value = true
            showsJob =
                viewModelScope.launch {
                    runCatchingCancellable {
                        repository.getPinnedShows(
                            comedianName = current.detail.name,
                            zip = zip,
                            distanceMiles = distance,
                            page = nextPage,
                        )
                    }.onSuccess { next ->
                        if (isCurrentRequest(id, generation)) {
                            val latest = (_state.value as? UiState.Success)?.value ?: return@onSuccess
                            _state.value =
                                UiState.Success(
                                    latest.copy(
                                        pinnedShows = (latest.pinnedShows + next.shows).distinctBy { it.id },
                                        pinnedShowsTotal = next.total,
                                        currentPinnedShowsPage = next.page,
                                    ),
                                )
                        }
                    }
                    if (isCurrentRequest(id, generation)) _isLoadingShows.value = false
                }
        }

        fun toggleFavorite(uuid: String) {
            val current = favoritesRepository.snapshot.value.comedianValues[uuid] ?: false
            viewModelScope.launch {
                favoritesRepository.setComedianFavorite(uuid, !current)
            }
        }

        fun isFavoritePending(uuid: String): Boolean =
            favoritesSnapshot.value.pending.contains(FavoriteEntity.COMEDIAN.name + uuid)

        private fun reloadPinnedShows(
            current: ComedianDetailUi,
            zip: String?,
            distanceMiles: Int,
        ) {
            requestGeneration += 1
            val generation = requestGeneration
            val id = current.detail.id
            showsJob?.cancel()
            _isLoadingShows.value = true
            _state.value =
                UiState.Success(
                    current.copy(
                        pinnedShows = emptyList(),
                        pinnedShowsTotal = 0,
                        currentPinnedShowsPage = 0,
                        activeZip = zip,
                        activeLocationLabel = null,
                        activeDistanceMiles = distanceMiles,
                    ),
                )
            showsJob =
                viewModelScope.launch {
                    runCatchingCancellable {
                        repository.getPinnedShows(
                            comedianName = current.detail.name,
                            zip = zip,
                            distanceMiles = distanceMiles.takeIf { zip != null },
                            page = 0,
                        )
                    }.onSuccess { page ->
                        if (isCurrentRequest(id, generation)) {
                            val latest = (_state.value as? UiState.Success)?.value ?: return@onSuccess
                            _state.value =
                                UiState.Success(
                                    latest.copy(
                                        pinnedShows = page.shows,
                                        pinnedShowsTotal = page.total,
                                        currentPinnedShowsPage = page.page,
                                    ),
                                )
                        }
                    }
                    if (isCurrentRequest(id, generation)) _isLoadingShows.value = false
                }
        }

        private fun isCurrentRequest(
            id: Int,
            generation: Long,
        ): Boolean = loadedId == id && requestGeneration == generation

        private companion object {
            const val ZIP_LENGTH = 5
        }
    }
