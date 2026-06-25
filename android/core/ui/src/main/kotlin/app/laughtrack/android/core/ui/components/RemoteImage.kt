package app.laughtrack.android.core.ui.components

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import app.laughtrack.android.core.ui.theme.LaughTrackColors
import coil.compose.SubcomposeAsyncImage
import coil.request.ImageRequest

/**
 * Coil-backed remote image — the single image primitive every feature reuses
 * (mirrors iOS CachedAsyncImage / RemoteImageView). Shows a [SkeletonBox] while
 * loading and a muted surface fill on error or when [url] is null.
 */
@Composable
fun RemoteImage(
    url: String?,
    contentDescription: String?,
    modifier: Modifier = Modifier,
    contentScale: ContentScale = ContentScale.Crop,
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
        loading = { SkeletonBox(Modifier.matchParentSize()) },
        error = { Box(Modifier.matchParentSize().background(LaughTrackColors.SurfaceMuted)) },
    )
}
