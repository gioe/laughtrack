package app.laughtrack.android.feature.library

import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onNodeWithContentDescription
import androidx.compose.ui.test.onNodeWithTag
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import androidx.compose.ui.test.performScrollTo
import androidx.test.ext.junit.runners.AndroidJUnit4
import app.laughtrack.android.core.data.favorites.FavoritesSnapshot
import app.laughtrack.android.core.data.savedshows.SavedShowPeriod
import app.laughtrack.android.core.data.savedshows.SavedShowsCollection
import app.laughtrack.android.core.data.savedshows.SavedShowsSnapshot
import app.laughtrack.android.core.network.generated.model.ComedianSearchItem
import app.laughtrack.android.core.network.generated.model.FavoriteClubItem
import app.laughtrack.android.core.network.generated.model.FavoritePodcastItem
import app.laughtrack.android.core.network.generated.model.Show
import app.laughtrack.android.core.network.generated.model.SocialData
import app.laughtrack.android.core.ui.components.RemoteImageFallback
import app.laughtrack.android.core.ui.components.RemoteImageTestTags
import app.laughtrack.android.core.ui.theme.LaughTrackTheme
import org.junit.Assert.assertEquals
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class LibraryScreenInteractionTest {
    @get:Rule
    val compose = createComposeRule()

    @Test
    fun savedShowsPageThroughDelayedLoadNavigateAndResetAfterRefreshShrink() {
        var savedShows by mutableStateOf(savedShowsSnapshot(loadedIds = 1..5, total = 6, totalPages = 2))
        val loadMoreRequests = mutableListOf<SavedShowPeriod>()
        val openedShows = mutableListOf<Int>()

        compose.setContent {
            LaughTrackTheme {
                LibraryScreen(
                    signedIn = true,
                    onOpenProfile = {},
                    snapshotOverride = FavoritesSnapshot(),
                    savedShowsSnapshotOverride = savedShows,
                    onOpenShow = openedShows::add,
                    onLoadMoreSavedShows = { period ->
                        loadMoreRequests += period
                    },
                )
            }
        }

        compose.onNodeWithText("Page 1 of 2").performScrollTo().assertIsDisplayed()
        compose.onNodeWithText("Next").performScrollTo().performClick()
        compose.waitForIdle()

        compose.runOnIdle {
            assertEquals(listOf(SavedShowPeriod.UPCOMING), loadMoreRequests)
        }
        compose.onNodeWithText("Page 1 of 2").assertIsDisplayed()
        compose.onNodeWithText("Saved show 6").assertDoesNotExist()

        compose.runOnIdle {
            savedShows = savedShowsSnapshot(loadedIds = 1..6, page = 2, total = 6, totalPages = 2)
        }
        compose.waitForIdle()
        compose.onNodeWithText("Page 2 of 2").assertIsDisplayed()
        compose.onNodeWithText("Saved show 6").performScrollTo().performClick()
        compose.runOnIdle { assertEquals(listOf(6), openedShows) }

        compose.onNodeWithText("Previous").performScrollTo().performClick()
        compose.onNodeWithText("Saved show 1").performScrollTo().assertIsDisplayed()

        compose.onNodeWithText("Next").performScrollTo().performClick()
        compose.onNodeWithText("Page 2 of 2").assertIsDisplayed()
        compose.runOnIdle {
            savedShows = savedShowsSnapshot(loadedIds = 1..5, page = 1, total = 6, totalPages = 2)
        }
        compose.waitForIdle()

        compose.onNodeWithText("Saved show 1").performScrollTo().assertIsDisplayed()
        compose.onNodeWithText("Page 1 of 2").assertIsDisplayed()
        compose.onNodeWithText("Saved show 6").assertDoesNotExist()
    }

    @Test
    fun canonicalFallbackRowsExposeOpenAndRemoveAccessibilityActions() {
        val comedian = comedian(id = 31, name = "Avery Example")
        val club = FavoriteClubItem(id = 41, name = "Comedy Room", imageUrl = "", isFavorite = true)
        val podcast =
            FavoritePodcastItem(
                id = 51,
                title = "Good One",
                episodeCount = 20,
                isFavorite = true,
                authorName = "Comedy Network",
                imageUrl = null,
            )
        val opened = mutableListOf<LibrarySavedDestination>()
        val removedComedians = mutableListOf<String>()
        val removedClubs = mutableListOf<Int>()
        val removedPodcasts = mutableListOf<Int>()

        compose.setContent {
            LaughTrackTheme {
                LibraryScreen(
                    signedIn = true,
                    onOpenProfile = {},
                    snapshotOverride =
                        FavoritesSnapshot(
                            comedians = listOf(comedian),
                            clubs = listOf(club),
                            podcasts = listOf(podcast),
                        ),
                    onOpenSaved = opened::add,
                    onToggleComedian = removedComedians::add,
                    onToggleClub = removedClubs::add,
                    onTogglePodcast = removedPodcasts::add,
                )
            }
        }

        assertFallbackIsVisible(RemoteImageFallback.Comedian)
        compose.onNodeWithText(comedian.name).performScrollTo().performClick()
        compose.onNodeWithContentDescription("Remove ${comedian.name}").performScrollTo().performClick()

        assertFallbackIsVisible(RemoteImageFallback.Club)
        compose.onNodeWithText(club.name).performScrollTo().performClick()
        compose.onNodeWithContentDescription("Remove ${club.name}").performScrollTo().performClick()

        assertFallbackIsVisible(RemoteImageFallback.Podcast)
        compose.onNodeWithText(podcast.title).performScrollTo().performClick()
        compose.onNodeWithContentDescription("Remove ${podcast.title}").performScrollTo().performClick()

        compose.runOnIdle {
            assertEquals(
                listOf(
                    LibrarySavedDestination.Comedian(comedian.id),
                    LibrarySavedDestination.Club(club.id),
                    LibrarySavedDestination.Podcast(podcast.id),
                ),
                opened,
            )
            assertEquals(listOf(comedian.uuid), removedComedians)
            assertEquals(listOf(club.id), removedClubs)
            assertEquals(listOf(podcast.id), removedPodcasts)
        }
    }

    private fun assertFallbackIsVisible(fallback: RemoteImageFallback) {
        compose
            .onNodeWithTag(RemoteImageTestTags.fallback(fallback))
            .performScrollTo()
            .assertIsDisplayed()
    }

    private fun savedShowsSnapshot(
        loadedIds: IntRange,
        page: Int = 1,
        total: Int,
        totalPages: Int,
    ) = SavedShowsSnapshot(
        upcoming =
            SavedShowsCollection(
                shows = loadedIds.map(::show),
                page = page,
                total = total,
                totalPages = totalPages,
            ),
    )

    private fun show(id: Int) =
        Show(
            id = id,
            clubId = 7,
            date = "2026-08-15T20:00:00-04:00",
            imageUrl = "",
            name = "Saved show $id",
            clubName = "Comedy Room",
            clubCity = "New York",
            timezone = "America/New_York",
        )

    private fun comedian(
        id: Int,
        name: String,
    ) = ComedianSearchItem(
        id = id,
        uuid = "comedian-$id",
        name = name,
        imageUrl = "",
        socialData = SocialData(id = id),
        showCount = 2,
    )
}
