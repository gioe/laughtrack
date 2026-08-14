package app.laughtrack.android

import app.laughtrack.android.screenshots.AuthenticatedScreenshotPersona
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test
import java.math.BigDecimal

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
    fun `saved entities are populated without inferred shows or remote images`() {
        val favorites = AuthenticatedScreenshotPersona.favoritesSnapshot

        assertEquals(listOf("Taylor Tomlinson", "Sam Jay"), favorites.comedians.map { it.name })
        assertTrue(favorites.comedians.all { it.imageUrl.isEmpty() })
        assertEquals(favorites.comedians.size, favorites.comedians.map { it.name }.distinct().size)
        assertTrue(favorites.clubs.all { it.imageUrl.isEmpty() })
        assertTrue(favorites.podcasts.all { it.imageUrl == null })
        assertFalse(favorites.isLoading)
        assertNull(favorites.errorMessage)
    }

    @Test
    fun `saved shows match the canonical two-page story`() {
        val savedShows = AuthenticatedScreenshotPersona.savedShowsSnapshot

        assertEquals((910_103..910_108).toList(), savedShows.upcoming.shows.map { it.id })
        assertEquals(6, savedShows.upcoming.total)
        assertEquals(2, savedShows.upcoming.totalPages)
        assertTrue(savedShows.past.shows.isEmpty())
        assertEquals(
            listOf(
                SavedShowStory(
                    "Atsuko Okatsuka: Full Grown Tour",
                    "2026-08-21T20:00:00-04:00",
                    "Town Hall",
                    "New York",
                ),
                SavedShowStory("Josh Johnson and Friends", "2026-08-24T20:00:00-04:00", "The Bell House", "Brooklyn"),
                SavedShowStory("Taylor Tomlinson Live", "2026-08-28T20:00:00-04:00", "The Comedy Cellar", "New York"),
                SavedShowStory("Sam Jay: Testing Material", "2026-09-02T19:30:00-04:00", "Union Hall", "Brooklyn"),
                SavedShowStory(
                    "Mike Birbiglia: Please Stop the Ride",
                    "2026-09-05T20:00:00-04:00",
                    "Beacon Theatre",
                    "New York",
                ),
                SavedShowStory(
                    "Michelle Wolf and Friends",
                    "2026-09-08T20:00:00-04:00",
                    "Gotham Comedy Club",
                    "New York",
                ),
            ),
            savedShows.upcoming.shows.map { show ->
                val ticket = show.tickets?.singleOrNull()
                SavedShowStory(
                    title = show.name,
                    date = show.date,
                    club = show.clubName,
                    city = show.clubCity,
                    state = show.clubState,
                    timezone = show.timezone,
                    price = ticket?.price,
                    soldOut = ticket?.soldOut,
                    ticketType = ticket?.type,
                )
            },
        )
        assertTrue(savedShows.upcoming.shows.all { it.imageUrl.isEmpty() })
        assertEquals(
            savedShows.upcoming.shows.size,
            savedShows.upcoming.shows.mapNotNull { it.name }.distinct().size,
        )
        assertTrue((910_103..910_108).all { savedShows.values[it] == true })
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

    private data class SavedShowStory(
        val title: String?,
        val date: String,
        val club: String?,
        val city: String?,
        val state: String? = "NY",
        val timezone: String? = "America/New_York",
        val price: BigDecimal? = BigDecimal("30"),
        val soldOut: Boolean? = false,
        val ticketType: String? = "General admission",
    )
}
