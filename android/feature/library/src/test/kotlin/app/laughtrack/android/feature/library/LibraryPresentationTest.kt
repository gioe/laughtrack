package app.laughtrack.android.feature.library

import app.laughtrack.android.core.network.generated.model.Show
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Test
import java.util.Locale

class LibraryPresentationTest {
    @Test
    fun authenticatedSectionsHaveDistinctOrderedHierarchyAndMetadata() {
        val presentations = AuthenticatedLibrarySection.entries.map { it.presentation }

        assertEquals(4, presentations.size)
        assertEquals(
            listOf("Favorites", "Comedians", "Clubs", "Podcasts"),
            presentations.map { it.eyebrow },
        )
        assertEquals(
            listOf(
                "Your favorites are touring",
                "Saved comedians",
                "Saved clubs",
                "Saved podcasts",
            ),
            presentations.map { it.title },
        )
        assertEquals(4, presentations.map { it.eyebrow }.distinct().size)
        assertEquals(4, presentations.map { it.title }.distinct().size)
        presentations.forEach { presentation ->
            assertFalse(presentation.eyebrow.isBlank())
            assertFalse(presentation.title.isBlank())
            assertFalse(presentation.subtitle.isBlank())
        }
    }

    @Test
    fun rawIsoTimestampsAreFormatted() {
        val rawDate = "2026-07-18T20:00:00-04:00"

        val subtitle = favoriteShowSubtitle(show(date = rawDate), Locale.US)

        assertEquals("The Comedy Cellar - New York - Jul 18, 2026 · 8:00 PM", subtitle)
        assertFalse(subtitle.contains(rawDate))
    }

    @Test
    fun touringDateRetainsVenueAndLocation() {
        val subtitle =
            favoriteShowSubtitle(
                show(
                    date = "2026-07-19T00:30:00Z",
                    timezone = "America/New_York",
                ),
                Locale.US,
            )

        assertEquals("The Comedy Cellar - New York - Jul 18, 2026 · 8:30 PM", subtitle)
    }

    @Test
    fun invalidAndMissingDatesHaveSafeFallbacks() {
        assertEquals(
            "The Comedy Cellar - New York",
            favoriteShowSubtitle(show(date = "not-a-date"), Locale.US),
        )
        assertEquals(
            "The Comedy Cellar - New York",
            favoriteShowSubtitle(show(date = "   "), Locale.US),
        )
    }

    private fun show(
        date: String,
        timezone: String? = "America/New_York",
    ) = Show(
        id = 1,
        clubId = 2,
        date = date,
        imageUrl = "",
        clubName = "The Comedy Cellar",
        clubCity = "New York",
        timezone = timezone,
    )
}
