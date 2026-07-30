package app.laughtrack.android.feature.detail.ui

import app.laughtrack.android.core.network.generated.model.PodcastDetailEpisode
import app.laughtrack.android.core.network.generated.model.PodcastDetailEpisodeAppearance
import app.laughtrack.android.core.network.generated.model.PodcastDetailHost
import app.laughtrack.android.core.network.generated.model.PodcastDetailPodcast
import app.laughtrack.android.core.network.generated.model.PodcastEpisodeDetailResponse
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import java.nio.file.Files
import java.nio.file.Path
import java.nio.file.Paths

class PodcastEpisodeDetailPresentationTest {
    @Test
    fun lineup_keeps_parent_hosts_and_removes_them_from_guests() {
        val host = appearance(id = 101, uuid = "host", name = "Mark Normand")
        val guest = appearance(id = 202, uuid = "guest", name = "Aparna Nancherla")
        val response = response(appearances = listOf(host, guest), hosts = listOf(host.asHost()))

        val lineup = podcastEpisodeDetailLineup(response)

        assertEquals(listOf(101), lineup.hosts.map { it.id })
        assertEquals(listOf(202), lineup.guests.map { it.id })
    }

    @Test
    fun audio_only_episode_resolves_to_direct_playback() {
        val response =
            response(
                audioUrl = "https://cdn.example.com/cellar.mp3",
                episodeUrl = null,
            )

        val action = podcastEpisodeDetailPrimaryAction(response)

        assertTrue(action is PodcastEpisodeDetailPrimaryAction.Play)
        val item = (action as PodcastEpisodeDetailPrimaryAction.Play).item
        assertEquals(501, item.episodeId)
        assertEquals(42, item.podcastId)
        assertEquals("https://cdn.example.com/cellar.mp3", item.audioUrl)
    }

    @Test
    fun external_only_episode_resolves_to_open_original() {
        val action =
            podcastEpisodeDetailPrimaryAction(
                response(
                    audioUrl = " ",
                    episodeUrl = "https://podcasts.example.com/cellar",
                ),
            )

        assertEquals(
            PodcastEpisodeDetailPrimaryAction.OpenOriginal("https://podcasts.example.com/cellar"),
            action,
        )
    }

    @Test
    fun metadata_only_episode_remains_available_without_a_transport_action() {
        val response = response(audioUrl = null, episodeUrl = null)

        assertEquals(
            PodcastEpisodeDetailPrimaryAction.Unavailable,
            podcastEpisodeDetailPrimaryAction(response),
        )
        assertEquals("Comedy Cellar Stories", response.episode.title)
        assertEquals("A full episode description.", response.episode.description)
    }

    @Test
    fun stable_semantics_tags_match_the_navigation_and_screenshot_contract() {
        assertEquals("podcastEpisodeDetail", PODCAST_EPISODE_DETAIL_TEST_TAG)
        assertEquals("podcastEpisodeDetailPrimaryAction", PODCAST_EPISODE_PRIMARY_ACTION_TEST_TAG)
        assertEquals("podcastEpisodeDetailPodcastLink", PODCAST_EPISODE_PODCAST_LINK_TEST_TAG)
        assertEquals("podcastEpisodeDetailComedian-202", podcastEpisodeComedianTestTag(202))
        assertEquals("podcastEpisodeRow-501", podcastEpisodeRowTestTag(501))
        assertEquals("podcastEpisodePlay-501", podcastEpisodePlayTestTag(501))
    }

