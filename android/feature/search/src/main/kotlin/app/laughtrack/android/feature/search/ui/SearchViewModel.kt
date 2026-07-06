package app.laughtrack.android.feature.search.ui

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import app.laughtrack.android.core.analytics.AnalyticsEvents
import app.laughtrack.android.core.analytics.AnalyticsManager
import app.laughtrack.android.core.data.search.SearchSeed
import app.laughtrack.android.core.data.search.SearchShortcut
import app.laughtrack.android.core.data.search.SearchShortcutCoordinator
import app.laughtrack.android.core.navigation.AppRoute
import app.laughtrack.android.core.network.generated.model.Filter
import app.laughtrack.android.core.network.generated.model.HomeCityFilter
import app.laughtrack.android.feature.search.data.SearchRepository
import app.laughtrack.android.feature.search.model.DEFAULT_DISTANCE_MILES
import app.laughtrack.android.feature.search.model.PagedList
import app.laughtrack.android.feature.search.model.SearchPivot
import app.laughtrack.android.feature.search.model.SearchQuery
import app.laughtrack.android.feature.search.model.SearchResult
import app.laughtrack.android.feature.search.model.SearchSort
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.Job
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.debounce
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import java.time.LocalDate
import java.time.format.DateTimeFormatter
import javax.inject.Inject

/** Per-pivot search state, retained when switching tabs (mirrors iOS per-pivot models). */
data class PivotState(
    val query: SearchQuery = SearchQuery(),
    val results: PagedList<SearchResult> = PagedList(),
    val loaded: Boolean = false,
    /** Tag facets echoed by the last successful response — populate the tag filter sheet. */
    val filters: List<Filter> = emptyList(),
    /** Comedian home-city facets echoed by the last successful response (comedians only). */
    val homeCityFilters: List<HomeCityFilter> = emptyList(),
)

/** Seeds each pivot with its server-default sort (and a default radius for geo pivots). */
private fun defaultPivotStates(): Map<SearchPivot, PivotState> =
    SearchPivot.entries.associateWith { pivot ->
        PivotState(
            query =
                SearchQuery(
                    sort = SearchSort.defaultFor(pivot),
                    distance = if (pivot.isGeoScoped) DEFAULT_DISTANCE_MILES else null,
                ),
        )
    }

data class SearchUiState(
    val pivot: SearchPivot = SearchPivot.SHOWS,
    val states: Map<SearchPivot, PivotState> = defaultPivotStates(),
) {
    val current: PivotState get() = states.getValue(pivot)
}

@HiltViewModel
class SearchViewModel
    @Inject
    constructor(
        private val repository: SearchRepository,
        private val analytics: AnalyticsManager,
        private val shortcutCoordinator: SearchShortcutCoordinator,
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
            // A Home shortcut chip publishes a seed; apply it to the Shows pivot when it arrives.
            viewModelScope.launch {
                shortcutCoordinator.seed.collect { seed -> seed?.let(::applySeed) }
            }
            selectPivot(SearchPivot.SHOWS)
        }

        /**
         * Apply a Home shortcut: pivot to Shows, pre-set the geo + date-window filters
         * (Tonight / This Week / Near Me), re-query, then clear the seed so it isn't
         * re-applied on the next recomposition. Mirrors iOS SearchRootModel shortcuts.
         */
        private fun applySeed(seed: SearchSeed) {
            _state.update { it.copy(pivot = SearchPivot.SHOWS) }
            updatePivot(SearchPivot.SHOWS) { pivotState ->
                pivotState.copy(query = buildShortcutQuery(seed, pivotState.query, LocalDate.now()))
            }
            reload(SearchPivot.SHOWS)
            shortcutCoordinator.consume()
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

        /** Set the server sort key for the active pivot (from the sort dropdown). */
        fun setSort(apiValue: String) = updateQuery { it.copy(sort = apiValue) }

        /** Set the geo radius (miles) for the Shows pivot (from the distance dropdown). */
        fun setDistance(miles: Int) = updateQuery { it.copy(distance = miles) }

        /**
         * Set (or clear, with nulls) the inclusive YYYY-MM-DD date window for the
         * Shows pivot from the date-range picker.
         */
        fun setDateRange(
            from: String?,
            to: String?,
        ) = updateQuery { it.copy(from = from, to = to) }

        /** Toggle a tag slug in/out of the active pivot's selected filters. */
        fun toggleFilter(slug: String) =
            updateQuery { query ->
                query.copy(filters = if (slug in query.filters) query.filters - slug else query.filters + slug)
            }

        /** Clear all selected tag filters on the active pivot. */
        fun clearFilters() = updateQuery { it.copy(filters = emptySet()) }

        /** Set (or clear, with null) the comedians home-city `city|state` token. */
        fun setHomeCity(value: String?) = updateQuery { it.copy(homeCity = value) }

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
                                it.copy(
                                    results = it.results.appendPage(page, result.results, result.total),
                                    // Facets accompany every page but only change with the query, not
                                    // the page — refresh them from page 1 so the sheets reflect the
                                    // current search without being reset mid-pagination.
                                    filters = if (page == 1) result.filters else it.filters,
                                    homeCityFilters = if (page == 1) result.homeCityFilters else it.homeCityFilters,
                                )
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

/** Server sort key for "earliest showtime first" (mirrors iOS ShowSort.earliest). */
private const val SORT_EARLIEST = "date_asc"

/**
 * Pure mapping from a Home shortcut seed to the Shows-pivot query, carrying the
 * seed's location (zip/distance) and layering the shortcut's date window on top.
 * The server treats [from]/[to] as INCLUSIVE end-of-day bounds (mirrors iOS
 * applyShortcutFilters), so Tonight = today..tomorrow, This Week = today..+7 days,
 * Near Me = no date bound (just the geo scope). All sort earliest-first. [today]
 * is injected so the date math is deterministically testable.
 */
internal fun buildShortcutQuery(
    seed: SearchSeed,
    base: SearchQuery,
    today: LocalDate,
): SearchQuery {
    val fmt = DateTimeFormatter.ISO_LOCAL_DATE
    val withLocation = base.copy(zip = seed.zip, distance = seed.distanceMiles, sort = SORT_EARLIEST)
    return when (seed.shortcut) {
        SearchShortcut.TONIGHT ->
            withLocation.copy(from = today.format(fmt), to = today.plusDays(1).format(fmt))
        SearchShortcut.THIS_WEEK ->
            withLocation.copy(from = today.format(fmt), to = today.plusDays(DAYS_IN_WEEK).format(fmt))
        SearchShortcut.NEAR_ME ->
            withLocation.copy(from = null, to = null)
    }
}

private const val DAYS_IN_WEEK = 7L
