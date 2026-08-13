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
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import app.laughtrack.android.core.ui.theme.LaughTrackColors

enum class SearchEntityKind {
    COMEDIAN,
    CLUB,
    PODCAST,
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
                SearchEntityArtwork(
                    title = title,
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

@Composable
private fun SearchEntityArtwork(
    title: String,
    artworkUrl: String?,
    kind: SearchEntityKind,
) {
    val shape = if (kind == SearchEntityKind.COMEDIAN) CircleShape else RoundedCornerShape(8.dp)
    val frameColor =
        when (kind) {
            SearchEntityKind.CLUB -> Color(0xFFFFC247)
            SearchEntityKind.PODCAST -> LaughTrackColors.AccentStrong
            SearchEntityKind.COMEDIAN -> LaughTrackColors.AccentMuted
        }
    Box(
        modifier =
            Modifier
                .size(66.dp)
                .then(
                    when (kind) {
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
                .background(LaughTrackColors.AccentStrong.copy(alpha = 0.14f)),
        contentAlignment = Alignment.Center,
    ) {
        RemoteImage(
            url = artworkUrl,
            contentDescription = null,
            modifier =
                Modifier
                    .fillMaxSize()
                    .clip(shape),
            fallback =
                when (kind) {
                    SearchEntityKind.COMEDIAN -> RemoteImageFallback.Comedian
                    SearchEntityKind.CLUB -> RemoteImageFallback.Club
                    SearchEntityKind.PODCAST -> RemoteImageFallback.Podcast
                },
        )
    }
}
