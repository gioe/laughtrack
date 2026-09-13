package app.laughtrack.android

import app.laughtrack.android.core.network.generated.model.MeData
import app.laughtrack.android.core.network.generated.model.MeResponse
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class FirstEntryAuthChoiceTest {
    @Test
    fun `restoration keeps the loading surface visible`() {
        assertEquals(
            FirstEntryRootSurface.Loading,
            firstEntryRootSurface(
                session = StartupSessionState.Loading,
                hasResolvedFirstEntryChoice = false,
            ),
        )
    }

    @Test
    fun `restored signed-out first launch shows auth choice`() {
        assertEquals(
            FirstEntryRootSurface.AuthChoice,
            firstEntryRootSurface(
                session = StartupSessionState.SignedOut,
                hasResolvedFirstEntryChoice = false,
            ),
        )
    }

    @Test
    fun `guest choice persists and opens app shell`() {
        var persisted = false
        val store = FirstEntryAuthChoiceStore(initialResolved = false) { persisted = true }

        assertFalse(store.hasResolvedFirstEntryChoice)
        store.continueAsGuest()

        assertTrue(store.hasResolvedFirstEntryChoice)
        assertTrue(persisted)
        assertEquals(
            FirstEntryRootSurface.AppShell,
            firstEntryRootSurface(
                session = StartupSessionState.SignedOut,
                hasResolvedFirstEntryChoice = store.hasResolvedFirstEntryChoice,
            ),
        )
    }

    @Test
    fun `sign-in resolves first entry and later sign-out stays in shell`() {
        var persistCalls = 0
        val store = FirstEntryAuthChoiceStore(initialResolved = false) { persistCalls += 1 }

        store.markSignedIn()
        store.markSignedIn()

        assertEquals(1, persistCalls)
        assertEquals(
            FirstEntryRootSurface.AppShell,
            firstEntryRootSurface(
                session = StartupSessionState.SignedOut,
                hasResolvedFirstEntryChoice = store.hasResolvedFirstEntryChoice,
            ),
        )
    }

    @Test
    fun `previous first entry choice never bypasses unresolved or failed startup`() {
        assertEquals(
            FirstEntryRootSurface.Loading,
            firstEntryRootSurface(StartupSessionState.Loading, hasResolvedFirstEntryChoice = true),
        )
        assertEquals(
            FirstEntryRootSurface.Recovery,
            firstEntryRootSurface(StartupSessionState.Failure, hasResolvedFirstEntryChoice = true),
        )
    }

    @Test
    fun `incomplete onboarding precedes shell even after a previous first entry choice`() {
        assertEquals(
            FirstEntryRootSurface.Onboarding,
            firstEntryRootSurface(authenticated(completed = false), hasResolvedFirstEntryChoice = true),
        )
    }

    @Test
    fun `completed account opens shell without an auth choice`() {
        assertEquals(
            FirstEntryRootSurface.AppShell,
            firstEntryRootSurface(authenticated(completed = true), hasResolvedFirstEntryChoice = false),
        )
    }

    private fun authenticated(completed: Boolean) =
        StartupSessionState.Authenticated(
            MeResponse(
                MeData(
                    userId = "user-1",
                    email = "test@example.com",
                    isAdmin = false,
                    emailShowNotifications = false,
                    pushShowNotifications = false,
                    comedianOnboardingCompleted = completed,
                    zipCode = null,
                    nearbyDistanceMiles = null,
                ),
            ),
        )
}
