package app.laughtrack.android.push

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable
import retrofit2.Response
import retrofit2.http.Body
import retrofit2.http.HTTP
import retrofit2.http.POST

/**
 * Hand-rolled client for the `/me/push-tokens` endpoint, which is intentionally
 * absent from the generated OpenAPI client (iOS calls it the same way via
 * PushDeviceTokenManager). Built from the shared authed [ApiClient], so the Bearer
 * interceptor is applied automatically.
 */
interface PushTokenApi {
    @POST("me/push-tokens")
    suspend fun register(
        @Body body: PushTokenRequest,
    ): Response<Unit>

    // DELETE carries a JSON body (the token to deactivate); @DELETE forbids @Body,
    // so use @HTTP with hasBody=true. The web route reads the token from the body.
    @HTTP(method = "DELETE", path = "me/push-tokens", hasBody = true)
    suspend fun deactivate(
        @Body body: PushTokenRequest,
    ): Response<Unit>
}

@Serializable
data class PushTokenRequest(
    @SerialName("token") val token: String,
    @SerialName("platform") val platform: String = ANDROID_PLATFORM,
) {
    companion object {
        const val ANDROID_PLATFORM = "android"
    }
}
