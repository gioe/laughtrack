package app.laughtrack.android.core.ui.components

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.Image
import androidx.compose.material.icons.outlined.Mic
import androidx.compose.material.icons.outlined.Person
import androidx.compose.material.icons.outlined.Podcasts
import androidx.compose.material.icons.outlined.Storefront
import androidx.compose.material.icons.outlined.TheaterComedy
import androidx.compose.material3.Icon
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.testTag
import app.laughtrack.android.core.ui.theme.LaughTrackColors
import coil.compose.SubcomposeAsyncImage
import coil.request.ImageRequest

/**
 * Entity kind rendered when an artwork URL is null or fails to load, so broken
 * or missing images read as intentional branding instead of a blank rectangle.
 * Pick the kind matching what the image depicts; [Generic] is the default for
 * surfaces with no single entity.
 */
enum class RemoteImageFallback(internal val icon: ImageVector) {
    Comedian(Icons.Outlined.Mic),
    Club(Icons.Outlined.Storefront),
    Show(Icons.Outlined.TheaterComedy),
    Podcast(Icons.Outlined.Podcasts),
    Person(Icons.Outlined.Person),
    Generic(Icons.Outlined.Image),
}

/** Semantics test tags for [RemoteImage]'s non-success states. */
object RemoteImageTestTags {
    const val SKELETON = "RemoteImageSkeleton"

    fun fallback(fallback: RemoteImageFallback): String = "RemoteImageFallback-${fallback.name}"
}

/**
 * Coil-backed remote image — the single image primitive every feature reuses
 * (mirrors iOS CachedAsyncImage / RemoteImageView). Shows a [SkeletonBox] while
 * loading and a branded entity [fallback] on error or when [url] is null, so
 * loading stays visually distinct from terminal failure.
 */
@Composable
fun RemoteImage(
    url: String?,
    contentDescription: String?,
    modifier: Modifier = Modifier,
    contentScale: ContentScale = ContentScale.Crop,
    fallback: RemoteImageFallback = RemoteImageFallback.Generic,
) {
    SubcomposeAsyncImage(
        model =
            ImageRequest.Builder(LocalContext.current)
                .data(url)
                .crossfade(true)
                .build(),
        contentDescription = contentDescription,
        contentScale = contentScale,
        modifier = modifier,
        loading = {
            SkeletonBox(
                Modifier
                    .matchParentSize()
                    .testTag(RemoteImageTestTags.SKELETON),
            )
        },
        error = { FallbackArtwork(fallback, Modifier.matchParentSize()) },
    )
}

@Composable
private fun FallbackArtwork(
    fallback: RemoteImageFallback,
    modifier: Modifier = Modifier,
) {
    Box(
        modifier =
            modifier
                .background(LaughTrackColors.SurfaceMuted)
                .testTag(RemoteImageTestTags.fallback(fallback)),
        contentAlignment = Alignment.Center,
    ) {
        Icon(
            imageVector = fallback.icon,
            // Decorative: the enclosing image node already carries the
            // contentDescription passed by the caller.
            contentDescription = null,
            tint = LaughTrackColors.AccentStrong.copy(alpha = 0.55f),
            modifier = Modifier.fillMaxSize(ICON_FRACTION),
        )
    }
}

// Icon scales with its container so the fallback reads at rail-thumbnail and
// full-bleed hero sizes alike.
private const val ICON_FRACTION = 0.34f
