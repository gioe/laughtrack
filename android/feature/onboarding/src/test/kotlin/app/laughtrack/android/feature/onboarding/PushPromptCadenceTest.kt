package app.laughtrack.android.feature.onboarding

import app.laughtrack.android.feature.onboarding.push.PushPromptCadence
import java.time.Instant
import org.junit.Assert.assertEquals
import org.junit.Test

class PushPromptCadenceTest {
    @Test
    fun becomes_eligible_after_three_engagement_signals() {
        val decision = PushPromptCadence.evaluate(
            PushPromptCadence.Input(
                now = Instant.parse("2026-06-24T12:00:00Z"),
                deferralCount = 0,
                lastDeferredAt = null,
                engagementCount = 3,
            ),
        )

        assertEquals(PushPromptCadence.Decision.Eligible, decision)
    }

    @Test
    fun tracks_deferral_backoff_before_reprompting() {
        val decision = PushPromptCadence.evaluate(
            PushPromptCadence.Input(
                now = Instant.parse("2026-06-25T12:00:00Z"),
                deferralCount = 1,
                lastDeferredAt = Instant.parse("2026-06-24T12:00:00Z"),
                engagementCount = 3,
            ),
        )

        assertEquals(PushPromptCadence.Decision.SuppressedBackoff, decision)
    }
}
