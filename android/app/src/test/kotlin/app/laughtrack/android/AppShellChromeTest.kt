package app.laughtrack.android

import app.laughtrack.android.core.navigation.AppRoute
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class AppShellChromeTest {
    @Test
    fun shell_top_app_bar_is_visible_for_secondary_destinations_that_do_not_own_chrome() {
        assertTrue(AppShellChrome.showsTopAppBar(AppRoute.Favorites()))
        assertTrue(AppShellChrome.showsTopAppBar(AppRoute.Profile))
    }

    @Test
    fun shell_top_app_bar_is_hidden_when_destination_owns_back_chrome() {
        assertFalse(AppShellChrome.showsTopAppBar(AppRoute.Discover))
        assertFalse(AppShellChrome.showsTopAppBar(AppRoute.Search))
        assertFalse(AppShellChrome.showsTopAppBar(AppRoute.ShowDetail(id = 1)))
        assertFalse(AppShellChrome.showsTopAppBar(AppRoute.ComedianDetail(id = 1)))
        assertFalse(AppShellChrome.showsTopAppBar(AppRoute.ClubDetail(id = 1)))
        assertFalse(AppShellChrome.showsTopAppBar(AppRoute.PodcastDetail(id = 1)))
        assertFalse(AppShellChrome.showsTopAppBar(AppRoute.NotificationCenter))
    }

    @Test
    fun shell_bottom_bar_is_visible_only_for_root_tabs() {
        assertTrue(AppShellChrome.showsBottomBar(AppRoute.Discover))
        assertTrue(AppShellChrome.showsBottomBar(AppRoute.Search))
        assertTrue(AppShellChrome.showsBottomBar(AppRoute.Favorites()))

        assertFalse(AppShellChrome.showsBottomBar(AppRoute.ShowDetail(id = 1)))
        assertFalse(AppShellChrome.showsBottomBar(AppRoute.ComedianDetail(id = 1)))
        assertFalse(AppShellChrome.showsBottomBar(AppRoute.ClubDetail(id = 1)))
        assertFalse(AppShellChrome.showsBottomBar(AppRoute.PodcastDetail(id = 1)))
        assertFalse(AppShellChrome.showsBottomBar(AppRoute.Profile))
        assertFalse(AppShellChrome.showsBottomBar(AppRoute.NotificationCenter))
    }
}
