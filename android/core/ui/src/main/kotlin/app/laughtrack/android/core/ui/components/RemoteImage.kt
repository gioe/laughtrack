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
                .data(normalizeRemoteImageUrl(url))
                // A request-level crossfade overrides the screenshot lane's
                // non-animated ImageLoader and can leave large hero artwork
                // visibly translucent even after Coil reports success.
                .crossfade(false)
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

/**
 * Resolves API-relative artwork paths and scheme-less external image URLs the
 * same way the iOS URL helper does before handing them to the image loader.
 */
internal fun normalizeRemoteImageUrl(rawUrl: String?): String? {
    val url = rawUrl?.trim()?.takeIf { it.isNotEmpty() } ?: return null
    return when {
        url.startsWith("//") -> "https:$url"
        url.startsWith("/") -> "$LAUGH_TRACK_WEB_ORIGIN$url"
        URL_SCHEME.matches(url.substringBefore('/')) -> url
        else -> "https://$url"
    }
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
private const val LAUGH_TRACK_WEB_ORIGIN = "https://www.laugh-track.com"
private val URL_SCHEME = Regex("[A-Za-z][A-Za-z0-9+.-]*:")
