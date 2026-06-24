package app.laughtrack.android.feature.onboarding

import app.laughtrack.android.core.analytics.AnalyticsManager
import app.laughtrack.android.core.network.generated.model.ComedianSearchItem
import app.laughtrack.android.core.network.generated.model.SocialData
import app.laughtrack.android.feature.onboarding.data.ComedianOnboardingRepository
import app.laughtrack.android.feature.onboarding.push.SoftPushPromptCoordinator
import app.laughtrack.android.feature.onboarding.ui.ComedianOnboardingViewModel
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.ExperimentalCoroutinesApi
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

@OptIn(ExperimentalCoroutinesApi::class)
class ComedianOnboardingViewModelTest {
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
    fun loads_more_suggestions_without_duplicates_and_updates_favorite_count() = runTest {
        val repository = FakeRepository(
            suggestionPages = listOf(
                listOf(comedian("a"), comedian("b", isFavorite = true)),
                listOf(comedian("b", isFavorite = true), comedian("c")),
            ),
        )
        val viewModel = ComedianOnboardingViewModel(
            repository = repository,
            softPushPromptCoordinator = FakeSoftPushPromptCoordinator(),
            analytics = AnalyticsManager(emptyList()),
        )

        advanceUntilIdle()
        viewModel.passComedian("a")
        viewModel.loadMoreSuggestions()
        advanceUntilIdle()
        viewModel.toggleFavorite("c")
        advanceUntilIdle()

        val state = viewModel.state.value
        assertEquals(listOf("a", "b", "c"), state.suggestions.map { it.uuid })
        assertEquals(2, state.favoriteCount)
        assertTrue(state.passed.contains("a"))
        assertTrue(repository.favoriteAdds.contains("c"))
    }

    @Test
    fun continue_marks_onboarding_completed() = runTest {
        val repository = FakeRepository(suggestionPages = listOf(listOf(comedian("a"))))
        val viewModel = ComedianOnboardingViewModel(
            repository = repository,
            softPushPromptCoordinator = FakeSoftPushPromptCoordinator(),
            analytics = AnalyticsManager(emptyList()),
        )

        advanceUntilIdle()
        viewModel.continueOnboarding()
        advanceUntilIdle()

        assertTrue(repository.completed)
        assertTrue(viewModel.state.value.isComplete)
    }

    @Test
    fun third_new_favorite_requests_soft_prompt() = runTest {
        val prompt = FakeSoftPushPromptCoordinator()
        val repository = FakeRepository(
            suggestionPages = listOf(
                listOf(comedian("a"), comedian("b"), comedian("c")),
            ),
        )
        val viewModel = ComedianOnboardingViewModel(
            repository = repository,
            softPushPromptCoordinator = prompt,
            analytics = AnalyticsManager(emptyList()),
        )

        advanceUntilIdle()
        viewModel.toggleFavorite("a")
        viewModel.toggleFavorite("b")
        viewModel.toggleFavorite("c")
        advanceUntilIdle()

        assertEquals(3, prompt.favoriteSignals)
        assertTrue(prompt.shouldShowPrompt)
        assertTrue(viewModel.state.value.showSoftPushPrompt)
    }

    @Test
    fun search_mode_uses_search_results_without_clearing_deck_favorites() = runTest {
        val repository = FakeRepository(
            suggestionPages = listOf(listOf(comedian("a"))),
            searchResults = listOf(comedian("z")),
        )
        val viewModel = ComedianOnboardingViewModel(
            repository = repository,
            softPushPromptCoordinator = FakeSoftPushPromptCoordinator(),
            analytics = AnalyticsManager(emptyList()),
        )

        advanceUntilIdle()
        viewModel.toggleFavorite("a")
        viewModel.search("z")
        advanceUntilIdle()

        val state = viewModel.state.value
        assertTrue(state.isSearchMode)
        assertEquals(listOf("z"), state.searchResults.map { it.uuid })
        assertEquals(1, state.favoriteCount)
    }

    private class FakeRepository(
        private val suggestionPages: List<List<ComedianSearchItem>>,
        private val searchResults: List<ComedianSearchItem> = emptyList(),
    ) : ComedianOnboardingRepository {
        private var suggestionIndex = 0
        val favoriteAdds = mutableListOf<String>()
        val favoriteRemoves = mutableListOf<String>()
        var completed = false

        override suspend fun suggestions(): List<ComedianSearchItem> =
            suggestionPages.getOrElse(suggestionIndex++) { emptyList() }

        override suspend fun search(query: String): List<ComedianSearchItem> = searchResults

        override suspend fun setFavorite(uuid: String, isFavorite: Boolean): Boolean {
            if (isFavorite) favoriteAdds += uuid else favoriteRemoves += uuid
            return isFavorite
        }

        override suspend fun completeOnboarding() {
            completed = true
        }
    }

    private class FakeSoftPushPromptCoordinator : SoftPushPromptCoordinator {
        var favoriteSignals = 0
        var shouldShowPrompt = false

        override suspend fun onFavoriteAdded(): Boolean {
            favoriteSignals += 1
            shouldShowPrompt = favoriteSignals >= 3
            return shouldShowPrompt
        }

        override suspend fun deferPrompt() {
            shouldShowPrompt = false
        }
    }

    private fun comedian(uuid: String, isFavorite: Boolean = false) = ComedianSearchItem(
        id = uuid.first().code,
        uuid = uuid,
        name = "Comedian $uuid",
        imageUrl = "https://example.com/$uuid.jpg",
        socialData = SocialData(id = uuid.first().code),
        showCount = 1,
        isFavorite = isFavorite,
    )
}
