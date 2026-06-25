package app.laughtrack.android.core.analytics

import android.os.Bundle
import com.google.firebase.analytics.FirebaseAnalytics

/**
 * Forwards events + identity to Firebase Analytics. Only instantiated when a
 * Firebase project is configured (a google-services.json was present at build
 * time) — see [AnalyticsModule].
 */
class FirebaseAnalyticsProvider(
    private val firebaseAnalytics: FirebaseAnalytics,
) : AnalyticsProvider {
    override fun logEvent(event: AnalyticsEvent) {
        firebaseAnalytics.logEvent(event.name, event.params.toBundle())
    }

    override fun setUserId(userId: String?) {
        firebaseAnalytics.setUserId(userId)
    }

    override fun setUserProperty(
        name: String,
        value: String?,
    ) {
        firebaseAnalytics.setUserProperty(name, value)
    }

    override fun reset() {
        firebaseAnalytics.resetAnalyticsData()
    }
}

/** Marshals primitive param values into a Firebase-compatible [Bundle]. */
internal fun Map<String, Any>.toBundle(): Bundle {
    val bundle = Bundle()
    forEach { (key, value) ->
        when (value) {
            is String -> bundle.putString(key, value)
            is Int -> bundle.putInt(key, value)
            is Long -> bundle.putLong(key, value)
            is Double -> bundle.putDouble(key, value)
            is Float -> bundle.putFloat(key, value)
            is Boolean -> bundle.putBoolean(key, value)
            else -> bundle.putString(key, value.toString())
        }
    }
    return bundle
}
