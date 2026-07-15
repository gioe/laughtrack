package app.laughtrack.android.core.ui.components

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import app.laughtrack.android.core.ui.theme.LaughTrackColors

/**
 * Shared app atmosphere matching iOS `LaughTrackAtmosphereBackground`: a warm
 * cedar spotlight that falls through a burgundy side glow into the dark canvas.
 */
@Composable
fun LaughTrackAtmosphereBackground(modifier: Modifier = Modifier) {
    Box(
        modifier =
            modifier
                .fillMaxSize()
                .background(
                    Brush.verticalGradient(
                        colorStops =
                            arrayOf(
                                0f to Color(0xFF70451F),
                                0.34f to Color(0xFF321B13),
                                0.68f to Color(0xFF1E0D11),
                                1f to LaughTrackColors.Canvas,
                            ),
                    ),
                ),
    ) {
        Canvas(Modifier.fillMaxSize()) {
            drawRect(
                brush =
                    Brush.radialGradient(
                        colors = listOf(Color(0xFF570A12).copy(alpha = 0.42f), Color.Transparent),
                        center = Offset(size.width * 0.04f, size.height * 0.57f),
                        radius = size.width * 1.05f,
                    ),
            )
        }
    }
}
