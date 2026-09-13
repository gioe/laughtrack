package app.laughtrack.android

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
