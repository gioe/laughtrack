package app.laughtrack.android.core.analytics

import javax.inject.Inject
import javax.inject.Singleton

/**
 * Fans analytics out to every registered [AnalyticsProvider] (Firebase when a
 * Firebase project is configured, plus a console provider in debug), mirroring the
 * iOS multi-provider AnalyticsManager. With no providers it is a silent no-op, so
 * call sites never need to null-check.
 */
@Singleton
class AnalyticsManager @Inject constructor(
    private val providers: List<@JvmSuppressWildcards AnalyticsProvider>,
) {
    fun logEvent(event: AnalyticsEvent) {
        providers.forEach { it.logEvent(event) }
    }

    fun logEvent(name: String, params: Map<String, Any> = emptyMap()) {
        logEvent(AnalyticsEvent(name, params))
    }

    /**
     * Set the analytics identity from a signed-in user: the server-issued userId
     * (preferred over any email-hash fallback per the iOS userId rollout) plus the
     * cross-client cohort properties.
     */
    fun identify(userId: String?, onboardingCompleted: Boolean, hasZip: Boolean) {
        providers.forEach { provider ->
            provider.setUserId(userId)
            provider.setUserProperty(
                AnalyticsUserProperties.COMEDIAN_ONBOARDING_COMPLETED,
                onboardingCompleted.toString(),
            )
            provider.setUserProperty(AnalyticsUserProperties.HAS_ZIP, hasZip.toString())
        }
    }

    /** Clear identity + accumulated state on sign-out. */
    fun reset() {
        providers.forEach { it.reset() }
    }
}
