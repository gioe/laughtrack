package app.laughtrack.android.core.network.generated.api

import app.laughtrack.android.core.network.generated.infrastructure.CollectionFormats.*
import retrofit2.http.*
import retrofit2.Response
import okhttp3.RequestBody
import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

import app.laughtrack.android.core.network.generated.model.ComedianSearchResponse
import app.laughtrack.android.core.network.generated.model.ErrorResponse
import app.laughtrack.android.core.network.generated.model.GetComedian200Response
import app.laughtrack.android.core.network.generated.model.GetComedianCoBill200Response
import app.laughtrack.android.core.network.generated.model.GetComedianPastShows200Response
import app.laughtrack.android.core.network.generated.model.GetComedianSuggestions200Response
import app.laughtrack.android.core.network.generated.model.ListComedians200Response
import app.laughtrack.android.core.network.generated.model.UpcomingRunResponse

interface ComediansApi {
    /**
     * Get a single comedian by numeric ID
     * 
     * Responses:
     *  - 200: Comedian detail
     *  - 400: Non-numeric ID
     *  - 404: Comedian not found
     *  - 500: Server error
     *
     * @param id 
     * @return [GetComedian200Response]
     */
    @GET("comedians/{id}")
    suspend fun getComedian(@Path("id") id: kotlin.Int): Response<GetComedian200Response>

    /**
     * List comedians who have recently shared bills with a comedian
     * 
     * Responses:
     *  - 200: Historically co-billed comedians
     *  - 400: Non-numeric ID
     *  - 429: Rate limit exceeded
     *  - 500: Server error
     *
     * @param id 
     * @return [GetComedianCoBill200Response]
     */
    @GET("comedians/{id}/co-bill")
    suspend fun getComedianCoBill(@Path("id") id: kotlin.Int): Response<GetComedianCoBill200Response>

    /**
     * List past shows for a comedian
     * Returns past shows (date &lt; now) where the named comedian appeared in the lineup, ordered by date desc. Paginated.
     * Responses:
     *  - 200: Past shows for the comedian
     *  - 400: Missing comedian, invalid page/size, or invalid X-Timezone
     *  - 429: Rate limit exceeded
     *  - 500: Server error
     *
     * @param comedian Comedian name to match against lineup items
     * @param page Zero-indexed page number (defaults to 0) (optional)
     * @param size Page size (1-50, defaults to 20) (optional, default to 20)
     * @param xTimezone IANA timezone identifier (defaults to UTC) (optional, default to "UTC")
     * @return [GetComedianPastShows200Response]
     */
    @GET("comedians/past-shows")
    suspend fun getComedianPastShows(@Query("comedian") comedian: kotlin.String, @Query("page") page: kotlin.Int? = null, @Query("size") size: kotlin.Int? = 20, @Header("X-Timezone") xTimezone: kotlin.String? = "UTC"): Response<GetComedianPastShows200Response>

    /**
     * Popularity-weighted random comedian suggestions for onboarding
     * Returns a fresh popularity-weighted random sample of comedians with upcoming shows for the post-auth favorite-a-comedian onboarding grid. Unlike comedian search (deterministic popularity sort), membership and order vary per call. Optional auth: when a bearer token is supplied, isFavorite reflects the caller&#39;s existing favorites.
     * Responses:
     *  - 200: Comedian suggestions
     *  - 429: Rate limit exceeded
     *  - 500: Server error
     *
     * @return [GetComedianSuggestions200Response]
     */
    @GET("comedians/suggestions")
    suspend fun getComedianSuggestions(): Response<GetComedianSuggestions200Response>

    /**
     * List upcoming show runs for a comedian
     * Returns upcoming shows grouped into consecutive same-club runs, ordered by first show date ascending.
     * Responses:
     *  - 200: Upcoming runs for the comedian
     *  - 400: Invalid id, date, or X-Timezone
     *  - 429: Rate limit exceeded
     *  - 500: Server error
     *
     * @param id 
     * @param club Optional club-name filter (optional)
     * @param location Optional venue location filter (optional)
     * @param date Optional show date in YYYY-MM-DD format (optional)
     * @param xTimezone IANA timezone identifier (defaults to UTC) (optional, default to "UTC")
     * @return [UpcomingRunResponse]
     */
    @GET("comedians/{id}/upcoming-runs")
    suspend fun getComedianUpcomingRuns(@Path("id") id: kotlin.Int, @Query("club") club: kotlin.String? = null, @Query("location") location: kotlin.String? = null, @Query("date") date: kotlin.String? = null, @Header("X-Timezone") xTimezone: kotlin.String? = "UTC"): Response<UpcomingRunResponse>

    /**
     * List trending comedians (3+ upcoming shows)
     * 
     * Responses:
     *  - 200: Comedian list
     *  - 400: Invalid parameters
     *  - 500: Server error
     *
     * @param limit  (optional, default to 8)
     * @param offset  (optional, default to 0)
     * @return [ListComedians200Response]
     */
    @GET("comedians")
    suspend fun listComedians(@Query("limit") limit: kotlin.Int? = 8, @Query("offset") offset: kotlin.Int? = 0): Response<ListComedians200Response>

    /**
     * Search comedians with filters and pagination
     * 
     * Responses:
     *  - 200: Search results
     *  - 400: Invalid X-Timezone header (non-IANA value)
     *  - 429: Rate limit exceeded
     *  - 500: Server error
     *
     * @param comedian Search term for comedian name (optional)
     * @param sort  (optional)
     * @param filters JSON-encoded filter object (optional)
     * @param page Zero-indexed page number (optional)
     * @param size  (optional)
     * @param includeEmpty Include comedians with no upcoming shows (optional)
     * @param homeCity Filter to comedians whose home city matches this &#39;city|state&#39; token (from the values in homeCityFilters). (optional)
     * @param homeClub Filter to comedians whose home club matches this club-id token (from the values in homeClubFilters). (optional)
     * @param xTimezone IANA timezone identifier (defaults to UTC) (optional, default to "UTC")
     * @return [ComedianSearchResponse]
     */
    @GET("comedians/search")
    suspend fun searchComedians(@Query("comedian") comedian: kotlin.String? = null, @Query("sort") sort: kotlin.String? = null, @Query("filters") filters: kotlin.String? = null, @Query("page") page: kotlin.Int? = null, @Query("size") size: kotlin.Int? = null, @Query("includeEmpty") includeEmpty: kotlin.String? = null, @Query("homeCity") homeCity: kotlin.String? = null, @Query("homeClub") homeClub: kotlin.String? = null, @Header("X-Timezone") xTimezone: kotlin.String? = "UTC"): Response<ComedianSearchResponse>

}