    @Test
    fun source_wires_stable_tags_and_actionable_content_descriptions() {
        val source = String(Files.readAllBytes(detailScreenPath("PodcastEpisodeDetailScreen.kt")))

        assertTrue(source.contains("testTag(PODCAST_EPISODE_DETAIL_TEST_TAG)"))
        assertTrue(source.contains("testTag(PODCAST_EPISODE_PRIMARY_ACTION_TEST_TAG)"))
        assertTrue(source.contains("testTag(PODCAST_EPISODE_PODCAST_LINK_TEST_TAG)"))
        assertTrue(source.contains("testTag(podcastEpisodeComedianTestTag(person.id))"))
        assertTrue(source.contains("contentDescription = \"Play episode\""))
        assertTrue(source.contains("contentDescription = \"Open original episode\""))
        assertTrue(source.contains("contentDescription = \"Open podcast \${response.podcast.title}\""))
        assertTrue(source.contains("contentDescription = \"Open comedian \${person.name}\""))
    }

    @Test
    fun episode_rows_open_detail_and_keep_playback_on_a_separate_control() {
        val podcastSource = String(Files.readAllBytes(detailScreenPath("PodcastDetailScreen.kt")))
        val comedianSource = String(Files.readAllBytes(detailScreenPath("ComedianDetailScreen.kt")))

        assertTrue(podcastSource.contains("AppRoute.PodcastEpisodeDetail(episode.id)"))
        assertTrue(podcastSource.contains("testTag(podcastEpisodeRowTestTag(episode.id))"))
        assertTrue(podcastSource.contains("testTag(podcastEpisodePlayTestTag(episode.id))"))
        assertTrue(comedianSource.contains("AppRoute.PodcastEpisodeDetail(appearance.episode.id)"))
        assertTrue(comedianSource.contains("testTag(podcastEpisodeRowTestTag(appearance.episode.id))"))
        assertTrue(comedianSource.contains("testTag(podcastEpisodePlayTestTag(appearance.episode.id))"))
    }

    private fun response(
        audioUrl: String? = "https://cdn.example.com/cellar.mp3",
        episodeUrl: String? = "https://podcasts.example.com/cellar",
        appearances: List<PodcastDetailEpisodeAppearance> = emptyList(),
        hosts: List<PodcastDetailHost> = emptyList(),
    ): PodcastEpisodeDetailResponse =
        PodcastEpisodeDetailResponse(
            podcast =
                PodcastDetailPodcast(
                    id = 42,
                    slug = "the-laugh-track-pod",
                    title = "The Laugh Track Pod",
                    imageUrl = "https://cdn.example.com/podcast.jpg",
                    episodeCount = 75,
                    hosts = hosts,
                ),
            episode =
                PodcastDetailEpisode(
                    id = 501,
                    title = "Comedy Cellar Stories",
                    description = "A full episode description.",
                    releaseDate = "2026-03-01T00:00:00Z",
                    durationSeconds = 3_720,
                    episodeUrl = episodeUrl,
                    audioUrl = audioUrl,
                    appearances = appearances,
                ),
        )

    private fun appearance(
        id: Int,
        uuid: String,
        name: String,
    ): PodcastDetailEpisodeAppearance =
        PodcastDetailEpisodeAppearance(
            id = id,
            uuid = uuid,
            name = name,
            imageUrl = "https://example.com/$uuid.jpg",
        )

    private fun PodcastDetailEpisodeAppearance.asHost(): PodcastDetailHost =
        PodcastDetailHost(
            id = id,
            uuid = uuid,
            name = name,
            imageUrl = imageUrl,
        )

    private fun detailScreenPath(fileName: String): Path {
        val relativePaths =
            listOf(
                Paths.get(
                    "android/feature/detail/src/main/kotlin",
                    "app/laughtrack/android/feature/detail/ui/$fileName",
                ),
                Paths.get(
                    "feature/detail/src/main/kotlin/app/laughtrack/android/feature/detail/ui/" +
                        fileName,
                ),
            )
        return generateSequence(Paths.get("").toAbsolutePath()) { it.parent }
            .flatMap { directory -> relativePaths.asSequence().map(directory::resolve) }
            .firstOrNull(Files::isRegularFile)
            ?: error(
                "Unable to locate $fileName from " +
                    Paths.get("").toAbsolutePath(),
            )
    }
}
