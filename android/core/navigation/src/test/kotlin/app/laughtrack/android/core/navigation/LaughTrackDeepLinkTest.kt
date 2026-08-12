package app.laughtrack.android.core.navigation

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

class LaughTrackDeepLinkTest {
    @Test
    fun parses_each_entity_host_singular_and_plural() {
        assertEquals(AppRoute.ShowDetail(123), LaughTrackDeepLink.route("laughtrack://show/123"))
        assertEquals(AppRoute.ShowDetail(123), LaughTrackDeepLink.route("laughtrack://shows/123"))
        assertEquals(AppRoute.ComedianDetail(45), LaughTrackDeepLink.route("laughtrack://comedian/45"))
        assertEquals(AppRoute.ClubDetail(7), LaughTrackDeepLink.route("laughtrack://clubs/7"))
        assertEquals(AppRoute.PodcastDetail(9), LaughTrackDeepLink.route("laughtrack://podcast/9"))
    }

    @Test
    fun scheme_is_case_insensitive() {
        assertEquals(AppRoute.ShowDetail(1), LaughTrackDeepLink.route("LaughTrack://show/1"))
    }

    @Test
    fun rejects_wrong_scheme_missing_id_unknown_entity_and_garbage() {
        assertNull(LaughTrackDeepLink.route("mailto:hi@laugh-track.com"))
        assertNull(LaughTrackDeepLink.route("laughtrack://show"))
        assertNull(LaughTrackDeepLink.route("laughtrack://show/not-a-number"))
        assertNull(LaughTrackDeepLink.route("laughtrack://widget/1"))
        assertNull(LaughTrackDeepLink.route("not a uri"))
        assertNull(LaughTrackDeepLink.route(null))
        assertNull(LaughTrackDeepLink.route(""))
    }

    @Test
    fun parses_https_app_links_on_the_web_host() {
        // /show/[id] is numeric on web and resolves end-to-end.
        assertEquals(AppRoute.ShowDetail(1), LaughTrackDeepLink.route("https://laugh-track.com/show/1"))
        assertEquals(AppRoute.ShowDetail(2), LaughTrackDeepLink.route("https://www.laugh-track.com/show/2"))
        assertEquals(AppRoute.ShowDetail(3), LaughTrackDeepLink.route("http://laugh-track.com/shows/3"))
        // Any entity with a numeric path segment routes symmetrically with the scheme.
        assertEquals(AppRoute.ComedianDetail(9), LaughTrackDeepLink.route("https://www.laugh-track.com/comedian/9"))
    }

    @Test
    fun rejects_http_links_off_host_or_with_non_numeric_slug() {
        // Non-LaughTrack hosts are never App Links.
        assertNull(LaughTrackDeepLink.route("https://evil.com/show/1"))
        // Web comedian/club/podcast pages use name/slug URLs, which cannot map to
        // an id-based route, so they stay browser-first (route returns null).
        assertNull(LaughTrackDeepLink.route("https://www.laugh-track.com/comedian/dave-chappelle"))
        assertNull(LaughTrackDeepLink.route("https://www.laugh-track.com/podcast/some-slug"))
        // A bare host or unknown entity is not a detail link.
        assertNull(LaughTrackDeepLink.route("https://laugh-track.com/"))
        assertNull(LaughTrackDeepLink.route("https://laugh-track.com/widget/1"))
    }

    @Test
    fun push_payload_prefers_url_then_falls_back_to_showId() {
        assertEquals(
            AppRoute.ComedianDetail(8),
            LaughTrackDeepLink.routeFromPush(mapOf("url" to "laughtrack://comedian/8", "showId" to "99")),
        )
        assertEquals(
            AppRoute.ShowDetail(42),
            LaughTrackDeepLink.routeFromPush(mapOf("showId" to "42")),
        )
        assertNull(LaughTrackDeepLink.routeFromPush(emptyMap()))
    }

    @Test
    fun push_payload_route_favorites_opens_notification_center() {
        assertEquals(
            AppRoute.NotificationCenter,
            LaughTrackDeepLink.routeFromPush(mapOf("route" to "favorites")),
        )
    }

    @Test
    fun push_payload_favorites_show_ids_still_open_notification_center() {
        assertEquals(
            AppRoute.NotificationCenter,
            LaughTrackDeepLink.routeFromPush(
                mapOf("route" to "favorites", "showIds" to "555,777"),
            ),
        )
    }

    @Test
    fun push_payload_route_wins_over_url_and_showId_fallback() {
        // Grouped pushes still carry a url + showId as the older-client fallback;
        // a present route must take precedence over both.
        assertEquals(
            AppRoute.NotificationCenter,
            LaughTrackDeepLink.routeFromPush(
                mapOf("route" to "favorites", "url" to "laughtrack://show/42", "showId" to "42"),
            ),
        )
    }

    @Test
    fun push_payload_with_invalid_url_falls_back_to_showId() {
        // A present-but-unparseable url must not short-circuit the numeric showId.
        assertEquals(
            AppRoute.ShowDetail(7),
            LaughTrackDeepLink.routeFromPush(mapOf("url" to "not-a-deep-link", "showId" to "7")),
        )
    }
}
