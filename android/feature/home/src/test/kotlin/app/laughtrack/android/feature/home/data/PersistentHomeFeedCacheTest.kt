package app.laughtrack.android.feature.home.data

import app.laughtrack.android.core.network.generated.model.HomeFeed
import app.laughtrack.android.core.network.generated.model.HomeFeedDynamicRail
import app.laughtrack.android.core.network.generated.model.HomeFeedHero
import app.laughtrack.android.core.network.generated.model.HomeFeedPodcastEpisode
import app.laughtrack.android.core.network.generated.model.HomeFeedPodcastEpisodeComedian
import app.laughtrack.android.core.network.generated.model.HomeFeedPodcastEpisodePodcast
import app.laughtrack.android.core.network.generated.model.HomeFeedPodcastEpisodeRecommendation
import app.laughtrack.android.core.network.generated.model.HomeFeedRailPlan
import app.laughtrack.android.core.network.generated.model.Show
import kotlinx.coroutines.test.runTest
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Rule
import org.junit.Test
import org.junit.rules.TemporaryFolder
import java.io.File

/**
 * Exercises the real disk-backed [PersistentHomeFeedCache] (not the fake used by
 * HomeViewModelTest) via its internal directory constructor pointed at a temp
 * folder — the project's plain-JVM test convention, no Robolectric. Covers the
 * two cache lifecycle guarantees: stale-schema entries and undecodable files are
 * both discarded on read so a poison file never fails every subsequent read.
 */
class PersistentHomeFeedCacheTest {
    @get:Rule
    val tmp = TemporaryFolder()

    /** The cache stores one file per (zip, distance) under its [directory]. */
    private fun newCache(): Pair<PersistentHomeFeedCache, File> {
        val directory = tmp.newFolder("home-feed-cache")
        val cache = PersistentHomeFeedCache(directory)
        val entryFile = File(directory, "home-feed-default-default.json")
        return cache to entryFile
    }

    @Test
    fun get_discards_and_deletes_entry_with_mismatched_schema_version() =
        runTest {
            val (cache, entryFile) = newCache()
            entryFile.parentFile!!.mkdirs()
            // Well-formed, not-yet-expired entry, but tagged with a stale schema version.
            entryFile.writeText(
                """{"schemaVersion":"home-feed-v2","expiresAtMillis":${Long.MAX_VALUE},"feedJson":"{}"}""",
            )

            assertNull(cache.get(zip = null, distance = null))
            assertFalse("stale-schema entry should be deleted on read", entryFile.exists())
        }

    @Test
    fun get_deletes_corrupt_undecodable_cache_file() =
        runTest {
            val (cache, entryFile) = newCache()
            entryFile.parentFile!!.mkdirs()
            entryFile.writeText("this is not valid json at all {{{")

            assertNull(cache.get(zip = null, distance = null))
            assertFalse("corrupt file should be deleted so reads don't keep failing", entryFile.exists())
        }

    @Test
    fun get_discards_and_deletes_an_expired_entry() =
        runTest {
            val (cache, entryFile) = newCache()
            entryFile.parentFile!!.mkdirs()
            // Current schema, but the expiry timestamp is already in the past.
            entryFile.writeText(
                """{"schemaVersion":"home-feed-v3","expiresAtMillis":1,"feedJson":"{}"}""",
            )

            assertNull(cache.get(zip = null, distance = null))
            assertFalse("expired entry should be deleted on read", entryFile.exists())
        }

    @Test
    fun get_returns_a_valid_cached_feed_and_keeps_the_file() =
        runTest {
            // Positive control: proves the discard tests aren't passing vacuously
            // (a get() that always returned null would fail here).
            val (cache, entryFile) = newCache()
            cache.set(zip = null, distance = null, feed = emptyFeed())

            val loaded = cache.get(zip = null, distance = null)

            assertEquals(emptyFeed(), loaded)
            assertTrue("a valid current-schema entry must survive a read", entryFile.exists())
        }

    @Test
    fun personalized_followed_shows_are_never_persisted() =
        runTest {
            val (cache, _) = newCache()
            val personalized =
                emptyFeed().copy(
                    followedComedianShows =
                        listOf(Show(id = 7, clubId = 9, date = "2026-08-07T20:00:00-04:00", imageUrl = "")),
                )

            cache.set(zip = null, distance = null, feed = personalized)

            assertTrue(cache.get(zip = null, distance = null)!!.followedComedianShows.isEmpty())
        }

    @Test
    fun personalized_podcast_episodes_are_never_persisted() =
        runTest {
            val (cache, _) = newCache()
            val personalized = emptyFeed().copy(podcastEpisodes = listOf(podcastEpisode()))

            cache.set(zip = null, distance = null, feed = personalized)

            assertNull(cache.get(zip = null, distance = null)!!.podcastEpisodes)
        }

    @Test
    fun account_scoped_rail_plan_and_dynamic_payloads_are_never_persisted() =
        runTest {
            val (cache, _) = newCache()
            val personalized =
                emptyFeed().copy(
                    dynamicRails =
                        listOf(
                            HomeFeedDynamicRail(
                                railKey = "starting_to_buzz",
                                label = "Starting to buzz",
                                items = emptyList(),
                            ),
                        ),
                    railPlan =
                        HomeFeedRailPlan(
                            version = 1,
                            catalogVersion = 1,
                            policyVersion = 2,
                            platform = HomeFeedRailPlan.Platform.ANDROID,
                            cycleIndex = 0,
                            rails = emptyList(),
                        ),
                )

            cache.set(zip = null, distance = null, feed = personalized)

            val loaded = cache.get(zip = null, distance = null)!!
            assertNull(loaded.dynamicRails)
            assertNull(loaded.railPlan)
        }

    private fun emptyFeed(): HomeFeed =
        HomeFeed(
            hero = HomeFeedHero(shows = emptyList(), zipCode = "10001", city = "New York", state = "NY"),
            trendingComedians = emptyList(),
            comediansNearYou = emptyList(),
            showsTonight = emptyList(),
            moreNearYou = emptyList(),
            trendingThisWeek = emptyList(),
            followedComedianShows = emptyList(),
            trendingPodcasts = emptyList(),
            popularClubs = emptyList(),
        )

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
}
