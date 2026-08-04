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
import app.laughtrack.android.feature.search.model.ShowActiveConstraint
import app.laughtrack.android.feature.search.model.ShowActiveConstraintKind
import app.laughtrack.android.feature.search.model.ShowDateShortcut
import app.laughtrack.android.feature.search.model.ShowFormatOption
import app.laughtrack.android.feature.search.model.ShowMaximumPriceOption
import app.laughtrack.android.feature.search.model.ShowResultsPresentation
import app.laughtrack.android.feature.search.model.ShowSearchSeed
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.FlowPreview
import kotlinx.coroutines.Job
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.debounce
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import java.time.DayOfWeek
import java.time.LocalDate
import java.time.format.DateTimeFormatter
import java.time.format.FormatStyle
import java.time.temporal.TemporalAdjusters
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
    /** Show-results presentation is local UI state and never changes the API query. */
    val resultsPresentation: ShowResultsPresentation = ShowResultsPresentation.AGENDA,
    /** ISO date -> show count for the currently displayed calendar month. */
    val showDensity: Map<String, Int> = emptyMap(),
    val densityMonthStart: String? = null,
    val isDensityLoading: Boolean = false,
    val densityError: String? = null,
)

/** Deterministic shortcut calculation shared by the ViewModel and focused tests. */
internal fun showDateRangeForShortcut(
    shortcut: ShowDateShortcut,
    today: LocalDate = LocalDate.now(),
): Pair<String, String> {
    val range =
        when (shortcut) {
            ShowDateShortcut.TONIGHT -> today to today
            ShowDateShortcut.THIS_WEEKEND -> {
                val start =
                    when (today.dayOfWeek) {
                        DayOfWeek.FRIDAY, DayOfWeek.SATURDAY, DayOfWeek.SUNDAY -> today
                        else -> today.with(TemporalAdjusters.next(DayOfWeek.FRIDAY))
                    }
                val end = today.with(TemporalAdjusters.nextOrSame(DayOfWeek.SUNDAY))
                start to end
            }
        }
    return range.first.toString() to range.second.toString()
}

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
@OptIn(FlowPreview::class)
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
        private var densityJob: Job? = null
        private val densityCache = mutableMapOf<ShowDensityCacheKey, Map<String, Int>>()
        private val userEditedLocationPivots = mutableSetOf<SearchPivot>()

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
            // Mark the pivot stale immediately. If the user changes pivots before
            // the debounce fires, returning here must not reuse results for the
            // previous text value.
            updatePivot(pivot) { it.copy(query = it.query.copy(text = text), loaded = false) }
            textChanges.tryEmit(pivot)
        }

        /** Explicit optional comedian constraint for the Shows explorer. */
        fun onComedianChange(comedian: String) {
            updateShowQueryWithoutReload { it.copy(comedian = comedian) }
            textChanges.tryEmit(SearchPivot.SHOWS)
        }

        /** Explicit optional club constraint for the Shows explorer. */
        fun onClubChange(club: String) {
            updateShowQueryWithoutReload { it.copy(club = club) }
            textChanges.tryEmit(SearchPivot.SHOWS)
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
            updatePivotQuery(pivot, transform)
            reload(pivot)
        }

        /** Set the server sort key for the active pivot (from the sort dropdown). */
        fun setSort(apiValue: String) = updateQuery { it.copy(sort = apiValue) }

        /** Set or clear the active geo pivot's ZIP filter. Explicit edits stop its Home sync. */
        fun setZip(zip: String?) {
            val pivot = _state.value.pivot
            if (pivot.isGeoScoped) userEditedLocationPivots += pivot
            updatePivot(pivot) {
                val nextQuery = it.query.copy(zip = zip?.takeIf { value -> value.isNotBlank() })
                it.copy(
                    query = nextQuery,
                    // A manually entered ZIP no longer has a trustworthy resolved city label.
                    locationLabel = null,
                    showDensity = emptyMap(),
                    densityMonthStart = null,
                    isDensityLoading = false,
                    densityError = null,
                )
            }
            reload(pivot)
        }

        /** Set the active geo pivot's radius (miles) from the distance dropdown. */
        fun setDistance(miles: Int) {
            val pivot = _state.value.pivot
            if (pivot.isGeoScoped) userEditedLocationPivots += pivot
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

        fun setMaximumPrice(option: ShowMaximumPriceOption) = updateQuery { it.copy(maxPrice = option.apiValue) }

        /** Applies a direct date shortcut and restores chronological ordering. */
        fun applyDateShortcut(
            shortcut: ShowDateShortcut,
            today: LocalDate = LocalDate.now(),
        ) {
            val (from, to) = showDateRangeForShortcut(shortcut, today)
            updateQuery { it.copy(from = from, to = to, sort = SearchSort.defaultFor(SearchPivot.SHOWS)) }
        }

        /** Calendar selection is one exact-date query mutation and one reload. */
        fun selectShowCalendarDate(isoDate: String) {
            val day = runCatching { LocalDate.parse(isoDate).toString() }.getOrNull() ?: return
            updateQuery {
                it.copy(
                    from = day,
                    to = day,
                    sort = SearchSort.defaultFor(SearchPivot.SHOWS),
                )
            }
        }

        /** Toggle a tag slug in/out of the active pivot's selected filters. */
        fun toggleFilter(slug: String) =
            updateQuery { query ->
                query.copy(filters = if (slug in query.filters) query.filters - slug else query.filters + slug)
            }

        /** Clear all selected tag filters on the active pivot. */
        fun clearFilters() = updateQuery { it.copy(filters = emptySet()) }

        /** Export every selected Shows constraint and its local presentation. */
        fun showSearchSeed(): ShowSearchSeed {
            val shows = _state.value.states.getValue(SearchPivot.SHOWS)
            return ShowSearchSeed(
                comedian = shows.query.comedian,
                club = shows.query.club,
                zip = shows.query.zip,
                locationLabel = shows.locationLabel,
                distance = shows.query.distance ?: DEFAULT_DISTANCE_MILES,
                from = shows.query.from,
                to = shows.query.to,
                filters = shows.query.filters,
                maxPrice = shows.query.maxPrice,
                resultsPresentation = shows.resultsPresentation,
            )
        }

        /** Replace stale Shows state with an externally supplied faceted seed. */
        fun applyShowSearchSeed(seed: ShowSearchSeed) {
            userEditedLocationPivots += SearchPivot.SHOWS
            updatePivot(SearchPivot.SHOWS) { current ->
                current.copy(
                    query =
                        current.query.copy(
                            text = "",
                            comedian = seed.comedian,
                            club = seed.club,
                            zip = seed.zip,
                            distance = seed.distance,
                            from = seed.from,
                            to = seed.to,
                            filters = seed.filters,
                            maxPrice = seed.maxPrice,
                            sort = SearchSort.defaultFor(SearchPivot.SHOWS),
                        ),
                    locationLabel = seed.locationLabel,
                    resultsPresentation = seed.resultsPresentation,
                    showDensity = emptyMap(),
                    densityMonthStart = null,
                    isDensityLoading = false,
                    densityError = null,
                    loaded = false,
                    results = PagedList(),
                )
            }
            reloadShowsIfActive()
        }

        /** Human-readable, individually removable constraints in stable display order. */
        fun activeShowConstraints(): List<ShowActiveConstraint> {
            val shows = _state.value.states.getValue(SearchPivot.SHOWS)
            val query = shows.query
            val namesBySlug = shows.filters.associate { it.slug to it.name }
            return buildList {
                query.zip?.let { zip ->
                    val place = shows.locationLabel?.takeIf(String::isNotBlank) ?: "ZIP $zip"
                    add(
                        ShowActiveConstraint(
                            ShowActiveConstraintKind.Location,
                            "$place · ${query.distance ?: DEFAULT_DISTANCE_MILES} mi",
                        ),
                    )
                }
                if (query.from != null || query.to != null) {
                    add(
                        ShowActiveConstraint(
                            ShowActiveConstraintKind.Date,
                            showDateConstraintLabel(query.from, query.to),
                        ),
                    )
                }
                query.filters.sorted().forEach { slug ->
                    val fixedLabel =
                        when (slug) {
                            "free" -> "Free"
                            else -> ShowFormatOption.entries.firstOrNull { it.slug == slug }?.label
                        }
                    add(
                        ShowActiveConstraint(
                            ShowActiveConstraintKind.Filter(slug),
                            namesBySlug[slug]
                                ?: fixedLabel
                                ?: slug.replace('-', ' ').replace('_', ' ').replaceFirstChar(Char::uppercase),
                        ),
                    )
                }
                ShowMaximumPriceOption.fromApiValue(query.maxPrice)
                    .takeUnless { it == ShowMaximumPriceOption.ANY }
                    ?.let { add(ShowActiveConstraint(ShowActiveConstraintKind.MaximumPrice, it.label)) }
                query.comedian.trim().takeIf(String::isNotEmpty)?.let {
                    add(ShowActiveConstraint(ShowActiveConstraintKind.Comedian, "Comedian: $it"))
                }
                query.club.trim().takeIf(String::isNotEmpty)?.let {
                    add(ShowActiveConstraint(ShowActiveConstraintKind.Club, "Club: $it"))
                }
            }
        }

        fun removeShowConstraint(kind: ShowActiveConstraintKind) {
            if (kind == ShowActiveConstraintKind.Location) userEditedLocationPivots += SearchPivot.SHOWS
            updatePivot(SearchPivot.SHOWS) { current ->
                val query =
                    when (kind) {
                        ShowActiveConstraintKind.Location ->
                            current.query.copy(zip = null, distance = DEFAULT_DISTANCE_MILES)
                        ShowActiveConstraintKind.Date -> current.query.copy(from = null, to = null)
                        is ShowActiveConstraintKind.Filter ->
                            current.query.copy(filters = current.query.filters - kind.slug)
                        ShowActiveConstraintKind.MaximumPrice -> current.query.copy(maxPrice = null)
                        ShowActiveConstraintKind.Comedian -> current.query.copy(comedian = "")
                        ShowActiveConstraintKind.Club -> current.query.copy(club = "")
                    }
                val densityScopeChanged = showDensityScope(current.query) != showDensityScope(query)
                current.copy(
                    query = query,
                    locationLabel = if (kind == ShowActiveConstraintKind.Location) null else current.locationLabel,
                    showDensity = if (densityScopeChanged) emptyMap() else current.showDensity,
                    densityMonthStart = if (densityScopeChanged) null else current.densityMonthStart,
                    isDensityLoading = if (densityScopeChanged) false else current.isDensityLoading,
                    densityError = if (densityScopeChanged) null else current.densityError,
                )
            }
            reloadShowsIfActive()
        }

        fun clearAllShowConstraints() {
            userEditedLocationPivots += SearchPivot.SHOWS
            updatePivot(SearchPivot.SHOWS) { current ->
                current.copy(
                    query =
                        current.query.copy(
                            text = "",
                            comedian = "",
                            club = "",
                            zip = null,
                            distance = DEFAULT_DISTANCE_MILES,
                            from = null,
                            to = null,
                            filters = emptySet(),
                            maxPrice = null,
                            sort = SearchSort.defaultFor(SearchPivot.SHOWS),
                        ),
                    locationLabel = null,
                    resultsPresentation = ShowResultsPresentation.AGENDA,
                    showDensity = emptyMap(),
                    densityMonthStart = null,
                    isDensityLoading = false,
                    densityError = null,
                )
            }
            reloadShowsIfActive()
        }

        /** Presentation changes are local and deliberately do not reload results. */
        fun setResultsPresentation(presentation: ShowResultsPresentation) {
            updatePivot(SearchPivot.SHOWS) { it.copy(resultsPresentation = presentation) }
        }

        /** Load density for the month containing an ISO YYYY-MM-DD value. */
        fun loadShowDensity(monthStart: String) {
            val month = runCatching { LocalDate.parse(monthStart).withDayOfMonth(1) }.getOrNull()
            if (month == null) {
                updatePivot(SearchPivot.SHOWS) {
                    it.copy(isDensityLoading = false, densityError = "Invalid calendar month")
                }
                return
            }
            val query = _state.value.states.getValue(SearchPivot.SHOWS).query
            val scope = showDensityScope(query)
            val normalizedMonth = month.toString()
            val key = ShowDensityCacheKey(scope, normalizedMonth)
            densityCache[key]?.let { cached ->
                updatePivot(SearchPivot.SHOWS) {
                    it.copy(
                        showDensity = cached,
                        densityMonthStart = normalizedMonth,
                        isDensityLoading = false,
                        densityError = null,
                    )
                }
                return
            }

            densityJob?.cancel()
            updatePivot(SearchPivot.SHOWS) {
                it.copy(
                    isDensityLoading = true,
                    densityError = null,
                    densityMonthStart = normalizedMonth,
                )
            }
            densityJob =
                viewModelScope.launch {
                    val monthEnd = month.with(TemporalAdjusters.lastDayOfMonth()).toString()
                    runCatchingCancellable { repository.showDensity(query, normalizedMonth, monthEnd) }
                        .onSuccess { density ->
                            densityCache[key] = density
                            val current = _state.value.states.getValue(SearchPivot.SHOWS)
                            if (
                                showDensityScope(current.query) == scope &&
                                current.densityMonthStart == normalizedMonth
                            ) {
                                updatePivot(SearchPivot.SHOWS) {
                                    it.copy(showDensity = density, isDensityLoading = false, densityError = null)
                                }
                            }
                        }
                        .onFailure { error ->
                            val current = _state.value.states.getValue(SearchPivot.SHOWS)
                            if (
                                showDensityScope(current.query) == scope &&
                                current.densityMonthStart == normalizedMonth
                            ) {
                                updatePivot(SearchPivot.SHOWS) {
                                    it.copy(
                                        isDensityLoading = false,
                                        densityError = error.message ?: "Calendar unavailable",
                                    )
                                }
                            }
                        }
                }
        }

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
            val nextZip = location?.zip
            val nextDistance = location?.distanceMiles ?: DEFAULT_DISTANCE_MILES
            var reloadActivePivot = false

            SearchPivot.entries
                .filter { it.isGeoScoped && it !in userEditedLocationPivots }
                .forEach { pivot ->
                    val current = _state.value.states.getValue(pivot)
                    if (
                        current.query.zip == nextZip &&
                        current.query.distance == nextDistance &&
                        current.locationLabel == location?.locationLabel
                    ) {
                        return@forEach
                    }

                    updatePivot(pivot) {
                        it.copy(
                            query = it.query.copy(zip = nextZip, distance = nextDistance),
                            locationLabel = location?.locationLabel,
                            results = PagedList(),
                            loaded = false,
                            showDensity = emptyMap(),
                            densityMonthStart = null,
                            isDensityLoading = false,
                            densityError = null,
                        )
                    }
                    reloadActivePivot = reloadActivePivot || _state.value.pivot == pivot
                }

            if (reloadActivePivot) {
                reload(_state.value.pivot)
            }
        }

        private fun reload(pivot: SearchPivot) {
            if (!pivot.isAvailable) return
            // Log a real user-initiated search (non-empty query) — not the empty-query
            // browse-load that fires when a pivot tab is first opened. Logged here,
            // before the network call, so failed searches are counted too.
            val query = _state.value.states.getValue(pivot).query
            val hasExplicitShowEntity =
                pivot == SearchPivot.SHOWS &&
                    (query.comedian.isNotBlank() || query.club.isNotBlank())
            if (query.text.isNotBlank() || hasExplicitShowEntity) {
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
                                    // Dedup by route — the results lazy grid keys rows by route,
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

        private fun updatePivotQuery(
            pivot: SearchPivot,
            transform: (SearchQuery) -> SearchQuery,
        ) {
            updatePivot(pivot) { current ->
                val query = transform(current.query)
                val densityScopeChanged =
                    pivot == SearchPivot.SHOWS &&
                        showDensityScope(current.query) != showDensityScope(query)
                current.copy(
                    query = query,
                    showDensity = if (densityScopeChanged) emptyMap() else current.showDensity,
                    densityMonthStart = if (densityScopeChanged) null else current.densityMonthStart,
                    isDensityLoading = if (densityScopeChanged) false else current.isDensityLoading,
                    densityError = if (densityScopeChanged) null else current.densityError,
                )
            }
        }

        private fun updateShowQueryWithoutReload(transform: (SearchQuery) -> SearchQuery) {
            updatePivotQuery(SearchPivot.SHOWS, transform)
            // The shared debounce intentionally reloads only the active pivot.
            // Retain the current rows while typing, but make a pivot round-trip
            // trigger a fresh query even when the debounce event was superseded.
            updatePivot(SearchPivot.SHOWS) { it.copy(loaded = false) }
        }

        private fun reloadShowsIfActive() {
            if (_state.value.pivot == SearchPivot.SHOWS) {
                reload(SearchPivot.SHOWS)
            } else {
                updatePivot(SearchPivot.SHOWS) { it.copy(loaded = false, results = PagedList()) }
            }
        }

        private companion object {
            const val TEXT_DEBOUNCE_MS = 300L
        }
    }

private data class ShowDensityScope(
    val zip: String?,
    val distance: Int?,
    val comedian: String,
    val club: String,
)

private data class ShowDensityCacheKey(
    val scope: ShowDensityScope,
    val monthStart: String,
)

private fun showDensityScope(query: SearchQuery): ShowDensityScope =
    ShowDensityScope(
        zip = query.zip,
        distance = query.distance,
        comedian = query.comedian.trim(),
        club = query.club.trim(),
    )

private val SHOW_CONSTRAINT_DATE_FORMATTER: DateTimeFormatter = DateTimeFormatter.ofLocalizedDate(FormatStyle.MEDIUM)

private fun showDateConstraintLabel(
    from: String?,
    to: String?,
): String {
    fun pretty(value: String): String =
        runCatching { LocalDate.parse(value).format(SHOW_CONSTRAINT_DATE_FORMATTER) }.getOrDefault(value)
    return when {
        from != null && to != null && from == to -> pretty(from)
        from != null && to != null -> "${pretty(from)} – ${pretty(to)}"
        from != null -> "From ${pretty(from)}"
        to != null -> "Until ${pretty(to)}"
        else -> "Any date"
    }
}
