package app.laughtrack.android

import app.laughtrack.android.core.navigation.AppRoute
import app.laughtrack.android.core.navigation.AppTab
import org.junit.Assert.assertEquals
import org.junit.Test

/**
 * The shell's top-level information architecture is stable across authentication
 * and Library-content changes. Entity pivots remain owned by SearchScreen rather
 * than being promoted into the shared shell.
 */
class AppShellTabsTest {
    @Test
    fun all_root_tab_pairs_use_lateral_crossfade_policy_in_both_directions() {
        AppTab.entries.forEach { from ->
            AppTab.entries.forEach { to ->
                assertEquals(AppShellMotionKind.TAB, AppShellMotion.kind(from.rootRoute::class, to.rootRoute::class))
            }
        }
    }

    @Test
    fun player_expansion_and_return_are_vertical_from_every_destination() {
        AppRoute::class.sealedSubclasses.forEach { route ->
            assertEquals(AppShellMotionKind.PLAYER, AppShellMotion.kind(route, AppRoute.NowPlaying::class))
            assertEquals(AppShellMotionKind.PLAYER, AppShellMotion.kind(AppRoute.NowPlaying::class, route))
        }
    }

    @Test
    fun detail_routes_keep_depth_when_entering_or_returning_to_a_root() {
        val details = AppShellChrome.fullScreenRoutes - setOf(AppRoute.NowPlaying::class)
        details.forEach { detail ->
            AppTab.entries.forEach { root ->
                assertEquals(AppShellMotionKind.DETAIL, AppShellMotion.kind(root.rootRoute::class, detail))
                assertEquals(AppShellMotionKind.DETAIL, AppShellMotion.kind(detail, root.rootRoute::class))
            }
        }
    }

    private val expectedTabs = listOf(AppTab.DISCOVER, AppTab.SEARCH, AppTab.FAVORITES)

    @Test
    fun signed_out_shell_has_permanent_three_tab_hierarchy() {
        assertEquals(expectedTabs, AppShellTabs.visibleTabs)
    }

    @Test
    fun signed_in_empty_library_has_permanent_three_tab_hierarchy() {
        assertEquals(expectedTabs, AppShellTabs.visibleTabs)
    }

    @Test
    fun signed_in_populated_library_has_permanent_three_tab_hierarchy() {
        assertEquals(expectedTabs, AppShellTabs.visibleTabs)
    }

    @Test
    fun top_level_labels_match_the_information_architecture() {
        assertEquals("Library", AppTab.FAVORITES.label)
        assertEquals("Search", AppTab.SEARCH.label)
    }

    @Test
    fun search_is_the_only_top_level_entity_pivot_owner() {
        assertEquals(listOf(AppTab.SEARCH), AppTab.entries.filter(AppTab::ownsEntityPivots))
    }
}
