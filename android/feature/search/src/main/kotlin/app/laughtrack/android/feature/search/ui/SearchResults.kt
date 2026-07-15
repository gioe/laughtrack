@file:Suppress("FunctionName")

package app.laughtrack.android.feature.search.ui

import androidx.compose.foundation.BorderStroke
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
import androidx.compose.material.icons.filled.Favorite
import androidx.compose.material.icons.filled.FavoriteBorder
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.drawBehind
import androidx.compose.ui.geometry.CornerRadius
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.PathEffect
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import app.laughtrack.android.core.data.favorites.FavoriteEntity
import app.laughtrack.android.core.data.favorites.FavoritesSnapshot
import app.laughtrack.android.core.navigation.AppRoute
import app.laughtrack.android.core.ui.components.RemoteImage
import app.laughtrack.android.core.ui.components.RemoteImageFallback
import app.laughtrack.android.core.ui.components.SkeletonLine
import app.laughtrack.android.core.ui.components.TicketShowRow
import app.laughtrack.android.core.ui.components.ticketStubDateParts
import app.laughtrack.android.core.ui.theme.LaughTrackColors
import app.laughtrack.android.feature.search.model.SearchFavoriteTarget
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
    favorites: FavoritesSnapshot,
    onSetFavorite: (SearchFavoriteTarget, Boolean) -> Unit,
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
            ResultRow(
                pivot = pivot,
                result = result,
                favorites = favorites,
                onOpen = onOpen,
                onSetFavorite = onSetFavorite,
            )
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
    pivot: SearchPivot,
    result: SearchResult,
    favorites: FavoritesSnapshot,
    onOpen: (AppRoute) -> Unit,
    onSetFavorite: (SearchFavoriteTarget, Boolean) -> Unit,
) {
    val favoriteTarget = result.favoriteTarget
    val isFavorite = result.favoriteValue(favorites)
    val favoritePending = favoriteTarget?.let { favorites.pending.contains(it.pendingKey) } == true
    Surface(
        modifier = Modifier.fillMaxWidth(),
        border = BorderStroke(1.dp, LaughTrackColors.BorderSubtle),
        color = LaughTrackColors.SurfaceElevated.copy(alpha = 0.96f),
        shape = RoundedCornerShape(14.dp),
    ) {
        Row(
            Modifier
                .fillMaxWidth()
                .padding(10.dp),
            horizontalArrangement = Arrangement.spacedBy(8.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Row(
                Modifier
                    .weight(1f)
                    .clip(RoundedCornerShape(10.dp))
                    .clickable { onOpen(result.route) }
                    .testTag(SEARCH_RESULT_ROW_TEST_TAG),
                horizontalArrangement = Arrangement.spacedBy(12.dp),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                SearchArtwork(result = result, pivot = pivot)
                Column(
                    Modifier.weight(1f),
                    verticalArrangement = Arrangement.spacedBy(4.dp),
                ) {
                    Text(
                        result.title,
                        style = MaterialTheme.typography.titleMedium,
                        color = LaughTrackColors.Foreground,
                        maxLines = 2,
                        overflow = TextOverflow.Ellipsis,
                    )
                    if (pivot == SearchPivot.CLUBS) {
                        result.subtitle?.takeIf { it.isNotBlank() }?.let { location ->
                            Text(
                                location,
                                style = MaterialTheme.typography.bodySmall,
                                color = LaughTrackColors.ForegroundMuted,
                                maxLines = 1,
                                overflow = TextOverflow.Ellipsis,
                            )
                        }
                    }
                }
                Icon(
                    imageVector = Icons.AutoMirrored.Filled.KeyboardArrowRight,
                    contentDescription = null,
                    tint = LaughTrackColors.ForegroundMuted,
                )
            }
            if (favoriteTarget != null) {
                Surface(
                    modifier = Modifier.size(46.dp),
                    shape = CircleShape,
                    color = LaughTrackColors.Canvas.copy(alpha = 0.72f),
                    border = BorderStroke(1.dp, LaughTrackColors.BorderSubtle),
                    enabled = !favoritePending,
                    onClick = { onSetFavorite(favoriteTarget, !isFavorite) },
                ) {
                    Box(contentAlignment = Alignment.Center) {
                        Icon(
                            imageVector = if (isFavorite) Icons.Filled.Favorite else Icons.Filled.FavoriteBorder,
                            contentDescription = if (isFavorite) "Remove favorite" else "Favorite",
                            tint = if (isFavorite) LaughTrackColors.AccentStrong else LaughTrackColors.Foreground,
                        )
                    }
                }
            }
        }
    }
}

@Composable
private fun SearchArtwork(
    result: SearchResult,
    pivot: SearchPivot? = null,
) {
    val circular = pivot == null
    val shape = if (circular) CircleShape else RoundedCornerShape(8.dp)
    val dottedFrameColor =
        when (pivot) {
            SearchPivot.CLUBS -> Color(0xFFFFC247)
            SearchPivot.PODCASTS -> LaughTrackColors.AccentStrong
            else -> LaughTrackColors.AccentMuted
        }
    Box(
        modifier =
            Modifier
                .size(66.dp)
                .then(
                    when (pivot) {
                        SearchPivot.COMEDIANS ->
                            Modifier
                                .clip(shape)
                                .background(LaughTrackColors.TicketPaper)
                                .border(2.dp, LaughTrackColors.TicketBorder, shape)
                                .padding(4.dp)
                        SearchPivot.CLUBS,
                        SearchPivot.PODCASTS,
                        ->
                            Modifier
                                .drawBehind {
                                    drawRoundRect(
                                        color = dottedFrameColor,
                                        cornerRadius = CornerRadius(8.dp.toPx()),
                                        style =
                                            Stroke(
                                                width = 1.5.dp.toPx(),
                                                cap = StrokeCap.Round,
                                                pathEffect =
                                                    PathEffect.dashPathEffect(
                                                        floatArrayOf(1.dp.toPx(), 5.dp.toPx()),
                                                    ),
                                            ),
                                    )
                                }
                                .padding(4.dp)
                        else -> Modifier
                    },
                )
                .clip(shape)
                .background(LaughTrackColors.AccentStrong.copy(alpha = 0.14f)),
        contentAlignment = Alignment.Center,
    ) {
        RemoteImage(
            url = result.artworkUrl,
            contentDescription = result.title,
            modifier =
                Modifier
                    .fillMaxSize()
                    .clip(shape),
            fallback = result.imageFallback,
        )
    }
}

private fun SearchResult.favoriteValue(snapshot: FavoritesSnapshot): Boolean =
    when (val target = favoriteTarget) {
        is SearchFavoriteTarget.Comedian -> snapshot.comedianValues[target.uuid] ?: isFavorite
        is SearchFavoriteTarget.Podcast -> snapshot.podcastValues[target.id] ?: isFavorite
        null -> false
    }

private val SearchFavoriteTarget.pendingKey: String
    get() =
        when (this) {
            is SearchFavoriteTarget.Comedian -> FavoriteEntity.COMEDIAN.name + uuid
            is SearchFavoriteTarget.Podcast -> FavoriteEntity.PODCAST.name + id
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
