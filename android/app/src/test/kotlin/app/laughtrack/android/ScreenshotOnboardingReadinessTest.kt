package app.laughtrack.android

import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class ScreenshotOnboardingReadinessTest {
    @Test
    fun `loading onboarding is not ready`() {
        assertFalse(readiness(loadingPresent = true))
    }

    @Test
    fun `empty onboarding is not ready`() {
        assertFalse(readiness(emptyStatePresent = true))
    }

    @Test
    fun `populated fixture card and controls are ready`() {
        assertTrue(readiness())
    }

    private fun readiness(
        loadingPresent: Boolean = false,
        emptyStatePresent: Boolean = false,
    ): Boolean =
        isOnboardingScreenshotReady(
            fixtureNamePresent = true,
            fixturePortraitPresent = true,
            passControlPresent = true,
            followControlPresent = true,
            loadingPresent = loadingPresent,
            emptyStatePresent = emptyStatePresent,
        )
}
