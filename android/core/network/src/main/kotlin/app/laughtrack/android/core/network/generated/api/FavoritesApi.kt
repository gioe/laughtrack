package app.laughtrack.android.core.network.generated.api

import app.laughtrack.android.core.network.generated.infrastructure.CollectionFormats.*
import retrofit2.http.*
import retrofit2.Response
import okhttp3.RequestBody
import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

import app.laughtrack.android.core.network.generated.model.AddFavoriteClubRequest
import app.laughtrack.android.core.network.generated.model.AddFavoritePodcastRequest
import app.laughtrack.android.core.network.generated.model.AddFavoriteRequest
import app.laughtrack.android.core.network.generated.model.ErrorResponse
import app.laughtrack.android.core.network.generated.model.FavoriteClubListResponse
import app.laughtrack.android.core.network.generated.model.FavoriteListResponse
import app.laughtrack.android.core.network.generated.model.FavoritePodcastListResponse
import app.laughtrack.android.core.network.generated.model.FavoriteResponse
import app.laughtrack.android.core.network.generated.model.FavoriteShowListResponse

interface FavoritesApi {
    /**
     * Favorite a comedian
     * 
     * Responses:
     *  - 200: Favorited successfully
     *  - 400: Missing or invalid comedianId
     *  - 401: Not authenticated
     *  - 404: Comedian not found
     *  - 422: User profile not found (re-auth needed)
     *  - 500: Server error
     *
     * @param addFavoriteRequest 
     * @return [FavoriteResponse]
     */
    @POST("favorites")
    suspend fun addFavorite(@Body addFavoriteRequest: AddFavoriteRequest): Response<FavoriteResponse>

    /**
     * Favorite a club
     * 
     * Responses:
     *  - 200: Favorited successfully
     *  - 400: Missing or invalid clubId
     *  - 401: Not authenticated
     *  - 404: Club not found
     *  - 422: User profile not found (re-auth needed)
     *  - 500: Server error
     *
     * @param addFavoriteClubRequest 
     * @return [FavoriteResponse]
     */
    @POST("favorite-clubs")
    suspend fun addFavoriteClub(@Body addFavoriteClubRequest: AddFavoriteClubRequest): Response<FavoriteResponse>

    /**
     * Favorite a podcast
     * 
     * Responses:
     *  - 200: Favorited successfully
     *  - 400: Missing or invalid podcastId
     *  - 401: Not authenticated
     *  - 404: Podcast not found
     *  - 422: User profile not found (re-auth needed)
     *  - 500: Server error
     *
     * @param addFavoritePodcastRequest 
     * @return [FavoriteResponse]
     */
    @POST("favorite-podcasts")
    suspend fun addFavoritePodcast(@Body addFavoritePodcastRequest: AddFavoritePodcastRequest): Response<FavoriteResponse>

    /**
     * List the signed-in user’s saved favorite clubs
     * 
     * Responses:
     *  - 200: Favorite clubs
     *  - 401: Not authenticated
     *  - 422: User profile not found (re-auth needed)
     *  - 500: Server error
     *
     * @return [FavoriteClubListResponse]
     */
    @GET("favorite-clubs")
    suspend fun getFavoriteClubs(): Response<FavoriteClubListResponse>

    /**
     * List the signed-in user’s saved favorite podcasts
     * 
     * Responses:
     *  - 200: Favorite podcasts
     *  - 401: Not authenticated
     *  - 422: User profile not found (re-auth needed)
     *  - 500: Server error
     *
     * @return [FavoritePodcastListResponse]
     */
    @GET("favorite-podcasts")
    suspend fun getFavoritePodcasts(): Response<FavoritePodcastListResponse>

    /**
     * List upcoming shows featuring the signed-in user&#39;s saved favorite comedians
     * 
     * Responses:
     *  - 200: Favorite comedian shows
     *  - 401: Not authenticated
     *  - 422: User profile not found (re-auth needed)
     *  - 429: Rate limit exceeded
     *  - 500: Server error
     *
     * @param page One-indexed page number (default 1) (optional, default to 1)
     * @param size Page size (default 20, max 50) (optional, default to 20)
     * @return [FavoriteShowListResponse]
     */
    @GET("favorite-shows")
    suspend fun getFavoriteShows(@Query("page") page: kotlin.Int? = 1, @Query("size") size: kotlin.Int? = 20): Response<FavoriteShowListResponse>

    /**
     * List the signed-in user’s saved favorite comedians
     * 
     * Responses:
     *  - 200: Favorite comedians
     *  - 401: Not authenticated
     *  - 422: User profile not found (re-auth needed)
     *  - 500: Server error
     *
     * @return [FavoriteListResponse]
     */
    @GET("favorites")
    suspend fun getFavorites(): Response<FavoriteListResponse>

    /**
     * Unfavorite a comedian
     * 
     * Responses:
     *  - 200: Unfavorited successfully
     *  - 400: Missing comedianId
     *  - 401: Not authenticated
     *  - 404: Favorite not found
     *  - 422: User profile not found (re-auth needed)
     *  - 500: Server error
     *
     * @param comedianId Comedian UUID
     * @return [FavoriteResponse]
     */
    @DELETE("favorites/{comedianId}")
    suspend fun removeFavorite(@Path("comedianId") comedianId: kotlin.String): Response<FavoriteResponse>

    /**
     * Unfavorite a club
     * 
     * Responses:
     *  - 200: Unfavorited successfully (idempotent — succeeds whether or not the favorite existed)
     *  - 400: Missing clubId
     *  - 401: Not authenticated
     *  - 422: User profile not found (re-auth needed)
     *  - 500: Server error
     *
     * @param clubId Club numeric id
     * @return [FavoriteResponse]
     */
    @DELETE("favorite-clubs/{clubId}")
    suspend fun removeFavoriteClub(@Path("clubId") clubId: kotlin.Int): Response<FavoriteResponse>

    /**
     * Unfavorite a podcast
     * 
     * Responses:
     *  - 200: Unfavorited successfully
     *  - 400: Missing podcastId
     *  - 401: Not authenticated
     *  - 404: Favorite not found
     *  - 422: User profile not found (re-auth needed)
     *  - 500: Server error
     *
     * @param podcastId Podcast numeric id
     * @return [FavoriteResponse]
     */
    @DELETE("favorite-podcasts/{podcastId}")
    suspend fun removeFavoritePodcast(@Path("podcastId") podcastId: kotlin.Int): Response<FavoriteResponse>

}
