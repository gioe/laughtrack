package app.laughtrack.android

import app.laughtrack.android.core.navigation.AppRoute
import app.laughtrack.android.core.navigation.AppTab
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * Pins the canonical route-class sets that the shipping
 * [AppShellChrome.showsTopAppBar]/[AppShellChrome.showsBottomBar]
 * `NavDestination` predicates read (production Scaffold calls those overloads;
 * building real typed NavDestinations needs an instrumented environment, so the
 * hasRoute adapter itself is covered by the androidTest AppShellTest).
 */
class AppShellChromeTest {
    @Test
    fun club_detail_home_is_hidden_only_for_an_internal_direct_discover_push() {
        assertFalse(
            AppShellChrome.showsClubDetailHome(
                previousIsDiscover = true,
                enteredExternally = false,
            ),
        )
        assertTrue(
            AppShellChrome.showsClubDetailHome(
                previousIsDiscover = false,
                enteredExternally = false,
            ),
        )
        assertTrue(
            AppShellChrome.showsClubDetailHome(
                previousIsDiscover = true,
                enteredExternally = true,
            ),
        )
    }

    @Test
    fun shell_top_app_bar_is_shown_only_for_secondary_destinations_that_do_not_own_chrome() {
        assertEquals(
            setOf(
                AppRoute.Favorites::class,
                AppRoute.Profile::class,
            ),
            AppShellChrome.topAppBarRoutes,
        )
        assertFalse(AppRoute.Discover::class in AppShellChrome.topAppBarRoutes)
        assertFalse(AppRoute.Search::class in AppShellChrome.topAppBarRoutes)
        assertFalse(AppRoute.ComedianOnboarding::class in AppShellChrome.topAppBarRoutes)
        assertFalse(AppRoute.ShowDetail::class in AppShellChrome.topAppBarRoutes)
        assertFalse(AppRoute.NotificationCenter::class in AppShellChrome.topAppBarRoutes)
    }

    @Test
    fun shell_bottom_bar_is_visible_only_for_root_tabs() {
        assertEquals(
            setOf(
                AppRoute.Discover::class,
                AppRoute.Search::class,
                AppRoute.Favorites::class,
            ),
            AppShellChrome.bottomBarRoutes,
        )
        assertFalse(AppRoute.Profile::class in AppShellChrome.bottomBarRoutes)
        assertFalse(AppRoute.NotificationCenter::class in AppShellChrome.bottomBarRoutes)
        assertFalse(AppRoute.ShowDetail::class in AppShellChrome.bottomBarRoutes)
    }

    @Test
    fun expanded_now_playing_is_the_only_route_that_hides_the_mini_player() {
        assertEquals(setOf(AppRoute.NowPlaying::class), AppShellChrome.miniPlayerHiddenRoutes)
    }

    @Test
    fun missing_destination_uses_discover_chrome_without_a_temporary_top_bar() {
        assertFalse(AppShellChrome.showsTopAppBar(null))
        assertTrue(AppShellChrome.showsBottomBar(null))
        assertTrue(AppShellChrome.showsMiniPlayer(null))
        assertFalse(AppShellBackgrounds.usesOpaqueCanvas(null))
        assertEquals(
            listOf(AppTab.DISCOVER),
            AppShellTabs.visibleTabs.filter { AppShellTabs.isSelected(null, it) },
        )
    }

    @Test
    fun unresolved_full_screen_entries_do_not_reserve_shell_bar_space() {
        val initialRoutes =
            listOf(
                AppRoute.ShowDetail(1),
                AppRoute.ClubDetail(1),
                AppRoute.ComedianOnboarding,
            )
        initialRoutes.forEach { route ->
            assertFalse(AppShellChrome.showsTopAppBar(null, route))
            assertFalse(AppShellChrome.showsBottomBar(null, route))
            assertTrue(AppShellChrome.showsMiniPlayer(null, route))
            assertFalse(AppShellBackgrounds.usesOpaqueCanvas(null, route))
            assertTrue(AppShellTabs.visibleTabs.none { AppShellTabs.isSelected(null, it, route) })
        }
    }

    @Test
    fun unresolved_expanded_playback_uses_opaque_canvas_without_shell_bars_or_mini_player() {
        val route = AppRoute.NowPlaying
        assertFalse(AppShellChrome.showsTopAppBar(null, route))
        assertFalse(AppShellChrome.showsBottomBar(null, route))
        assertFalse(AppShellChrome.showsMiniPlayer(null, route))
        assertTrue(AppShellBackgrounds.usesOpaqueCanvas(null, route))
    }

    @Test
    fun unresolved_library_entry_keeps_its_own_chrome_and_selected_tab() {
        val route = AppRoute.Favorites
        assertTrue(AppShellChrome.showsTopAppBar(null, route))
        assertTrue(AppShellChrome.showsBottomBar(null, route))
        assertEquals(
            listOf(AppTab.FAVORITES),
            AppShellTabs.visibleTabs.filter { AppShellTabs.isSelected(null, it, route) },
        )
    }

    /**
     * Replaces the compile-time exhaustiveness the deleted `when(AppRoute)`
     * overloads provided: a new AppRoute class must be added to one of the
     * canonical sets (or explicitly to [AppShellChrome.fullScreenRoutes])
     * before this suite goes green again.
     */
    @Test
    fun every_route_class_has_an_explicit_chrome_classification() {
        val classified =
            AppShellChrome.topAppBarRoutes +
                AppShellChrome.bottomBarRoutes +
                AppShellChrome.fullScreenRoutes
        val unclassified = AppRoute::class.sealedSubclasses.toSet() - classified
        assertTrue(
            "AppRoute classes missing a chrome classification in AppShellChrome: $unclassified",
            unclassified.isEmpty(),
        )
    }

    @Test
    fun full_screen_routes_do_not_overlap_the_bar_sets() {
        val overlap =
            AppShellChrome.fullScreenRoutes intersect
                (AppShellChrome.topAppBarRoutes + AppShellChrome.bottomBarRoutes)
        assertTrue("fullScreenRoutes must not also claim a bar: $overlap", overlap.isEmpty())
        assertTrue(AppRoute.ComedianOnboarding::class in AppShellChrome.fullScreenRoutes)
    }

    @Test
    fun now_playing_is_the_only_route_that_replaces_the_app_atmosphere() {
        assertEquals(setOf(AppRoute.NowPlaying::class), AppShellBackgrounds.opaqueRoutes)
    }

    @Test
    fun every_ordinary_route_inherits_the_app_atmosphere() {
        val atmosphereRoutes = AppRoute::class.sealedSubclasses.toSet() - AppShellBackgrounds.opaqueRoutes

        assertEquals(
            setOf(
                AppRoute.Discover::class,
                AppRoute.Search::class,
                AppRoute.Favorites::class,
                AppRoute.ComedianOnboarding::class,
                AppRoute.ShowDetail::class,
                AppRoute.ComedianDetail::class,
                AppRoute.ClubDetail::class,
                AppRoute.PodcastDetail::class,
                AppRoute.PodcastEpisodeDetail::class,
                AppRoute.Profile::class,
                AppRoute.NotificationCenter::class,
            ),
            atmosphereRoutes,
        )
    }
}
