package app.laughtrack.android.feature.home.ui

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import app.laughtrack.android.core.data.location.HomeLocationState
import app.laughtrack.android.core.data.runCatchingCancellable
import app.laughtrack.android.core.network.generated.model.ClubListItem
import app.laughtrack.android.core.network.generated.model.ComedianListItem
import app.laughtrack.android.core.network.generated.model.HomeFeed
import app.laughtrack.android.core.network.generated.model.HomeFeedPodcast
import app.laughtrack.android.core.network.generated.model.Show
import app.laughtrack.android.core.ui.UiState
import app.laughtrack.android.feature.home.data.HomeFeedCache
import app.laughtrack.android.feature.home.data.HomeFeedRepository
import app.laughtrack.android.feature.home.location.HomeLocationResolver
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.Job
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import javax.inject.Inject

data class HomeUiState(
    val feed: UiState<HomeFeed> = UiState.Idle,
    val zip: String? = null,
    val distanceMiles: Int = HomeFeedRepository.DEFAULT_DISTANCE_MILES,
    val isResolvingLocation: Boolean = false,
) {
    private val loadedFeed: HomeFeed?
        get() = (feed as? UiState.Success<HomeFeed>)?.value

    /**
     * The ZIP the feed is actually scoped to: the feed's hero ZIP wins, else the
     * requested ZIP. Public so the location editor sheet can prefill its field
     * with the same ZIP the Saved ZIP subtitle reports (TASK-3697).
     */
    val activeZip: String?
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

    /**
     * True while the user has explicitly set a location or radius — exactly when
     * clearLocation() would change anything. Gates the sheet's Clear action
     * (mirrors iOS, which shows Clear only when nearbyPreference is non-nil);
     * the hero/server-inferred fallback alone must NOT count as clearable.
     */
    val hasExplicitLocation: Boolean
        get() = zip != null || distanceMiles != HomeFeedRepository.DEFAULT_DISTANCE_MILES

    val locationSubtitle: String
        get() =
            activeZip?.let { "Saved ZIP - $distanceMiles mi" }
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
        private val homeLocationState: HomeLocationState,
    ) : ViewModel() {
        private val _state = MutableStateFlow(HomeUiState(feed = UiState.Loading))
        val state: StateFlow<HomeUiState> = _state.asStateFlow()

        /** The ZIP currently driving the feed (null = server-inferred from the caller). */
        private var currentZip: String? = null

        /** The geo radius currently driving the feed, in miles. */
        private var currentDistance: Int = HomeFeedRepository.DEFAULT_DISTANCE_MILES
        private var loadJob: Job? = null

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

        /** Set the feed geo radius (from the sheet's distance chips) and reload. */
        fun setDistance(miles: Int) {
            if (miles != currentDistance) {
                currentDistance = miles
                load(currentZip)
            }
        }

        /**
         * Drop the explicit location back to the server-inferred default area,
         * resetting the radius too (mirrors iOS clearNearbyPreference).
         */
        fun clearLocation() {
            if (currentZip != null || currentDistance != HomeFeedRepository.DEFAULT_DISTANCE_MILES) {
                currentZip = null
                currentDistance = HomeFeedRepository.DEFAULT_DISTANCE_MILES
                load(null)
            }
        }

        private fun load(zip: String?) {
            loadJob?.cancel()
            val distance = currentDistance
            loadJob =
                viewModelScope.launch {
                    // Render the persisted snapshot immediately, if any, so relaunch is instant;
                    // otherwise show the skeleton while the network call is in flight.
                    val cached = cache.get(zip, distance)
                    publishState(
                        HomeUiState(
                            feed = cached?.let { UiState.Success(it) } ?: UiState.Loading,
                            zip = zip,
                            distanceMiles = distance,
                        ),
                    )
                    runCatchingCancellable { repository.getHomeFeed(zip, distance) }
                        .onSuccess { feed ->
                            cache.set(zip, distance, feed)
                            publishState(
                                HomeUiState(
                                    feed = UiState.Success(feed),
                                    zip = zip,
                                    distanceMiles = distance,
                                ),
                            )
                        }
                        .onFailure { error ->
                            // Keep the cached feed visible on a refresh failure; only surface an
                            // error when there was nothing to fall back on.
                            if (cached == null) {
                                publishState(
                                    HomeUiState(
                                        feed = UiState.Failure(error),
                                        zip = zip,
                                        distanceMiles = distance,
                                    ),
                                )
                            }
                        }
                }
        }

        /**
         * Publish the new feed state and mirror its active area into the shared
         * HomeLocationState so Search seeds its geo pivots from the same location
         * Home is showing (TASK-3698, mirrors iOS SearchRootModel seeding).
         */
        private fun publishState(state: HomeUiState) {
            _state.value = state
            homeLocationState.update(state.activeZip, state.distanceMiles)
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
