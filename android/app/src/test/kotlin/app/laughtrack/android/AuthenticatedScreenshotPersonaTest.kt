package app.laughtrack.android

import app.laughtrack.android.screenshots.AuthenticatedScreenshotPersona
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class AuthenticatedScreenshotPersonaTest {
    @Test
    fun `persona is a complete authenticated fixture with stable identity`() {
        val profile = AuthenticatedScreenshotPersona.profileUiState

        assertTrue(profile.signedIn)
        assertFalse(profile.isLoading)
        assertEquals("Jordan Rivera", profile.account?.displayName)
        assertEquals("jordan.rivera@example.com", profile.account?.email)
        assertNull(profile.account?.avatarUrl)
        assertEquals("10012", profile.preferences.zipCode)
        assertEquals(25, profile.preferences.nearbyDistanceMiles)
        assertTrue(profile.preferences.emailShowNotifications)
        assertTrue(profile.preferences.pushShowNotifications)
    }

    @Test
    fun `favorites are populated and use fixed ids without remote images`() {
        val favorites = AuthenticatedScreenshotPersona.favoritesSnapshot

        assertEquals(listOf("Taylor Tomlinson", "Sam Jay"), favorites.comedians.map { it.name })
        assertEquals(listOf(910_101, 910_102), favorites.shows.map { it.id })
        assertTrue(favorites.comedians.all { it.imageUrl.isEmpty() })
        assertTrue(favorites.shows.all { it.imageUrl.isEmpty() })
        assertTrue(favorites.clubs.all { it.imageUrl.isEmpty() })
        assertTrue(favorites.podcasts.all { it.imageUrl == null })
        assertFalse(favorites.isLoading)
        assertNull(favorites.errorMessage)
    }

    @Test
    fun `saved shows include deterministic upcoming and past collections`() {
        val savedShows = AuthenticatedScreenshotPersona.savedShowsSnapshot

        assertEquals(listOf(910_103), savedShows.upcoming.shows.map { it.id })
        assertEquals(listOf(910_104), savedShows.past.shows.map { it.id })
        assertTrue(savedShows.upcoming.shows.all { it.imageUrl.isEmpty() })
        assertTrue(savedShows.past.shows.all { it.imageUrl.isEmpty() })
        assertEquals(true, savedShows.values[910_103])
        assertEquals(true, savedShows.values[910_104])
        assertFalse(savedShows.upcoming.isLoading)
        assertFalse(savedShows.past.isLoading)
    }

    @Test
    fun `notifications are populated with fixed timestamps and no remote images`() {
        val notifications = AuthenticatedScreenshotPersona.notificationListResponseData

        assertEquals(2, notifications.items.size)
        assertEquals(1, notifications.unreadCount)
        assertEquals(
            listOf(
                "Taylor Tomlinson has a show near you",
                "Your favorites have 2 new shows",
            ),
            notifications.items.map { it.title },
        )
        assertEquals(
            listOf(
                "The Comedy Cellar on Saturday at 8:00 PM",
                "The Comedy Cellar and The Bell House",
            ),
            notifications.items.map { it.body },
        )
        assertEquals(
            listOf("2026-07-15T13:00:00-04:00", "2026-07-14T15:00:00-04:00"),
            notifications.items.map { it.sentAt },
        )
        assertTrue(notifications.items.all { it.comedianImageUrl.isEmpty() })
        assertTrue(notifications.items.flatMap { it.comedians }.all { it.comedianImageUrl.isEmpty() })
        assertTrue(notifications.items.flatMap { it.shows }.all { it.showPageUrl == null })
    }
}
