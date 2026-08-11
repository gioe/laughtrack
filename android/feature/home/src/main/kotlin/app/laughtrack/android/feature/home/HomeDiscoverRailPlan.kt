package app.laughtrack.android.feature.home

import app.laughtrack.android.core.analytics.AnalyticsEvent
import app.laughtrack.android.core.analytics.AnalyticsEvents
import app.laughtrack.android.core.navigation.AppRoute
import app.laughtrack.android.core.network.generated.model.ClubListItem
import app.laughtrack.android.core.network.generated.model.ComedianListItem
import app.laughtrack.android.core.network.generated.model.HomeFeed
import app.laughtrack.android.core.network.generated.model.HomeFeedDynamicRail
import app.laughtrack.android.core.network.generated.model.HomeFeedDynamicRailItem
import app.laughtrack.android.core.network.generated.model.HomeFeedPodcastEpisode
import app.laughtrack.android.core.network.generated.model.HomeFeedRailPlan
import app.laughtrack.android.core.network.generated.model.HomeFeedRailPlanEntry
import app.laughtrack.android.core.network.generated.model.Show

internal data class HomeDiscoverRailAttribution(
    val railKey: String,
    val policyVersion: Int,
    val rank: Int,
)

internal data class HomeDiscoverRailSection(
    val railKey: String,
    val policyVersion: Int,
    val content: Content,
) {
    val stableKey: String = "discover-rail-$railKey"

    fun attributionFor(route: AppRoute): HomeDiscoverRailAttribution =
        HomeDiscoverRailAttribution(
            railKey = railKey,
            policyVersion = policyVersion,
            rank = (itemIds().indexOf(route.entityId()) + 1).coerceAtLeast(1),
        )

    fun attributionForPodcastEpisode(episodeId: Int): HomeDiscoverRailAttribution =
        HomeDiscoverRailAttribution(
            railKey = railKey,
            policyVersion = policyVersion,
            rank = (itemIds().indexOf(episodeId) + 1).coerceAtLeast(1),
        )

    internal sealed interface Content {
        data class ShowsTonight(val shows: List<Show>) : Content

        data class FollowedComedianShows(val shows: List<Show>) : Content

        data class TrendingThisWeek(val shows: List<Show>) : Content

        data class TrendingComedians(val comedians: List<ComedianListItem>) : Content

        data class PopularClubs(val clubs: List<ClubListItem>) : Content

        data class PodcastEpisodes(val episodes: List<HomeFeedPodcastEpisode>) : Content

        data class NearbyShows(val shows: List<Show>) : Content

        data class DynamicShows(
            val label: String,
            val items: List<HomeFeedDynamicRailItem>,
        ) : Content
    }

    private fun itemIds(): List<Int> =
        when (val value = content) {
            is Content.ShowsTonight -> value.shows.map { it.id }
            is Content.FollowedComedianShows -> value.shows.map { it.id }
            is Content.TrendingThisWeek -> value.shows.map { it.id }
            is Content.TrendingComedians -> value.comedians.map { it.id }
            is Content.PopularClubs -> value.clubs.map { it.id }
            is Content.PodcastEpisodes -> value.episodes.map { it.id }
            is Content.NearbyShows -> value.shows.map { it.id }
            is Content.DynamicShows -> value.items.map { it.show.id }
        }
}

private fun AppRoute.entityId(): Int =
    when (this) {
        is AppRoute.ShowDetail -> id
        is AppRoute.ComedianDetail -> id
        is AppRoute.ClubDetail -> id
        is AppRoute.PodcastDetail -> id
        is AppRoute.PodcastEpisodeDetail -> id
        else -> -1
    }

/**
 * Resolves the server plan into native Android presentation data. A null result
 * tells HomeScreen to mount the established fixed rails unchanged.
 */
internal fun resolveHomeDiscoverRails(feed: HomeFeed?): List<HomeDiscoverRailSection>? {
    val plan = feed?.railPlan ?: return null
    if (plan.version != SUPPORTED_RAIL_PLAN_VERSION || plan.platform != HomeFeedRailPlan.Platform.ANDROID) {
        return null
    }

    val dynamicRails = feed.dynamicRails.orEmpty().associateBy { it.railKey }
    val seenRailKeys = mutableSetOf<String>()
    val sections =
        plan.rails
            .sortedWith(compareBy({ it.position }, { it.railKey }))
            .mapNotNull { entry ->
                val railKey = entry.railKey
                val payloadKey = entry.payloadKey
                if (!seenRailKeys.add(railKey)) return@mapNotNull null
                val content = resolveContent(entry, railKey, payloadKey, feed, dynamicRails)
                content?.let {
                    HomeDiscoverRailSection(
                        railKey = railKey,
                        policyVersion = plan.policyVersion,
                        content = it,
                    )
                }
            }

    return sections.takeIf { it.isNotEmpty() }
}

