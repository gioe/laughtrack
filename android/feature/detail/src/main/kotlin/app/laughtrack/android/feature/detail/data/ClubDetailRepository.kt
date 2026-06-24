package app.laughtrack.android.feature.detail.data

import app.laughtrack.android.core.network.generated.api.ClubsApi
import app.laughtrack.android.core.network.generated.infrastructure.ApiClient
import app.laughtrack.android.core.network.generated.model.ClubDetail
import javax.inject.Inject

/**
 * Loads Club detail from `GET /clubs/{id}`. The contract exposes venue identity
 * only (name, hero/thumbnail image, address, website, phone, coordinates) — there
 * is no club-scoped shows or related-venues endpoint in the generated client, so
 * the screen renders venue info and outbound actions. (Upcoming shows / related
 * venues would need a `/clubs/{id}/shows` contract addition; tracked separately.)
 */
class ClubDetailRepository @Inject constructor(
    apiClient: ApiClient,
) {
    private val clubsApi: ClubsApi = apiClient.createService(ClubsApi::class.java)

    suspend fun getClub(id: Int): ClubDetail {
        val response = clubsApi.getClub(id)
        return response.body()?.data ?: error("Club unavailable (HTTP ${response.code()})")
    }
}
