package app.laughtrack.android.core.navigation

import java.net.URI

/**
 * Parses `laughtrack://` deep links and push-notification payloads into typed
 * [AppRoute]s. Pure (java.net.URI — no `android.net.Uri`) so it unit-tests on the
 * JVM. Mirrors the iOS LaughTrackNotificationDeepLink: a custom-scheme URL
 * `laughtrack://<entity>/<id>` maps to the matching detail route, and a push data
 * payload carrying a `url` deep link or a numeric `showId` maps to a route.
 */
object LaughTrackDeepLink {
    const val SCHEME = "laughtrack"

    /** Map a deep-link URI string to a detail route, or null if it isn't one. */
    fun route(uri: String?): AppRoute? {
        if (uri.isNullOrBlank()) return null
        val parsed = runCatching { URI(uri) }.getOrNull() ?: return null
        if (!parsed.scheme.equals(SCHEME, ignoreCase = true)) return null
        val host = (parsed.host ?: parsed.authority)?.lowercase() ?: return null
        val id = parsed.path?.trim('/')?.substringBefore('/')?.toIntOrNull() ?: return null
        return when (host) {
            "show", "shows" -> AppRoute.ShowDetail(id)
            "comedian", "comedians" -> AppRoute.ComedianDetail(id)
            "club", "clubs" -> AppRoute.ClubDetail(id)
            "podcast", "podcasts" -> AppRoute.PodcastDetail(id)
            else -> null
        }
    }

    /**
     * Resolve a route from an FCM data payload (delivered as a string map).
     * Prefers an explicit `url` deep link, then falls back to a numeric `showId`
     * (the comedian-arrival push shape). Returns null when neither is present.
     */
    fun routeFromPush(data: Map<String, String?>): AppRoute? {
        route(data["url"])?.let { return it }
        data["showId"]?.toIntOrNull()?.let { return AppRoute.ShowDetail(it) }
        return null
    }
}
