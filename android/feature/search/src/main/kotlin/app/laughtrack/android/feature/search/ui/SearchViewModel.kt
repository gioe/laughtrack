package app.laughtrack.android.feature.search.ui

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import app.laughtrack.android.core.analytics.AnalyticsEvents
import app.laughtrack.android.core.analytics.AnalyticsManager
import app.laughtrack.android.core.data.location.HomeLocation
import app.laughtrack.android.core.data.location.HomeLocationState
import app.laughtrack.android.core.data.runCatchingCancellable
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
import javax.inject.Inject

/** Per-pivot search state, retained when switching tabs (mirrors iOS per-pivot models). */
data class PivotState(
    val query: SearchQuery = SearchQuery(),
    val results: PagedList<SearchResult> = PagedList(),
    val loaded: Boolean = false,
    /** Human-readable label for the inherited Home location, when available. */
    val locationLabel: String? = null,
    /** Tag facets echoed by the last successful response — populate the tag filter sheet. */
    val filters: List<Filter> = emptyList(),
    /** Comedian home-city facets echoed by the last successful response (comedians only). */
    val homeCityFilters: List<HomeCityFilter> = emptyList(),
)

/**
 * Seeds each pivot with its server-default sort. Geo pivots inherit the Home
 * feed's location (saved or hero-inferred ZIP plus radius) so Search opens
 * scoped to the same area Home is showing, the way iOS seeds SearchRootModel
 * from the nearby preference; with no Home location they fall back to the
 * global corpus with the default radius, as before.
 */
private fun defaultPivotStates(homeLocation: HomeLocation? = null): Map<SearchPivot, PivotState> =
    SearchPivot.entries.associateWith { pivot ->
        PivotState(
            query =
                SearchQuery(
                    sort = SearchSort.defaultFor(pivot),
                    zip = if (pivot.isGeoScoped) homeLocation?.zip else null,
                    distance =
                        if (pivot.isGeoScoped) {
                            homeLocation?.distanceMiles ?: DEFAULT_DISTANCE_MILES
                        } else {
                            null
                        },
                ),
            locationLabel = if (pivot.isGeoScoped) homeLocation?.locationLabel else null,
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
        homeLocationState: HomeLocationState,
    ) : ViewModel() {
        private val _state =
            MutableStateFlow(
                SearchUiState(states = defaultPivotStates(homeLocationState.location.value)),
            )
        val state: StateFlow<SearchUiState> = _state.asStateFlow()

        private val loadJobs = mutableMapOf<SearchPivot, Job>()
        private var userEditedLocation = false

        // Debounce free-text typing so only the settled query hits the API; immediate
        // filters (zip/sort) go through updateQuery directly.
        private val textChanges = MutableSharedFlow<SearchPivot>(extraBufferCapacity = 64)

        init {
            viewModelScope.launch {
                textChanges.debounce(TEXT_DEBOUNCE_MS).collect { pivot ->
                    if (pivot == _state.value.pivot) reload(pivot)
                }
            }
            viewModelScope.launch {
                homeLocationState.location.collect { location ->
                    applyHomeLocation(location)
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

        /** Set the server sort key for the active pivot (from the sort dropdown). */
        fun setSort(apiValue: String) = updateQuery { it.copy(sort = apiValue) }

        /** Set or clear the Shows ZIP filter. Explicit Search location edits stop Home sync. */
        fun setZip(zip: String?) {
            userEditedLocation = true
            val pivot = _state.value.pivot
            updatePivot(pivot) {
                it.copy(
                    query = it.query.copy(zip = zip?.takeIf { value -> value.isNotBlank() }),
                    // A manually entered ZIP no longer has a trustworthy resolved city label.
                    locationLabel = null,
                )
            }
            reload(pivot)
        }

        /** Set the geo radius (miles) for the Shows pivot (from the distance dropdown). */
        fun setDistance(miles: Int) {
            userEditedLocation = true
            updateQuery { it.copy(distance = miles) }
        }

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

        private fun applyHomeLocation(location: HomeLocation?) {
            if (userEditedLocation) return
            val pivot = SearchPivot.SHOWS
            val nextZip = location?.zip
            val nextDistance = location?.distanceMiles ?: DEFAULT_DISTANCE_MILES
            val current = _state.value.states.getValue(pivot)
            if (
                current.query.zip == nextZip &&
                current.query.distance == nextDistance &&
                current.locationLabel == location?.locationLabel
            ) {
                return
            }

            updatePivot(pivot) {
                it.copy(
                    query = it.query.copy(zip = nextZip, distance = nextDistance),
                    locationLabel = location?.locationLabel,
                    results = PagedList(),
                    loaded = false,
                )
            }
            if (_state.value.pivot == pivot) {
                reload(pivot)
            }
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
            fetch(pivot, page = 0)
        }

        private fun fetch(
            pivot: SearchPivot,
            page: Int,
        ) {
            loadJobs[pivot]?.cancel()
            val query = _state.value.states.getValue(pivot).query
            if (page > 0) updatePivot(pivot) { it.copy(results = it.results.loading()) }
            loadJobs[pivot] =
                viewModelScope.launch {
                    runCatchingCancellable { repository.search(pivot, query, page) }
                        .onSuccess { result ->
                            updatePivot(pivot) {
                                it.copy(
                                    // Dedup by route — the results LazyColumn keys rows by route,
                                    // and a duplicate key crashes the list.
                                    results =
                                        it.results.appendPage(
                                            page,
                                            result.results,
                                            result.total,
                                            dedupKey = { r -> r.route },
                                        ),
                                    // Facets accompany every page but only change with the query, not
                                    // the page — refresh them from the zero-indexed initial page so
                                    // every filter-capable pivot exposes its sheet immediately without
                                    // resetting the available options during pagination.
                                    filters = if (page == 0) result.filters else it.filters,
                                    homeCityFilters = if (page == 0) result.homeCityFilters else it.homeCityFilters,
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
