package app.laughtrack.android.feature.home

import app.laughtrack.android.core.navigation.SearchDestination
import app.laughtrack.android.core.network.generated.model.HomeFeed
import app.laughtrack.android.core.network.generated.model.HomeFeedHero
import app.laughtrack.android.core.network.generated.model.Show
import app.laughtrack.android.core.ui.UiState
import app.laughtrack.android.feature.home.ui.HomeUiState
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test
import java.nio.file.Files
import java.nio.file.Path
import java.nio.file.Paths
import java.time.LocalDate

class HomeDiscoverSearchTest {
    private val today = LocalDate.of(2026, 8, 4)
    private val state = HomeUiState(feed = UiState.Success(feed()))

    @Test
    fun discovery_ideas_expose_four_distinct_property_searches_with_location() {
        val ideas = homeDiscoveryIdeas(state, today)

        assertEquals(listOf("Tonight", "This weekend", "Free shows", "Open mics"), ideas.map { it.title })
        assertEquals("2026-08-04" to "2026-08-04", ideas[0].request.from to ideas[0].request.to)
        assertEquals("2026-08-07" to "2026-08-09", ideas[1].request.from to ideas[1].request.to)
        assertEquals(setOf("free"), ideas[2].request.filters)
        assertEquals(setOf("open_mic"), ideas[3].request.filters)
        assertTrue(ideas.all { it.request.destination == SearchDestination.SHOWS })
        assertTrue(ideas.all { it.request.zip == "10001" && it.request.distanceMiles == 25 })
    }

    @Test
    fun every_expandable_rail_has_the_applicable_search_constraints() {
        val requests = HomeExpandableRail.entries.associateWith { homeRailSearchRequest(it, state, today) }

        assertEquals("2026-08-04", requests.getValue(HomeExpandableRail.TONIGHT).from)
        assertEquals("2026-08-11", requests.getValue(HomeExpandableRail.BEST_THIS_WEEK).to)
        assertEquals(SearchDestination.COMEDIANS, requests.getValue(HomeExpandableRail.COMEDIANS).destination)
        assertEquals(SearchDestination.CLUBS, requests.getValue(HomeExpandableRail.CLUBS).destination)
        assertEquals("10001", requests.getValue(HomeExpandableRail.CLUBS).zip)
        assertEquals(SearchDestination.PODCASTS, requests.getValue(HomeExpandableRail.PODCASTS).destination)
    }

    @Test
    fun followed_section_is_conditional_and_deliberately_not_expandable() {
        val source = String(Files.readAllBytes(homeScreenPath()))

        assertTrue(source.contains("if (state.followedComedianShows.isNotEmpty())"))
        assertTrue(source.contains("key = \"followed-comedian-shows\""))
        assertTrue(source.contains("title = \"Because you follow them\""))
        assertTrue(source.contains("onOpenSearch = null"))
        assertFalse(HomeExpandableRail.entries.any { it.name.contains("FOLLOWED") })
    }

    @Test
    fun discover_state_is_saveable_and_search_handoff_switches_tabs() {
        val home = String(Files.readAllBytes(homeScreenPath()))
        val shell = String(Files.readAllBytes(appShellPath()))

        assertTrue(home.contains("val listState = rememberLazyListState()"))
        assertTrue(home.contains("state = listState"))
        assertTrue(home.contains("item(key = \"followed-comedian-shows\")"))
        assertTrue(shell.contains("pendingSearchRequest = request"))
        assertTrue(shell.contains("navController.switchTab(AppTab.SEARCH)"))
        assertTrue(shell.contains("onRequestedSearchConsumed = { pendingSearchRequest = null }"))
    }

    private fun feed(): HomeFeed =
        HomeFeed(
            hero = HomeFeedHero(shows = emptyList(), zipCode = "10001", city = "New York", state = "NY"),
            trendingComedians = emptyList(),
            comediansNearYou = emptyList(),
            showsTonight = emptyList(),
            moreNearYou = emptyList(),
            trendingThisWeek = emptyList(),
            followedComedianShows =
                listOf(Show(id = 1, clubId = 2, date = "2026-08-05T20:00:00-04:00", imageUrl = "")),
            trendingPodcasts = emptyList(),
            popularClubs = emptyList(),
        )

    private fun homeScreenPath(): Path =
        locate(
            "android/feature/home/src/main/kotlin/app/laughtrack/android/feature/home/HomeScreen.kt",
        )

    private fun appShellPath(): Path = locate("android/app/src/main/kotlin/app/laughtrack/android/AppShell.kt")

    private fun locate(relative: String): Path =
        generateSequence(Paths.get("").toAbsolutePath()) { it.parent }
            .map { it.resolve(relative) }
            .firstOrNull(Files::isRegularFile)
            ?: error("Unable to locate $relative")
}
