package app.laughtrack.android

import app.laughtrack.android.core.navigation.AppTab
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * Favorites bottom-tab visibility, mirroring iOS AppShellView.showFavoritesTab:
 * the tab is exposed only for a signed-in user who has at least one favorite.
 */
class AppShellTabsTest {
    @Test
    fun favorites_tab_hidden_for_logged_out_user() {
        assertFalse(AppShellTabs.showsFavoritesTab(signedIn = false, hasFavorites = false))
        // Logged out, even if a stale snapshot still reports favorites.
        assertFalse(AppShellTabs.showsFavoritesTab(signedIn = false, hasFavorites = true))

        val tabs = AppShellTabs.visibleTabs(signedIn = false, hasFavorites = false)
        assertEquals(listOf(AppTab.DISCOVER, AppTab.SEARCH), tabs)
    }

    @Test
    fun favorites_tab_hidden_for_logged_in_user_without_favorites() {
        assertFalse(AppShellTabs.showsFavoritesTab(signedIn = true, hasFavorites = false))

        val tabs = AppShellTabs.visibleTabs(signedIn = true, hasFavorites = false)
        assertEquals(listOf(AppTab.DISCOVER, AppTab.SEARCH), tabs)
    }

    @Test
    fun favorites_tab_shown_for_logged_in_user_with_favorites() {
        assertTrue(AppShellTabs.showsFavoritesTab(signedIn = true, hasFavorites = true))

        val tabs = AppShellTabs.visibleTabs(signedIn = true, hasFavorites = true)
        assertEquals(listOf(AppTab.DISCOVER, AppTab.SEARCH, AppTab.FAVORITES), tabs)
    }
}
