package app.laughtrack.android.feature.notifications

import app.laughtrack.android.core.network.generated.api.AuthApi
import app.laughtrack.android.core.network.generated.model.NotificationListResponseData
import javax.inject.Inject

/**
 * Reads the notification center (`GET /me/notifications`, capped at 100 server-side)
 * and clears the unread badge (`POST /me/notifications/seen`). The generated
 * [AuthApi] hosts both endpoints; it is provided once by core:network.
 */
class NotificationsRepository @Inject constructor(
    private val authApi: AuthApi,
) {
    suspend fun getNotifications(): NotificationListResponseData {
        val response = authApi.getMeNotifications()
        return response.body()?.data
            ?: error("Notifications unavailable (HTTP ${response.code()})")
    }

    /** Stamp the last-seen high-water mark. Failure is non-fatal — the list still renders. */
    suspend fun markSeen() {
        runCatching { authApi.markMeNotificationsSeen() }
    }
}
