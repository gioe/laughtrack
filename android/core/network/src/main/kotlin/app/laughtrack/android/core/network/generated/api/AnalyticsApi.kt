package app.laughtrack.android.core.network.generated.api

import app.laughtrack.android.core.network.generated.infrastructure.CollectionFormats.*
import retrofit2.http.*
import retrofit2.Response
import okhttp3.RequestBody
import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

import app.laughtrack.android.core.network.generated.model.ErrorResponse
import app.laughtrack.android.core.network.generated.model.TicketClickRequest

interface AnalyticsApi {
    /**
     * Record an outbound ticket purchase click
     * Records first-party analytics for ticket CTA clicks. Authenticated requests are attributed to the caller profile; anonymous requests are attributed to an opaque visitor cookie.
     * Responses:
     *  - 201: Click recorded
     *  - 400: Invalid click payload
     *  - 401: Invalid Bearer token
     *  - 429: Rate limit exceeded
     *  - 500: Server error
     *
     * @param ticketClickRequest 
     * @return [Unit]
     */
    @POST("ticket-clicks")
    suspend fun recordTicketClick(@Body ticketClickRequest: TicketClickRequest): Response<Unit>

}
