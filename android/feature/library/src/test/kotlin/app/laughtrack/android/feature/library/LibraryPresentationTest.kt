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
            listOf("Shows", "Comedians", "Clubs", "Podcasts"),
            LibrarySection.entries.map { it.presentation.title },
        )
        assertEquals(
            listOf("", "", "", ""),
            LibrarySection.entries.map { it.presentation.eyebrow },
        )
        LibrarySection.entries.forEach { section ->
            assertFalse(section.presentation.title.isBlank())
            assertTrue(section.presentation.subtitle.isBlank())
        }
    }

    @Test
    fun fullyEmptyRequiresEveryGroupToBeSettledEmpty() {
        val empty =
            LibraryContentState(
                nextUp = LibraryGroupResolution.EMPTY,
                comedians = LibraryGroupResolution.EMPTY,
                clubs = LibraryGroupResolution.EMPTY,
                podcasts = LibraryGroupResolution.EMPTY,
            )

        assertTrue(empty.isFullyEmpty)

        LibraryGroupResolution.entries
            .filterNot { it == LibraryGroupResolution.EMPTY }
            .forEach { nonEmptyResolution ->
                assertFalse(empty.copy(nextUp = nonEmptyResolution).isFullyEmpty)
                assertFalse(empty.copy(comedians = nonEmptyResolution).isFullyEmpty)
                assertFalse(empty.copy(clubs = nonEmptyResolution).isFullyEmpty)
                assertFalse(empty.copy(podcasts = nonEmptyResolution).isFullyEmpty)
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
        assertEquals(LibraryGroupResolution.FAILURE, failed.comedians)
        assertEquals(LibraryGroupResolution.FAILURE, failed.clubs)
        assertEquals(LibraryGroupResolution.FAILURE, failed.podcasts)
        assertFalse(failed.isFullyEmpty)
    }

    @Test
    fun eachSavedEntityTypeResolvesAsAnIndependentRail() {
        val state =
            libraryContentState(
                snapshot = FavoritesSnapshot(comedians = listOf(comedian(id = 31))),
                savedShowsSnapshot = SavedShowsSnapshot(),
                initialRefreshComplete = true,
            )

        assertEquals(
            listOf(
                LibraryGroupResolution.EMPTY,
                LibraryGroupResolution.CONTENT,
                LibraryGroupResolution.EMPTY,
                LibraryGroupResolution.EMPTY,
            ),
            state.asOrderedList(),
        )
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
    fun allLibraryRailsPageFiveItemsAtATime() {
        val items = (1..11).toList()

        assertEquals(listOf(1, 2, 3, 4, 5), libraryItemsForPage(items, page = 0))
        assertEquals(listOf(6, 7, 8, 9, 10), libraryItemsForPage(items, page = 1))
        assertEquals(listOf(11), libraryItemsForPage(items, page = 2))
        assertEquals(3, libraryPageCount(items.size))
    }

    private fun LibraryContentState.asOrderedList() = listOf(nextUp, comedians, clubs, podcasts)

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
