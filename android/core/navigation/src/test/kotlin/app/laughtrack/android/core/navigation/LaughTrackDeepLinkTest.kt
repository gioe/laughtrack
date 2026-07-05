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
        assertNull(LaughTrackDeepLink.route("https://laugh-track.com/show/1"))
        assertNull(LaughTrackDeepLink.route("laughtrack://show"))
        assertNull(LaughTrackDeepLink.route("laughtrack://show/not-a-number"))
        assertNull(LaughTrackDeepLink.route("laughtrack://widget/1"))
        assertNull(LaughTrackDeepLink.route("not a uri"))
        assertNull(LaughTrackDeepLink.route(null))
        assertNull(LaughTrackDeepLink.route(""))
    }

    @Test
    fun universal_link_form_is_intentionally_not_parsed() {
        // Only the custom laughtrack:// scheme is treated as a deep link; web
        // universal links (https://laugh-track.com/...) are handled elsewhere.
        assertNull(LaughTrackDeepLink.route("https://laugh-track.com/show/1"))
        assertNull(LaughTrackDeepLink.route("http://laugh-track.com/comedian/2"))
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
    fun push_payload_route_favorites_opens_favorites_tab() {
        assertEquals(
            AppRoute.Favorites,
            LaughTrackDeepLink.routeFromPush(mapOf("route" to "favorites")),
        )
    }

    @Test
    fun push_payload_route_wins_over_url_and_showId_fallback() {
        // Grouped pushes still carry a url + showId as the older-client fallback;
        // a present route must take precedence over both.
        assertEquals(
            AppRoute.Favorites,
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
