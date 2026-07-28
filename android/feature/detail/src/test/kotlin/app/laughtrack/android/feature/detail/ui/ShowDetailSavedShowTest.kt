package app.laughtrack.android.feature.detail.ui

import app.laughtrack.android.core.data.auth.CurrentUserState
import app.laughtrack.android.core.data.savedshows.SavedShowMutationResult
import app.laughtrack.android.core.data.savedshows.SavedShowsSnapshot
import app.laughtrack.android.core.network.generated.api.ShowsApi
import app.laughtrack.android.core.network.generated.model.ShowDetail
import app.laughtrack.android.core.network.generated.model.ShowDetailClub
import app.laughtrack.android.core.network.generated.model.ShowDetailCta
import app.laughtrack.android.core.network.generated.model.ShowDetailResponse
import app.laughtrack.android.core.testing.throwingApi
import app.laughtrack.android.feature.detail.data.ShowDetailRepository
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
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test
import retrofit2.Response
import java.time.Instant

@OptIn(ExperimentalCoroutinesApi::class)
class ShowDetailSavedShowTest {
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
    fun loading_show_also_loads_repository_saved_state() =
        runTest {
            var loadedSavedShowId: Int? = null
            val viewModel =
                viewModel(
                    loadSavedState = { showId ->
                        loadedSavedShowId = showId
                        true
                    },
                )

            viewModel.load(42)
            advanceUntilIdle()

            assertEquals(42, loadedSavedShowId)
        }

    @Test
    fun toggle_uses_inverse_snapshot_value_and_publishes_offline_feedback() =
        runTest {
            val snapshot = MutableStateFlow(SavedShowsSnapshot(values = mapOf(42 to false)))
            var mutation: Pair<Int, Boolean>? = null
            val viewModel =
                viewModel(
                    snapshot = snapshot,
                    setSaved = { showId, isSaved ->
                        mutation = showId to isSaved
                        SavedShowMutationResult.Queued(isSaved)
                    },
                )

            viewModel.toggleSaved(42)
            advanceUntilIdle()

            assertEquals(42 to true, mutation)
            assertEquals(
                "Saved offline. LaughTrack will sync this when you're connected.",
                viewModel.savedShowMessage.value,
            )
        }

    @Test
    fun queued_unsave_uses_removal_feedback() =
        runTest {
            val viewModel =
                viewModel(
                    snapshot = MutableStateFlow(SavedShowsSnapshot(values = mapOf(42 to true))),
                    setSaved = { _, isSaved -> SavedShowMutationResult.Queued(isSaved) },
                )

            viewModel.toggleSaved(42)
            advanceUntilIdle()

            assertEquals(
                "Removal queued. LaughTrack will sync this when you're connected.",
                viewModel.savedShowMessage.value,
            )
        }

    @Test
    fun pending_state_is_exposed_for_the_current_show() {
        val snapshot = MutableStateFlow(SavedShowsSnapshot(pending = setOf(42)))
        val viewModel = viewModel(snapshot = snapshot)

        assertTrue(42 in viewModel.savedShowsSnapshot.value.pending)
        assertFalse(41 in viewModel.savedShowsSnapshot.value.pending)
    }

    @Test
    fun past_unsaved_show_is_hidden_but_saved_show_can_be_removed() {
        val now = Instant.parse("2026-07-28T12:00:00Z")
        val past = show("2026-07-27T20:00:00Z")
        val future = show("2026-07-29T20:00:00Z")

        assertFalse(showDetailSavedActionVisible(past, isSaved = false, now = now))
        assertTrue(showDetailSavedActionVisible(past, isSaved = true, now = now))
        assertTrue(showDetailSavedActionVisible(future, isSaved = false, now = now))
    }

    private fun viewModel(
        snapshot: MutableStateFlow<SavedShowsSnapshot> = MutableStateFlow(SavedShowsSnapshot()),
        loadSavedState: suspend (Int) -> Boolean? = { null },
        setSaved: suspend (Int, Boolean) -> SavedShowMutationResult = { _, isSaved ->
            SavedShowMutationResult.Updated(isSaved)
        },
    ) = ShowDetailViewModel(
        repository =
            ShowDetailRepository(
                showsApi =
                    object : ShowsApi by throwingApi() {
                        override suspend fun getShow(id: Int): Response<ShowDetailResponse> =
                            Response.success(
                                ShowDetailResponse(
                                    data = show("2026-07-29T20:00:00Z"),
                                    relatedShows = emptyList(),
                                ),
                            )
                    },
                apiBaseUrl = "https://api.example.com",
            ),
        currentUserState = CurrentUserState(),
        savedShowsSnapshot = snapshot,
        loadSavedShowState = loadSavedState,
        setSavedShow = setSaved,
    )

    private companion object {
        fun show(date: String) =
            ShowDetail(
                id = 42,
                date = date,
                imageUrl = "",
                showPageUrl = "https://example.com/show/42",
                club = ShowDetailClub(id = 7, name = "Comedy Room", imageUrl = ""),
                cta = ShowDetailCta(label = "Tickets", isSoldOut = false),
                name = "Comedy Show",
            )
    }
}
