package app.laughtrack.android.feature.onboarding.ui

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import app.laughtrack.android.core.analytics.AnalyticsEvents
import app.laughtrack.android.core.analytics.AnalyticsManager
import app.laughtrack.android.core.network.generated.model.ComedianSearchItem
import app.laughtrack.android.feature.onboarding.data.ComedianOnboardingRepository
import app.laughtrack.android.feature.onboarding.push.SoftPushPromptCoordinator
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import javax.inject.Inject

data class ComedianOnboardingUiState(
    val suggestions: List<ComedianSearchItem> = emptyList(),
    val searchResults: List<ComedianSearchItem> = emptyList(),
    val favorites: Map<String, Boolean> = emptyMap(),
    val passed: Set<String> = emptySet(),
    val searchQuery: String = "",
    val isSearchMode: Boolean = false,
    val isLoading: Boolean = true,
    val isSaving: Boolean = false,
    val isComplete: Boolean = false,
    val emailAlertsEnabled: Boolean = true,
    val pushAlertsEnabled: Boolean = true,
    val showSoftPushPrompt: Boolean = false,
    val errorMessage: String? = null,
) {
    val visibleComedians: List<ComedianSearchItem>
        get() = if (isSearchMode) searchResults else suggestions

    val favoriteCount: Int
        get() = favorites.count { it.value }
}