private fun resolveContent(
    entry: HomeFeedRailPlanEntry,
    railKey: String,
    payloadKey: String,
    feed: HomeFeed,
    dynamicRails: Map<String, HomeFeedDynamicRail>,
): HomeDiscoverRailSection.Content? =
    when (railKey to payloadKey) {
        SHOWS_TONIGHT to PAYLOAD_SHOWS_TONIGHT ->
            select(entry.itemIds, feed.showsTonight) { it.id.toString() }
                .ifNotEmpty(HomeDiscoverRailSection.Content::ShowsTonight)
        FOLLOWED_COMEDIAN_SHOWS to PAYLOAD_FOLLOWED_SHOWS ->
            select(entry.itemIds, feed.followedComedianShows) { it.id.toString() }
                .take(HOME_DISCOVER_RAIL_ITEM_LIMIT)
                .ifNotEmpty(HomeDiscoverRailSection.Content::FollowedComedianShows)
        TRENDING_THIS_WEEK to PAYLOAD_TRENDING_THIS_WEEK ->
            select(entry.itemIds, feed.trendingThisWeek) { it.id.toString() }
                .take(HOME_DISCOVER_RAIL_ITEM_LIMIT)
                .ifNotEmpty(HomeDiscoverRailSection.Content::TrendingThisWeek)
        TRENDING_COMEDIANS to PAYLOAD_TRENDING_COMEDIANS ->
            select(entry.itemIds, feed.trendingComedians) { it.id.toString() }
                .ifNotEmpty(HomeDiscoverRailSection.Content::TrendingComedians)
        POPULAR_CLUBS to PAYLOAD_POPULAR_CLUBS ->
            select(entry.itemIds, feed.popularClubs) { it.id.toString() }
                .ifNotEmpty(HomeDiscoverRailSection.Content::PopularClubs)
        TRENDING_PODCASTS to PAYLOAD_PODCAST_EPISODES ->
            select(entry.itemIds, feed.podcastEpisodes.orEmpty()) { it.id.toString() }
                .take(HOME_DISCOVER_RAIL_ITEM_LIMIT)
                .ifNotEmpty(HomeDiscoverRailSection.Content::PodcastEpisodes)
        NEARBY_SHOWS to PAYLOAD_MORE_NEAR_YOU ->
            select(entry.itemIds, feed.moreNearYou) { it.id.toString() }
                .ifNotEmpty(HomeDiscoverRailSection.Content::NearbyShows)
        else -> resolveDynamicContent(entry, railKey, payloadKey, dynamicRails)
    }

private fun resolveDynamicContent(
    entry: HomeFeedRailPlanEntry,
    railKey: String,
    payloadKey: String,
    dynamicRails: Map<String, HomeFeedDynamicRail>,
): HomeDiscoverRailSection.Content.DynamicShows? {
    if (payloadKey != PAYLOAD_DYNAMIC_RAILS || railKey !in DYNAMIC_RAIL_KEYS) return null
    val rail = dynamicRails[railKey] ?: return null
    val items =
        select(entry.itemIds, rail.items) { it.id.toString() }
            .let { selected ->
                if (isTodayStyleDynamicShowRail(railKey)) selected.take(HOME_DISCOVER_RAIL_ITEM_LIMIT) else selected
            }
    return items
        .ifNotEmpty { HomeDiscoverRailSection.Content.DynamicShows(rail.label, it) }
}

internal fun homeDiscoverRailSelectedEvent(attribution: HomeDiscoverRailAttribution): AnalyticsEvent =
    AnalyticsEvent(
        name = AnalyticsEvents.Discover.RAIL_SELECTED,
        params =
            mapOf(
                AnalyticsEvents.Discover.Param.RAIL_KEY to attribution.railKey,
                AnalyticsEvents.Discover.Param.POLICY_VERSION to attribution.policyVersion,
                AnalyticsEvents.Discover.Param.RANK to attribution.rank,
            ),
    )

internal fun preferredDynamicRailHeadlinerId(
    railKey: String,
    item: HomeFeedDynamicRailItem,
): Int? = item.performer?.id.takeIf { isTodayStyleDynamicShowRail(railKey) }

internal fun preferredFavoriteHeadlinerId(show: Show): Int? =
    show.lineup.orEmpty().firstOrNull { it.isFavorite == true }?.id

internal fun isTodayStyleDynamicShowRail(railKey: String): Boolean = railKey in DYNAMIC_RAIL_KEYS

private fun <T> select(
    itemIds: List<String>,
    values: List<T>,
    id: (T) -> String,
): List<T> {
    val valuesById = values.associateBy(id)
    return itemIds.mapNotNull(valuesById::get)
}

private fun <T, R> List<T>.ifNotEmpty(transform: (List<T>) -> R): R? = takeIf { it.isNotEmpty() }?.let(transform)

internal const val HOME_DISCOVER_RAIL_ITEM_LIMIT = 5

private const val SUPPORTED_RAIL_PLAN_VERSION = 1
private const val SHOWS_TONIGHT = "shows_tonight"
private const val FOLLOWED_COMEDIAN_SHOWS = "followed_comedian_shows"
private const val TRENDING_THIS_WEEK = "trending_this_week"
private const val TRENDING_COMEDIANS = "trending_comedians"
private const val POPULAR_CLUBS = "popular_clubs"
private const val TRENDING_PODCASTS = "trending_podcasts"
private const val NEARBY_SHOWS = "nearby_shows"

private const val PAYLOAD_SHOWS_TONIGHT = "showsTonight"
private const val PAYLOAD_FOLLOWED_SHOWS = "followedComedianShows"
private const val PAYLOAD_TRENDING_THIS_WEEK = "trendingThisWeek"
private const val PAYLOAD_TRENDING_COMEDIANS = "trendingComedians"
private const val PAYLOAD_POPULAR_CLUBS = "popularClubs"
private const val PAYLOAD_PODCAST_EPISODES = "podcastEpisodes"
private const val PAYLOAD_MORE_NEAR_YOU = "moreNearYou"
private const val PAYLOAD_DYNAMIC_RAILS = "dynamicRails"

private val DYNAMIC_RAIL_KEYS =
    setOf(
        "just_passing_through",
        "starting_to_buzz",
        "from_your_podcasts",
    )
