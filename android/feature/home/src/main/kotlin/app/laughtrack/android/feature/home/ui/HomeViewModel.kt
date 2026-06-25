package app.laughtrack.android.feature.home.ui

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import app.laughtrack.android.core.data.UiState
import app.laughtrack.android.core.network.generated.model.ClubListItem
import app.laughtrack.android.core.network.generated.model.ComedianListItem
import app.laughtrack.android.core.network.generated.model.HomeFeed
import app.laughtrack.android.core.network.generated.model.HomeFeedPodcast
import app.laughtrack.android.core.network.generated.model.Show
import app.laughtrack.android.feature.home.data.HomeFeedRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

data class HomeUiState(
    val feed: UiState<HomeFeed> = UiState.Idle,
) {
    private val loadedFeed: HomeFeed?
        get() = (feed as? UiState.Success<HomeFeed>)?.value

    val locationTitle: String
        get() {
            val hero = loadedFeed?.hero ?: return "Set your location"
            val city = hero.city
            val state = hero.state
            return if (!city.isNullOrBlank() && !state.isNullOrBlank()) {
                "Near $city, $state"
            } else if (!hero.zipCode.isNullOrBlank()) {
                "ZIP ${hero.zipCode}"
            } else {
                "Set your location"
            }
        }

    val locationSubtitle: String
        get() =
            loadedFeed?.hero?.zipCode?.let { "Saved ZIP - ${HomeFeedRepository.DEFAULT_DISTANCE_MILES} mi" }
                ?: "Get shows, clubs, and comedians near you."

    val showsTonight: List<Show>
        get() = loadedFeed?.let { dedupeShows(it.showsTonight + it.hero.shows) }.orEmpty()

    val trendingThisWeek: List<Show>
        get() =
            loadedFeed?.let { feed ->
                val tonightIds = showsTonight.map { it.id }.toSet()
                dedupeShows((feed.trendingThisWeek + feed.moreNearYou).filterNot { it.id in tonightIds })
            }.orEmpty()

    val comedians: List<ComedianListItem>
        get() = loadedFeed?.let { dedupeComedians(it.comediansNearYou + it.trendingComedians) }.orEmpty()

    val clubs: List<ClubListItem>
        get() = loadedFeed?.popularClubs.orEmpty()

    val podcasts: List<HomeFeedPodcast>
        get() = loadedFeed?.trendingPodcasts.orEmpty()
}

@HiltViewModel
class HomeViewModel
    @Inject
    constructor(
        private val repository: HomeFeedRepository,
    ) : ViewModel() {
        private val _state = MutableStateFlow(HomeUiState(feed = UiState.Loading))
        val state: StateFlow<HomeUiState> = _state.asStateFlow()

        init {
            load()
        }

        fun retry() {
            load()
        }

        private fun load() {
            _state.value = HomeUiState(feed = UiState.Loading)
            viewModelScope.launch {
                runCatching { repository.getHomeFeed() }
                    .onSuccess { _state.value = HomeUiState(feed = UiState.Success(it)) }
                    .onFailure { _state.value = HomeUiState(feed = UiState.Failure(it)) }
            }
        }
    }

private fun dedupeShows(shows: List<Show>): List<Show> {
    val seen = mutableSetOf<Int>()
    return shows.filter { show -> seen.add(show.id) }
}

private fun dedupeComedians(comedians: List<ComedianListItem>): List<ComedianListItem> {
    val seen = mutableSetOf<String>()
    return comedians.filter { comedian -> seen.add(comedian.uuid) }
}