@HiltViewModel
class ComedianOnboardingViewModel
    @Inject
    constructor(
        private val repository: ComedianOnboardingRepository,
        private val softPushPromptCoordinator: SoftPushPromptCoordinator,
        private val analytics: AnalyticsManager,
    ) : ViewModel() {
        private val _state = MutableStateFlow(ComedianOnboardingUiState())
        val state: StateFlow<ComedianOnboardingUiState> = _state.asStateFlow()

        init {
            loadInitialSuggestions()
        }

        fun loadMoreSuggestions() {
            viewModelScope.launch {
                runCatching { repository.suggestions() }
                    .onSuccess { appendSuggestions(it) }
                    .onFailure { showError("LaughTrack couldn't load more comedians.") }
            }
        }

        fun search(query: String) {
            _state.update { it.copy(searchQuery = query) }
            viewModelScope.launch {
                val trimmed = query.trim()
                if (trimmed.isEmpty()) {
                    _state.update { it.copy(isSearchMode = false, searchResults = emptyList(), errorMessage = null) }
                    return@launch
                }
                _state.update { it.copy(isLoading = true, isSearchMode = true, errorMessage = null) }
                runCatching { repository.search(trimmed) }
                    .onSuccess { results ->
                        _state.update {
                            it.copy(
                                searchResults = results,
                                favorites =
                                    it.favorites +
                                        results.associate { comedian ->
                                            val isFavorite =
                                                it.favorites[comedian.uuid] ?: (comedian.isFavorite == true)
                                            comedian.uuid to isFavorite
                                        },
                                isLoading = false,
                            )
                        }
                    }
                    .onFailure { showError("LaughTrack couldn't search comedians.") }
            }
        }

        fun toggleFavorite(uuid: String) {
            val current = _state.value.favorites[uuid] ?: false
            val next = !current
            _state.update { it.copy(favorites = it.favorites + (uuid to next), errorMessage = null) }
            viewModelScope.launch {
                runCatching { repository.setFavorite(uuid, next) }
                    .onSuccess { persisted ->
                        _state.update { it.copy(favorites = it.favorites + (uuid to persisted)) }
                        if (
                            !current &&
                            persisted &&
                            _state.value.pushAlertsEnabled &&
                            softPushPromptCoordinator.onFavoriteAdded()
                        ) {
                            _state.update { it.copy(showSoftPushPrompt = true) }
                            analytics.logEvent(
                                AnalyticsEvents.Push.SOFT_PROMPT_SHOWN,
                                mapOf(
                                    AnalyticsEvents.Push.Param.TRIGGER to
                                        AnalyticsEvents.Push.Trigger.ENGAGEMENT_MOMENT,
                                ),
                            )
                        }
                    }
                    .onFailure {
                        _state.update {
                            it.copy(
                                favorites = it.favorites + (uuid to current),
                                errorMessage = "LaughTrack couldn't update that favorite.",
                            )
                        }
                    }
            }
        }

        fun passComedian(uuid: String) {
            _state.update { it.copy(passed = it.passed + uuid) }
            if (remainingDeckCount() < DECK_PREFETCH_THRESHOLD) {
                loadMoreSuggestions()
            }
        }

        fun setEmailAlertsEnabled(enabled: Boolean) {
            _state.update { it.copy(emailAlertsEnabled = enabled) }
        }

        fun setPushAlertsEnabled(enabled: Boolean) {
            _state.update { it.copy(pushAlertsEnabled = enabled) }
        }

        fun dismissSoftPushPrompt() {
            _state.update { it.copy(showSoftPushPrompt = false) }
        }

        /** User tapped Enable on the soft prompt (before the OS dialog). iOS parity. */
        fun softPushEnableTapped() {
            analytics.logEvent(AnalyticsEvents.Push.SOFT_PROMPT_ENABLE_TAPPED)
        }

        /** OS push-authorization dialog resolved from the onboarding soft prompt. */
        fun onPushPermissionResult(granted: Boolean) {
            analytics.logEvent(
                AnalyticsEvents.Push.OS_PROMPT_RESULT,
                mapOf(AnalyticsEvents.Push.Param.GRANTED to granted),
            )
            dismissSoftPushPrompt()
        }

        fun deferSoftPushPrompt() {
            analytics.logEvent(AnalyticsEvents.Push.SOFT_PROMPT_DEFER_TAPPED)
            viewModelScope.launch {
                softPushPromptCoordinator.deferPrompt()
                dismissSoftPushPrompt()
            }
        }

        fun continueOnboarding() {
            viewModelScope.launch {
                _state.update { it.copy(isSaving = true, errorMessage = null) }
                runCatching { repository.completeOnboarding() }
                    .onSuccess {
                        _state.update { it.copy(isSaving = false, isComplete = true) }
                        analytics.logEvent(AnalyticsEvents.Onboarding.COMPLETED)
                    }
                    .onFailure {
                        _state.update {
                            it.copy(
                                isSaving = false,
                                errorMessage = "LaughTrack couldn't finish onboarding.",
                            )
                        }
                    }
            }
        }

        private fun loadInitialSuggestions() {
            viewModelScope.launch {
                _state.update { it.copy(isLoading = true, errorMessage = null) }
                runCatching { repository.suggestions() }
                    .onSuccess { comedians ->
                        _state.update {
                            it.copy(
                                suggestions = comedians,
                                favorites =
                                    comedians.associate { comedian ->
                                        comedian.uuid to (comedian.isFavorite == true)
                                    },
                                isLoading = false,
                            )
                        }
                    }
                    .onFailure { showError("LaughTrack couldn't load comedians right now.") }
            }
        }

        private fun appendSuggestions(comedians: List<ComedianSearchItem>) {
            _state.update { current ->
                val seen = current.suggestions.map { it.uuid }.toSet()
                val fresh = comedians.filterNot { it.uuid in seen }
                current.copy(
                    suggestions = current.suggestions + fresh,
                    favorites = current.favorites + fresh.associate { it.uuid to (it.isFavorite == true) },
                    isLoading = false,
                    errorMessage = null,
                )
            }
        }

        private fun remainingDeckCount(): Int {
            val current = _state.value
            return current.suggestions.count {
                current.favorites[it.uuid] != true && it.uuid !in current.passed
            }
        }

        private fun showError(message: String) {
            _state.update { it.copy(isLoading = false, isSaving = false, errorMessage = message) }
        }

        private companion object {
            const val DECK_PREFETCH_THRESHOLD = 4
        }
    }
