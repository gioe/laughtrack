@file:Suppress("FunctionName")

package app.laughtrack.android.feature.search.ui

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.IntrinsicSize
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyListScope
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.KeyboardArrowRight
import androidx.compose.material.icons.filled.ArrowDropDown
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.filled.Person
import androidx.compose.material.icons.filled.Search
import androidx.compose.material3.DatePickerDialog
import androidx.compose.material3.DateRangePicker
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FilterChip
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.ModalBottomSheet
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.rememberDateRangePickerState
import androidx.compose.material3.rememberModalBottomSheetState
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.PathEffect
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import app.laughtrack.android.core.navigation.AppRoute
import app.laughtrack.android.core.network.generated.model.Filter
import app.laughtrack.android.core.network.generated.model.HomeCityFilter
import app.laughtrack.android.core.ui.components.RemoteImage
import app.laughtrack.android.core.ui.components.SkeletonLine
import app.laughtrack.android.core.ui.theme.LaughTrackColors
import app.laughtrack.android.feature.search.model.DEFAULT_DISTANCE_MILES
import app.laughtrack.android.feature.search.model.DISTANCE_OPTIONS
import app.laughtrack.android.feature.search.model.SearchPivot
import app.laughtrack.android.feature.search.model.SearchQuery
import app.laughtrack.android.feature.search.model.SearchResult
import app.laughtrack.android.feature.search.model.SearchSort
import app.laughtrack.android.feature.search.model.searchResultSummary
import java.time.Instant
import java.time.OffsetDateTime
import java.time.ZoneId
import java.time.ZoneOffset
import java.time.format.DateTimeFormatter
import java.util.Locale

/**
 * Search tab with the same branded shell as iOS SearchRootView: primitive chips,
 * title copy, a rounded search/filter card, and entity result rows.
 */
@Composable
fun SearchScreen(
    onOpenEntity: (AppRoute) -> Unit,
    modifier: Modifier = Modifier,
    viewModel: SearchViewModel = hiltViewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    val pivotState = state.current

    Box(
        modifier =
            modifier
                .fillMaxSize()
                .background(
                    Brush.verticalGradient(
                        colors =
                            listOf(
                                LaughTrackColors.Highlight.copy(alpha = 0.18f),
                                LaughTrackColors.Canvas,
                            ),
                    ),
                ),
    ) {
        LazyColumn(
            modifier = Modifier.fillMaxSize(),
            contentPadding = PaddingValues(horizontal = 16.dp, vertical = 12.dp),
            verticalArrangement = Arrangement.spacedBy(14.dp),
        ) {
            item {
                SearchHeader(
                    selectedPivot = state.pivot,
                    onSelectPivot = viewModel::selectPivot,
                )
            }
            item { SearchIntro() }

            if (!state.pivot.isAvailable) {
                item { CenteredMessage("Podcast search is coming soon.") }
            } else {
                item {
                    SearchControls(
                        pivot = state.pivot,
                        query = pivotState.query,
                        filters = pivotState.filters,
                        homeCityFilters = pivotState.homeCityFilters,
                        total = pivotState.results.total,
                        onText = viewModel::onTextChange,
                        onZip = { value -> viewModel.updateQuery { it.copy(zip = value.ifBlank { null }) } },
                        onSort = viewModel::setSort,
                        onDistance = viewModel::setDistance,
                        onDateRange = viewModel::setDateRange,
                        onToggleFilter = viewModel::toggleFilter,
                        onClearFilters = viewModel::clearFilters,
                        onHomeCity = viewModel::setHomeCity,
                    )
                }

                val results = pivotState.results
                when {
                    results.isLoading && results.items.isEmpty() -> item { LoadingList() }
                    results.error != null && results.items.isEmpty() ->
                        item { CenteredMessage(results.error, onRetry = viewModel::retry) }
                    results.items.isEmpty() -> item { CenteredMessage("No results yet - try a search.") }
                    else ->
                        resultsContent(
                            pivot = state.pivot,
                            results = results.items,
                            total = results.total,
                            loadMore =
                                LoadMoreState(
                                    isLoading = results.isLoading,
                                    hasMore = results.hasMore,
                                    error = results.error,
                                    onLoadMore = viewModel::loadMore,
                                ),
                            onOpen = { route ->
                                viewModel.logResultTapped(route)
                                onOpenEntity(route)
                            },
                        )
                }
            }
        }
    }
}

