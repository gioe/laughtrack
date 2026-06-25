@file:Suppress("FunctionName")

package app.laughtrack.android.feature.search.ui

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.FilterChip
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Surface
import androidx.compose.material3.Tab
import androidx.compose.material3.TabRow
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import app.laughtrack.android.core.navigation.AppRoute
import app.laughtrack.android.core.ui.components.RemoteImage
import app.laughtrack.android.core.ui.components.SkeletonLine
import app.laughtrack.android.feature.search.model.SearchPivot
import app.laughtrack.android.feature.search.model.SearchResult
import app.laughtrack.android.feature.search.model.searchResultSummary

/**
 * Search tab: a four-pivot TabRow over per-pivot paginated result lists, mirroring
 * iOS SearchRootView. Shows is geo-scoped (zip filter); Comedians, Clubs, and
 * Podcasts are nationwide. Tapping a result navigates via [onOpenEntity].
 */
@Composable
fun SearchScreen(
    onOpenEntity: (AppRoute) -> Unit,
    modifier: Modifier = Modifier,
    viewModel: SearchViewModel = hiltViewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    val pivotState = state.current

    Column(modifier.fillMaxSize()) {
        TabRow(selectedTabIndex = state.pivot.ordinal) {
            SearchPivot.entries.forEach { pivot ->
                Tab(
                    selected = pivot == state.pivot,
                    onClick = { viewModel.selectPivot(pivot) },
                    enabled = pivot.isAvailable,
                    text = { Text(pivot.label) },
                )
            }
        }

        if (!state.pivot.isAvailable) {
            CenteredMessage("Podcast search is coming soon.")
        } else {
            SearchControls(
                pivot = state.pivot,
                text = pivotState.query.text,
                zip = pivotState.query.zip.orEmpty(),
                popularitySort = pivotState.query.sort == SORT_POPULARITY,
                onText = viewModel::onTextChange,
                onZip = { value -> viewModel.updateQuery { it.copy(zip = value.ifBlank { null }) } },
                onTogglePopularity = { enabled ->
                    viewModel.updateQuery { it.copy(sort = if (enabled) SORT_POPULARITY else null) }
                },
            )

            val results = pivotState.results
            when {
                results.isLoading && results.items.isEmpty() -> LoadingList()
                results.error != null && results.items.isEmpty() ->
                    CenteredMessage(results.error, onRetry = viewModel::retry)
                results.items.isEmpty() -> CenteredMessage("No results yet — try a search.")
                else ->
                    ResultsList(
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

@Composable
private fun SearchControls(
    pivot: SearchPivot,
    text: String,
    zip: String,
    popularitySort: Boolean,
    onText: (String) -> Unit,
    onZip: (String) -> Unit,
    onTogglePopularity: (Boolean) -> Unit,
) {
    Column(
        Modifier.fillMaxWidth().padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(8.dp),
    ) {
        OutlinedTextField(
            value = text,
            onValueChange = onText,
            label = { Text("Search ${pivot.label.lowercase()}") },
            singleLine = true,
            modifier = Modifier.fillMaxWidth(),
        )
        if (pivot.isGeoScoped) {
            OutlinedTextField(
                value = zip,
                onValueChange = onZip,
                label = { Text("ZIP code") },
                singleLine = true,
                modifier = Modifier.fillMaxWidth(),
            )
        }
        if (pivot == SearchPivot.COMEDIANS || pivot == SearchPivot.CLUBS) {
            FilterChip(
                selected = popularitySort,
                onClick = { onTogglePopularity(!popularitySort) },
                label = { Text("Popular") },
            )
        }
    }
}

@Composable
private fun ResultsList(
    results: List<SearchResult>,
    total: Int,
    isLoadingMore: Boolean,
    hasMore: Boolean,
    loadMoreError: String?,
    onLoadMore: () -> Unit,
    onOpen: (AppRoute) -> Unit,
) {
    LazyColumn(
        Modifier.fillMaxSize(),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        item {
            Text(
                searchResultSummary(loaded = results.size, total = total),
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                modifier = Modifier.padding(horizontal = 16.dp).padding(top = 4.dp),
            )
        }
        items(results) { result -> ResultRow(result, onOpen) }
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
                        modifier = Modifier.fillMaxWidth().padding(16.dp),
                    ) {
                        Text(if (isLoadingMore) "Loading…" else "Load more")
                    }
                }
        }
    }
}

@Composable
private fun ResultRow(
    result: SearchResult,
    onOpen: (AppRoute) -> Unit,
) {
    Surface(
        modifier = Modifier.padding(horizontal = 16.dp),
        color = MaterialTheme.colorScheme.surfaceContainer,
        shape = RoundedCornerShape(8.dp),
        tonalElevation = 1.dp,
    ) {
        Row(
            Modifier
                .fillMaxWidth()
                .clickable { onOpen(result.route) }
                .padding(12.dp),
            horizontalArrangement = Arrangement.spacedBy(14.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            RemoteImage(
                url = result.artworkUrl,
                contentDescription = result.title,
                modifier = Modifier.size(88.dp),
            )
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
            Text(
                ">",
                style = MaterialTheme.typography.titleMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
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
        Modifier.fillMaxSize().padding(24.dp),
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
