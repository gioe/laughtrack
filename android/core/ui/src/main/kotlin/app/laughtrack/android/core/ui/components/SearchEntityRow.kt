package app.laughtrack.android.core.ui.components

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
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.KeyboardArrowRight
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
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
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import app.laughtrack.android.core.ui.theme.LaughTrackColors

enum class SearchEntityKind(
    val fallback: RemoteImageFallback,
) {
    SHOW(RemoteImageFallback.Show),
    COMEDIAN(RemoteImageFallback.Comedian),
    CLUB(RemoteImageFallback.Club),
    PODCAST(RemoteImageFallback.Podcast),
}

/** Stable tags for the visible icon inside an image-less [EntityArtwork]. */
object EntityArtworkTestTags {
    fun icon(kind: SearchEntityKind): String = "EntityArtworkIcon-${kind.name}"
}

/** Canonical rich entity row shared by Search and Library. */
@Composable
fun SearchEntityRow(
    title: String,
    subtitle: String?,
    artworkUrl: String?,
    kind: SearchEntityKind,
    onOpen: () -> Unit,
    modifier: Modifier = Modifier,
    openTestTag: String? = null,
    trailing: (@Composable () -> Unit)? = null,
) {
    Surface(
        modifier = modifier.fillMaxWidth(),
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
                    .clickable(onClickLabel = "Open $title", onClick = onOpen)
                    .then(if (openTestTag != null) Modifier.testTag(openTestTag) else Modifier),
                horizontalArrangement = Arrangement.spacedBy(12.dp),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                EntityArtwork(
                    artworkUrl = artworkUrl,
                    kind = kind,
                )
                Column(
                    Modifier.weight(1f),
                    verticalArrangement = Arrangement.spacedBy(4.dp),
                ) {
                    Text(
                        title,
                        style = MaterialTheme.typography.titleMedium,
                        color = LaughTrackColors.Foreground,
                        maxLines = 2,
                        overflow = TextOverflow.Ellipsis,
                    )
                    subtitle?.takeIf(String::isNotBlank)?.let { value ->
                        Text(
                            value,
                            style = MaterialTheme.typography.bodySmall,
                            color = LaughTrackColors.ForegroundMuted,
                            maxLines = 1,
                            overflow = TextOverflow.Ellipsis,
                        )
                    }
                }
                Icon(
                    imageVector = Icons.AutoMirrored.Filled.KeyboardArrowRight,
                    contentDescription = null,
                    tint = LaughTrackColors.ForegroundMuted,
                )
            }
            trailing?.invoke()
        }
    }
}

/**
 * Shared artwork treatment for Search and Library entity rows. Missing artwork
 * gets a deliberately prominent, entity-specific mark while remote artwork
 * continues through [RemoteImage] unchanged.
 */
@Composable
fun EntityArtwork(
    artworkUrl: String?,
    kind: SearchEntityKind,
    artworkSize: Dp = 66.dp,
    contentDescription: String? = null,
) {
    val shape = if (kind == SearchEntityKind.COMEDIAN) CircleShape else RoundedCornerShape(8.dp)
    val frameColor =
        when (kind) {
            SearchEntityKind.SHOW -> LaughTrackColors.TicketAccent
            SearchEntityKind.CLUB -> Color(0xFFFFC247)
            SearchEntityKind.PODCAST -> LaughTrackColors.AccentStrong
            SearchEntityKind.COMEDIAN -> LaughTrackColors.AccentMuted
        }
    val isArtworkMissing = artworkUrl.isNullOrBlank()
    val fillColor =
        when (kind) {
            SearchEntityKind.SHOW -> LaughTrackColors.SurfaceMuted
            SearchEntityKind.COMEDIAN -> LaughTrackColors.TicketPaper
            SearchEntityKind.CLUB -> frameColor.copy(alpha = 0.16f)
            SearchEntityKind.PODCAST -> LaughTrackColors.AccentStrong.copy(alpha = 0.16f)
        }
    Box(
        modifier =
            Modifier
                .size(artworkSize)
                .then(
                    when (kind) {
                        SearchEntityKind.SHOW ->
                            if (isArtworkMissing) {
                                Modifier
                                    .clip(shape)
                                    .background(LaughTrackColors.SurfaceMuted)
                                    .border(1.5.dp, frameColor, shape)
                                    .padding(4.dp)
                            } else {
                                Modifier
                            }
                        SearchEntityKind.COMEDIAN ->
                            Modifier
                                .clip(shape)
                                .background(LaughTrackColors.TicketPaper)
                                .border(2.dp, LaughTrackColors.TicketBorder, shape)
                                .padding(4.dp)
                        SearchEntityKind.CLUB,
                        SearchEntityKind.PODCAST,
                        ->
                            Modifier
                                .drawBehind {
                                    drawRoundRect(
                                        color = frameColor,
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
                    },
                )
                .clip(shape)
                .background(fillColor),
        contentAlignment = Alignment.Center,
    ) {
        if (isArtworkMissing) {
            Box(
                modifier =
                    Modifier
                        .fillMaxSize()
                        // Keep the established fallback tag observable in the
                        // merged tree even when artwork sits inside a clickable
                        // row. The icon remains decorative because this node
                        // carries no description unless the caller supplied one.
                        .semantics(mergeDescendants = true) {
                            if (contentDescription != null) {
                                this.contentDescription = contentDescription
                            }
                        }
                        .testTag(RemoteImageTestTags.fallback(kind.fallback)),
                contentAlignment = Alignment.Center,
            ) {
                Icon(
                    imageVector = kind.fallback.icon,
                    contentDescription = null,
                    tint =
                        when (kind) {
                            SearchEntityKind.SHOW,
                            SearchEntityKind.CLUB,
                            -> LaughTrackColors.TicketAccent
                            SearchEntityKind.COMEDIAN,
                            SearchEntityKind.PODCAST,
                            -> LaughTrackColors.AccentStrong
                        },
                    modifier =
                        Modifier
                            .size(artworkSize * FALLBACK_ICON_FRACTION)
                            .testTag(EntityArtworkTestTags.icon(kind)),
                )
            }
        } else {
            RemoteImage(
                url = artworkUrl,
                contentDescription = contentDescription,
                modifier =
                    Modifier
                        .fillMaxSize()
                        .clip(shape),
                fallback = kind.fallback,
            )
        }
    }
}

private const val FALLBACK_ICON_FRACTION = 0.5f
