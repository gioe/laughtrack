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
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.PathEffect
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.semantics.clearAndSetSemantics
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import app.laughtrack.android.core.ui.theme.LaughTrackColors
import java.util.Locale

enum class SearchEntityKind(
    val fallback: RemoteImageFallback,
) {
    SHOW(RemoteImageFallback.Show),
    COMEDIAN(RemoteImageFallback.Comedian),
    CLUB(RemoteImageFallback.Club),
    PODCAST(RemoteImageFallback.Podcast),
}

/** Stable tags for the visible treatment inside an image-less [EntityArtwork]. */
object EntityArtworkTestTags {
    fun icon(kind: SearchEntityKind): String = "EntityArtworkIcon-${kind.name}"

    fun curated(
        kind: SearchEntityKind,
        identity: String,
    ): String = "EntityArtworkCurated-${kind.name}-${identity.stableArtworkHash()}"

    fun monogram(
        kind: SearchEntityKind,
        identity: String,
    ): String = "EntityArtworkMonogram-${kind.name}-${identity.stableArtworkHash()}"
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
                    artworkIdentity = title,
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
    artworkIdentity: String? = null,
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
    val curatedIdentity =
        (artworkIdentity ?: contentDescription)
            ?.trim()
            ?.takeIf(String::isNotEmpty)
            ?.takeIf { kind == SearchEntityKind.SHOW || kind == SearchEntityKind.COMEDIAN }
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
                if (curatedIdentity != null) {
                    CuratedEntityArtwork(
                        identity = curatedIdentity,
                        kind = kind,
                        modifier =
                            Modifier
                                .fillMaxSize()
                                .testTag(EntityArtworkTestTags.curated(kind, curatedIdentity)),
                    )
                } else {
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

/**
 * Network-free artwork for named shows and comedians. A stable title hash picks
 * from a small hand-tuned palette while the monogram makes each saved entity
 * recognizable at screenshot scale.
 */
@Composable
private fun CuratedEntityArtwork(
    identity: String,
    kind: SearchEntityKind,
    modifier: Modifier = Modifier,
) {
    val palette = CURATED_ARTWORK_PALETTES[identity.stableArtworkHash() % CURATED_ARTWORK_PALETTES.size]
    val shape = if (kind == SearchEntityKind.COMEDIAN) CircleShape else RoundedCornerShape(5.dp)
    Box(
        modifier =
            modifier
                .clip(shape)
                .background(Brush.linearGradient(listOf(palette.start, palette.end)))
                .drawBehind {
                    drawCircle(
                        color = palette.detail.copy(alpha = 0.32f),
                        radius = size.minDimension * 0.34f,
                        center = Offset(size.width * 0.78f, size.height * 0.2f),
                    )
                    if (kind == SearchEntityKind.SHOW) {
                        drawLine(
                            color = palette.detail.copy(alpha = 0.65f),
                            start = Offset(size.width * 0.14f, size.height * 0.78f),
                            end = Offset(size.width * 0.86f, size.height * 0.78f),
                            strokeWidth = 1.dp.toPx(),
                            cap = StrokeCap.Round,
                        )
                    }
                },
        contentAlignment = Alignment.Center,
    ) {
        Box(
            modifier = Modifier.testTag(EntityArtworkTestTags.monogram(kind, identity)),
            contentAlignment = Alignment.Center,
        ) {
            Text(
                text = curatedArtworkInitials(identity),
                color = palette.foreground,
                style = MaterialTheme.typography.titleMedium,
                fontWeight = FontWeight.Black,
                modifier = Modifier.clearAndSetSemantics { },
            )
        }
    }
}

internal fun curatedArtworkInitials(identity: String): String {
    val words =
        identity
            .substringBefore(':')
            .split(Regex("[^\\p{L}\\p{N}]+"))
            .filter(String::isNotBlank)
            .filterNot { it.lowercase(Locale.US) in ARTWORK_INITIAL_STOP_WORDS }
    return words.take(2).joinToString("") { it.first().uppercaseChar().toString() }.ifEmpty { "LT" }
}

private fun String.stableArtworkHash(): Int {
    var hash = 17
    trim().lowercase(Locale.US).forEach { character -> hash = 31 * hash + character.code }
    return hash and Int.MAX_VALUE
}

private data class CuratedArtworkPalette(
    val start: Color,
    val end: Color,
    val detail: Color,
    val foreground: Color,
)

private val CURATED_ARTWORK_PALETTES =
    listOf(
        CuratedArtworkPalette(Color(0xFF6E213D), Color(0xFFB74837), Color(0xFFFFC247), Color(0xFFFFF3D6)),
        CuratedArtworkPalette(Color(0xFF173F5F), Color(0xFF20639B), Color(0xFFFFC247), Color.White),
        CuratedArtworkPalette(Color(0xFF4A256D), Color(0xFF8A3D7C), Color(0xFFF2A65A), Color.White),
        CuratedArtworkPalette(Color(0xFF1E4D45), Color(0xFF347A68), Color(0xFFFFC857), Color.White),
        CuratedArtworkPalette(Color(0xFF71351F), Color(0xFFC45A32), Color(0xFFFFD166), Color(0xFFFFF7E6)),
        CuratedArtworkPalette(Color(0xFF283044), Color(0xFF59647D), Color(0xFFF26B38), Color.White),
    )

private val ARTWORK_INITIAL_STOP_WORDS = setOf("a", "an", "and", "at", "of", "the", "with")

private const val FALLBACK_ICON_FRACTION = 0.5f
