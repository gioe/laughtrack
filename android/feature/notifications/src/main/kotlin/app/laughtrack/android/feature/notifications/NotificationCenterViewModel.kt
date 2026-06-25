package app.laughtrack.android.feature.notifications

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import app.laughtrack.android.core.analytics.AnalyticsEvents
import app.laughtrack.android.core.analytics.AnalyticsManager
import app.laughtrack.android.core.data.UiState
import app.laughtrack.android.core.network.generated.model.NotificationListResponseData
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

@HiltViewModel
class NotificationCenterViewModel
    @Inject
    constructor(
        private val repository: NotificationsRepository,
        private val analytics: AnalyticsManager,
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
                        analytics.logEvent(
                            AnalyticsEvents.Notifications.VIEWED,
                            mapOf(AnalyticsEvents.Notifications.Param.UNREAD_COUNT to data.unreadCount),
                        )
                        repository.markSeen()
                    }
                    .onFailure { _state.value = UiState.Failure(it) }
            }
        }

        fun retry() {
            loaded = false
            load()
        }

        /** Logs a notification_card_tapped event before deep-linking to the show. */
        fun onCardTapped(showId: Int) {
            analytics.logEvent(
                AnalyticsEvents.Notifications.CARD_TAPPED,
                mapOf(AnalyticsEvents.Notifications.Param.SHOW_ID to showId),
            )
        }
    }
