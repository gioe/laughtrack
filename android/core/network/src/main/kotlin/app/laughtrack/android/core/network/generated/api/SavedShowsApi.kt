package app.laughtrack.android.core.network.generated.api

import app.laughtrack.android.core.network.generated.infrastructure.CollectionFormats.*
import retrofit2.http.*
import retrofit2.Response
import okhttp3.RequestBody
import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

import app.laughtrack.android.core.network.generated.model.ErrorResponse
import app.laughtrack.android.core.network.generated.model.SavedShowListResponse
import app.laughtrack.android.core.network.generated.model.SavedShowStateResponse

interface SavedShowsApi {
    /**
     * Get the signed-in user&#39;s saved state for a show
     * 
     * Responses:
     *  - 200: Saved-show state
     *  - 400: Invalid showId
     *  - 401: Not authenticated
     *  - 404: Show not found or hidden
     *  - 422: User profile not found (re-auth needed)
     *  - 429: Rate limit exceeded
     *  - 500: Server error
     *
     * @param showId Show numeric id
     * @return [SavedShowStateResponse]
     */
    @GET("saved-shows/{showId}")
    suspend fun getSavedShowState(@Path("showId") showId: kotlin.Int): Response<SavedShowStateResponse>


    /**
    * enum for parameter period
    */
    enum class PeriodGetSavedShows(val value: kotlin.String) {
        @SerialName(value = "upcoming") UPCOMING("upcoming"),
        @SerialName(value = "past") PAST("past")
    }

    /**
     * List the signed-in user&#39;s saved shows
     * 
     * Responses:
     *  - 200: Saved shows ordered by the requested period
     *  - 400: Invalid period
     *  - 401: Not authenticated
     *  - 422: User profile not found (re-auth needed)
     *  - 429: Rate limit exceeded
     *  - 500: Server error
     *
     * @param period Whether to return upcoming or past saved shows (optional, default to upcoming)
     * @param page One-indexed page number (default 1) (optional, default to 1)
     * @param size Page size (default 20, max 50) (optional, default to 20)
     * @return [SavedShowListResponse]
     */
    @GET("saved-shows")
    suspend fun getSavedShows(@Query("period") period: PeriodGetSavedShows? = PeriodGetSavedShows.UPCOMING, @Query("page") page: kotlin.Int? = 1, @Query("size") size: kotlin.Int? = 20): Response<SavedShowListResponse>

    /**
     * Save an upcoming visible show
     * Idempotently saves an upcoming visible show. Repeating the request after the saved show passes still succeeds.
     * Responses:
     *  - 200: Show saved
     *  - 400: Invalid showId
     *  - 401: Not authenticated
     *  - 404: Show not found or hidden
     *  - 409: A new save cannot be created for a past show
     *  - 422: User profile not found (re-auth needed)
     *  - 429: Rate limit exceeded
     *  - 500: Server error
     *
     * @param showId Show numeric id
     * @return [SavedShowStateResponse]
     */
    @POST("saved-shows/{showId}")
    suspend fun saveShow(@Path("showId") showId: kotlin.Int): Response<SavedShowStateResponse>

    /**
     * Unsave a show
     * Idempotently removes the saved-show record, including for past or hidden shows.
     * Responses:
     *  - 200: Show unsaved
     *  - 400: Invalid showId
     *  - 401: Not authenticated
     *  - 422: User profile not found (re-auth needed)
     *  - 429: Rate limit exceeded
     *  - 500: Server error
     *
     * @param showId Show numeric id
     * @return [SavedShowStateResponse]
     */
    @DELETE("saved-shows/{showId}")
    suspend fun unsaveShow(@Path("showId") showId: kotlin.Int): Response<SavedShowStateResponse>

}
