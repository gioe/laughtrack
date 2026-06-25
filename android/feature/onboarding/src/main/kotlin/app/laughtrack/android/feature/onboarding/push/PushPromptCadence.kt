package app.laughtrack.android.feature.onboarding.push

import java.time.Duration
import java.time.Instant

object PushPromptCadence {
    data class Input(
        val now: Instant,
        val deferralCount: Int,
        val lastDeferredAt: Instant?,
        val engagementCount: Int,
        val hasPresentedThisSession: Boolean = false,
    )

    enum class Decision {
        Eligible,
        SuppressedAlreadyPresented,
        SuppressedMaxDeferrals,
        SuppressedInsufficientEngagement,
        SuppressedBackoff,
    }

    const val REQUIRED_ENGAGEMENT_COUNT = 3
    const val MAX_DEFERRALS = 3
    private val BackoffDays = listOf(0L, 3L, 14L)

    fun evaluate(input: Input): Decision {
        if (input.hasPresentedThisSession) return Decision.SuppressedAlreadyPresented
        if (input.deferralCount >= MAX_DEFERRALS) return Decision.SuppressedMaxDeferrals
        if (input.engagementCount < REQUIRED_ENGAGEMENT_COUNT) return Decision.SuppressedInsufficientEngagement
        if (input.deferralCount > 0) {
            val lastDeferredAt = input.lastDeferredAt ?: return Decision.Eligible
            val backoffIndex = input.deferralCount.coerceAtMost(BackoffDays.lastIndex)
            val minimumDays = BackoffDays[backoffIndex]
            if (minimumDays > 0 && Duration.between(lastDeferredAt, input.now).toDays() < minimumDays) {
                return Decision.SuppressedBackoff
            }
        }
        return Decision.Eligible
    }
}
