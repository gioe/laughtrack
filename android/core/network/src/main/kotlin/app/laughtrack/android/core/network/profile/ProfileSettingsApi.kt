package app.laughtrack.android.core.network.profile

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable
import retrofit2.Response
import retrofit2.http.Body
import retrofit2.http.PATCH

interface ProfileSettingsApi {
    @PATCH("me/location")
    suspend fun updateLocation(
        @Body request: ProfileLocationUpdateRequest,
    ): Response<ProfileLocationUpdateResponse>

    @PATCH("me/notifications")
    suspend fun updateNotifications(
        @Body request: ProfileNotificationUpdateRequest,
    ): Response<ProfileNotificationUpdateResponse>
}

@Serializable
data class ProfileLocationUpdateRequest(
    @SerialName("zipCode")
    val zipCode: String?,
    @SerialName("nearbyDistanceMiles")
    val nearbyDistanceMiles: Int?,
)

@Serializable
data class ProfileLocationUpdateResponse(
    @SerialName("data")
    val data: ProfileLocationUpdateData,
)

@Serializable
data class ProfileLocationUpdateData(
    @SerialName("zipCode")
    val zipCode: String?,
    @SerialName("nearbyDistanceMiles")
    val nearbyDistanceMiles: Int?,
)

@Serializable
data class ProfileNotificationUpdateRequest(
    @SerialName("emailShowNotifications")
    val emailShowNotifications: Boolean? = null,
    @SerialName("pushShowNotifications")
    val pushShowNotifications: Boolean? = null,
)

@Serializable
data class ProfileNotificationUpdateResponse(
    @SerialName("data")
    val data: ProfileNotificationUpdateData,
)

@Serializable
data class ProfileNotificationUpdateData(
    @SerialName("emailShowNotifications")
    val emailShowNotifications: Boolean,
    @SerialName("pushShowNotifications")
    val pushShowNotifications: Boolean,
)
