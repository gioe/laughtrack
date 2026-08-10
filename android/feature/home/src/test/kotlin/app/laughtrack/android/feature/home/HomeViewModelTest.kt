package app.laughtrack.android.feature.home

import app.laughtrack.android.core.analytics.AnalyticsManager
import app.laughtrack.android.core.data.location.HomeLocation
import app.laughtrack.android.core.data.location.HomeLocationState
import app.laughtrack.android.core.network.generated.model.ClubListItem
import app.laughtrack.android.core.network.generated.model.ComedianListItem
import app.laughtrack.android.core.network.generated.model.HomeFeed
import app.laughtrack.android.core.network.generated.model.HomeFeedHero
import app.laughtrack.android.core.network.generated.model.HomeFeedPodcast
import app.laughtrack.android.core.network.generated.model.HomeFeedPodcastEpisode
import app.laughtrack.android.core.network.generated.model.HomeFeedPodcastEpisodeComedian
import app.laughtrack.android.core.network.generated.model.HomeFeedPodcastEpisodePodcast
import app.laughtrack.android.core.network.generated.model.HomeFeedPodcastEpisodeRecommendation
import app.laughtrack.android.core.network.generated.model.Show
import app.laughtrack.android.core.network.generated.model.SocialData
import app.laughtrack.android.core.network.generated.model.Ticket
import app.laughtrack.android.core.ui.UiState
import app.laughtrack.android.feature.home.data.HomeFeedCache
import app.laughtrack.android.feature.home.data.HomeFeedRepository
import app.laughtrack.android.feature.home.location.HomeLocationResolver
import app.laughtrack.android.feature.home.ui.HomeUiState
import app.laughtrack.android.feature.home.ui.HomeViewModel
import kotlinx.coroutines.CompletableDeferred
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.test.StandardTestDispatcher
import kotlinx.coroutines.test.advanceUntilIdle
import kotlinx.coroutines.test.resetMain
import kotlinx.coroutines.test.runTest
import kotlinx.coroutines.test.setMain
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test
import java.io.IOException

@OptIn(ExperimentalCoroutinesApi::class)
class HomeViewModelTest {
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
    fun load_replaces_skeleton_state_with_feed_content() =
        runTest {
            val repository = FakeHomeFeedRepository(feed = homeFeed())
            val viewModel = viewModel(repository)

            assertEquals(UiState.Loading, viewModel.state.value.feed)
            advanceUntilIdle()

            val state = viewModel.state.value
            assertTrue(state.feed is UiState.Success)
            assertEquals("Near New York, NY", state.locationTitle)
            assertEquals(3, state.showsTonight.size)
            assertEquals(1, state.trendingThisWeek.size)
            assertEquals(1, state.comedians.size)
            assertEquals(1, state.clubs.size)
            assertEquals(1, state.podcasts.size)
            assertEquals(1, repository.loads)
        }

    @Test
    fun retry_recovers_from_user_visible_error_state() =
        runTest {
            val repository =
                FakeHomeFeedRepository(
                    failuresBeforeSuccess = 1,
                    feed = homeFeed(),
                )
            val viewModel = viewModel(repository)
            advanceUntilIdle()

            assertTrue(viewModel.state.value.feed is UiState.Failure)

            viewModel.retry()
            advanceUntilIdle()

            assertTrue(viewModel.state.value.feed is UiState.Success)
            assertEquals(2, repository.loads)
        }

    @Test
    fun tonight_hero_matches_ios_candidate_filtering_and_display_limit() {
        val candidates =
            listOf(
                show(1, "Sold out by show").copy(soldOut = true),
                show(2, "Sold out by tickets").copy(tickets = listOf(Ticket(soldOut = true))),
                show(3, "Available 3"),
                show(4, "Available 4"),
                show(5, "Available 5"),
                show(6, "Available 6"),
                show(7, "Available 7"),
                show(8, "Capped 8"),
            )
        val feed =
            homeFeed().copy(
                hero = homeFeed().hero.copy(shows = emptyList()),
                showsTonight = candidates,
                trendingThisWeek = listOf(show(3, "Duplicate 3")),
            )

        val state = HomeUiState(feed = UiState.Success(feed))

        assertEquals(listOf(3, 4, 5, 6, 7), state.showsTonight.map { it.id })
    }

