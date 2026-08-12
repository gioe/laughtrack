package app.laughtrack.android.core.navigation

import java.net.URI

/**
 * Parses `laughtrack://` deep links, `https://` App Links, and push-notification
 * payloads into typed [AppRoute]s. Pure (java.net.URI — no `android.net.Uri`) so
 * it unit-tests on the JVM. Mirrors the iOS deep-link + universal-link handling:
 *  - a custom-scheme URL `laughtrack://<entity>/<id>` maps to the matching detail
 *    route (entity in the host, id in the path),
 *  - an http(s) LaughTrack web URL `https://www.laugh-track.com/<entity>/<id>`
 *    maps the same way (entity + id in the path) when the id is numeric, and
 *  - a push payload carrying a `url` deep link or a numeric `showId` maps to a
 *    route.
 *
 * Only numeric detail ids resolve. Web comedian/club/podcast pages use
 * name/slug URLs (`/comedian/[name]`), which cannot map to the id-based routes,
 * so those links stay browser-first — matching iOS, whose App Links register
 * `/show` only. `/show/[id]` is numeric on web and resolves end-to-end.
 */
object LaughTrackDeepLink {
    const val SCHEME = "laughtrack"

    /** Web hosts whose http(s) URLs are treated as App Links. */
    private val WEB_HOSTS = setOf("laugh-track.com", "www.laugh-track.com")

    /** Map a deep-link / App Link URI string to a detail route, or null if it isn't one. */
    fun route(uri: String?): AppRoute? {
        if (uri.isNullOrBlank()) return null
        val parsed = runCatching { URI(uri) }.getOrNull() ?: return null
        val entityAndId =
            when (parsed.scheme?.lowercase()) {
                SCHEME -> parseSchemeLink(parsed)
                "http", "https" -> parseWebLink(parsed)
                else -> null
            } ?: return null
        return detailRoute(entityAndId.first, entityAndId.second)
    }

    /** Custom scheme `laughtrack://<entity>/<id>`: entity in the host, id as the first path segment. */
    private fun parseSchemeLink(uri: URI): Pair<String, Int>? {
        val host = (uri.host ?: uri.authority)?.lowercase() ?: return null
        val id = uri.path?.trim('/')?.substringBefore('/')?.toIntOrNull() ?: return null
        return host to id
    }

    /** Web App Link `https://<web-host>/<entity>/<id>`: entity + numeric id are the first two path segments. */
    private fun parseWebLink(uri: URI): Pair<String, Int>? {
        if (uri.host?.lowercase() !in WEB_HOSTS) return null
        val segments = uri.path?.split('/')?.filter { it.isNotBlank() } ?: return null
        val entity = segments.getOrNull(0)?.lowercase() ?: return null
        val id = segments.getOrNull(1)?.toIntOrNull() ?: return null
        return entity to id
    }

    private fun detailRoute(
        entity: String,
        id: Int,
    ): AppRoute? =
        when (entity) {
            "show", "shows" -> AppRoute.ShowDetail(id)
            "comedian", "comedians" -> AppRoute.ComedianDetail(id)
            "club", "clubs" -> AppRoute.ClubDetail(id)
            "podcast", "podcasts" -> AppRoute.PodcastDetail(id)
            else -> null
        }

    /**
     * Resolve a route from an FCM data payload (delivered as a string map).
     * Prefers an explicit `url` deep link, then falls back to a numeric `showId`
     * (the comedian-arrival push shape). Returns null when neither is present.
     */
    fun routeFromPush(data: Map<String, String?>): AppRoute? {
        // Grouped-push tap → Notification Center. Checked before url/showId,
        // which grouped pushes still carry
        // as the fallback for older builds that predate this key.
        if (data["route"]?.trim() == "favorites") {
            return AppRoute.NotificationCenter
        }
        route(data["url"])?.let { return it }
        data["showId"]?.toIntOrNull()?.let { return AppRoute.ShowDetail(it) }
        return null
    }
}