@Composable
private fun SearchHeader(
    selectedPivot: SearchPivot,
    onSelectPivot: (SearchPivot) -> Unit,
) {
    Row(
        modifier =
            Modifier
                .fillMaxWidth()
                .padding(top = 8.dp),
        horizontalArrangement = Arrangement.spacedBy(10.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Surface(
            modifier =
                Modifier
                    .size(48.dp)
                    .clip(CircleShape)
                    .border(1.dp, LaughTrackColors.BorderSubtle, CircleShape),
            color = LaughTrackColors.SurfaceElevated.copy(alpha = 0.94f),
            shape = CircleShape,
        ) {
            Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                Icon(
                    imageVector = Icons.Filled.Person,
                    contentDescription = null,
                    tint = MaterialTheme.colorScheme.onSurface,
                    modifier = Modifier.size(28.dp),
                )
            }
        }

        Row(
            modifier =
                Modifier
                    .weight(1f)
                    .horizontalScroll(rememberScrollState()),
            horizontalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            SearchPivot.entries.forEach { pivot ->
                PrimitiveChip(
                    title = pivot.label,
                    selected = pivot == selectedPivot,
                    enabled = pivot.isAvailable,
                    onClick = { onSelectPivot(pivot) },
                )
            }
        }
    }
}

@Composable
private fun PrimitiveChip(
    title: String,
    selected: Boolean,
    enabled: Boolean,
    onClick: () -> Unit,
) {
    val shape = RoundedCornerShape(999.dp)
    Surface(
        shape = shape,
        // Unselected pills are dark-filled (mirroring the iOS primitive-filter row's
        // Color.black.opacity(0.98) fill in AppShellView) rather than the old ghost
        // fill; the selected pill stays solid orange. Selection reads off the fill +
        // text color, matching the iOS/Android divergence noted in the task.
        color = if (selected) LaughTrackColors.AccentStrong else Color.Black.copy(alpha = 0.98f),
        modifier =
            Modifier
                .height(34.dp)
                .clip(shape)
                .clickable(enabled = enabled, onClick = onClick)
                .border(1.dp, LaughTrackColors.AccentMuted, shape),
    ) {
        Box(
            modifier = Modifier.padding(horizontal = 14.dp),
            contentAlignment = Alignment.Center,
        ) {
            Text(
                text = title.uppercase(),
                style = MaterialTheme.typography.labelSmall.copy(fontWeight = FontWeight.SemiBold),
                color = if (selected) LaughTrackColors.Foreground else MaterialTheme.colorScheme.onSurfaceVariant,
                maxLines = 1,
            )
        }
    }
}

@Composable
private fun SearchIntro() {
    Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
        Text(
            "Search",
            style = MaterialTheme.typography.headlineMedium.copy(fontWeight = FontWeight.Bold),
            color = MaterialTheme.colorScheme.onSurface,
        )
        Text(
            "Find shows, comedians, clubs, and podcasts across LaughTrack.",
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
    }
}

@Composable
private fun SearchControls(
    pivot: SearchPivot,
    query: SearchQuery,
    filters: List<Filter>,
    homeCityFilters: List<HomeCityFilter>,
    total: Int,
    onText: (String) -> Unit,
    onZip: (String) -> Unit,
    onSort: (String) -> Unit,
    onDistance: (Int) -> Unit,
    onDateRange: (String?, String?) -> Unit,
    onToggleFilter: (String) -> Unit,
    onClearFilters: () -> Unit,
    onHomeCity: (String?) -> Unit,
) {
    Surface(
        color = LaughTrackColors.SurfaceElevated,
        shape = RoundedCornerShape(14.dp),
        modifier =
            Modifier
                .fillMaxWidth()
                .border(1.dp, LaughTrackColors.BorderSubtle, RoundedCornerShape(14.dp)),
    ) {
        Column(
            Modifier.fillMaxWidth().padding(12.dp),
            verticalArrangement = Arrangement.spacedBy(10.dp),
        ) {
            OutlinedTextField(
                value = query.text,
                onValueChange = onText,
                leadingIcon = { Icon(Icons.Filled.Search, contentDescription = null) },
                placeholder = { Text(queryPrompt(pivot)) },
                singleLine = true,
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(14.dp),
            )

            Row(
                modifier =
                    Modifier
                        .fillMaxWidth()
                        .horizontalScroll(rememberScrollState()),
                horizontalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                SortPill(pivot = pivot, selected = query.sort, onSort = onSort)
                if (pivot.isGeoScoped) {
                    DistancePill(distance = query.distance, onDistance = onDistance)
                    DateRangePill(from = query.from, to = query.to, onDateRange = onDateRange)
                }
                if (pivot.supportsTagFilters && filters.isNotEmpty()) {
                    TagFilterPill(
                        available = filters,
                        selected = query.filters,
                        total = total,
                        onToggle = onToggleFilter,
                        onClear = onClearFilters,
                    )
                }
                if (pivot == SearchPivot.COMEDIANS && homeCityFilters.isNotEmpty()) {
                    HomeCityPill(
                        available = homeCityFilters,
                        selected = query.homeCity,
                        onSelect = onHomeCity,
                    )
                }
            }

            if (pivot.isGeoScoped) {
                OutlinedTextField(
                    value = query.zip.orEmpty(),
                    onValueChange = onZip,
                    label = { Text("ZIP code") },
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth(),
                    shape = RoundedCornerShape(14.dp),
                )
            }
        }
    }
}

