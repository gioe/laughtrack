package app.laughtrack.android.feature.library

import app.laughtrack.android.core.data.favorites.FavoritesSnapshot
import app.laughtrack.android.core.data.savedshows.SavedShowsSnapshot
import app.laughtrack.android.core.network.generated.model.ComedianSearchItem
import app.laughtrack.android.core.network.generated.model.FavoriteClubItem
import app.laughtrack.android.core.network.generated.model.FavoritePodcastItem
import app.laughtrack.android.core.network.generated.model.Show
import app.laughtrack.android.core.network.generated.model.SocialData
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test
import java.util.Locale

class LibraryPresentationTest {
    @Test
    fun librarySectionsUseTheCanonicalPriorityOrder() {
        assertEquals(
            listOf("Next Up", "From Your Follows", "Saved", "History"),
            LibrarySection.entries.map { it.presentation.title },
        )
        assertEquals(
            listOf("Plans", "Following", "Your collection", "Past plans"),
            LibrarySection.entries.map { it.presentation.eyebrow },
        )
        LibrarySection.entries.forEach { section ->
            assertFalse(section.presentation.title.isBlank())
            assertFalse(section.presentation.subtitle.isBlank())
        }
    }

    @Test
    fun fullyEmptyRequiresEveryGroupToBeSettledEmpty() {
        val empty =
            LibraryContentState(
                nextUp = LibraryGroupResolution.EMPTY,
                fromFollows = LibraryGroupResolution.EMPTY,
                saved = LibraryGroupResolution.EMPTY,
                history = LibraryGroupResolution.EMPTY,
            )

        assertTrue(empty.isFullyEmpty)

        LibraryGroupResolution.entries
            .filterNot { it == LibraryGroupResolution.EMPTY }
            .forEach { nonEmptyResolution ->
                assertFalse(empty.copy(nextUp = nonEmptyResolution).isFullyEmpty)
                assertFalse(empty.copy(fromFollows = nonEmptyResolution).isFullyEmpty)
                assertFalse(empty.copy(saved = nonEmptyResolution).isFullyEmpty)
                assertFalse(empty.copy(history = nonEmptyResolution).isFullyEmpty)
            }
    }

    @Test
    fun contentStateKeepsInitialAndFailedGroupsVisibleButOmitsSettledEmptyGroups() {
        val initial =
            libraryContentState(
                snapshot = FavoritesSnapshot(),
                savedShowsSnapshot = SavedShowsSnapshot(),
                initialRefreshComplete = false,
            )
        assertEquals(
            listOf(
                LibraryGroupResolution.LOADING,
                LibraryGroupResolution.LOADING,
                LibraryGroupResolution.LOADING,
                LibraryGroupResolution.LOADING,
            ),
            initial.asOrderedList(),
        )
        assertFalse(initial.isFullyEmpty)

        val settled =
            libraryContentState(
                snapshot = FavoritesSnapshot(),
                savedShowsSnapshot = SavedShowsSnapshot(),
                initialRefreshComplete = true,
            )
        assertEquals(List(4) { LibraryGroupResolution.EMPTY }, settled.asOrderedList())
        assertTrue(settled.isFullyEmpty)

        val failed =
            libraryContentState(
                snapshot = FavoritesSnapshot(errorMessage = "Try again"),
                savedShowsSnapshot = SavedShowsSnapshot(),
                initialRefreshComplete = true,
            )
        assertEquals(LibraryGroupResolution.FAILURE, failed.fromFollows)
        assertEquals(LibraryGroupResolution.FAILURE, failed.saved)
        assertFalse(failed.isFullyEmpty)
    }

    @Test
    fun emptyLibraryOffersOneSearchSeedForEveryEntityShape() {
        assertEquals(
            listOf("Shows near me", "Follow comedians", "Save clubs", "Save podcasts"),
            LibrarySearchSeed.entries.map(LibrarySearchSeed::label),
        )
        assertEquals(
            listOf(LibrarySearchSeed.SHOWS),
            LibrarySearchSeed.entries.filter(LibrarySearchSeed::nearMe),
        )
    }

    @Test
    fun savedEntitiesMapToTheirCanonicalDetailIdentifiers() {
        assertEquals(
            LibrarySavedDestination.Comedian(31),
            savedComedianDestination(comedian(id = 31)),
        )
        assertEquals(
            LibrarySavedDestination.Club(41),
            savedClubDestination(
                FavoriteClubItem(
                    id = 41,
                    name = "Comedy Room",
                    imageUrl = "",
                    isFavorite = true,
                ),
            ),
        )
        assertEquals(
            LibrarySavedDestination.Podcast(51),
            savedPodcastDestination(
                FavoritePodcastItem(
                    id = 51,
                    title = "Good One",
                    episodeCount = 20,
                    isFavorite = true,
                ),
            ),
        )
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

    private fun LibraryContentState.asOrderedList() = listOf(nextUp, fromFollows, saved, history)

    private fun comedian(id: Int) =
        ComedianSearchItem(
            id = id,
            uuid = "comedian-$id",
            name = "Comedian $id",
            imageUrl = "",
            socialData = SocialData(id = id),
            showCount = 2,
        )

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
