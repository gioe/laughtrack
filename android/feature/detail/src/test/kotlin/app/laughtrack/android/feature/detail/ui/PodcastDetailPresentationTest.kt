package app.laughtrack.android.feature.detail.ui

import app.laughtrack.android.core.network.generated.model.PodcastDetailEpisode
import app.laughtrack.android.core.network.generated.model.PodcastDetailEpisodeAppearance
import app.laughtrack.android.core.network.generated.model.PodcastDetailHost
import app.laughtrack.android.core.network.generated.model.PodcastDetailPodcast
import app.laughtrack.android.core.network.generated.model.PodcastDetailResponse
import org.junit.Assert.assertEquals
import org.junit.Test

class PodcastDetailPresentationTest {
    @Test
    fun frequentGuests_excludesHostsAndRequiresTwoDistinctEpisodes() {
        val host = appearance(id = 1, uuid = "host", name = "Host")
        val regular = appearance(id = 2, uuid = "regular", name = "Regular")
        val oneOff = appearance(id = 3, uuid = "one-off", name = "One-off")
        val response =
            response(
                hosts = listOf(host.asHost()),
                episodes =
                    listOf(
                        episode(id = 10, appearances = listOf(host, regular, oneOff)),
                        episode(id = 11, appearances = listOf(host, regular)),
                    ),
            )

        assertEquals(listOf(regular), frequentPodcastGuests(response))
    }

    @Test
    fun episodeMetadata_matchesIosDateAndDurationFormatting() {
        val episode =
            episode(
                id = 10,
                releaseDate = "2026-07-10T12:30:00Z",
                durationSeconds = 2_685,
            )

        assertEquals("Jul 10, 2026 • 44 min", podcastEpisodeMetadata(episode))
    }

    @Test
    fun episodeMetadata_usesEpisodeFallbackWhenMetadataIsMissing() {
        assertEquals("Episode", podcastEpisodeMetadata(episode(id = 10)))
    }

    private fun response(
        hosts: List<PodcastDetailHost> = emptyList(),
        episodes: List<PodcastDetailEpisode> = emptyList(),
    ): PodcastDetailResponse =
        PodcastDetailResponse(
            podcast =
                PodcastDetailPodcast(
                    id = 20,
                    slug = "podcast",
                    title = "Podcast",
                    episodeCount = episodes.size,
                    hosts = hosts,
                ),
            episodes = episodes,
            relatedComedians = emptyList(),
        )

    private fun episode(
        id: Int,
        releaseDate: String? = null,
        durationSeconds: Int? = null,
        appearances: List<PodcastDetailEpisodeAppearance> = emptyList(),
    ): PodcastDetailEpisode =
        PodcastDetailEpisode(
            id = id,
            title = "Episode $id",
            description = null,
            releaseDate = releaseDate,
            durationSeconds = durationSeconds,
            episodeUrl = null,
            audioUrl = null,
            appearances = appearances,
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
}
