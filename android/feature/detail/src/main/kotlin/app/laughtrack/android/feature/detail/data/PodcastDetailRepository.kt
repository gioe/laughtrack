package app.laughtrack.android.feature.detail.data

import app.laughtrack.android.core.network.generated.api.PodcastsApi
import app.laughtrack.android.core.network.generated.infrastructure.ApiClient
import app.laughtrack.android.core.network.generated.model.PodcastDetailResponse
import javax.inject.Inject

/**
 * Loads Podcast detail from `GET /podcasts/{id}`, which returns the podcast
 * metadata, its episode list, and related comedians in one payload.
 */
class PodcastDetailRepository @Inject constructor(
    apiClient: ApiClient,
) {
    private val podcastsApi: PodcastsApi = apiClient.createService(PodcastsApi::class.java)

    suspend fun getPodcast(id: Int): PodcastDetailResponse {
        val response = podcastsApi.getPodcast(id)
        return response.body() ?: error("Podcast unavailable (HTTP ${response.code()})")
    }
}
