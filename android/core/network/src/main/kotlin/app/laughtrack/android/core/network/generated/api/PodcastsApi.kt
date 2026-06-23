package app.laughtrack.android.core.network.generated.api

import app.laughtrack.android.core.network.generated.infrastructure.CollectionFormats.*
import retrofit2.http.*
import retrofit2.Response
import okhttp3.RequestBody
import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

import app.laughtrack.android.core.network.generated.model.ErrorResponse
import app.laughtrack.android.core.network.generated.model.PodcastDetailResponse

interface PodcastsApi {
    /**
     * Get podcast detail with recent episodes
     * Returns podcast metadata, recent episodes, related comedians, and approved comedian appearances per episode.
     * Responses:
     *  - 200: Podcast detail payload
     *  - 400: Invalid podcast id
     *  - 404: Podcast not found
     *  - 429: Rate limit exceeded
     *  - 500: Server error
     *
     * @param id Podcast numeric id
     * @return [PodcastDetailResponse]
     */
    @GET("podcasts/{id}")
    suspend fun getPodcast(@Path("id") id: kotlin.Int): Response<PodcastDetailResponse>

}
