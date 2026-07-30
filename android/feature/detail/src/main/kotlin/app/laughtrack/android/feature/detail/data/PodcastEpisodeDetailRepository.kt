package app.laughtrack.android.feature.detail.data

import app.laughtrack.android.core.network.generated.api.PodcastsApi
import app.laughtrack.android.core.network.generated.infrastructure.ApiClient
import app.laughtrack.android.core.network.generated.model.PodcastEpisodeDetailResponse
import javax.inject.Inject

/** Loads one podcast episode directly by its internal numeric ID. */
class PodcastEpisodeDetailRepository(
    private val podcastsApi: PodcastsApi,
) {
    @Inject
    constructor(apiClient: ApiClient) : this(apiClient.createService(PodcastsApi::class.java))

    suspend fun getPodcastEpisode(id: Int): PodcastEpisodeDetailResponse {
        val response = podcastsApi.getPodcastEpisode(id)
        return response.body() ?: error("Podcast episode unavailable (HTTP ${response.code()})")
    }
}
