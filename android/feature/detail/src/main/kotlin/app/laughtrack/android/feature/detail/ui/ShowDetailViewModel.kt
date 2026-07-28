package app.laughtrack.android.feature.detail.ui

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import app.laughtrack.android.core.data.auth.CurrentUserState
import app.laughtrack.android.core.data.runCatchingCancellable
import app.laughtrack.android.core.data.savedshows.SavedShowMutationResult
import app.laughtrack.android.core.data.savedshows.SavedShowsRepository
import app.laughtrack.android.core.data.savedshows.SavedShowsSnapshot
import app.laughtrack.android.core.ui.UiState
import app.laughtrack.android.feature.detail.data.ShowDetailRepository
import app.laughtrack.android.feature.detail.model.ShowDetailUi
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

@HiltViewModel
class ShowDetailViewModel(
    private val repository: ShowDetailRepository,
    currentUserState: CurrentUserState,
    val savedShowsSnapshot: StateFlow<SavedShowsSnapshot> = MutableStateFlow(SavedShowsSnapshot()),
    private val loadSavedShowState: suspend (Int) -> Boolean? = { null },
    private val setSavedShow: suspend (Int, Boolean) -> SavedShowMutationResult = { _, isSaved ->
        SavedShowMutationResult.Updated(isSaved)
    },
) : ViewModel() {
    @Inject
    constructor(
        repository: ShowDetailRepository,
        currentUserState: CurrentUserState,
        savedShowsRepository: SavedShowsRepository,
    ) : this(
        repository = repository,
        currentUserState = currentUserState,
        savedShowsSnapshot = savedShowsRepository.snapshot,
        loadSavedShowState = savedShowsRepository::loadState,
        setSavedShow = savedShowsRepository::setSaved,
    )

    private val _state = MutableStateFlow<UiState<ShowDetailUi>>(UiState.Idle)
    val state: StateFlow<UiState<ShowDetailUi>> = _state.asStateFlow()
    private val _savedShowMessage = MutableStateFlow<String?>(null)
    val savedShowMessage: StateFlow<String?> = _savedShowMessage.asStateFlow()

    /** Gates the admin-only Show-ID badge (mirrors iOS's isAdmin gate). */
    val isAdmin: StateFlow<Boolean> = currentUserState.isAdmin

    private var loadedId: Int? = null

    /** Loads the show once per id; re-entrant calls for the same loaded id are ignored. */
    fun load(id: Int) {
        if (loadedId == id && _state.value is UiState.Success) return
        loadedId = id
        _state.value = UiState.Loading
        viewModelScope.launch {
            runCatchingCancellable { repository.getShow(id) }
                .onSuccess { _state.value = UiState.Success(it) }
                .onFailure { _state.value = UiState.Failure(it) }
        }
        viewModelScope.launch {
            runCatchingCancellable { loadSavedShowState(id) }
        }
    }

    fun retry() {
        val id = loadedId ?: return
        loadedId = null
        load(id)
    }

    fun toggleSaved(showId: Int) {
        val nextValue = !(savedShowsSnapshot.value.values[showId] ?: false)
        viewModelScope.launch {
            _savedShowMessage.value =
                when (val result = setSavedShow(showId, nextValue)) {
                    is SavedShowMutationResult.Updated -> null
                    is SavedShowMutationResult.Queued ->
                        "Saved offline. LaughTrack will sync this when you're connected."
                    is SavedShowMutationResult.Failure -> result.message
                    SavedShowMutationResult.SignInRequired -> null
                }
        }
    }

    fun clearSavedShowMessage() {
        _savedShowMessage.value = null
    }
}
