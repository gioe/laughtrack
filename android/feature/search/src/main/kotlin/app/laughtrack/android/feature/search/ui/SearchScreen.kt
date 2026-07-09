@file:Suppress("FunctionName")

package app.laughtrack.android.feature.search.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ArrowDropDown
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.filled.Person
import androidx.compose.material.icons.filled.Search
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.DatePickerDialog
import androidx.compose.material3.DateRangePicker
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FilterChip
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.ModalBottomSheet
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
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import app.laughtrack.android.core.navigation.AppRoute
import app.laughtrack.android.core.network.generated.model.Filter
import app.laughtrack.android.core.network.generated.model.HomeCityFilter
import app.laughtrack.android.core.ui.theme.LaughTrackColors
import app.laughtrack.android.feature.search.model.DEFAULT_DISTANCE_MILES
import app.laughtrack.android.feature.search.model.DISTANCE_OPTIONS
import app.laughtrack.android.feature.search.model.SearchPivot
import app.laughtrack.android.feature.search.model.SearchQuery
import app.laughtrack.android.feature.search.model.SearchSort
import java.time.Instant
import java.time.ZoneOffset
import java.time.format.DateTimeFormatter
import java.util.Locale

/**
 * Search tab with the same branded shell as iOS SearchRootView: primitive chips,
 * a rounded search/filter card, and entity result rows.
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
                    LocationPill(zip = query.zip, onZip = onZip)
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
        }
    }
}

/**
 * Location pill (geo pivots only) — mirrors the iOS "Location" chip: the ZIP the
 * search is scoped to lives behind a dialog instead of an always-visible field.
 */
@Composable
private fun LocationPill(
    zip: String?,
    onZip: (String) -> Unit,
) {
    var showDialog by remember { mutableStateOf(false) }
    FilterPillButton(
        label = zip?.takeIf { it.isNotBlank() }?.let { "ZIP $it" } ?: "Location",
        active = !zip.isNullOrBlank(),
        onClick = { showDialog = true },
    )
    if (showDialog) {
        var zipText by remember { mutableStateOf(zip.orEmpty()) }
        AlertDialog(
            onDismissRequest = { showDialog = false },
            title = { Text("Set location") },
            text = {
                Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Text(
                        "Scope results to a ZIP code.",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                    OutlinedTextField(
                        value = zipText,
                        onValueChange = { entry -> zipText = entry.filter(Char::isDigit).take(5) },
                        label = { Text("ZIP code") },
                        singleLine = true,
                        keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
                        modifier = Modifier.fillMaxWidth(),
                    )
                }
            },
            confirmButton = {
                TextButton(onClick = {
                    onZip(zipText)
                    showDialog = false
                }) { Text("Apply") }
            },
            dismissButton = {
                TextButton(onClick = {
                    onZip("")
                    showDialog = false
                }) { Text("Clear") }
            },
        )
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
