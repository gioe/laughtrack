package app.laughtrack.android

import app.laughtrack.android.core.navigation.AppRoute
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class AppShellChromeTest {
    @Test
    fun shell_top_app_bar_is_visible_for_tab_destinations() {
        assertTrue(AppShellChrome.showsTopAppBar(AppRoute.Discover))
        assertTrue(AppShellChrome.showsTopAppBar(AppRoute.Search))
        assertTrue(AppShellChrome.showsTopAppBar(AppRoute.Favorites))
    }

    @Test
    fun shell_top_app_bar_is_hidden_when_destination_owns_back_chrome() {
        assertFalse(AppShellChrome.showsTopAppBar(AppRoute.ShowDetail(id = 1)))
        assertFalse(AppShellChrome.showsTopAppBar(AppRoute.ComedianDetail(id = 1)))
        assertFalse(AppShellChrome.showsTopAppBar(AppRoute.ClubDetail(id = 1)))
        assertFalse(AppShellChrome.showsTopAppBar(AppRoute.PodcastDetail(id = 1)))
        assertFalse(AppShellChrome.showsTopAppBar(AppRoute.NotificationCenter))
    }
}
