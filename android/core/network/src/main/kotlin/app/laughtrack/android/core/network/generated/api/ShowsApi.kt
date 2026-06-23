package app.laughtrack.android.core.network.generated.api

import app.laughtrack.android.core.network.generated.infrastructure.CollectionFormats.*
import retrofit2.http.*
import retrofit2.Response
import okhttp3.RequestBody
import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

import app.laughtrack.android.core.network.generated.model.ErrorResponse
import app.laughtrack.android.core.network.generated.model.ShowDetailResponse
import app.laughtrack.android.core.network.generated.model.ShowListResponse
import app.laughtrack.android.core.network.generated.model.ShowSearchResponse

interface ShowsApi {
    /**
     * Get a single show by ID
     * 
     * Responses:
     *  - 200: Show detail
     *  - 400: Non-numeric ID
     *  - 404: Show not found or hidden
     *  - 429: Rate limit exceeded
     *  - 500: Server error
     *
     * @param id 
     * @return [ShowDetailResponse]
     */
    @GET("shows/{id}")
    suspend fun getShow(@Path("id") id: kotlin.Int): Response<ShowDetailResponse>

    /**
     * Per-day show counts for a date range
     * Returns a map of ISO date string (YYYY-MM-DD) to the number of shows scheduled on that day. Used to render density dots on the date-picker calendar. Range is capped at 90 days; if &#x60;to&#x60; exceeds the cap, it is silently clamped server-side.  Optional &#x60;comedian&#x60; and &#x60;club&#x60; filters scope the result to dates where the named entity appears in the show lineup (comedian) or hosts the show (club). The two are mutually exclusive — supplying both returns 400. Either may be combined with &#x60;zip&#x60; + &#x60;distance&#x60; for an additional geographic narrow.
     * Responses:
     *  - 200: Per-day show counts keyed by YYYY-MM-DD.
     *  - 400: Invalid parameters
     *  - 429: Rate limit exceeded
     *  - 500: Server error
     *
     * @param zip 5-digit US ZIP code; required for distance filtering. (optional)
     * @param from Start date (YYYY-MM-DD). Defaults to today. (optional)
     * @param to End date (YYYY-MM-DD). Defaults to from+89 days. (optional)
     * @param distance Radius in miles (1-500, defaults to 25 when zip provided). (optional)
     * @param comedian Filter density to dates where this comedian appears in the show lineup. Mutually exclusive with &#x60;club&#x60;. (optional)
     * @param club Filter density to dates hosted by this venue. Mutually exclusive with &#x60;comedian&#x60;. (optional)
     * @param xTimezone IANA timezone identifier (defaults to UTC). (optional, default to "UTC")
     * @return [kotlin.collections.Map<kotlin.String, kotlin.Int>]
     */
    @GET("shows/density")
    suspend fun getShowsDensity(@Query("zip") zip: kotlin.String? = null, @Query("from") from: kotlin.String? = null, @Query("to") to: kotlin.String? = null, @Query("distance") distance: kotlin.Int? = null, @Query("comedian") comedian: kotlin.String? = null, @Query("club") club: kotlin.String? = null, @Header("X-Timezone") xTimezone: kotlin.String? = "UTC"): Response<kotlin.collections.Map<kotlin.String, kotlin.Int>>

    /**
     * List shows near a ZIP code
     * 
     * Responses:
     *  - 200: Show list
     *  - 400: Invalid parameters (zip, date format, distance range)
     *  - 429: Rate limit exceeded
     *  - 500: Server error
     *
     * @param zip 5-digit US ZIP code
     * @param from Start date (YYYY-MM-DD) (optional)
     * @param to End date (YYYY-MM-DD) (optional)
     * @param page Zero-indexed page number (optional)
     * @param size  (optional)
     * @param comedian Filter by comedian name (optional)
     * @param filters JSON-encoded filter object (optional)
     * @param distance Radius in miles (1-500, default 25) (optional, default to 25)
     * @param xTimezone IANA timezone identifier (defaults to UTC) (optional, default to "UTC")
     * @return [ShowListResponse]
     */
    @GET("shows")
    suspend fun listShows(@Query("zip") zip: kotlin.String, @Query("from") from: kotlin.String? = null, @Query("to") to: kotlin.String? = null, @Query("page") page: kotlin.Int? = null, @Query("size") size: kotlin.Int? = null, @Query("comedian") comedian: kotlin.String? = null, @Query("filters") filters: kotlin.String? = null, @Query("distance") distance: kotlin.Int? = 25, @Header("X-Timezone") xTimezone: kotlin.String? = "UTC"): Response<ShowListResponse>

    /**
     * Search shows with flexible filters
     * More flexible than /shows — ZIP is optional, supports club filter and sort.
     * Responses:
     *  - 200: Search results
     *  - 400: Invalid parameters
     *  - 429: Rate limit exceeded
     *  - 500: Server error
     *
     * @param zip 5-digit US ZIP code (optional here, unlike /shows) (optional)
     * @param from Start date (YYYY-MM-DD) (optional)
     * @param to End date (YYYY-MM-DD) (optional)
     * @param page Zero-indexed page number (optional)
     * @param size  (optional)
     * @param comedian Filter by comedian name (optional)
     * @param club Filter by club name (optional)
     * @param filters JSON-encoded filter object (optional)
     * @param distance Radius in miles (1-500, defaults to 25 when zip provided) (optional)
     * @param sort  (optional)
     * @param xTimezone IANA timezone identifier (defaults to UTC) (optional, default to "UTC")
     * @return [ShowSearchResponse]
     */
    @GET("shows/search")
    suspend fun searchShows(@Query("zip") zip: kotlin.String? = null, @Query("from") from: kotlin.String? = null, @Query("to") to: kotlin.String? = null, @Query("page") page: kotlin.Int? = null, @Query("size") size: kotlin.Int? = null, @Query("comedian") comedian: kotlin.String? = null, @Query("club") club: kotlin.String? = null, @Query("filters") filters: kotlin.String? = null, @Query("distance") distance: kotlin.Int? = null, @Query("sort") sort: kotlin.String? = null, @Header("X-Timezone") xTimezone: kotlin.String? = "UTC"): Response<ShowSearchResponse>

}
