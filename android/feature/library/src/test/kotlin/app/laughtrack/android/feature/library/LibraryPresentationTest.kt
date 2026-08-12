package app.laughtrack.android.feature.library

import app.laughtrack.android.core.data.favorites.FavoritesSnapshot
import app.laughtrack.android.core.data.savedshows.SavedShowsSnapshot
import app.laughtrack.android.core.network.generated.model.ComedianSearchItem
import app.laughtrack.android.core.network.generated.model.FavoriteClubItem
import app.laughtrack.android.core.network.generated.model.FavoritePodcastItem
import app.laughtrack.android.core.network.generated.model.SocialData
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class LibraryPresentationTest {
    @Test
    fun librarySectionsUseTheCanonicalPriorityOrder() {
        assertEquals(
            listOf("Next Up", "Saved", "History"),
            LibrarySection.entries.map { it.presentation.title },
        )
        assertEquals(
            listOf("Plans", "Your collection", "Past plans"),
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
                saved = LibraryGroupResolution.EMPTY,
                history = LibraryGroupResolution.EMPTY,
            )

        assertTrue(empty.isFullyEmpty)

        LibraryGroupResolution.entries
            .filterNot { it == LibraryGroupResolution.EMPTY }
            .forEach { nonEmptyResolution ->
                assertFalse(empty.copy(nextUp = nonEmptyResolution).isFullyEmpty)
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
        assertEquals(List(3) { LibraryGroupResolution.EMPTY }, settled.asOrderedList())
        assertTrue(settled.isFullyEmpty)

        val failed =
            libraryContentState(
                snapshot = FavoritesSnapshot(errorMessage = "Try again"),
                savedShowsSnapshot = SavedShowsSnapshot(),
                initialRefreshComplete = true,
            )
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

    private fun LibraryContentState.asOrderedList() = listOf(nextUp, saved, history)

    private fun comedian(id: Int) =
        ComedianSearchItem(
            id = id,
            uuid = "comedian-$id",
            name = "Comedian $id",
            imageUrl = "",
            socialData = SocialData(id = id),
            showCount = 2,
        )
}