    @Test
    fun best_shows_this_week_is_limited_to_five_shows() {
        val weeklyShows = (10..16).map { show(it, "Week show $it") }
        val state =
            HomeUiState(
                feed =
                    UiState.Success(
                        homeFeed().copy(
                            hero = homeFeed().hero.copy(shows = emptyList()),
                            showsTonight = emptyList(),
                            moreNearYou = emptyList(),
                            trendingThisWeek = weeklyShows,
                        ),
                    ),
            )

        assertEquals(listOf(10, 11, 12, 13, 14), state.trendingThisWeek.map { it.id })
    }

    @Test
    fun followed_comedian_shows_are_exposed_without_sold_out_rows() {
        val available = show(40, "Followed favorite")
        val soldOut = show(41, "Sold out favorite").copy(soldOut = true)
        val state =
            HomeUiState(
                feed = UiState.Success(homeFeed().copy(followedComedianShows = listOf(available, soldOut))),
            )

        assertEquals(listOf(40), state.followedComedianShows.map { it.id })
    }

    @Test
    fun personalized_rows_only_mount_for_the_current_signed_in_session() =
        runTest {
            val personalized = homeFeed().copy(followedComedianShows = listOf(show(40, "Followed favorite")))
            val viewModel = viewModel(FakeHomeFeedRepository(feed = personalized))
            advanceUntilIdle()

            assertTrue(viewModel.state.value.followedComedianShows.isEmpty())

            viewModel.onAuthStateChanged(signedIn = true)
            advanceUntilIdle()
            assertEquals(listOf(40), viewModel.state.value.followedComedianShows.map { it.id })

            viewModel.onAuthStateChanged(signedIn = false)
            advanceUntilIdle()
            assertTrue(viewModel.state.value.followedComedianShows.isEmpty())
        }

    @Test
    fun sign_out_clears_account_episodes_before_anonymous_refresh_repopulates_them() =
        runTest {
            val feed = homeFeed().copy(podcastEpisodes = listOf(podcastEpisode()))
            val viewModel = viewModel(FakeHomeFeedRepository(feed = feed))
            advanceUntilIdle()

            viewModel.onAuthStateChanged(signedIn = true)
            advanceUntilIdle()
            assertEquals(listOf(501), viewModel.state.value.podcastEpisodes.map { it.id })

            viewModel.onAuthStateChanged(signedIn = false)
            assertTrue(viewModel.state.value.podcastEpisodes.isEmpty())

            advanceUntilIdle()
            assertEquals(listOf(501), viewModel.state.value.podcastEpisodes.map { it.id })
        }

    @Test
    fun repeated_signed_out_state_preserves_anonymous_episode_recommendations() =
        runTest {
            val repository = FakeHomeFeedRepository(feed = homeFeed().copy(podcastEpisodes = listOf(podcastEpisode())))
            val viewModel = viewModel(repository)
            advanceUntilIdle()

            viewModel.onAuthStateChanged(signedIn = false)
            advanceUntilIdle()

            assertEquals(listOf(501), viewModel.state.value.podcastEpisodes.map { it.id })
            assertEquals(1, repository.loads)
        }

    @Test
    fun cached_feed_survives_network_failure() =
        runTest {
            // Cache holds a prior snapshot; the network always fails. The user keeps
            // seeing the cached feed instead of an error (criterion: re-render from cache).
            val repository = FakeHomeFeedRepository(failuresBeforeSuccess = Int.MAX_VALUE, feed = homeFeed())
            val cache = FakeHomeFeedCache(stored = homeFeed())
            val viewModel = viewModel(repository, cache)
            advanceUntilIdle()

            assertTrue(viewModel.state.value.feed is UiState.Success)
        }

