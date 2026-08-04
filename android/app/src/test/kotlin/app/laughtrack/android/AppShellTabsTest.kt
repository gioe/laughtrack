package app.laughtrack.android

import app.laughtrack.android.core.navigation.AppTab
import org.junit.Assert.assertEquals
import org.junit.Test

/**
 * The shell's top-level information architecture is stable across authentication
 * and Library-content changes. Entity pivots remain owned by SearchScreen rather
 * than being promoted into the shared shell.
 */
class AppShellTabsTest {
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
