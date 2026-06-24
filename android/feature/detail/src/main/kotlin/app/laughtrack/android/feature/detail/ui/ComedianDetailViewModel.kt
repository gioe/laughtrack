package app.laughtrack.android.feature.detail.ui

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import app.laughtrack.android.core.data.UiState
import app.laughtrack.android.feature.detail.data.ComedianDetailRepository
import app.laughtrack.android.feature.detail.model.ComedianDetailUi
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

@HiltViewModel
class ComedianDetailViewModel @Inject constructor(
    private val repository: ComedianDetailRepository,
) : ViewModel() {
    private val _state = MutableStateFlow<UiState<ComedianDetailUi>>(UiState.Idle)
    val state: StateFlow<UiState<ComedianDetailUi>> = _state.asStateFlow()

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
}
