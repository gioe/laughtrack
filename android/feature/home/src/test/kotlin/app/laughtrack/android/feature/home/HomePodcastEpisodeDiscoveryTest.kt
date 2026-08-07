package app.laughtrack.android.feature.home

import app.laughtrack.android.core.navigation.AppRoute
import app.laughtrack.android.core.network.generated.model.HomeFeedPodcast
import app.laughtrack.android.core.network.generated.model.HomeFeedPodcastEpisode
import app.laughtrack.android.core.network.generated.model.HomeFeedPodcastEpisodeComedian
import app.laughtrack.android.core.network.generated.model.HomeFeedPodcastEpisodePodcast
import app.laughtrack.android.core.network.generated.model.HomeFeedPodcastEpisodeRecommendation
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test
import java.nio.file.Files
import java.nio.file.Path
import java.nio.file.Paths
import java.time.LocalDate

class HomePodcastEpisodeDiscoveryTest {
    private val today = LocalDate.of(2026, 8, 6)

    @Test
    fun episode_presentation_includes_discovery_context_and_explainable_reasons() {
        val item = homePodcastEpisodeDiscoveryItem(episode(), today)

        assertEquals("A Great New Set", item.title)
        assertEquals("The Comedy Hour", item.podcastTitle)
        assertEquals("https://example.com/podcast.jpg", item.artworkUrl)
        assertEquals("Yesterday • 61 min", item.releaseMetadata)
        assertEquals("Guest", item.comedianRole)
        assertEquals("Jane Comic", item.comedianName)
        assertEquals("Guest appearance by Jane Comic", item.recommendationReason)

        val expectedReasons =
            mapOf(
                HomeFeedPodcastEpisodeRecommendation.Reason.FOLLOWED_COMEDIAN to "Because you follow Jane Comic",
                HomeFeedPodcastEpisodeRecommendation.Reason.FAVORITE_PODCAST to "From a favorite podcast",
                HomeFeedPodcastEpisodeRecommendation.Reason.GUEST_APPEARANCE to "Guest appearance by Jane Comic",
                HomeFeedPodcastEpisodeRecommendation.Reason.POPULAR_COMEDIAN to "Featuring popular comedian Jane Comic",
                HomeFeedPodcastEpisodeRecommendation.Reason.RECENT_EPISODE to "A recent episode with Jane Comic",
            )
        expectedReasons.forEach { (reason, label) ->
            assertEquals(label, homePodcastEpisodeDiscoveryItem(episode(reason = reason), today).recommendationReason)
        }
    }

    @Test
    fun detail_route_is_independent_from_the_optional_play_action() {
        val playable = homePodcastEpisodeDiscoveryItem(episode(audioUrl = " https://example.com/audio.mp3 "), today)

        assertEquals(AppRoute.PodcastEpisodeDetail(501), homePodcastEpisodeRoute(playable))
        assertEquals(501, playable.playbackItem?.episodeId)
        assertEquals(88, playable.playbackItem?.podcastId)
        assertEquals("https://example.com/audio.mp3", playable.playbackItem?.audioUrl)

        val unavailable = homePodcastEpisodeDiscoveryItem(episode(audioUrl = "  "), today)
        assertEquals(AppRoute.PodcastEpisodeDetail(501), homePodcastEpisodeRoute(unavailable))
        assertNull(unavailable.playbackItem)
    }

    @Test
    fun episode_content_wins_while_missing_recommendations_use_the_legacy_catalog() {
        val podcast = legacyPodcast()
        val duplicateEpisodes = listOf(episode(), episode())

        val discovery = homePodcastRailContent(duplicateEpisodes, listOf(podcast))
        assertTrue(discovery is HomePodcastRailContent.Episodes)
        assertEquals(1, (discovery as HomePodcastRailContent.Episodes).episodes.size)

        listOf(null, emptyList<HomeFeedPodcastEpisode>()).forEach { episodes ->
            val fallback = homePodcastRailContent(episodes, listOf(podcast, podcast))
            assertTrue(fallback is HomePodcastRailContent.LegacyPodcasts)
            assertEquals(1, (fallback as HomePodcastRailContent.LegacyPodcasts).podcasts.size)
        }
    }

    @Test
    fun discover_wiring_keeps_open_and_play_actions_separate_and_labels_the_catalog() {
        val discoverySource = String(Files.readAllBytes(discoveryPath()))
        val homeSource = String(Files.readAllBytes(homeScreenPath()))
        val shellSource = String(Files.readAllBytes(appShellPath()))

        assertTrue(discoverySource.contains("onOpenEntity(homePodcastEpisodeRoute(item))"))
        assertTrue(discoverySource.contains("onPlay(playbackItem)"))
        assertTrue(discoverySource.contains("homePodcastEpisodeRowTestTag(item.id)"))
        assertTrue(discoverySource.contains("homePodcastEpisodePlayTestTag(item.id)"))
        assertTrue(discoverySource.contains("SeeAllButton(label = \"Browse podcasts\""))
        assertTrue(homeSource.contains("episodes = state.podcastEpisodes"))
        assertTrue(shellSource.contains("onPlay = { item -> playbackController?.play(item) }"))
    }

    private fun episode(
        audioUrl: String? = "https://example.com/audio.mp3",
        reason: HomeFeedPodcastEpisodeRecommendation.Reason =
            HomeFeedPodcastEpisodeRecommendation.Reason.GUEST_APPEARANCE,
    ): HomeFeedPodcastEpisode =
        HomeFeedPodcastEpisode(
            id = 501,
            title = "A Great New Set",
            description = "Episode description",
            releaseDate = "2026-08-05",
            durationSeconds = 3_660,
            episodeUrl = "https://example.com/episode",
            audioUrl = audioUrl,
            podcast =
                HomeFeedPodcastEpisodePodcast(
                    id = 88,
                    slug = "the-comedy-hour",
                    title = "The Comedy Hour",
                    imageUrl = "https://example.com/podcast.jpg",
                ),
            recommendation =
                HomeFeedPodcastEpisodeRecommendation(
                    reason = reason,
                    comedian =
                        HomeFeedPodcastEpisodeComedian(
                            id = 7,
                            uuid = "comedian-7",
                            name = "Jane Comic",
                            imageUrl = "https://example.com/jane.jpg",
                        ),
                    appearanceRole = HomeFeedPodcastEpisodeRecommendation.AppearanceRole.GUEST,
                    followedComedian = reason == HomeFeedPodcastEpisodeRecommendation.Reason.FOLLOWED_COMEDIAN,
                    favoritePodcast = reason == HomeFeedPodcastEpisodeRecommendation.Reason.FAVORITE_PODCAST,
                ),
        )

    private fun legacyPodcast(): HomeFeedPodcast =
        HomeFeedPodcast(
            id = 88,
            slug = "the-comedy-hour",
            title = "The Comedy Hour",
            episodeCount = 42,
        )

    private fun discoveryPath(): Path =
        locate(
            "android/feature/home/src/main/kotlin/app/laughtrack/android/feature/home/" +
                "HomePodcastEpisodeDiscovery.kt",
        )

    private fun homeScreenPath(): Path =
        locate("android/feature/home/src/main/kotlin/app/laughtrack/android/feature/home/HomeScreen.kt")

    private fun appShellPath(): Path = locate("android/app/src/main/kotlin/app/laughtrack/android/AppShell.kt")

    private fun locate(relative: String): Path =
        generateSequence(Paths.get("").toAbsolutePath()) { it.parent }
            .map { it.resolve(relative) }
            .firstOrNull(Files::isRegularFile)
            ?: error("Unable to locate $relative")
}
