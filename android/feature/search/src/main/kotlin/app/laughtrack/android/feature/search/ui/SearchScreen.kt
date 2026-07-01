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
import androidx.compose.material.icons.filled.Person
import androidx.compose.material.icons.filled.Search
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.FilterChip
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
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
import androidx.compose.ui.graphics.PathEffect
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import app.laughtrack.android.core.navigation.AppRoute
import app.laughtrack.android.core.network.generated.model.HomeCityFilter
import app.laughtrack.android.core.ui.components.RemoteImage
import app.laughtrack.android.core.ui.components.SkeletonLine
import app.laughtrack.android.core.ui.theme.LaughTrackColors
import app.laughtrack.android.feature.search.model.SearchPivot
import app.laughtrack.android.feature.search.model.SearchResult
import app.laughtrack.android.feature.search.model.searchResultSummary
import java.time.OffsetDateTime
import java.time.ZoneId
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
                        text = pivotState.query.text,
                        zip = pivotState.query.zip.orEmpty(),
                        popularitySort = pivotState.query.sort == SORT_POPULARITY,
                        homeCity = pivotState.query.homeCity,
                        homeCityFilters = pivotState.homeCityFilters,
                        onText = viewModel::onTextChange,
                        onZip = { value -> viewModel.updateQuery { it.copy(zip = value.ifBlank { null }) } },
                        onTogglePopularity = { enabled ->
                            viewModel.updateQuery { it.copy(sort = if (enabled) SORT_POPULARITY else null) }
                        },
                        onSelectHomeCity = { token ->
                            viewModel.updateQuery { it.copy(homeCity = token) }
                        },
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
                            isLoadingMore = results.isLoading,
                            hasMore = results.hasMore,
                            loadMoreError = results.error,
                            onLoadMore = viewModel::loadMore,
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
        color = if (selected) LaughTrackColors.AccentStrong else LaughTrackColors.Canvas.copy(alpha = 0.1f),
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
    text: String,
    zip: String,
    popularitySort: Boolean,
    homeCity: String?,
    homeCityFilters: List<HomeCityFilter>,
    onText: (String) -> Unit,
    onZip: (String) -> Unit,
    onTogglePopularity: (Boolean) -> Unit,
    onSelectHomeCity: (String?) -> Unit,
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
                value = text,
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
                if (pivot.isGeoScoped) {
                    SearchFilterPill(zip.ifBlank { "Location" })
                    SearchFilterPill("25 mi")
                }
                SearchFilterPill(if (pivot == SearchPivot.SHOWS) "Earliest" else "Popular")
                SearchFilterPill("Any date")
                // Comedian-only home-city filter, hidden until the response carries
                // options (no home-location data -> no control), mirroring iOS.
                if (pivot == SearchPivot.COMEDIANS && homeCityFilters.isNotEmpty()) {
                    HomeCityFilterPill(
                        selectedToken = homeCity,
                        filters = homeCityFilters,
                        onSelect = onSelectHomeCity,
                    )
                }
                FilterChip(
                    selected = popularitySort,
                    onClick = { onTogglePopularity(!popularitySort) },
                    label = { Text("Filters") },
                )
            }

            if (pivot.isGeoScoped) {
                OutlinedTextField(
                    value = zip,
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

@Composable
private fun SearchFilterPill(label: String) {
    Surface(
        color = LaughTrackColors.Surface,
        shape = RoundedCornerShape(999.dp),
        modifier = Modifier.border(1.dp, LaughTrackColors.BorderSubtle, RoundedCornerShape(999.dp)),
    ) {
        Text(
            label,
            style = MaterialTheme.typography.labelSmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
            modifier = Modifier.padding(horizontal = 12.dp, vertical = 8.dp),
            maxLines = 1,
        )
    }
}

/**
 * Single-select home-city filter: a pill that opens a [DropdownMenu] of
 * "All home cities" (clears the filter) plus one entry per option. Mirrors the
 * iOS PillDropdown behavior; [onSelect] receives the `city|state` token (or null
 * for "all").
 */
@Composable
private fun HomeCityFilterPill(
    selectedToken: String?,
    filters: List<HomeCityFilter>,
    onSelect: (String?) -> Unit,
) {
    var expanded by remember { mutableStateOf(false) }
    Box {
        Surface(
            color = LaughTrackColors.Surface,
            shape = RoundedCornerShape(999.dp),
            modifier =
                Modifier
                    .border(1.dp, LaughTrackColors.BorderSubtle, RoundedCornerShape(999.dp))
                    .clickable { expanded = true },
        ) {
            Text(
                homeCityTriggerLabel(selectedToken, filters),
                style = MaterialTheme.typography.labelSmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                modifier = Modifier.padding(horizontal = 12.dp, vertical = 8.dp),
                maxLines = 1,
            )
        }
        DropdownMenu(expanded = expanded, onDismissRequest = { expanded = false }) {
            homeCityMenuOptions(filters).forEach { option ->
                DropdownMenuItem(
                    text = { Text(option.label) },
                    onClick = {
                        expanded = false
                        onSelect(option.token)
                    },
                )
            }
        }
    }
}

/** One home-city dropdown entry: [token] is the `city|state` value (null = all). */
internal data class HomeCityMenuOption(val token: String?, val label: String)

/**
 * The dropdown entries: an "All home cities" sentinel that clears the filter,
 * followed by one "Label (count)" entry per option (mirrors web/iOS).
 */
internal fun homeCityMenuOptions(filters: List<HomeCityFilter>): List<HomeCityMenuOption> =
    listOf(HomeCityMenuOption(token = null, label = "All home cities")) +
        filters.map { HomeCityMenuOption(token = it.value, label = "${it.label} (${it.count})") }

/** Compact pill label: the selected city's name, or "Home city" when none is set. */
internal fun homeCityTriggerLabel(
    selectedToken: String?,
    filters: List<HomeCityFilter>,
): String = filters.firstOrNull { it.value == selectedToken }?.label ?: "Home city"

private fun queryPrompt(pivot: SearchPivot): String =
    when (pivot) {
        SearchPivot.SHOWS -> "Search nearby comedy"
        SearchPivot.COMEDIANS -> "Search comedian names"
        SearchPivot.CLUBS -> "Search club names"
        SearchPivot.PODCASTS -> "Search podcast titles"
    }

// A LazyListScope section builder that hoists list state + callbacks the same way
// a @Composable does, so it legitimately exceeds the param budget (detekt exempts
// @Composable for this reason; this extension isn't annotated but is the same shape).
@Suppress("LongParameterList")
private fun LazyListScope.resultsContent(
    pivot: SearchPivot,
    results: List<SearchResult>,
    total: Int,
    isLoadingMore: Boolean,
    hasMore: Boolean,
    loadMoreError: String?,
    onLoadMore: () -> Unit,
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
        loadMoreError != null ->
            item {
                Column(
                    Modifier.fillMaxWidth().padding(16.dp),
                    verticalArrangement = Arrangement.spacedBy(8.dp),
                    horizontalAlignment = Alignment.CenterHorizontally,
                ) {
                    Text("Couldn't load more.", color = MaterialTheme.colorScheme.onSurfaceVariant)
                    OutlinedButton(onClick = onLoadMore, enabled = !isLoadingMore) { Text("Retry") }
                }
            }
        hasMore ->
            item {
                OutlinedButton(
                    onClick = onLoadMore,
                    enabled = !isLoadingMore,
                    modifier = Modifier.fillMaxWidth().padding(vertical = 8.dp),
                ) {
                    Text(if (isLoadingMore) "Loading..." else "Load more")
                }
            }
    }
}

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
                .border(1.dp, LaughTrackColors.BorderSubtle, RoundedCornerShape(12.dp)),
        color = LaughTrackColors.SurfaceElevated,
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
    Box(
        modifier = modifier.background(LaughTrackColors.AccentMuted.copy(alpha = 0.035f)),
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
                    color = MaterialTheme.colorScheme.onSurface,
                    maxLines = 2,
                    overflow = TextOverflow.Ellipsis,
                )
                result.subtitle?.takeIf { it.isNotBlank() }?.let { club ->
                    Text(
                        club,
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
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
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                            maxLines = 1,
                            overflow = TextOverflow.Ellipsis,
                        )
                    }
                if (result.isSoldOut) {
                    Text(
                        "Sold out",
                        style = MaterialTheme.typography.labelSmall.copy(fontWeight = FontWeight.SemiBold),
                        color = LaughTrackColors.AccentStrong,
                        modifier =
                            Modifier
                                .clip(RoundedCornerShape(999.dp))
                                .background(LaughTrackColors.AccentMuted.copy(alpha = 0.22f))
                                .border(
                                    1.dp,
                                    LaughTrackColors.AccentMuted.copy(alpha = 0.45f),
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
    val color = LaughTrackColors.ForegroundMuted.copy(alpha = 0.6f)
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
                .background(LaughTrackColors.Surface)
                .padding(vertical = 10.dp, horizontal = 6.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center,
    ) {
        Text(
            dateParts.weekday,
            style = MaterialTheme.typography.labelSmall.copy(fontWeight = FontWeight.SemiBold, letterSpacing = 1.4.sp),
            color = LaughTrackColors.AccentStrong,
            maxLines = 1,
        )
        Text(
            dateParts.day,
            fontWeight = FontWeight.Black,
            fontSize = 26.sp,
            color = MaterialTheme.colorScheme.onSurface,
            maxLines = 1,
        )
        Text(
            dateParts.month,
            style = MaterialTheme.typography.labelSmall.copy(fontWeight = FontWeight.SemiBold, letterSpacing = 1.2.sp),
            color = MaterialTheme.colorScheme.onSurfaceVariant,
            maxLines = 1,
        )
        Text(
            dateParts.time,
            style = MaterialTheme.typography.labelSmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
            maxLines = 1,
            modifier = Modifier.padding(top = 2.dp),
        )
        result.showPriceLabel?.let { price ->
            Text(
                price,
                style = MaterialTheme.typography.labelMedium.copy(fontWeight = FontWeight.SemiBold),
                color = LaughTrackColors.AccentStrong,
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
                .border(1.dp, LaughTrackColors.BorderSubtle, RoundedCornerShape(14.dp)),
        color = LaughTrackColors.SurfaceElevated,
        shape = RoundedCornerShape(14.dp),
    ) {
        Row(
            Modifier
                .fillMaxWidth()
                .clickable { onOpen(result.route) }
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
                    maxLines = 2,
                    overflow = TextOverflow.Ellipsis,
                )
                result.displayMetadata.take(3).forEach { line ->
                    Text(
                        line,
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis,
                    )
                }
            }
            Icon(
                imageVector = Icons.AutoMirrored.Filled.KeyboardArrowRight,
                contentDescription = null,
                tint = MaterialTheme.colorScheme.onSurfaceVariant,
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

private const val SORT_POPULARITY = "popularity"
