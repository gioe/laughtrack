package app.laughtrack.android

import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class LaunchHandoffTest {
    @Test
    fun `loading layout cannot release splash`() {
        val handoff = LaunchHandoff()
        handoff.destinationLaidOut(FirstEntryRootSurface.Loading, hasPendingRoute = false)
        assertTrue(handoff.keepSplashVisible)
    }

    @Test
    fun `home releases immediately after layout with no minimum wait`() {
        val handoff = LaunchHandoff()
        handoff.destinationLaidOut(FirstEntryRootSurface.AppShell, hasPendingRoute = false)
        assertFalse(handoff.keepSplashVisible)
    }

    @Test
    fun `cold link waits for consumption before shell reveal`() {
        val handoff = LaunchHandoff()
        handoff.destinationLaidOut(FirstEntryRootSurface.AppShell, hasPendingRoute = true)
        assertTrue(handoff.keepSplashVisible)
        handoff.destinationLaidOut(FirstEntryRootSurface.AppShell, hasPendingRoute = false)
        assertFalse(handoff.keepSplashVisible)
    }

    @Test
    fun `auth choice onboarding and failure release while preserving a link`() {
        listOf(FirstEntryRootSurface.AuthChoice, FirstEntryRootSurface.Onboarding, FirstEntryRootSurface.Recovery)
            .forEach { surface ->
                val handoff = LaunchHandoff()
                handoff.destinationLaidOut(surface, hasPendingRoute = true)
                assertFalse(handoff.keepSplashVisible)
            }
    }

    @Test
    fun `retry or subsequent route never reacquires splash`() {
        val handoff = LaunchHandoff()
        handoff.destinationLaidOut(FirstEntryRootSurface.Recovery, hasPendingRoute = false)
        handoff.destinationLaidOut(FirstEntryRootSurface.Loading, hasPendingRoute = false)
        assertFalse(handoff.keepSplashVisible)
        handoff.destinationLaidOut(FirstEntryRootSurface.AppShell, hasPendingRoute = true)
        assertFalse(handoff.keepSplashVisible)
    }
}
