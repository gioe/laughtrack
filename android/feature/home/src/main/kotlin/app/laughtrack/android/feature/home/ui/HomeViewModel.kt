package app.laughtrack.android.feature.home.ui

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import app.laughtrack.android.core.analytics.AnalyticsManager
import app.laughtrack.android.core.data.location.HomeLocationState
import app.laughtrack.android.core.data.runCatchingCancellable
import app.laughtrack.android.core.network.generated.model.ClubListItem
import app.laughtrack.android.core.network.generated.model.ComedianListItem
import app.laughtrack.android.core.network.generated.model.HomeFeed
import app.laughtrack.android.core.network.generated.model.HomeFeedPodcast
import app.laughtrack.android.core.network.generated.model.HomeFeedPodcastEpisode
import app.laughtrack.android.core.network.generated.model.Show
import app.laughtrack.android.core.ui.UiState
import app.laughtrack.android.feature.home.HomeDiscoverRailAttribution
import app.laughtrack.android.feature.home.data.HomeFeedCache
import app.laughtrack.android.feature.home.data.HomeFeedRepository
import app.laughtrack.android.feature.home.homeDiscoverRailSelectedEvent
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
    internal val loadedFeed: HomeFeed?
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

    val activeLocationLabel: String?
        get() {
            val hero = loadedFeed?.hero
            return listOfNotNull(hero?.city, hero?.state).joinToString(", ").ifBlank { null }
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
        get() =
            loadedFeed
                ?.let { feed ->
                    dedupeShows(feed.showsTonight + feed.hero.shows + feed.trendingThisWeek)
                        .filterNot(::isSoldOut)
                        .take(HOME_HERO_DISPLAY_LIMIT)
                }.orEmpty()

    val trendingThisWeek: List<Show>
        get() =
            loadedFeed?.let { feed ->
                val tonightIds = (feed.showsTonight + feed.hero.shows).map { it.id }.toSet()
                dedupeShows((feed.trendingThisWeek + feed.moreNearYou).filterNot { it.id in tonightIds })
                    .filterNot(::isSoldOut)
            }.orEmpty()

    val followedComedianShows: List<Show>
        get() = loadedFeed?.followedComedianShows.orEmpty().filterNot(::isSoldOut)

    val comedians: List<ComedianListItem>
        get() = loadedFeed?.let { dedupeComedians(it.comediansNearYou + it.trendingComedians) }.orEmpty()

    val clubs: List<ClubListItem>
        get() = loadedFeed?.popularClubs.orEmpty()

    val podcasts: List<HomeFeedPodcast>
        get() = loadedFeed?.trendingPodcasts.orEmpty()

    val podcastEpisodes: List<HomeFeedPodcastEpisode>
        get() = loadedFeed?.podcastEpisodes.orEmpty().distinctBy { it.id }
}

@HiltViewModel
class HomeViewModel
    @Inject
    constructor(
        private val repository: HomeFeedRepository,
        private val cache: HomeFeedCache,
        private val locationResolver: HomeLocationResolver,
        private val homeLocationState: HomeLocationState,
        private val analytics: AnalyticsManager,
    ) : ViewModel() {
        private val _state = MutableStateFlow(HomeUiState(feed = UiState.Loading))
        val state: StateFlow<HomeUiState> = _state.asStateFlow()

        /** The ZIP currently driving the feed (null = server-inferred from the caller). */
        private var currentZip: String? = null

        /** The geo radius currently driving the feed, in miles. */
        private var currentDistance: Int = HomeFeedRepository.DEFAULT_DISTANCE_MILES
        private var currentSignedIn = false
        private var loadJob: Job? = null

        init {
            // Mirror every settled feed publication into the shared HomeLocationState
            // so Search seeds its geo pivots from the same area Home is showing
            // (TASK-3698, mirrors iOS SearchRootModel seeding). Derived from the
            // state flow so no publication path can silently bypass the mirror, and
            // gated on Success so transient Loading states (a cache-miss reload
            // publishes zip=null before the hero answers) never blank the shared
            // location mid-reload.
            viewModelScope.launch {
                state.collect { snapshot ->
                    if (snapshot.feed is UiState.Success<*>) {
                        homeLocationState.update(
                            snapshot.activeZip,
                            snapshot.distanceMiles,
                            snapshot.activeLocationLabel,
                        )
                    }
                }
            }
            load(currentZip)
        }

        fun retry() {
            load(currentZip)
        }

        internal fun onDiscoverRailSelected(attribution: HomeDiscoverRailAttribution) {
            analytics.logEvent(homeDiscoverRailSelectedEvent(attribution))
        }

        /** Strip account-scoped content immediately, then refresh for the new session. */
        fun onAuthStateChanged(signedIn: Boolean) {
            val signingOut = currentSignedIn && !signedIn
            if (signingOut) {
                _state.update { snapshot ->
                    val feed = (snapshot.feed as? UiState.Success<HomeFeed>)?.value
                    if (feed == null) {
                        snapshot
                    } else {
                        snapshot.copy(feed = UiState.Success(feed.withoutAccountScopedContent()))
                    }
                }
            }
            if (signedIn != currentSignedIn) {
                currentSignedIn = signedIn
                load(currentZip)
            }
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
            val previousFeed = (_state.value.feed as? UiState.Success<HomeFeed>)?.value
            loadJob =
                viewModelScope.launch {
                    // Render the persisted snapshot immediately, if any, so relaunch is instant;
                    // otherwise keep the last feed mounted during a refresh. Only show the
                    // skeleton when there is no prior content to preserve.
                    val cached = cache.get(zip, distance)
                    val fallbackFeed = cached ?: previousFeed
                    _state.value =
                        HomeUiState(
                            feed = fallbackFeed?.let { UiState.Success(it) } ?: UiState.Loading,
                            zip = zip,
                            distanceMiles = distance,
                        )
                    runCatchingCancellable { repository.getHomeFeed(zip, distance) }
                        .onSuccess { feed ->
                            cache.set(zip, distance, feed)
                            val visibleFeed = if (currentSignedIn) feed else feed.withoutFollowedShows()
                            _state.value =
                                HomeUiState(
                                    feed = UiState.Success(visibleFeed),
                                    zip = zip,
                                    distanceMiles = distance,
                                )
                        }
                        .onFailure { error ->
                            // Keep fallback content visible on a refresh failure; only surface an
                            // error when there was nothing to fall back on.
                            if (fallbackFeed == null) {
                                _state.value =
                                    HomeUiState(
                                        feed = UiState.Failure(error),
                                        zip = zip,
                                        distanceMiles = distance,
                                    )
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

private fun HomeFeed.withoutFollowedShows(): HomeFeed = copy(followedComedianShows = emptyList())

private fun HomeFeed.withoutAccountScopedContent(): HomeFeed =
    copy(
        followedComedianShows = emptyList(),
        podcastEpisodes = null,
        dynamicRails = null,
        railPlan = null,
    )

private fun isSoldOut(show: Show): Boolean {
    if (show.soldOut == true) return true
    val tickets = show.tickets.orEmpty()
    return tickets.isNotEmpty() && tickets.all { it.soldOut == true }
}

private const val HOME_HERO_DISPLAY_LIMIT = 5

private fun dedupeComedians(comedians: List<ComedianListItem>): List<ComedianListItem> {
    val seen = mutableSetOf<String>()
    return comedians.filter { comedian -> seen.add(comedian.uuid) }
}