    @Test
    fun successful_load_writes_through_to_cache() =
        runTest {
            val cache = FakeHomeFeedCache()
            val viewModel = viewModel(FakeHomeFeedRepository(feed = homeFeed()), cache)
            advanceUntilIdle()

            assertEquals(1, cache.sets)
        }

    @Test
    fun manual_zip_reloads_feed_scoped_to_that_zip() =
        runTest {
            val repository = FakeHomeFeedRepository(feed = homeFeed())
            val viewModel = viewModel(repository)
            advanceUntilIdle()

            viewModel.setManualZip("90210")
            advanceUntilIdle()

            assertEquals("90210", repository.lastZip)
            assertEquals(2, repository.loads)
        }

    @Test
    fun use_device_location_reloads_with_resolved_zip() =
        runTest {
            val repository = FakeHomeFeedRepository(feed = homeFeed())
            val resolver = FakeLocationResolver(zip = "60614")
            val viewModel = viewModel(repository, resolver = resolver)
            advanceUntilIdle()

            viewModel.useDeviceLocation()
            advanceUntilIdle()

            assertEquals("60614", repository.lastZip)
            assertTrue(repository.loads >= 2)
        }

    @Test
    fun device_location_load_cancels_superseded_manual_zip_load() =
        runTest {
            val repository = SupersededHomeFeedRepository()
            val resolver = FakeLocationResolver(zip = "60614")
            val viewModel = viewModel(repository, resolver = resolver)
            advanceUntilIdle()

            viewModel.setManualZip("90210")
            advanceUntilIdle()
            viewModel.useDeviceLocation()
            advanceUntilIdle()

            assertEquals("60614", viewModel.state.value.zip)

            repository.completeManualZip()
            advanceUntilIdle()

            assertEquals("60614", viewModel.state.value.zip)
            assertEquals("ZIP 60614", viewModel.state.value.locationTitle)
        }

    @Test
    fun set_distance_reloads_feed_with_that_radius() =
        runTest {
            val repository = FakeHomeFeedRepository(feed = homeFeed())
            val viewModel = viewModel(repository)
            advanceUntilIdle()

            viewModel.setDistance(50)
            advanceUntilIdle()

            assertEquals(50, repository.lastDistance)
            assertEquals(50, viewModel.state.value.distanceMiles)
            assertEquals("Saved ZIP - 50 mi", viewModel.state.value.locationSubtitle)
            assertEquals(2, repository.loads)
        }

    @Test
    fun distance_reload_with_prior_feed_does_not_publish_bare_loading_on_cache_miss() =
        runTest {
            val reloadFeed = CompletableDeferred<HomeFeed>()
            val initialFeed = homeFeed()
            val repository =
                DelayedDistanceHomeFeedRepository(
                    delayedDistance = 50,
                    delayedFeed = reloadFeed,
                    initialFeed = initialFeed,
                )
            val viewModel = viewModel(repository)
            advanceUntilIdle()

            viewModel.setDistance(50)
            advanceUntilIdle()

            val refreshingState = viewModel.state.value
            assertEquals(50, refreshingState.distanceMiles)
            assertEquals(UiState.Success(initialFeed), refreshingState.feed)

            val refreshedFeed = homeFeed(city = "Brooklyn")
            reloadFeed.complete(refreshedFeed)
            advanceUntilIdle()

            assertEquals(UiState.Success(refreshedFeed), viewModel.state.value.feed)
        }

    @Test
    fun clear_location_reverts_to_server_inferred_default_area() =
        runTest {
            val repository = FakeHomeFeedRepository(feed = homeFeed())
            val viewModel = viewModel(repository)
            advanceUntilIdle()
            viewModel.setManualZip("90210")
            advanceUntilIdle()
            viewModel.setDistance(100)
            advanceUntilIdle()

            viewModel.clearLocation()
            advanceUntilIdle()

            assertNull(repository.lastZip)
            assertEquals(HomeFeedRepository.DEFAULT_DISTANCE_MILES, repository.lastDistance)
            assertNull(viewModel.state.value.zip)
            assertEquals(HomeFeedRepository.DEFAULT_DISTANCE_MILES, viewModel.state.value.distanceMiles)
        }

