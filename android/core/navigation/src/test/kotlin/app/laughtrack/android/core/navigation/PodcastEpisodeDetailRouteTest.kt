package app.laughtrack.android.core.navigation

import kotlinx.serialization.json.Json
import org.junit.Assert.assertEquals
import org.junit.Test

class PodcastEpisodeDetailRouteTest {
    @Test
    fun podcast_episode_detail_route_round_trips_with_episode_id() {
        val route = AppRoute.PodcastEpisodeDetail(id = 501)
        val encoded = Json.encodeToString(AppRoute.PodcastEpisodeDetail.serializer(), route)

        assertEquals(
            route,
            Json.decodeFromString(AppRoute.PodcastEpisodeDetail.serializer(), encoded),
        )
    }

    @Test
    fun podcast_episode_detail_routes_participate_in_stack_dedup_by_id() {
        val route = AppRoute.PodcastEpisodeDetail(id = 501)
        val stack = listOf<AppRoute>(AppRoute.PodcastDetail(42), route, AppRoute.ComedianDetail(7))

        assertEquals(
            listOf(AppRoute.PodcastDetail(42), route),
            NavStackDedup.navigate(stack, route),
        )
        assertEquals(
            stack + AppRoute.PodcastEpisodeDetail(502),
            NavStackDedup.navigate(stack, AppRoute.PodcastEpisodeDetail(502)),
        )
    }
}
