package app.laughtrack.android

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
                sessionRestoreCompleted = false,
                signedIn = false,
                hasResolvedFirstEntryChoice = false,
            ),
        )
    }

    @Test
    fun `restored signed-out first launch shows auth choice`() {
        assertEquals(
            FirstEntryRootSurface.AuthChoice,
            firstEntryRootSurface(
                sessionRestoreCompleted = true,
                signedIn = false,
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
                sessionRestoreCompleted = true,
                signedIn = false,
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
                sessionRestoreCompleted = true,
                signedIn = false,
                hasResolvedFirstEntryChoice = store.hasResolvedFirstEntryChoice,
            ),
        )
    }
}
