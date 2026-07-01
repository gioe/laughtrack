package app.laughtrack.android.feature.home.ui

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import app.laughtrack.android.core.data.UiState
import app.laughtrack.android.core.data.search.SearchSeed
import app.laughtrack.android.core.data.search.SearchShortcut
import app.laughtrack.android.core.data.search.SearchShortcutCoordinator
import app.laughtrack.android.core.network.generated.model.ClubListItem
import app.laughtrack.android.core.network.generated.model.ComedianListItem
import app.laughtrack.android.core.network.generated.model.HomeFeed
import app.laughtrack.android.core.network.generated.model.HomeFeedPodcast
import app.laughtrack.android.core.network.generated.model.Show
import app.laughtrack.android.feature.home.data.HomeFeedCache
import app.laughtrack.android.feature.home.data.HomeFeedRepository
import app.laughtrack.android.feature.home.location.HomeLocationResolver
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import javax.inject.Inject

data class HomeUiState(
    val feed: UiState<HomeFeed> = UiState.Idle,
    val zip: String? = null,
    val isResolvingLocation: Boolean = false,
) {
    private val loadedFeed: HomeFeed?
        get() = (feed as? UiState.Success<HomeFeed>)?.value

    /** The ZIP the feed is actually scoped to: the feed's hero ZIP wins, else the requested ZIP. */
    private val activeZip: String?
        get() = loadedFeed?.hero?.zipCode?.takeIf { it.isNotBlank() } ?: zip

    val locationTitle: String
        get() {
            val hero = loadedFeed?.hero
            val city = hero?.city
            val state = hero?.state
            return if (!city.isNullOrBlank() && !state.isNullOrBlank()) {
                "Near $city, $state"
            } else {
                activeZip?.let { "ZIP $it" } ?: "Set your location"
            }
        }

    val locationSubtitle: String
        get() =
            activeZip?.let { "Saved ZIP - ${HomeFeedRepository.DEFAULT_DISTANCE_MILES} mi" }
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
        private val cache: HomeFeedCache,
        private val locationResolver: HomeLocationResolver,
        private val shortcutCoordinator: SearchShortcutCoordinator,
    ) : ViewModel() {
        private val _state = MutableStateFlow(HomeUiState(feed = UiState.Loading))
        val state: StateFlow<HomeUiState> = _state.asStateFlow()

        /** The ZIP currently driving the feed (null = server-inferred from the caller). */
        private var currentZip: String? = null

        init {
            load(currentZip)
        }

        fun retry() {
            load(currentZip)
        }

        /** Apply a user-typed ZIP once it is a full 5 digits, and reload the feed. */
        fun setManualZip(zip: String) {
            val clean = zip.filter(Char::isDigit).take(ZIP_LENGTH)
            if (clean.length == ZIP_LENGTH && clean != currentZip) {
                currentZip = clean
                load(clean)
            }
        }

        /** Resolve the device location to a ZIP (post permission grant) and reload. */
        fun useDeviceLocation() {
            viewModelScope.launch {
                _state.update { it.copy(isResolvingLocation = true) }
                val zip = locationResolver.resolveZip()
                _state.update { it.copy(isResolvingLocation = false) }
                if (zip != null && zip != currentZip) {
                    currentZip = zip
                    load(zip)
                }
            }
        }

        /** Publish a shortcut seed (carrying the current location) for the Search tab. */
        fun requestShortcut(shortcut: SearchShortcut) {
            shortcutCoordinator.request(
                SearchSeed(
                    shortcut = shortcut,
                    zip = currentZip,
                    distanceMiles = HomeFeedRepository.DEFAULT_DISTANCE_MILES,
                ),
            )
        }

        private fun load(zip: String?) {
            val distance = HomeFeedRepository.DEFAULT_DISTANCE_MILES
            viewModelScope.launch {
                // Render the persisted snapshot immediately, if any, so relaunch is instant;
                // otherwise show the skeleton while the network call is in flight.
                val cached = cache.get(zip, distance)
                _state.value =
                    HomeUiState(
                        feed = cached?.let { UiState.Success(it) } ?: UiState.Loading,
                        zip = zip,
                    )
                runCatching { repository.getHomeFeed(zip, distance) }
                    .onSuccess { feed ->
                        cache.set(zip, distance, feed)
                        _state.value = HomeUiState(feed = UiState.Success(feed), zip = zip)
                    }
                    .onFailure { error ->
                        // Keep the cached feed visible on a refresh failure; only surface an
                        // error when there was nothing to fall back on.
                        if (cached == null) {
                            _state.value = HomeUiState(feed = UiState.Failure(error), zip = zip)
                        }
                    }
            }
        }

        private companion object {
            const val ZIP_LENGTH = 5
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
