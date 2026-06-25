package app.laughtrack.android.feature.detail.data

import app.laughtrack.android.core.network.generated.api.ShowsApi
import app.laughtrack.android.core.network.generated.infrastructure.ApiClient
import app.laughtrack.android.feature.detail.model.ShowDetailUi
import app.laughtrack.android.feature.detail.util.buildTicketOutboundUrl
import javax.inject.Inject
import javax.inject.Named

/**
 * Loads Show detail from `GET /shows/{id}`. Injects the shared configured
 * [ApiClient] (core:network) and builds its own generated service from it, as the
 * NetworkModule contract prescribes — this avoids re-binding [ShowsApi], which
 * `:feature:search` already provides into the same Hilt graph.
 */
class ShowDetailRepository
    @Inject
    constructor(
        apiClient: ApiClient,
        @Named("apiBaseUrl") private val apiBaseUrl: String,
    ) {
        private val showsApi: ShowsApi = apiClient.createService(ShowsApi::class.java)

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
