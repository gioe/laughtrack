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

    // Warm cream "ticket" card tokens, mirrored from the iOS ShowRow .compactTicket
    // presentation (ios/Sources/LaughTrackApp/Components/ShowRow.swift). The result/
    // calendar cards render as a warm paper body + darker perforated stub with dark
    // ink text, matching the App Store / Play Store ticket screenshots. Keep in sync
    // with iOS: TicketPaper = ticketPaper, TicketStub = ticketStubBackground,
    // TicketInk = ticketInk, TicketInkMuted = ticketInkMuted, TicketBorder =
    // ticketBorder@78%, TicketAccent = ticketAccent.
    val TicketPaper = Color(0xFFEDDEBD) // rgb(0.93, 0.87, 0.74) — card body
    val TicketStub = Color(0xFFDBC7A1) // rgb(0.86, 0.78, 0.63) — perforated date stub
    val TicketInk = Color(0xFF261A0D) // rgb(0.15, 0.10, 0.05) — primary text
    val TicketInkMuted = Color(0xFF735938) // rgb(0.45, 0.35, 0.22) — secondary text
    val TicketBorder = Color(0xC794784F) // rgb(0.58, 0.47, 0.31) @ 78% — hairline/perforation
    val TicketAccent = Color(0xFFBD4D21) // rgb(0.74, 0.30, 0.13) — weekday/price accent
}
