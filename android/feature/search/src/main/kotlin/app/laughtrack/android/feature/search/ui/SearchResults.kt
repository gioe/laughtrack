@file:Suppress("FunctionName")

package app.laughtrack.android.feature.search.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyListScope
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.KeyboardArrowRight
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import app.laughtrack.android.core.navigation.AppRoute
import app.laughtrack.android.core.ui.components.RemoteImage
import app.laughtrack.android.core.ui.components.RemoteImageFallback
import app.laughtrack.android.core.ui.components.SkeletonLine
import app.laughtrack.android.core.ui.components.TicketShowRow
import app.laughtrack.android.core.ui.components.ticketStubDateParts
import app.laughtrack.android.core.ui.theme.LaughTrackColors
import app.laughtrack.android.feature.search.model.SearchPivot
import app.laughtrack.android.feature.search.model.SearchResult
import app.laughtrack.android.feature.search.model.searchResultSummary

/** Paging state + trigger for [resultsContent]'s load-more footer. */
internal data class LoadMoreState(
    val isLoading: Boolean,
    val hasMore: Boolean,
    val error: String?,
    val onLoadMore: () -> Unit,
)

internal fun LazyListScope.resultsContent(
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
    // route is the row's entity identity (SearchResult has no id field); stringified
    // because LazyColumn keys must be Bundle-saveable and AppRoute is not Parcelable.
    items(results, key = { it.route.toString() }) { result ->
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
    TicketShowRow(
        dateParts = ticketStubDateParts(isoDateTime = result.showDate, timezone = result.showTimezone),
        priceLabel = result.showPriceLabel,
        onClick = { onOpen(result.route) },
        modifier = Modifier.testTag(SEARCH_RESULT_ROW_TEST_TAG),
    ) { bodyModifier ->
        ShowResultBody(result = result, modifier = bodyModifier)
    }
}

@Composable
private fun ShowResultBody(
    result: SearchResult,
    modifier: Modifier = Modifier,
) {
    // Body paper comes from the shared TicketShowRow Surface in core:ui (default
    // creamColors paper); no separate background needed here.
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
        RemoteImage(
            url = result.artworkUrl,
            contentDescription = result.title,
            modifier =
                Modifier
                    .fillMaxSize()
                    .clip(CircleShape),
            fallback = result.imageFallback,
        )
    }
}

@Composable
internal fun LoadingList() {
    Column(
        Modifier.fillMaxWidth().padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        repeat(6) { SkeletonLine() }
    }
}

@Composable
internal fun CenteredMessage(
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

/** Entity-branded artwork fallback derived from the result's typed destination. */
private val SearchResult.imageFallback: RemoteImageFallback
    get() =
        when (route) {
            is AppRoute.ComedianDetail -> RemoteImageFallback.Comedian
            is AppRoute.ClubDetail -> RemoteImageFallback.Club
            is AppRoute.ShowDetail -> RemoteImageFallback.Show
            is AppRoute.PodcastDetail -> RemoteImageFallback.Podcast
            else -> RemoteImageFallback.Generic
        }
