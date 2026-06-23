package app.laughtrack.android.core.ui.theme

import androidx.compose.ui.graphics.Color

/**
 * LaughTrack dark design tokens, mirrored 1:1 from the iOS design system
 * (ios/Sources/LaughTrackBridge/LaughTrackTheme.swift) and the web app
 * (apps/web/tailwind.config.ts). Keep all three in sync — a color change in one
 * client must be reflected in the others. The app is dark-only, matching iOS.
 */
object LaughTrackColors {
    val Canvas = Color(0xFF121212)
    val Surface = Color(0xFF181818)
    val SurfaceMuted = Color(0xFF1F1F1F)
    val SurfaceElevated = Color(0xFF282828)
    val SurfaceSkeleton = Color(0xFF322921)

    val AccentStrong = Color(0xFFCD6837)
    val AccentMuted = Color(0xFF6C4527)
    val Highlight = Color(0xFF5F472F)

    // Warm off-white foreground + 70% gray secondary, matching iOS text tokens.
    val Foreground = Color(0xFFFAF1E8)
    val ForegroundMuted = Color(0xFFB3B3B3)

    val BorderSubtle = Color(0x1FFFFFFF) // faint white hairline over canvas/surface
}
