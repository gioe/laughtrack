package app.laughtrack.android.feature.detail.data

import app.laughtrack.android.core.network.generated.api.ShowsApi
import app.laughtrack.android.core.network.generated.infrastructure.ApiClient
import app.laughtrack.android.feature.detail.model.ShowDetailUi
import app.laughtrack.android.feature.detail.util.buildTicketOutboundUrl
import javax.inject.Inject
import javax.inject.Named

/**
 * Loads Show detail from `GET /shows/{id}`. The Hilt path injects the shared
 * configured [ApiClient] (core:network) and builds its own generated service from
 * it, as the NetworkModule contract prescribes — this avoids re-binding
 * [ShowsApi], which `:feature:search` already provides into the same Hilt graph.
 * The primary constructor takes the generated [ShowsApi] interface directly so
 * JVM unit tests can construct the repository over a fake.
 */
class ShowDetailRepository(
    private val showsApi: ShowsApi,
    private val apiBaseUrl: String,
) {
    @Inject
    constructor(
        apiClient: ApiClient,
        @Named("apiBaseUrl") apiBaseUrl: String,
    ) : this(apiClient.createService(ShowsApi::class.java), apiBaseUrl)

    suspend fun getShow(id: Int): ShowDetailUi {
        val response = showsApi.getShow(id)
        val body = response.body() ?: error("Show unavailable (HTTP ${response.code()})")
        val detail = body.data
        return ShowDetailUi(
            detail = detail,
            relatedShows = body.relatedShows,
            ticketOutboundUrl =
                buildTicketOutboundUrl(
                    apiBaseUrl = apiBaseUrl,
                    showId = detail.id,
                    clubId = detail.club.id,
                    destinationUrl = detail.cta.url,
                ),
        )
    }
}
