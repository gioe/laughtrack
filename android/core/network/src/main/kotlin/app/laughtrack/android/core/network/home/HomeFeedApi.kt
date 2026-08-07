package app.laughtrack.android.core.network.home

import app.laughtrack.android.core.network.generated.model.HomeFeedResponse
import retrofit2.Response
import retrofit2.http.GET
import retrofit2.http.Query

/** Home-feed request boundary with an explicitly lower-case Android platform. */
interface HomeFeedApi {
    @GET("home/feed")
    suspend fun getHomeFeed(
        @Query("zip") zip: String? = null,
        @Query("distance") distance: Int? = null,
        @Query("platform") platform: String = PLATFORM_ANDROID,
    ): Response<HomeFeedResponse>

    companion object {
        const val PLATFORM_ANDROID = "android"
    }
}
