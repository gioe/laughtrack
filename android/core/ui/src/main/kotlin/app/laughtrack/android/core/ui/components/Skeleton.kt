package app.laughtrack.android.core.ui.components

import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.drawWithContent
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import app.laughtrack.android.core.ui.theme.LaughTrackColors

/**
 * Pulsing skeleton placeholder reused while content loads, mirroring the iOS
 * detail/list skeletons. [SkeletonBox] fills its [modifier]'s bounds; [SkeletonLine]
 * is a convenience for text-line placeholders.
 */
@Composable
fun SkeletonBox(modifier: Modifier = Modifier, cornerRadius: Dp = 8.dp) {
    val transition = rememberInfiniteTransition(label = "skeleton")
    val alpha by transition.animateFloat(
        initialValue = 0.35f,
        targetValue = 0.85f,
        animationSpec = infiniteRepeatable(tween(900), RepeatMode.Reverse),
        label = "skeleton-alpha",
    )
    Box(
        modifier
            .clip(RoundedCornerShape(cornerRadius))
            .background(LaughTrackColors.SurfaceSkeleton)
            .drawWithContent {
                drawContent()
                drawRect(color = Color.White, alpha = alpha * 0.06f)
            },
    )
}

@Composable
fun SkeletonLine(modifier: Modifier = Modifier, height: Dp = 14.dp) {
    SkeletonBox(modifier.fillMaxWidth().height(height), cornerRadius = height / 2)
}
