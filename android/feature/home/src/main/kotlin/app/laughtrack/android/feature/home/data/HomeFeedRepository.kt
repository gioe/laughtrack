package app.laughtrack.android.feature.home.data

import app.laughtrack.android.core.network.generated.api.HomeApi
import app.laughtrack.android.core.network.generated.infrastructure.ApiClient
import app.laughtrack.android.core.network.generated.model.HomeFeed
import java.io.IOException
import javax.inject.Inject

interface HomeFeedRepository {
    suspend fun getHomeFeed(
        zip: String? = null,
        distance: Int? = DEFAULT_DISTANCE_MILES,
    ): HomeFeed

    companion object {
        const val DEFAULT_DISTANCE_MILES = 25
    }
}

class DefaultHomeFeedRepository
    @Inject
    constructor(
        apiClient: ApiClient,
    ) : HomeFeedRepository {
        private val homeApi: HomeApi = apiClient.createService(HomeApi::class.java)

        override suspend fun getHomeFeed(
            zip: String?,
            distance: Int?,
        ): HomeFeed {
            val response = homeApi.getHomeFeed(zip = zip, distance = distance)
            if (!response.isSuccessful) {
                throw IOException("Home feed failed with HTTP ${response.code()}")
            }
            return response.body()?.data ?: throw IOException("Home feed returned an empty body")
        }
    }
