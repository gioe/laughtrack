package app.laughtrack.android.core.network.generated.api

import app.laughtrack.android.core.network.generated.infrastructure.CollectionFormats.*
import retrofit2.http.*
import retrofit2.Response
import okhttp3.RequestBody
import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

import app.laughtrack.android.core.network.generated.model.ClubSearchResponse
import app.laughtrack.android.core.network.generated.model.ErrorResponse
import app.laughtrack.android.core.network.generated.model.GetClub200Response
import app.laughtrack.android.core.network.generated.model.ListClubs200Response

interface ClubsApi {
    /**
     * Get a single club by ID
     * 
     * Responses:
     *  - 200: Club detail
     *  - 400: Non-numeric ID
     *  - 404: Club not found or inactive
     *  - 500: Server error
     *
     * @param id 
     * @return [GetClub200Response]
     */
    @GET("clubs/{id}")
    suspend fun getClub(@Path("id") id: kotlin.Int): Response<GetClub200Response>

    /**
     * List active clubs with upcoming shows
     * 
     * Responses:
     *  - 200: Club list
     *  - 400: Invalid parameters
     *  - 429: Rate limit exceeded
     *  - 500: Server error
     *
     * @param limit  (optional, default to 8)
     * @param offset  (optional, default to 0)
     * @return [ListClubs200Response]
     */
    @GET("clubs")
    suspend fun listClubs(@Query("limit") limit: kotlin.Int? = 8, @Query("offset") offset: kotlin.Int? = 0): Response<ListClubs200Response>

    /**
     * Search clubs with filters and pagination
     * 
     * Responses:
     *  - 200: Search results
     *  - 400: Invalid X-Timezone header (non-IANA value)
     *  - 429: Rate limit exceeded
     *  - 500: Server error
     *
     * @param club Search term for club name (optional)
     * @param sort  (optional)
     * @param filters JSON-encoded filter object (optional)
     * @param page Zero-indexed page number (optional)
     * @param size  (optional)
     * @param includeEmpty Include clubs with no upcoming shows (optional)
     * @param xTimezone IANA timezone identifier (defaults to UTC) (optional, default to "UTC")
     * @return [ClubSearchResponse]
     */
    @GET("clubs/search")
    suspend fun searchClubs(@Query("club") club: kotlin.String? = null, @Query("sort") sort: kotlin.String? = null, @Query("filters") filters: kotlin.String? = null, @Query("page") page: kotlin.Int? = null, @Query("size") size: kotlin.Int? = null, @Query("includeEmpty") includeEmpty: kotlin.String? = null, @Header("X-Timezone") xTimezone: kotlin.String? = "UTC"): Response<ClubSearchResponse>

}
