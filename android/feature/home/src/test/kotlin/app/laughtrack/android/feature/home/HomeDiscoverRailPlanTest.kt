package app.laughtrack.android.feature.home

import app.laughtrack.android.core.navigation.AppRoute
import app.laughtrack.android.core.network.generated.model.HomeFeed
import app.laughtrack.android.core.network.generated.model.HomeFeedDynamicRail
import app.laughtrack.android.core.network.generated.model.HomeFeedDynamicRailItem
import app.laughtrack.android.core.network.generated.model.HomeFeedDynamicRailPerformer
import app.laughtrack.android.core.network.generated.model.HomeFeedDynamicRailReason
import app.laughtrack.android.core.network.generated.model.HomeFeedDynamicRailReasonEvidence
import app.laughtrack.android.core.network.generated.model.HomeFeedHero
import app.laughtrack.android.core.network.generated.model.HomeFeedRailPlan
import app.laughtrack.android.core.network.generated.model.HomeFeedRailPlanEntry
import app.laughtrack.android.core.network.generated.model.Show
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class HomeDiscoverRailPlanTest {
    @Test
    fun resolves_server_order_and_exact_item_id_order() {
        val feed =
            feed(
                showsTonight = listOf(show(1), show(2)),
                trendingThisWeek = listOf(show(3), show(4)),
                rails =
                    listOf(
                        entry("shows_tonight", "showsTonight", position = 2, itemIds = listOf("2", "1")),
                        entry("trending_this_week", "trendingThisWeek", position = 1, itemIds = listOf("4", "3")),
                    ),
            )

        val sections = resolveHomeDiscoverRails(feed)!!

        assertEquals(listOf("trending_this_week", "shows_tonight"), sections.map { it.railKey })
        assertEquals(
            listOf(4, 3),
            (sections[0].content as HomeDiscoverRailSection.Content.TrendingThisWeek).shows.map { it.id },
        )
        assertEquals(1, sections[0].attributionFor(AppRoute.ShowDetail(4)).rank)
        assertEquals(2, sections[0].attributionFor(AppRoute.ShowDetail(3)).rank)
        assertEquals(
            listOf(2, 1),
            (sections[1].content as HomeDiscoverRailSection.Content.ShowsTonight).shows.map { it.id },
        )
    }

    @Test
    fun limits_best_shows_this_week_to_five_shows() {
        val shows = (1..7).map(::show)
        val sections =
            resolveHomeDiscoverRails(
                feed(
                    trendingThisWeek = shows,
                    rails =
                        listOf(
                            entry(
                                "trending_this_week",
                                "trendingThisWeek",
                                position = 0,
                                itemIds = shows.map { it.id.toString() },
                            ),
                        ),
                ),
            )!!

        val content = sections.single().content as HomeDiscoverRailSection.Content.TrendingThisWeek
        assertEquals(listOf(1, 2, 3, 4, 5), content.shows.map { it.id })
    }

    @Test
    fun skips_unknown_empty_and_duplicate_rails_but_keeps_accessible_dynamic_reason() {
        val dynamicItem =
            HomeFeedDynamicRailItem(
                id = 91,
                show = show(9),
                reason =
                    HomeFeedDynamicRailReason(
                        kind = "starting_to_buzz",
                        label = "Momentum is rising near you",
                        evidence = HomeFeedDynamicRailReasonEvidence(),
                    ),
            )
        val feed =
            feed(
                rails =
                    listOf(
                        entry("future_rail", "futurePayload", 0, listOf("1")),
                        entry("shows_tonight", "showsTonight", 1, listOf("missing")),
                        entry("starting_to_buzz", "dynamicRails", 2, listOf("91")),
                        entry("starting_to_buzz", "dynamicRails", 3, listOf("91")),
                    ),
                dynamicRails =
                    listOf(
                        HomeFeedDynamicRail(
                            railKey = "starting_to_buzz",
                            label = "Starting to buzz",
                            items = listOf(dynamicItem),
                        ),
                    ),
            )

        val sections = resolveHomeDiscoverRails(feed)!!
        val content = sections.single().content as HomeDiscoverRailSection.Content.DynamicShows

        assertEquals("discover-rail-starting_to_buzz", sections.single().stableKey)
        assertEquals("Momentum is rising near you", content.items.single().reason.label)
        assertEquals(
            "Show 9. Momentum is rising near you",
            homeDiscoverDynamicShowContentDescription(content.items.single().show, content.items.single().reason.label),
        )
    }

    @Test
    fun stable_keys_do_not_change_when_policy_order_changes() {
        val first =
            resolveHomeDiscoverRails(
                feed(
                    showsTonight = listOf(show(1)),
                    trendingThisWeek = listOf(show(2)),
                    rails =
                        listOf(
                            entry("shows_tonight", "showsTonight", 0, listOf("1")),
                            entry("trending_this_week", "trendingThisWeek", 1, listOf("2")),
                        ),
                ),
            )!!
        val reordered =
            resolveHomeDiscoverRails(
                feed(
                    showsTonight = listOf(show(1)),
                    trendingThisWeek = listOf(show(2)),
                    rails =
                        listOf(
                            entry("shows_tonight", "showsTonight", 2, listOf("1")),
                            entry("trending_this_week", "trendingThisWeek", 0, listOf("2")),
                        ),
                ),
            )!!

        assertEquals(first.map { it.stableKey }.toSet(), reordered.map { it.stableKey }.toSet())
    }

    @Test
    fun just_passing_through_features_its_associated_comedian() {
        val item =
            HomeFeedDynamicRailItem(
                id = 91,
                show = show(9),
                performer = HomeFeedDynamicRailPerformer(id = 81, uuid = "avery-stone", name = "Avery Stone"),
                reason =
                    HomeFeedDynamicRailReason(
                        kind = "just_passing_through",
                        label = "Avery is visiting",
                        evidence = HomeFeedDynamicRailReasonEvidence(),
                    ),
            )

        assertEquals(81, preferredDynamicRailHeadlinerId("just_passing_through", item))
        assertNull(preferredDynamicRailHeadlinerId("rare_returns", item))
    }

    @Test
    fun limits_just_passing_through_to_five_shows() {
        val items =
            (1..7).map { id ->
                HomeFeedDynamicRailItem(
                    id = id,
                    show = show(id),
                    reason =
                        HomeFeedDynamicRailReason(
                            kind = "just_passing_through",
                            label = "Comic $id is visiting",
                            evidence = HomeFeedDynamicRailReasonEvidence(),
                        ),
                )
            }
        val sections =
            resolveHomeDiscoverRails(
                feed(
                    rails = listOf(entry("just_passing_through", "dynamicRails", 0, items.map { it.id.toString() })),
                    dynamicRails =
                        listOf(
                            HomeFeedDynamicRail(
                                railKey = "just_passing_through",
                                label = "Just passing through",
                                items = items,
                            ),
                        ),
                ),
            )!!

        val content = sections.single().content as HomeDiscoverRailSection.Content.DynamicShows
        assertEquals(listOf(1, 2, 3, 4, 5), content.items.map { it.id })
    }

    @Test
    fun removed_stacked_lineups_rail_is_ignored() {
        val item =
            HomeFeedDynamicRailItem(
                id = 91,
                show = show(9),
                reason =
                    HomeFeedDynamicRailReason(
                        kind = "stacked_lineup",
                        label = "Three comedians",
                        evidence = HomeFeedDynamicRailReasonEvidence(),
                    ),
            )
        val result =
            resolveHomeDiscoverRails(
                feed(
                    rails = listOf(entry("stacked_lineups", "dynamicRails", 0, listOf("91"))),
                    dynamicRails =
                        listOf(
                            HomeFeedDynamicRail(
                                railKey = "stacked_lineups",
                                label = "Stacked lineups",
                                items = listOf(item),
                            ),
                        ),
                ),
            )

        assertNull(result)
    }

    @Test
    fun missing_incompatible_or_empty_plan_uses_legacy_fallback() {
        assertNull(resolveHomeDiscoverRails(feed(railPlan = null)))
        assertNull(
            resolveHomeDiscoverRails(
                feed(
                    railPlan =
                        plan(
                            rails = listOf(entry("shows_tonight", "showsTonight", 0, listOf("1"))),
                            platform = HomeFeedRailPlan.Platform.IOS,
                        ),
                ),
            ),
        )
        assertNull(resolveHomeDiscoverRails(feed(rails = emptyList())))
        assertTrue(resolveHomeDiscoverRails(feed(rails = listOf(entry("future", "future", 0, emptyList())))) == null)
    }

    private fun feed(
        showsTonight: List<Show> = emptyList(),
        trendingThisWeek: List<Show> = emptyList(),
        dynamicRails: List<HomeFeedDynamicRail>? = null,
        rails: List<HomeFeedRailPlanEntry> = emptyList(),
        railPlan: HomeFeedRailPlan? = plan(rails),
    ): HomeFeed =
        HomeFeed(
            hero = HomeFeedHero(shows = emptyList()),
            trendingComedians = emptyList(),
            comediansNearYou = emptyList(),
            showsTonight = showsTonight,
            moreNearYou = emptyList(),
            trendingThisWeek = trendingThisWeek,
            followedComedianShows = emptyList(),
            trendingPodcasts = emptyList(),
            popularClubs = emptyList(),
            dynamicRails = dynamicRails,
            railPlan = railPlan,
        )

    private fun plan(
        rails: List<HomeFeedRailPlanEntry>,
        platform: HomeFeedRailPlan.Platform = HomeFeedRailPlan.Platform.ANDROID,
    ) = HomeFeedRailPlan(
        version = 1,
        catalogVersion = 1,
        policyVersion = 7,
        platform = platform,
        cycleIndex = 0,
        rails = rails,
    )

    private fun entry(
        railKey: String,
        payloadKey: String,
        position: Int,
        itemIds: List<String>,
    ) = HomeFeedRailPlanEntry(
        railKey = railKey,
        payloadKey = payloadKey,
        position = position,
        itemIds = itemIds,
    )

    private fun show(id: Int) =
        Show(
            id = id,
            clubId = 10,
            date = "2026-08-07T20:00:00-04:00",
            imageUrl = "",
            name = "Show $id",
        )
}
