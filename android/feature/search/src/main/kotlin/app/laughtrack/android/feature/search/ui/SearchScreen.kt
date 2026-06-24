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
import androidx.compose.material3.FilterChip
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Tab
import androidx.compose.material3.TabRow
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.material3.MaterialTheme
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import app.laughtrack.android.core.navigation.AppRoute
import app.laughtrack.android.core.ui.components.RemoteImage
import app.laughtrack.android.core.ui.components.SkeletonLine
import app.laughtrack.android.feature.search.model.SearchPivot
import app.laughtrack.android.feature.search.model.SearchResult

/**
 * Search tab: a four-pivot TabRow over per-pivot paginated result lists, mirroring
 * iOS SearchRootView. Shows is geo-scoped (zip filter); Comedians/Clubs are
 * nationwide; Podcasts is disabled until its endpoint ships (TASK-3273). Tapping a
 * result navigates via [onOpenEntity].
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
                onText = { value -> viewModel.updateQuery { it.copy(text = value) } },
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
                else -> ResultsList(
                    results = results.items,
                    isLoadingMore = results.isLoading,
                    hasMore = results.hasMore,
                    onLoadMore = viewModel::loadMore,
                    onOpen = onOpenEntity,
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
    isLoadingMore: Boolean,
    hasMore: Boolean,
    onLoadMore: () -> Unit,
    onOpen: (AppRoute) -> Unit,
) {
    LazyColumn(Modifier.fillMaxSize()) {
        items(results) { result -> ResultRow(result, onOpen) }
        if (hasMore) {
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
private fun ResultRow(result: SearchResult, onOpen: (AppRoute) -> Unit) {
    Row(
        Modifier
            .fillMaxWidth()
            .clickable { onOpen(result.route) }
            .padding(horizontal = 16.dp, vertical = 8.dp),
        horizontalArrangement = Arrangement.spacedBy(12.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        RemoteImage(
            url = result.imageUrl,
            contentDescription = result.title,
            modifier = Modifier.size(56.dp),
        )
        Column(Modifier.weight(1f)) {
            Text(
                result.title,
                style = MaterialTheme.typography.titleMedium,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
            )
            result.subtitle?.let {
                Text(
                    it,
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                )
            }
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
private fun CenteredMessage(message: String, onRetry: (() -> Unit)? = null) {
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
