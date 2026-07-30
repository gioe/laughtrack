package app.laughtrack.android.core.network.generated.api

import app.laughtrack.android.core.network.generated.infrastructure.CollectionFormats.*
import retrofit2.http.*
import retrofit2.Response
import okhttp3.RequestBody
import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

import app.laughtrack.android.core.network.generated.model.ErrorResponse
import app.laughtrack.android.core.network.generated.model.PodcastDetailResponse
import app.laughtrack.android.core.network.generated.model.PodcastEpisodeDetailResponse
import app.laughtrack.android.core.network.generated.model.PodcastSearchResponse

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

    /**
     * Get podcast episode detail
     * Returns one podcast episode by internal numeric id with its public parent podcast context and accepted visible comedian appearances. Unlike podcast detail, this endpoint is not limited to the 50 most recent episodes.
     * Responses:
     *  - 200: Podcast episode detail payload
     *  - 400: Invalid podcast episode id
     *  - 404: Podcast episode not found
     *  - 429: Rate limit exceeded
     *  - 500: Server error
     *
     * @param id Podcast episode numeric id
     * @return [PodcastEpisodeDetailResponse]
     */
    @GET("podcast-episodes/{id}")
    suspend fun getPodcastEpisode(@Path("id") id: kotlin.Int): Response<PodcastEpisodeDetailResponse>

    /**
     * Search podcasts with sorting and pagination
     * 
     * Responses:
     *  - 200: Search results
     *  - 429: Rate limit exceeded
     *  - 500: Server error
     *
     * @param q Search term matched against podcast title, author, and description (optional)
     * @param sort Sort order (e.g. show_count_desc, name_asc); defaults to show_count_desc (optional)
     * @param page Zero-indexed page number (optional)
     * @param size  (optional)
     * @param includeEmpty Include podcasts with no episodes (optional)
     * @return [PodcastSearchResponse]
     */
    @GET("podcasts/search")
    suspend fun searchPodcasts(@Query("q") q: kotlin.String? = null, @Query("sort") sort: kotlin.String? = null, @Query("page") page: kotlin.Int? = null, @Query("size") size: kotlin.Int? = null, @Query("includeEmpty") includeEmpty: kotlin.String? = null): Response<PodcastSearchResponse>

}
