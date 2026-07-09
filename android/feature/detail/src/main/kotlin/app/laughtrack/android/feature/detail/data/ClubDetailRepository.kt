package app.laughtrack.android.feature.detail.data

import app.laughtrack.android.core.data.runCatchingCancellable
import app.laughtrack.android.core.network.generated.api.ClubsApi
import app.laughtrack.android.core.network.generated.infrastructure.ApiClient
import app.laughtrack.android.feature.detail.model.ClubDetailUi
import javax.inject.Inject

/**
 * Loads Club detail plus its club-scoped upcoming shows. The Hilt path injects the
 * shared configured [ApiClient] and builds its own generated service from it,
 * matching the rest of the detail repositories; the primary constructor takes the
 * generated [ClubsApi] interface directly so JVM unit tests can construct the
 * repository over a fake.
 */
class ClubDetailRepository(
    private val clubsApi: ClubsApi,
) {
    @Inject
    constructor(apiClient: ApiClient) : this(apiClient.createService(ClubsApi::class.java))

    suspend fun getClub(id: Int): ClubDetailUi {
        val clubResponse = clubsApi.getClub(id)
        val club =
            clubResponse.body()?.data
                ?: error("Club unavailable (HTTP ${clubResponse.code()})")
        val shows =
            runCatchingCancellable {
                clubsApi.getClubShows(
                    id = id,
                    page = 0,
                    size = CLUB_SHOWS_LIMIT,
                ).body()?.data.orEmpty()
            }.getOrDefault(emptyList())
        return ClubDetailUi(detail = club, upcomingShows = shows)
    }

    private companion object {
        const val CLUB_SHOWS_LIMIT = 20
    }
}
