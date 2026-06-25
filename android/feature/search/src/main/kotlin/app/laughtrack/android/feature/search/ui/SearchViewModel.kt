package app.laughtrack.android.feature.search.ui

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import app.laughtrack.android.core.analytics.AnalyticsEvents
import app.laughtrack.android.core.analytics.AnalyticsManager
import app.laughtrack.android.core.navigation.AppRoute
import app.laughtrack.android.feature.search.data.SearchRepository
import app.laughtrack.android.feature.search.model.PagedList
import app.laughtrack.android.feature.search.model.SearchPivot
import app.laughtrack.android.feature.search.model.SearchQuery
import app.laughtrack.android.feature.search.model.SearchResult
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.Job
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.debounce
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import javax.inject.Inject

/** Per-pivot search state, retained when switching tabs (mirrors iOS per-pivot models). */
data class PivotState(
    val query: SearchQuery = SearchQuery(),
    val results: PagedList<SearchResult> = PagedList(),
    val loaded: Boolean = false,
)

data class SearchUiState(
    val pivot: SearchPivot = SearchPivot.SHOWS,
    val states: Map<SearchPivot, PivotState> = SearchPivot.entries.associateWith { PivotState() },
) {
    val current: PivotState get() = states.getValue(pivot)
}

@HiltViewModel
class SearchViewModel
    @Inject
    constructor(
        private val repository: SearchRepository,
        private val analytics: AnalyticsManager,
    ) : ViewModel() {
        private val _state = MutableStateFlow(SearchUiState())
        val state: StateFlow<SearchUiState> = _state.asStateFlow()

        private val loadJobs = mutableMapOf<SearchPivot, Job>()

        // Debounce free-text typing so only the settled query hits the API; immediate
        // filters (zip/sort) go through updateQuery directly.
        private val textChanges = MutableSharedFlow<SearchPivot>(extraBufferCapacity = 64)

        init {
            viewModelScope.launch {
                textChanges.debounce(TEXT_DEBOUNCE_MS).collect { pivot ->
                    if (pivot == _state.value.pivot) reload(pivot)
                }
            }
            selectPivot(SearchPivot.SHOWS)
        }

        /** Free-text edit: reflected in the field immediately, but the query is debounced. */
        fun onTextChange(text: String) {
            val pivot = _state.value.pivot
            updatePivot(pivot) { it.copy(query = it.query.copy(text = text)) }
            textChanges.tryEmit(pivot)
        }

        fun selectPivot(pivot: SearchPivot) {
            _state.update { it.copy(pivot = pivot) }
            val pivotState = _state.value.states.getValue(pivot)
            if (pivot.isAvailable && !pivotState.loaded) {
                reload(pivot)
            }
        }

        /** Any query/filter/sort edit resets pagination and re-queries from page 1. */
        fun updateQuery(transform: (SearchQuery) -> SearchQuery) {
            val pivot = _state.value.pivot
            updatePivot(pivot) { it.copy(query = transform(it.query)) }
            reload(pivot)
        }

        fun loadMore() {
            val pivot = _state.value.pivot
            val results = _state.value.states.getValue(pivot).results
            if (!pivot.isAvailable || results.isLoading || !results.hasMore) return
            fetch(pivot, results.nextPage)
        }

        fun retry() {
            reload(_state.value.pivot)
        }

        /** Logs a card_tapped event for a result before navigation. */
        fun logResultTapped(route: AppRoute) {
            val (type, id) =
                when (route) {
                    is AppRoute.ShowDetail -> "show" to route.id
                    is AppRoute.ComedianDetail -> "comedian" to route.id
                    is AppRoute.ClubDetail -> "club" to route.id
                    is AppRoute.PodcastDetail -> "podcast" to route.id
                    else -> return
                }
            analytics.logEvent(
                AnalyticsEvents.Cards.TAPPED,
                mapOf(
                    AnalyticsEvents.Cards.Param.ENTITY_TYPE to type,
                    AnalyticsEvents.Cards.Param.ENTITY_ID to id,
                ),
            )
        }

        private fun reload(pivot: SearchPivot) {
            if (!pivot.isAvailable) return
            // Log a real user-initiated search (non-empty query) — not the empty-query
            // browse-load that fires when a pivot tab is first opened. Logged here,
            // before the network call, so failed searches are counted too.
            val query = _state.value.states.getValue(pivot).query
            if (query.text.isNotBlank()) {
                analytics.logEvent(
                    AnalyticsEvents.Search.PERFORMED,
                    mapOf(AnalyticsEvents.Search.Param.PIVOT to pivot.name.lowercase()),
                )
            }
            updatePivot(pivot) { it.copy(results = PagedList<SearchResult>().loading(), loaded = true) }
            fetch(pivot, page = 1)
        }

        private fun fetch(
            pivot: SearchPivot,
            page: Int,
        ) {
            loadJobs[pivot]?.cancel()
            val query = _state.value.states.getValue(pivot).query
            if (page > 1) updatePivot(pivot) { it.copy(results = it.results.loading()) }
            loadJobs[pivot] =
                viewModelScope.launch {
                    runCatching { repository.search(pivot, query, page) }
                        .onSuccess { result ->
                            updatePivot(pivot) {
                                it.copy(results = it.results.appendPage(page, result.results, result.total))
                            }
                        }
                        .onFailure { error ->
                            updatePivot(pivot) {
                                it.copy(results = it.results.failed(error.message ?: "Search failed"))
                            }
                        }
                }
        }

        private fun updatePivot(
            pivot: SearchPivot,
            transform: (PivotState) -> PivotState,
        ) {
            _state.update { ui ->
                val updated = ui.states.toMutableMap().apply { put(pivot, transform(getValue(pivot))) }
                ui.copy(states = updated)
            }
        }

        private companion object {
            const val TEXT_DEBOUNCE_MS = 300L
        }
    }
