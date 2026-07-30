package app.laughtrack.android.feature.detail.data

import app.laughtrack.android.core.data.runCatchingCancellable
import app.laughtrack.android.core.network.generated.api.ClubsApi
import app.laughtrack.android.core.network.generated.infrastructure.ApiClient
import app.laughtrack.android.core.network.generated.model.ClubHighlights
import app.laughtrack.android.feature.detail.model.ClubDetailUi
import app.laughtrack.android.feature.detail.model.ClubShowsPage
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
        val showsPage =
            runCatchingCancellable {
                getClubShows(id = id, page = 0)
            }.getOrDefault(ClubShowsPage(shows = emptyList(), total = 0, page = 0))
        return ClubDetailUi(
            detail = club,
            upcomingShows = showsPage.shows,
            totalShows = showsPage.total,
            currentPage = showsPage.page,
        )
    }

    suspend fun getClubShows(
        id: Int,
        page: Int,
    ): ClubShowsPage {
        val response = clubsApi.getClubShows(id = id, page = page, size = CLUB_SHOWS_LIMIT)
        val body = response.body() ?: error("Club shows unavailable (HTTP ${response.code()})")
        return ClubShowsPage(shows = body.data, total = body.total, page = page)
    }

    suspend fun getClubHighlights(id: Int): ClubHighlights {
        val response = clubsApi.getClubHighlights(id)
        return response.body()?.data
            ?: error("Club highlights unavailable (HTTP ${response.code()})")
    }

    private companion object {
        const val CLUB_SHOWS_LIMIT = 20
    }
}
