package app.laughtrack.android.feature.detail.data

import app.laughtrack.android.core.network.generated.api.ClubsApi
import app.laughtrack.android.core.network.generated.infrastructure.ApiClient
import app.laughtrack.android.feature.detail.model.ClubDetailUi
import javax.inject.Inject

/**
 * Loads Club detail plus its club-scoped upcoming shows. Injects the shared
 * configured [ApiClient] and builds its own generated service from it, matching
 * the rest of the detail repositories.
 */
class ClubDetailRepository @Inject constructor(
    apiClient: ApiClient,
) {
    private val clubsApi: ClubsApi = apiClient.createService(ClubsApi::class.java)

    suspend fun getClub(id: Int): ClubDetailUi {
        val clubResponse = clubsApi.getClub(id)
        val club = clubResponse.body()?.data
            ?: error("Club unavailable (HTTP ${clubResponse.code()})")
        val showsResponse = clubsApi.getClubShows(
            id = id,
            page = 0,
            size = CLUB_SHOWS_LIMIT,
        )
        val shows = showsResponse.body()?.data
            ?: error("Club shows unavailable (HTTP ${showsResponse.code()})")
        return ClubDetailUi(detail = club, upcomingShows = shows)
    }

    private companion object {
        const val CLUB_SHOWS_LIMIT = 20
    }
}
