package app.laughtrack.android.feature.library

import app.laughtrack.android.core.data.savedshows.SavedShowPeriod
import app.laughtrack.android.core.data.savedshows.SavedShowsCollection
import app.laughtrack.android.core.data.savedshows.SavedShowsSnapshot
import app.laughtrack.android.core.network.generated.model.Show
import app.laughtrack.android.core.testing.signedOutFavoritesRepository
import app.laughtrack.android.core.testing.throwingApi
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.test.StandardTestDispatcher
import kotlinx.coroutines.test.advanceUntilIdle
import kotlinx.coroutines.test.resetMain
import kotlinx.coroutines.test.runTest
import kotlinx.coroutines.test.setMain
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test
import java.math.BigDecimal

@OptIn(ExperimentalCoroutinesApi::class)
class LibrarySavedShowsTest {
    private val dispatcher = StandardTestDispatcher()

    @Before
    fun setUp() {
        Dispatchers.setMain(dispatcher)
    }

    @After
    fun tearDown() {
        Dispatchers.resetMain()
    }

    @Test
    fun signedInRefreshLoadsUpcomingAndPastSavedShowsWithoutReplacingFavoritesSource() =
        runTest {
            val source = RecordingSavedShowsSource()
            val favorites = signedOutFavoritesRepository(throwingApi())
            val viewModel = LibraryViewModel(favorites, source)

            viewModel.refresh(signedIn = true)
            advanceUntilIdle()

            assertEquals(
                listOf(SavedShowPeriod.UPCOMING, SavedShowPeriod.PAST),
                source.refreshedPeriods,
            )
            assertTrue(viewModel.snapshot.value.comedians.isEmpty())
            assertEquals(source.snapshot.value, viewModel.savedShowsSnapshot.value)
        }

    @Test
    fun signedOutRefreshResetsSavedShowsAndDoesNotRequestEitherCollection() =
        runTest {
            val source =
                RecordingSavedShowsSource(
                    SavedShowsSnapshot(
                        upcoming = SavedShowsCollection(shows = listOf(show(id = 41))),
                        past = SavedShowsCollection(shows = listOf(show(id = 42))),
                    ),
                )
            val viewModel = LibraryViewModel(signedOutFavoritesRepository(throwingApi()), source)

            viewModel.refresh(signedIn = false)
            advanceUntilIdle()

            assertEquals(1, source.resetCount)
            assertTrue(source.refreshedPeriods.isEmpty())
            assertEquals(SavedShowsSnapshot(), viewModel.savedShowsSnapshot.value)
        }

    @Test
    fun retryRefreshesOnlyTheRequestedSavedShowCollection() =
        runTest {
            val source = RecordingSavedShowsSource()
            val viewModel = LibraryViewModel(signedOutFavoritesRepository(throwingApi()), source)

            viewModel.refreshSavedShows(SavedShowPeriod.PAST)
            advanceUntilIdle()

            assertEquals(listOf(SavedShowPeriod.PAST), source.refreshedPeriods)
        }

    @Test
    fun savedShowCollectionsBookendTheCanonicalLibraryHierarchy() {
        assertEquals(
            listOf(
                "Next Up",
                "Saved",
                "History",
            ),
            LibrarySection.entries.map { it.presentation.title },
        )
    }

    @Test
    fun collectionPresentationDistinguishesLoadingEmptyErrorAndContent() {
        val show = show(id = 51)

        assertEquals(
            SavedShowCollectionPresentationState.Loading,
            savedShowCollectionState(
                collection = SavedShowsCollection(),
                initialRefreshComplete = false,
            ),
        )
        assertEquals(
            SavedShowCollectionPresentationState.Loading,
            savedShowCollectionState(SavedShowsCollection(isLoading = true)),
        )
        assertEquals(
            SavedShowCollectionPresentationState.Empty,
            savedShowCollectionState(SavedShowsCollection()),
        )
        assertEquals(
            SavedShowCollectionPresentationState.Error("Try again"),
            savedShowCollectionState(SavedShowsCollection(errorMessage = "Try again")),
        )
        assertEquals(
            SavedShowCollectionPresentationState.Content(listOf(show)),
            savedShowCollectionState(SavedShowsCollection(shows = listOf(show))),
        )
        assertEquals(
            SavedShowCollectionPresentationState.Content(
                shows = listOf(show),
                isRefreshing = true,
            ),
            savedShowCollectionState(
                SavedShowsCollection(
                    shows = listOf(show),
                    isLoading = true,
                ),
            ),
        )
        assertEquals(
            SavedShowCollectionPresentationState.Content(
                shows = listOf(show),
                errorMessage = "Try again",
            ),
            savedShowCollectionState(
                SavedShowsCollection(
                    shows = listOf(show),
                    errorMessage = "Try again",
                ),
            ),
        )
    }

    @Test
    fun canonicalSavedShowRowNavigationUsesTheShowIdentifier() {
        assertEquals(73, savedShowNavigationId(show(id = 73)))
    }

    @Test
    fun savedShowTicketPriceUsesTheLowestAvailablePrice() {
        assertEquals(
            "$18.50",
            savedShowPriceLabel(listOf(BigDecimal("25.00"), BigDecimal("18.50"))),
        )
        assertEquals("$20", savedShowPriceLabel(listOf(BigDecimal("20.00"))))
        assertEquals(null, savedShowPriceLabel(emptyList()))
    }

    private class RecordingSavedShowsSource(
        initial: SavedShowsSnapshot = SavedShowsSnapshot(),
    ) : LibrarySavedShowsSource {
        override val snapshot = MutableStateFlow(initial)
        val refreshedPeriods = mutableListOf<SavedShowPeriod>()
        var resetCount = 0

        override suspend fun refresh(period: SavedShowPeriod): Boolean {
            refreshedPeriods += period
            return true
        }

        override fun resetSignedOut() {
            resetCount += 1
            snapshot.value = SavedShowsSnapshot()
        }
    }

    private fun show(id: Int) =
        Show(
            id = id,
            clubId = 7,
            date = "2026-08-15T20:00:00-04:00",
            imageUrl = "https://example.com/show.jpg",
            name = "Saved show $id",
            clubName = "Comedy Room",
            clubCity = "New York",
            timezone = "America/New_York",
        )
}
