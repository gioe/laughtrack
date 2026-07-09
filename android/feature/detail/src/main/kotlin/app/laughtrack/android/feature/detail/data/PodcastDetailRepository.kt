package app.laughtrack.android.feature.detail.data

import app.laughtrack.android.core.network.generated.api.PodcastsApi
import app.laughtrack.android.core.network.generated.infrastructure.ApiClient
import app.laughtrack.android.core.network.generated.model.PodcastDetailResponse
import javax.inject.Inject

/**
 * Loads Podcast detail from `GET /podcasts/{id}`, which returns the podcast
 * metadata, its episode list, and related comedians in one payload. The primary
 * constructor takes the generated [PodcastsApi] interface directly so JVM unit
 * tests can construct the repository over a fake; the Hilt path builds the
 * service from the shared configured [ApiClient].
 */
class PodcastDetailRepository(
    private val podcastsApi: PodcastsApi,
) {
    @Inject
    constructor(apiClient: ApiClient) : this(apiClient.createService(PodcastsApi::class.java))

    suspend fun getPodcast(id: Int): PodcastDetailResponse {
        val response = podcastsApi.getPodcast(id)
        return response.body() ?: error("Podcast unavailable (HTTP ${response.code()})")
    }
}
