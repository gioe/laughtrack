package app.laughtrack.android.core.network.generated.api

import app.laughtrack.android.core.network.generated.infrastructure.CollectionFormats.*
import retrofit2.http.*
import retrofit2.Response
import okhttp3.RequestBody
import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

import app.laughtrack.android.core.network.generated.model.ErrorResponse
import app.laughtrack.android.core.network.generated.model.HomeFeedResponse

interface HomeApi {
    /**
     * Composite home-screen feed (hero + six curated sections)
     * Single round-trip replacement for seven per-section calls. Returns hero context (zip/city/state + up to 3 near-you shows) plus arrays for trendingComedians, comediansNearYou, showsTonight, moreNearYou, trendingThisWeek, and popularClubs. Rate limit: 60 req/min anon, 300 req/min authenticated. Cache-Control: private, max-age&#x3D;60 — response is personalized by session profile zipCode and Vercel geo-IP, so shared CDN caching is disabled.
     * Responses:
     *  - 200: Home feed payload
     *  - 400: Invalid zip parameter
     *  - 429: Rate limit exceeded
     *  - 500: Server error
     *
     * @param zip Optional 5-digit US zip override. When supplied, beats the signed-in user&#39;s profile zipCode for this request — used for anonymous callers or profile-preview. (optional)
     * @param distance Radius in miles for zip-scoped recommendations (1-500, default 25). (optional, default to 25)
     * @param xTimezone IANA timezone identifier (defaults to UTC) (optional, default to "UTC")
     * @return [HomeFeedResponse]
     */
    @GET("home/feed")
    suspend fun getHomeFeed(@Query("zip") zip: kotlin.String? = null, @Query("distance") distance: kotlin.Int? = 25, @Header("X-Timezone") xTimezone: kotlin.String? = "UTC"): Response<HomeFeedResponse>

}
