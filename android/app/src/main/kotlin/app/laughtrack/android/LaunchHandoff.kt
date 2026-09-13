package app.laughtrack.android

import androidx.compose.ui.Modifier
import androidx.compose.ui.layout.layout

/** A launch-only latch: resolving or retrying later never acquires the system splash again. */
internal class LaunchHandoff {
    var keepSplashVisible = true
        private set

    fun destinationLaidOut(
        surface: FirstEntryRootSurface,
        hasPendingRoute: Boolean,
    ) {
        if (surface == FirstEntryRootSurface.Loading) return
        if (surface == FirstEntryRootSurface.AppShell && hasPendingRoute) return
        keepSplashVisible = false
    }
}

/**
 * Routing can change without changing the root bounds. A layout modifier is
 * invalidated when these inputs change; a geometry observer need not run again.
 * Keep the existing content node so navigation state survives the handoff.
 */
internal fun Modifier.launchDestinationLayout(
    handoff: LaunchHandoff,
    surface: FirstEntryRootSurface,
    hasPendingRoute: Boolean,
): Modifier =
    layout { measurable, constraints ->
        val content = measurable.measure(constraints)
        layout(content.width, content.height) {
            content.placeRelative(0, 0)
            handoff.destinationLaidOut(surface, hasPendingRoute)
        }
    }