/** Shared rounded pill trigger: a tappable label with a trailing chevron. */
@Composable
private fun FilterPillButton(
    label: String,
    active: Boolean,
    onClick: () -> Unit,
) {
    Surface(
        color = if (active) LaughTrackColors.AccentStrong else LaughTrackColors.Surface,
        shape = RoundedCornerShape(999.dp),
        modifier =
            Modifier
                .clip(RoundedCornerShape(999.dp))
                .clickable(onClick = onClick)
                .border(
                    1.dp,
                    if (active) LaughTrackColors.AccentStrong else LaughTrackColors.BorderSubtle,
                    RoundedCornerShape(999.dp),
                ),
    ) {
        Row(
            modifier = Modifier.padding(start = 12.dp, end = 8.dp, top = 8.dp, bottom = 8.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(2.dp),
        ) {
            Text(
                label,
                style = MaterialTheme.typography.labelSmall.copy(fontWeight = FontWeight.SemiBold),
                color = if (active) LaughTrackColors.Foreground else MaterialTheme.colorScheme.onSurfaceVariant,
                maxLines = 1,
            )
            Icon(
                Icons.Filled.ArrowDropDown,
                contentDescription = null,
                tint = if (active) LaughTrackColors.Foreground else MaterialTheme.colorScheme.onSurfaceVariant,
                modifier = Modifier.size(16.dp),
            )
        }
    }
}

/** Sort dropdown — lists the active pivot's sort vocabulary and applies the chosen key. */
@Composable
private fun SortPill(
    pivot: SearchPivot,
    selected: String?,
    onSort: (String) -> Unit,
) {
    var expanded by remember { mutableStateOf(false) }
    val options = SearchSort.optionsFor(pivot)
    val current = selected ?: SearchSort.defaultFor(pivot)
    Box {
        FilterPillButton(
            label = SearchSort.labelFor(pivot, selected),
            active = false,
            onClick = { expanded = true },
        )
        DropdownMenu(expanded = expanded, onDismissRequest = { expanded = false }) {
            options.forEach { option ->
                DropdownMenuItem(
                    text = { Text(option.label) },
                    trailingIcon =
                        if (option.apiValue == current) {
                            { Icon(Icons.Filled.Check, contentDescription = null) }
                        } else {
                            null
                        },
                    onClick = {
                        expanded = false
                        onSort(option.apiValue)
                    },
                )
            }
        }
    }
}

/** Distance dropdown (Shows only) — 10/25/50/100 mi radius applied to the geo search. */
@Composable
private fun DistancePill(
    distance: Int?,
    onDistance: (Int) -> Unit,
) {
    var expanded by remember { mutableStateOf(false) }
    val current = distance ?: DEFAULT_DISTANCE_MILES
    Box {
        FilterPillButton(label = "$current mi", active = false, onClick = { expanded = true })
        DropdownMenu(expanded = expanded, onDismissRequest = { expanded = false }) {
            DISTANCE_OPTIONS.forEach { miles ->
                DropdownMenuItem(
                    text = { Text("$miles mi") },
                    trailingIcon =
                        if (miles == current) {
                            { Icon(Icons.Filled.Check, contentDescription = null) }
                        } else {
                            null
                        },
                    onClick = {
                        expanded = false
                        onDistance(miles)
                    },
                )
            }
        }
    }
}

/** Date-range pill (Shows only) — opens a Material date-range picker; label reflects the window. */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun DateRangePill(
    from: String?,
    to: String?,
    onDateRange: (String?, String?) -> Unit,
) {
    var showPicker by remember { mutableStateOf(false) }
    val active = from != null || to != null
    FilterPillButton(
        label = dateRangeLabel(from, to),
        active = active,
        onClick = { showPicker = true },
    )
    if (showPicker) {
        val pickerState =
            rememberDateRangePickerState(
                initialSelectedStartDateMillis = from?.let(::isoDateToUtcMillis),
                initialSelectedEndDateMillis = to?.let(::isoDateToUtcMillis),
            )
        DatePickerDialog(
            onDismissRequest = { showPicker = false },
            confirmButton = {
                TextButton(onClick = {
                    onDateRange(
                        pickerState.selectedStartDateMillis?.let(::utcMillisToIsoDate),
                        pickerState.selectedEndDateMillis?.let(::utcMillisToIsoDate),
                    )
                    showPicker = false
                }) { Text("Apply") }
            },
            dismissButton = {
                TextButton(onClick = {
                    onDateRange(null, null)
                    showPicker = false
                }) { Text("Clear") }
            },
        ) {
            DateRangePicker(state = pickerState, modifier = Modifier.heightIn(max = 520.dp))
        }
    }
}

/** Tag-filter sheet — toggles facet slugs with a live result count. Mirrors iOS SearchFilterModal. */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun TagFilterPill(
    available: List<Filter>,
    selected: Set<String>,
    total: Int,
    onToggle: (String) -> Unit,
    onClear: () -> Unit,
) {
    var showSheet by remember { mutableStateOf(false) }
    val count = selected.size
    FilterPillButton(
        label = if (count > 0) "Filters ($count)" else "Filters",
        active = count > 0,
        onClick = { showSheet = true },
    )
    if (showSheet) {
        val sheetState = rememberModalBottomSheetState()
        ModalBottomSheet(onDismissRequest = { showSheet = false }, sheetState = sheetState) {
            Column(
                Modifier
                    .fillMaxWidth()
                    .padding(horizontal = 20.dp)
                    .padding(bottom = 24.dp),
                verticalArrangement = Arrangement.spacedBy(12.dp),
            ) {
                Row(
                    Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    Text(
                        "Filter results",
                        style = MaterialTheme.typography.titleMedium.copy(fontWeight = FontWeight.Bold),
                    )
                    if (count > 0) {
                        TextButton(onClick = onClear) { Text("Clear") }
                    }
                }
                Text(
                    "Tap a tag to add or remove it. Showing $total results.",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
                Row(
                    Modifier
                        .fillMaxWidth()
                        .horizontalScroll(rememberScrollState()),
                    horizontalArrangement = Arrangement.spacedBy(8.dp),
                ) {
                    available.forEach { filter ->
                        FilterChip(
                            selected = filter.slug in selected,
                            onClick = { onToggle(filter.slug) },
                            label = { Text(filter.name) },
                        )
                    }
                }
            }
        }
    }
}

/** Home-city dropdown (Comedians only) — filters by the selected `city|state` token. */
@Composable
private fun HomeCityPill(
    available: List<HomeCityFilter>,
    selected: String?,
    onSelect: (String?) -> Unit,
) {
    var expanded by remember { mutableStateOf(false) }
    // Keep label and active-highlight consistent: when a city is selected but the
    // refreshed facets no longer include it, fall back to the raw token rather than
    // "All cities" so an active pill never reads as unselected.
    val label =
        when {
            selected == null -> "All cities"
            else -> available.firstOrNull { it.value == selected }?.label ?: selected
        }
    Box {
        FilterPillButton(label = label, active = selected != null, onClick = { expanded = true })
        DropdownMenu(expanded = expanded, onDismissRequest = { expanded = false }) {
            DropdownMenuItem(
                text = { Text("All cities") },
                trailingIcon =
                    if (selected == null) {
                        { Icon(Icons.Filled.Check, contentDescription = null) }
                    } else {
                        null
                    },
                onClick = {
                    expanded = false
                    onSelect(null)
                },
            )
            available.forEach { city ->
                DropdownMenuItem(
                    text = { Text("${city.label} (${city.count})") },
                    trailingIcon =
                        if (city.value == selected) {
                            { Icon(Icons.Filled.Check, contentDescription = null) }
                        } else {
                            null
                        },
                    onClick = {
                        expanded = false
                        onSelect(city.value)
                    },
                )
            }
        }
    }
}

private val PILL_DATE_FORMAT = DateTimeFormatter.ofPattern("MMM d", Locale.US)

/** Human label for the date pill: "Any date", a single day, or a "from – to" range. */
internal fun dateRangeLabel(
    from: String?,
    to: String?,
): String {
    fun pretty(iso: String): String =
        runCatching { java.time.LocalDate.parse(iso).format(PILL_DATE_FORMAT) }.getOrDefault(iso)
    return when {
        from != null && to != null && from == to -> pretty(from)
        from != null && to != null -> "${pretty(from)} - ${pretty(to)}"
        from != null -> "From ${pretty(from)}"
        to != null -> "Until ${pretty(to)}"
        else -> "Any date"
    }
}

/** The date picker emits UTC-midnight millis; convert to/from the YYYY-MM-DD the API expects. */
private fun utcMillisToIsoDate(millis: Long): String =
    Instant.ofEpochMilli(millis).atZone(ZoneOffset.UTC).toLocalDate().format(DateTimeFormatter.ISO_LOCAL_DATE)

private fun isoDateToUtcMillis(iso: String): Long? =
    runCatching { java.time.LocalDate.parse(iso).atStartOfDay(ZoneOffset.UTC).toInstant().toEpochMilli() }.getOrNull()

private fun queryPrompt(pivot: SearchPivot): String =
    when (pivot) {
        SearchPivot.SHOWS -> "Search nearby comedy"
        SearchPivot.COMEDIANS -> "Search comedian names"
        SearchPivot.CLUBS -> "Search club names"
        SearchPivot.PODCASTS -> "Search podcast titles"
    }

/** Paging state + trigger for [resultsContent]'s load-more footer. */
internal data class LoadMoreState(
    val isLoading: Boolean,
    val hasMore: Boolean,
    val error: String?,
    val onLoadMore: () -> Unit,
)

private fun LazyListScope.resultsContent(
    pivot: SearchPivot,
    results: List<SearchResult>,
    total: Int,
    loadMore: LoadMoreState,
    onOpen: (AppRoute) -> Unit,
) {
    item {
        Text(
            searchResultSummary(loaded = results.size, total = total),
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
            modifier = Modifier.padding(horizontal = 2.dp).padding(top = 2.dp),
        )
    }
    items(results) { result ->
        if (pivot == SearchPivot.SHOWS) {
            ShowResultRow(result = result, onOpen = onOpen)
        } else {
            ResultRow(result = result, onOpen = onOpen)
        }
    }
    when {
        loadMore.error != null ->
            item {
                Column(
                    Modifier.fillMaxWidth().padding(16.dp),
                    verticalArrangement = Arrangement.spacedBy(8.dp),
                    horizontalAlignment = Alignment.CenterHorizontally,
                ) {
                    Text("Couldn't load more.", color = MaterialTheme.colorScheme.onSurfaceVariant)
                    OutlinedButton(onClick = loadMore.onLoadMore, enabled = !loadMore.isLoading) { Text("Retry") }
                }
            }
        loadMore.hasMore ->
            item {
                OutlinedButton(
                    onClick = loadMore.onLoadMore,
                    enabled = !loadMore.isLoading,
                    modifier = Modifier.fillMaxWidth().padding(vertical = 8.dp),
                ) {
                    Text(if (loadMore.isLoading) "Loading..." else "Load more")
                }
            }
    }
}

/**
 * Semantics tag applied to every tappable search result row (both the ticket-style
 * show rows and the card-style comedian/club/podcast rows) so instrumented tests —
 * notably AppStoreScreenshotTest — can open the first result without hardcoding a
 * production entity name. Inert at runtime.
 */
const val SEARCH_RESULT_ROW_TEST_TAG = "searchResultRow"

@Composable
private fun ShowResultRow(
    result: SearchResult,
    onOpen: (AppRoute) -> Unit,
) {
    Surface(
        modifier =
            Modifier
                .fillMaxWidth()
                .height(IntrinsicSize.Min)
                .clip(RoundedCornerShape(12.dp))
                .clickable { onOpen(result.route) }
                .testTag(SEARCH_RESULT_ROW_TEST_TAG)
                .border(1.dp, LaughTrackColors.TicketBorder, RoundedCornerShape(12.dp)),
        color = LaughTrackColors.TicketPaper,
        shape = RoundedCornerShape(12.dp),
    ) {
        Row(
            modifier =
                Modifier
                    .fillMaxWidth()
                    .heightIn(min = 104.dp),
        ) {
            ShowResultBody(
                result = result,
                modifier =
                    Modifier
                        .weight(1f)
                        .fillMaxHeight(),
            )
            TicketDashedDivider(
                modifier =
                    Modifier
                        .fillMaxHeight()
                        .padding(vertical = 10.dp),
            )
            ShowResultStub(
                result = result,
                modifier =
                    Modifier
                        .width(88.dp)
                        .fillMaxHeight(),
            )
        }
    }
}

@Composable
private fun ShowResultBody(
    result: SearchResult,
    modifier: Modifier = Modifier,
) {
    // Body paper comes from the enclosing ShowResultRow Surface (color = TicketPaper);
    // no separate background needed here.
    Box(
        modifier = modifier,
        contentAlignment = Alignment.CenterStart,
    ) {
        Row(
            modifier = Modifier.padding(10.dp),
            horizontalArrangement = Arrangement.spacedBy(10.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            SearchArtwork(result)
            Column(
                modifier = Modifier.weight(1f),
                verticalArrangement = Arrangement.spacedBy(3.dp),
            ) {
                Text(
                    result.title,
                    style = MaterialTheme.typography.titleSmall,
                    color = LaughTrackColors.TicketInk,
                    maxLines = 2,
                    overflow = TextOverflow.Ellipsis,
                )
                result.subtitle?.takeIf { it.isNotBlank() }?.let { club ->
                    Text(
                        club,
                        style = MaterialTheme.typography.bodySmall,
                        color = LaughTrackColors.TicketInkMuted,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis,
                    )
                }
                result.showRoom
                    ?.takeIf { room -> room.isNotBlank() && !room.equals(result.subtitle.orEmpty(), ignoreCase = true) }
                    ?.let { room ->
                        Text(
                            room,
                            style = MaterialTheme.typography.bodySmall,
                            color = LaughTrackColors.TicketInkMuted,
                            maxLines = 1,
                            overflow = TextOverflow.Ellipsis,
                        )
                    }
                if (result.isSoldOut) {
                    Text(
                        "Sold out",
                        style = MaterialTheme.typography.labelSmall.copy(fontWeight = FontWeight.SemiBold),
                        color = LaughTrackColors.TicketAccent,
                        modifier =
                            Modifier
                                .clip(RoundedCornerShape(999.dp))
                                .background(LaughTrackColors.TicketAccent.copy(alpha = 0.14f))
                                .border(
                                    1.dp,
                                    LaughTrackColors.TicketAccent.copy(alpha = 0.4f),
                                    RoundedCornerShape(999.dp),
                                )
                                .padding(horizontal = 8.dp, vertical = 2.dp),
                    )
                }
            }
        }
    }
}

@Composable
private fun TicketDashedDivider(modifier: Modifier = Modifier) {
    val color = LaughTrackColors.TicketBorder
    Canvas(modifier = modifier.width(1.dp)) {
        drawLine(
            color = color,
            start = Offset(size.width / 2, 0f),
            end = Offset(size.width / 2, size.height),
            strokeWidth = 1.dp.toPx(),
            pathEffect = PathEffect.dashPathEffect(floatArrayOf(6f, 6f)),
        )
    }
}

@Composable
private fun ShowResultStub(
    result: SearchResult,
    modifier: Modifier = Modifier,
) {
    val dateParts = showDateParts(result)
    Column(
        modifier =
            modifier
                .background(LaughTrackColors.TicketStub)
                .padding(vertical = 10.dp, horizontal = 6.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center,
    ) {
        Text(
            dateParts.weekday,
            style = MaterialTheme.typography.labelSmall.copy(fontWeight = FontWeight.SemiBold, letterSpacing = 1.4.sp),
            color = LaughTrackColors.TicketAccent,
            maxLines = 1,
        )
        Text(
            dateParts.day,
            fontWeight = FontWeight.Black,
            fontSize = 26.sp,
            color = LaughTrackColors.TicketInk,
            maxLines = 1,
        )
        Text(
            dateParts.month,
            style = MaterialTheme.typography.labelSmall.copy(fontWeight = FontWeight.SemiBold, letterSpacing = 1.2.sp),
            color = LaughTrackColors.TicketInkMuted,
            maxLines = 1,
        )
        Text(
            dateParts.time,
            style = MaterialTheme.typography.labelSmall,
            color = LaughTrackColors.TicketInkMuted,
            maxLines = 1,
            modifier = Modifier.padding(top = 2.dp),
        )
        result.showPriceLabel?.let { price ->
            Text(
                price,
                style = MaterialTheme.typography.labelMedium.copy(fontWeight = FontWeight.SemiBold),
                color = LaughTrackColors.TicketAccent,
                maxLines = 1,
                modifier = Modifier.padding(top = 2.dp),
            )
        }
    }
}

private data class ShowDateParts(
    val weekday: String,
    val day: String,
    val month: String,
    val time: String,
)

private fun showDateParts(result: SearchResult): ShowDateParts =
    runCatching {
        val zone = result.showTimezone?.let(ZoneId::of) ?: ZoneId.systemDefault()
        val dateTime = OffsetDateTime.parse(result.showDate).atZoneSameInstant(zone)
        ShowDateParts(
            weekday = dateTime.format(DateTimeFormatter.ofPattern("EEE", Locale.US)).uppercase(Locale.US),
            day = dateTime.format(DateTimeFormatter.ofPattern("d", Locale.US)),
            month = dateTime.format(DateTimeFormatter.ofPattern("MMM", Locale.US)).uppercase(Locale.US),
            time = dateTime.format(DateTimeFormatter.ofPattern("h:mm a", Locale.US)),
        )
    }.getOrElse {
        ShowDateParts(weekday = "", day = "", month = "", time = "")
    }

@Composable
private fun ResultRow(
    result: SearchResult,
    onOpen: (AppRoute) -> Unit,
) {
    Surface(
        modifier =
            Modifier
                .fillMaxWidth()
                .border(1.dp, LaughTrackColors.TicketBorder, RoundedCornerShape(14.dp)),
        color = LaughTrackColors.TicketPaper,
        shape = RoundedCornerShape(14.dp),
    ) {
        Row(
            Modifier
                .fillMaxWidth()
                .clickable { onOpen(result.route) }
                .testTag(SEARCH_RESULT_ROW_TEST_TAG)
                .padding(12.dp),
            horizontalArrangement = Arrangement.spacedBy(12.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            SearchArtwork(result)
            Column(
                Modifier.weight(1f),
                verticalArrangement = Arrangement.spacedBy(4.dp),
            ) {
                Text(
                    result.title,
                    style = MaterialTheme.typography.titleMedium,
                    color = LaughTrackColors.TicketInk,
                    maxLines = 2,
                    overflow = TextOverflow.Ellipsis,
                )
                result.displayMetadata.take(3).forEach { line ->
                    Text(
                        line,
                        style = MaterialTheme.typography.bodySmall,
                        color = LaughTrackColors.TicketInkMuted,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis,
                    )
                }
            }
            Icon(
                imageVector = Icons.AutoMirrored.Filled.KeyboardArrowRight,
                contentDescription = null,
                tint = LaughTrackColors.TicketInkMuted,
            )
        }
    }
}

@Composable
private fun SearchArtwork(result: SearchResult) {
    Box(
        modifier =
            Modifier
                .size(66.dp)
                .clip(CircleShape)
                .background(LaughTrackColors.AccentStrong.copy(alpha = 0.14f)),
        contentAlignment = Alignment.Center,
    ) {
        if (result.artworkUrl != null) {
            RemoteImage(
                url = result.artworkUrl,
                contentDescription = result.title,
                modifier =
                    Modifier
                        .fillMaxSize()
                        .clip(CircleShape),
            )
        } else {
            Icon(
                Icons.Filled.Search,
                contentDescription = null,
                tint = LaughTrackColors.AccentStrong,
                modifier = Modifier.size(28.dp),
            )
        }
    }
}

@Composable
private fun LoadingList() {
    Column(
        Modifier.fillMaxWidth().padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        repeat(6) { SkeletonLine() }
    }
}

@Composable
private fun CenteredMessage(
    message: String,
    onRetry: (() -> Unit)? = null,
) {
    Column(
        Modifier.fillMaxWidth().padding(24.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp, Alignment.CenterVertically),
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        Text(message, color = MaterialTheme.colorScheme.onSurfaceVariant)
        if (onRetry != null) {
            OutlinedButton(onClick = onRetry) { Text("Retry") }
        }
    }
}
