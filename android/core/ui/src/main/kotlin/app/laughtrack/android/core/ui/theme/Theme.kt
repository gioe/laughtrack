package app.laughtrack.android.core.ui.theme

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable

/**
 * Maps the LaughTrack design tokens onto a Material 3 color scheme. The app is
 * dark-only (parity with iOS). A darkTheme/light-scheme toggle is intentionally
 * omitted until a light scheme actually exists, so the contract never lies.
 */
private val LaughTrackDarkColorScheme =
    darkColorScheme(
        primary = LaughTrackColors.AccentStrong,
        onPrimary = LaughTrackColors.Foreground,
        secondary = LaughTrackColors.AccentMuted,
        onSecondary = LaughTrackColors.Foreground,
        background = LaughTrackColors.Canvas,
        onBackground = LaughTrackColors.Foreground,
        surface = LaughTrackColors.Surface,
        onSurface = LaughTrackColors.Foreground,
        surfaceVariant = LaughTrackColors.SurfaceElevated,
        onSurfaceVariant = LaughTrackColors.ForegroundMuted,
        outline = LaughTrackColors.BorderSubtle,
    )

@Composable
fun LaughTrackTheme(content: @Composable () -> Unit) {
    MaterialTheme(
        colorScheme = LaughTrackDarkColorScheme,
        typography = LaughTrackTypography,
        content = content,
    )
}
