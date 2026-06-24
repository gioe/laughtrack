package app.laughtrack.android.feature.detail.ui

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import app.laughtrack.android.core.data.UiState
import app.laughtrack.android.feature.detail.data.ShowDetailRepository
import app.laughtrack.android.feature.detail.model.ShowDetailUi
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

@HiltViewModel
class ShowDetailViewModel @Inject constructor(
    private val repository: ShowDetailRepository,
) : ViewModel() {
    private val _state = MutableStateFlow<UiState<ShowDetailUi>>(UiState.Idle)
    val state: StateFlow<UiState<ShowDetailUi>> = _state.asStateFlow()

    private var loadedId: Int? = null

    /** Loads the show once per id; re-entrant calls for the same loaded id are ignored. */
    fun load(id: Int) {
        if (loadedId == id && _state.value is UiState.Success) return
        loadedId = id
        _state.value = UiState.Loading
        viewModelScope.launch {
            runCatching { repository.getShow(id) }
                .onSuccess { _state.value = UiState.Success(it) }
                .onFailure { _state.value = UiState.Failure(it) }
        }
    }

    fun retry() {
        val id = loadedId ?: return
        loadedId = null
        load(id)
    }
}