    @Test
    fun active_zip_falls_back_to_hero_zip_for_sheet_prefill() =
        runTest {
            // Fresh launch: no requested zip, but the hero reports the inferred ZIP —
            // the sheet prefill (activeZip) must expose it (TASK-3697). The hero
            // fallback alone must NOT count as an explicit, clearable location.
            val viewModel = viewModel(FakeHomeFeedRepository(feed = homeFeed()))
            advanceUntilIdle()

            assertNull(viewModel.state.value.zip)
            assertEquals("10001", viewModel.state.value.activeZip)
            assertTrue(!viewModel.state.value.hasExplicitLocation)
        }

    @Test
    fun set_distance_with_current_value_does_not_reload() =
        runTest {
            val repository = FakeHomeFeedRepository(feed = homeFeed())
            val viewModel = viewModel(repository)
            advanceUntilIdle()

            viewModel.setDistance(HomeFeedRepository.DEFAULT_DISTANCE_MILES)
            advanceUntilIdle()

            assertEquals(1, repository.loads)
        }

    @Test
    fun clear_location_without_explicit_location_does_not_reload() =
        runTest {
            val repository = FakeHomeFeedRepository(feed = homeFeed())
            val viewModel = viewModel(repository)
            advanceUntilIdle()

            viewModel.clearLocation()
            advanceUntilIdle()

            assertEquals(1, repository.loads)
        }

    @Test
    fun load_publishes_active_location_for_search_seeding() =
        runTest {
            // Search seeds its geo pivots from this holder (TASK-3698): the hero
            // ZIP and current radius must be mirrored on every feed publication.
            val locationState = HomeLocationState()
            val viewModel = viewModel(FakeHomeFeedRepository(feed = homeFeed()), locationState = locationState)
            advanceUntilIdle()

            assertEquals(
                HomeLocation("10001", HomeFeedRepository.DEFAULT_DISTANCE_MILES, "New York, NY"),
                locationState.location.value,
            )

            viewModel.setDistance(50)
            advanceUntilIdle()

            assertEquals(HomeLocation("10001", 50, "New York, NY"), locationState.location.value)
        }

    private fun viewModel(
        repository: HomeFeedRepository,
        cache: HomeFeedCache = FakeHomeFeedCache(),
        resolver: HomeLocationResolver = FakeLocationResolver(),
        locationState: HomeLocationState = HomeLocationState(),
    ) = HomeViewModel(repository, cache, resolver, locationState, AnalyticsManager(emptyList()))

    private class FakeHomeFeedRepository(
        private val failuresBeforeSuccess: Int = 0,
        private val feed: HomeFeed,
    ) : HomeFeedRepository {
        var loads = 0
        var lastZip: String? = null
        var lastDistance: Int? = null

        override suspend fun getHomeFeed(
            zip: String?,
            distance: Int?,
        ): HomeFeed {
            loads += 1
            lastZip = zip
            lastDistance = distance
            if (loads <= failuresBeforeSuccess) {
                throw IOException("Home feed failed")
            }
            return feed
        }
    }

    private class FakeHomeFeedCache(
        private val stored: HomeFeed? = null,
    ) : HomeFeedCache {
        private val storedByKey =
            mutableMapOf<Pair<String?, Int?>, HomeFeed>().apply {
                stored?.let { put(null to HomeFeedRepository.DEFAULT_DISTANCE_MILES, it) }
            }
        var sets = 0

        override suspend fun get(
            zip: String?,
            distance: Int?,
        ): HomeFeed? = storedByKey[zip to distance]

        override suspend fun set(
            zip: String?,
            distance: Int?,
            feed: HomeFeed,
        ) {
            storedByKey[zip to distance] = feed
            sets += 1
        }
    }

    private class FakeLocationResolver(
        private val zip: String? = null,
    ) : HomeLocationResolver {
        override suspend fun resolveZip(): String? = zip
    }

