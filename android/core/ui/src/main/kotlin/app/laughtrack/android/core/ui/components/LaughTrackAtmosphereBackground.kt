package app.laughtrack.android.core.ui.components

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import app.laughtrack.android.core.ui.theme.LaughTrackColors

/**
 * Shared app atmosphere matching iOS `LaughTrackAtmosphereBackground`: a warm
 * cedar spotlight that falls through a burgundy side glow into the dark canvas.
 */
@Composable
fun LaughTrackAtmosphereBackground(modifier: Modifier = Modifier) {
    Canvas(modifier.fillMaxSize()) {
        val transparentCanvas = LaughTrackColors.Canvas.copy(alpha = 0f)
        val spotlight = Color(0xFFFFB84D)

        drawRect(LaughTrackColors.Canvas)
        drawRect(
            brush =
                Brush.radialGradient(
                    colorStops =
                        arrayOf(
                            0f to spotlight.copy(alpha = 0.30f),
                            0.5f to LaughTrackColors.AccentStrong.copy(alpha = 0.18f),
                            1f to transparentCanvas,
                        ),
                    center = Offset.Zero,
                    radius = 430.dp.toPx(),
                ),
        )
        drawRect(
            brush =
                Brush.linearGradient(
                    colorStops =
                        arrayOf(
                            0f to spotlight.copy(alpha = 0.22f),
                            1f / 3f to Color(0xFFB87333).copy(alpha = 0.20f),
                            2f / 3f to LaughTrackColors.AccentMuted.copy(alpha = 0.10f),
                            1f to transparentCanvas,
                        ),
                    start = Offset.Zero,
                    end = Offset(size.width * 0.72f, size.height * 0.46f),
                ),
        )
        drawRect(
            brush =
                Brush.radialGradient(
                    colorStops =
                        arrayOf(
                            0f to LaughTrackColors.AccentStrong.copy(alpha = 0.24f),
                            18f / 300f to LaughTrackColors.AccentStrong.copy(alpha = 0.24f),
                            159f / 300f to LaughTrackColors.AccentMuted.copy(alpha = 0.08f),
                            1f to transparentCanvas,
                        ),
                    center = Offset(size.width * 0.72f, size.height * 0.08f),
                    radius = 300.dp.toPx(),
                ),
        )
        drawRect(
            brush =
                Brush.radialGradient(
                    colorStops =
                        arrayOf(
                            0f to Color(0xFF570A12).copy(alpha = 0.24f),
                            36f / 360f to Color(0xFF570A12).copy(alpha = 0.24f),
                            1f to transparentCanvas,
                        ),
                    center = Offset(size.width * 0.05f, size.height * 0.56f),
                    radius = 360.dp.toPx(),
                ),
        )
    }
}
