package app.laughtrack.android.core.analytics

/**
 * A sink for analytics events + user identity, mirroring the iOS AnalyticsProvider
 * protocol (FirebaseAnalyticsProvider / ConsoleAnalyticsProvider). [AnalyticsManager]
 * fans every call out to the registered providers.
 */
interface AnalyticsProvider {
    fun logEvent(event: AnalyticsEvent)

    fun setUserId(userId: String?)

    fun setUserProperty(name: String, value: String?)

    /** Clears the analytics identity (sign-out). */
    fun reset()
}
