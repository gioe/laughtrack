package app.laughtrack.android.core.analytics

import android.util.Log

/**
 * Logs analytics to logcat. Registered in debug builds so events are visible
 * without a Firebase project; mirrors the iOS ConsoleAnalyticsProvider. Uses
 * Log.d, which is stripped/ignored in release, so it is effectively silent there.
 */
class ConsoleAnalyticsProvider : AnalyticsProvider {
    override fun logEvent(event: AnalyticsEvent) {
        Log.d(TAG, "event=${event.name} params=${event.params}")
    }

    override fun setUserId(userId: String?) {
        Log.d(TAG, "setUserId=$userId")
    }

    override fun setUserProperty(
        name: String,
        value: String?,
    ) {
        Log.d(TAG, "setUserProperty $name=$value")
    }

    override fun reset() {
        Log.d(TAG, "reset")
    }

    private companion object {
        const val TAG = "Analytics"
    }
}