    private inner class SupersededHomeFeedRepository : HomeFeedRepository {
        private val manualZipFeed = CompletableDeferred<HomeFeed>()

        override suspend fun getHomeFeed(
            zip: String?,
            distance: Int?,
        ): HomeFeed =
            when (zip) {
                "90210" -> manualZipFeed.await()
                "60614" -> homeFeed(zipCode = "60614", city = null, state = null)
                else -> homeFeed()
            }

        fun completeManualZip() {
            manualZipFeed.complete(homeFeed(zipCode = "90210", city = null, state = null))
        }
    }

    private class DelayedDistanceHomeFeedRepository(
        private val delayedDistance: Int,
        private val delayedFeed: CompletableDeferred<HomeFeed>,
        private val initialFeed: HomeFeed,
    ) : HomeFeedRepository {
        override suspend fun getHomeFeed(
            zip: String?,
            distance: Int?,
        ): HomeFeed =
            if (distance == delayedDistance) {
                delayedFeed.await()
            } else {
                initialFeed
            }
    }

    private fun homeFeed(
        zipCode: String = "10001",
        city: String? = "New York",
        state: String? = "NY",
    ): HomeFeed {
        val heroShow = show(1, "Friday Night Laughs")
        val tonightShow = show(2, "Late Show")
        val weekShow = show(3, "Weekend Showcase")
        return HomeFeed(
            hero =
                HomeFeedHero(
                    shows = listOf(heroShow),
                    zipCode = zipCode,
                    city = city,
                    state = state,
                ),
            trendingComedians = listOf(comedian()),
            comediansNearYou = emptyList(),
            showsTonight = listOf(heroShow, tonightShow),
            moreNearYou = emptyList(),
            trendingThisWeek = listOf(weekShow),
            followedComedianShows = emptyList(),
            trendingPodcasts = listOf(podcast()),
            popularClubs = listOf(club()),
        )
    }

    private fun podcastEpisode(): HomeFeedPodcastEpisode =
        HomeFeedPodcastEpisode(
            id = 501,
            title = "A Great New Set",
            description = null,
            releaseDate = "2026-08-05",
            durationSeconds = 3_600,
            episodeUrl = null,
            audioUrl = "https://example.com/audio.mp3",
            podcast =
                HomeFeedPodcastEpisodePodcast(
                    id = 88,
                    slug = "the-comedy-hour",
                    title = "The Comedy Hour",
                    imageUrl = null,
                ),
            recommendation =
                HomeFeedPodcastEpisodeRecommendation(
                    reason = HomeFeedPodcastEpisodeRecommendation.Reason.RECENT_EPISODE,
                    comedian =
                        HomeFeedPodcastEpisodeComedian(
                            id = 7,
                            uuid = "comedian-7",
                            name = "Jane Comic",
                            imageUrl = "",
                        ),
                    appearanceRole = HomeFeedPodcastEpisodeRecommendation.AppearanceRole.GUEST,
                    followedComedian = false,
                    favoritePodcast = false,
                ),
        )

    private fun show(
        id: Int,
        name: String,
    ) = Show(
        id = id,
        clubId = 10 + id,
        date = "2026-06-25T20:00:00-04:00",
        imageUrl = "https://example.com/show-$id.jpg",
        clubName = "Comedy Room",
        clubCity = "New York",
        clubState = "NY",
        name = name,
    )

    private fun comedian() =
        ComedianListItem(
            id = 7,
            uuid = "comedian-7",
            name = "Jane Comic",
            imageUrl = "https://example.com/jane.jpg",
            socialData = SocialData(id = 7),
            showCount = 4,
        )

    private fun club() =
        ClubListItem(
            id = 9,
            address = "123 Main St, New York, NY",
            name = "Comedy Room",
            imageUrl = "https://example.com/club.jpg",
            activeComedianCount = 12,
            zipCode = "10001",
        )

    private fun podcast() =
        HomeFeedPodcast(
            id = 11,
            slug = "laughs-weekly",
            title = "Laughs Weekly",
            episodeCount = 48,
            authorName = "LaughTrack",
            imageUrl = "https://example.com/podcast.jpg",
        )
}
