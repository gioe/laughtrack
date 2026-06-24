package app.laughtrack.android.feature.notifications

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import app.laughtrack.android.core.data.UiState
import app.laughtrack.android.core.network.generated.model.NotificationListResponseData
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

@HiltViewModel
class NotificationCenterViewModel @Inject constructor(
    private val repository: NotificationsRepository,
) : ViewModel() {
    private val _state = MutableStateFlow<UiState<NotificationListResponseData>>(UiState.Idle)
    val state: StateFlow<UiState<NotificationListResponseData>> = _state.asStateFlow()

    private var loaded = false

    /** Loads the list once, then marks the center seen to clear the unread badge. */
    fun load() {
        if (loaded && _state.value is UiState.Success) return
        loaded = true
        _state.value = UiState.Loading
        viewModelScope.launch {
            runCatching { repository.getNotifications() }
                .onSuccess { data ->
                    _state.value = UiState.Success(data)
                    repository.markSeen()
                }
                .onFailure { _state.value = UiState.Failure(it) }
        }
    }

    fun retry() {
        loaded = false
        load()
    }
}
