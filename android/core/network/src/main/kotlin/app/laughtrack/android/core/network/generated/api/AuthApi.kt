package app.laughtrack.android.core.network.generated.api

import app.laughtrack.android.core.network.generated.infrastructure.CollectionFormats.*
import retrofit2.http.*
import retrofit2.Response
import okhttp3.RequestBody
import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

import app.laughtrack.android.core.network.generated.model.AccountDeletionResponse
import app.laughtrack.android.core.network.generated.model.ErrorResponse
import app.laughtrack.android.core.network.generated.model.MeResponse
import app.laughtrack.android.core.network.generated.model.MeUpdateRequest
import app.laughtrack.android.core.network.generated.model.MeUpdateResponse
import app.laughtrack.android.core.network.generated.model.NotificationListResponse
import app.laughtrack.android.core.network.generated.model.NotificationPreferenceUpdateRequest
import app.laughtrack.android.core.network.generated.model.NotificationPreferenceUpdateResponse
import app.laughtrack.android.core.network.generated.model.NotificationsSeenResponse
import app.laughtrack.android.core.network.generated.model.ProfileLocationUpdateRequest
import app.laughtrack.android.core.network.generated.model.ProfileLocationUpdateResponse
import app.laughtrack.android.core.network.generated.model.PushTokenDeleteResponse
import app.laughtrack.android.core.network.generated.model.PushTokenRegisterRequest
import app.laughtrack.android.core.network.generated.model.PushTokenRegisterResponse
import app.laughtrack.android.core.network.generated.model.RefreshTokenRequest
import app.laughtrack.android.core.network.generated.model.SignoutRequest
import app.laughtrack.android.core.network.generated.model.SignoutResponse
import app.laughtrack.android.core.network.generated.model.TokenResponse

interface AuthApi {
    /**
     * Delete the authenticated user account
     * Requires a valid Bearer access token. Deletes profile-owned rows before deleting the caller user. User-linked accounts, refresh tokens, and sent notifications are removed by database cascades. iOS clients should clear local keychain entries after a 200 response.
     * Responses:
     *  - 200: Account deleted
     *  - 401: Missing or invalid Bearer token
     *  - 422: Authenticated user has no UserProfile row
     *  - 429: Rate limit exceeded
     *  - 500: Account deletion failed
     *
     * @return [AccountDeletionResponse]
     */
    @DELETE("me")
    suspend fun deleteMe(): Response<AccountDeletionResponse>

    /**
     * Deactivate a device push token for the authenticated user
     * Deactivates (soft-deletes) a previously registered device token so the device stops receiving push notifications.
     * Responses:
     *  - 200: Push token deactivation result
     *  - 400: Invalid request body (token length / platform)
     *  - 401: Missing or invalid Bearer token
     *  - 422: Authenticated user has no UserProfile row
     *  - 429: Rate limit exceeded
     *
     * @param pushTokenRegisterRequest 
     * @return [PushTokenDeleteResponse]
     */
    @DELETE("me/push-tokens")
    suspend fun deleteMePushToken(@Body pushTokenRegisterRequest: PushTokenRegisterRequest): Response<PushTokenDeleteResponse>

    /**
     * Exchange a session cookie for an access + refresh token pair
     * iOS clients call this after completing OAuth via ASWebAuthenticationSession. Returns a short-lived access JWT (15 minutes) plus a long-lived opaque refresh token (30 days). Store both in the keychain separately.
     * Responses:
     *  - 200: Token pair issued successfully
     *  - 401: No active session
     *  - 403: Invalid origin (CSRF protection)
     *  - 429: Rate limit exceeded
     *
     * @return [TokenResponse]
     */
    @POST("auth/token")
    suspend fun exchangeToken(): Response<TokenResponse>

    /**
     * Get the authenticated user&#39;s identity (display name, email, avatar URL)
     * Returns the User row backing the access token. iOS clients use this to render real account info on the Profile tab instead of the OAuth provider stub.
     * Responses:
     *  - 200: User profile
     *  - 401: Missing or invalid Bearer token
     *  - 422: Authenticated user has no UserProfile row
     *  - 429: Rate limit exceeded
     *
     * @return [MeResponse]
     */
    @GET("me")
    suspend fun getMe(): Response<MeResponse>

    /**
     * List the authenticated user&#39;s notification history
     * Returns the user&#39;s comedian-arrival notifications (push + email), reconstructed from sent-notification records and grouped per (comedian, show). iOS renders these in the notification center. Capped at the 100 most-recent; no cursor pagination.
     * Responses:
     *  - 200: Notification history
     *  - 401: Missing or invalid Bearer token
     *  - 422: Authenticated user has no UserProfile row
     *  - 429: Rate limit exceeded
     *
     * @return [NotificationListResponse]
     */
    @GET("me/notifications")
    suspend fun getMeNotifications(): Response<NotificationListResponse>

    /**
     * Mark the notification center as seen
     * Stamps the notifications last-seen high-water mark to now, clearing the unread badge. iOS calls this when the user opens the notification center.
     * Responses:
     *  - 200: Last-seen timestamp updated
     *  - 401: Missing or invalid Bearer token
     *  - 422: Authenticated user has no UserProfile row
     *  - 429: Rate limit exceeded
     *
     * @return [NotificationsSeenResponse]
     */
    @POST("me/notifications/seen")
    suspend fun markMeNotificationsSeen(): Response<NotificationsSeenResponse>

    /**
     * Update the authenticated user&#39;s Near-Me location preferences
     * Sets the saved ZIP code and nearby search radius used for Near Me. Send null for a field to clear it (the client sends explicit JSON null to clear the saved ZIP / distance).
     * Responses:
     *  - 200: Location preferences updated
     *  - 400: Invalid request body (zipCode must be a 5-digit US ZIP, distance a positive integer)
     *  - 401: Missing or invalid Bearer token
     *  - 422: Authenticated user has no UserProfile row
     *  - 429: Rate limit exceeded
     *
     * @param profileLocationUpdateRequest 
     * @return [ProfileLocationUpdateResponse]
     */
    @PATCH("me/location")
    suspend fun patchMeLocation(@Body profileLocationUpdateRequest: ProfileLocationUpdateRequest): Response<ProfileLocationUpdateResponse>

    /**
     * Update the authenticated user&#39;s show-notification preferences
     * Updates the email/push show-notification toggles for the authenticated user. At least one field must be provided; omitted fields are left unchanged.
     * Responses:
     *  - 200: Notification preferences updated
     *  - 400: Invalid request body or no preference provided
     *  - 401: Missing or invalid Bearer token
     *  - 422: Authenticated user has no UserProfile row
     *  - 429: Rate limit exceeded
     *
     * @param notificationPreferenceUpdateRequest 
     * @return [NotificationPreferenceUpdateResponse]
     */
    @PATCH("me/notifications")
    suspend fun patchMeNotifications(@Body notificationPreferenceUpdateRequest: NotificationPreferenceUpdateRequest): Response<NotificationPreferenceUpdateResponse>

    /**
     * Rotate a refresh token for a new access + refresh pair
     * Atomically revokes the submitted refresh token and issues a new access+refresh pair. Revoked, expired, or unknown tokens return 401. No Bearer authentication required — the refresh token itself is the credential.
     * Responses:
     *  - 200: New token pair issued; the submitted refresh token is now revoked.
     *  - 400: Missing or malformed body
     *  - 401: Refresh token is unknown, revoked, or expired
     *  - 429: Rate limit exceeded
     *
     * @param refreshTokenRequest 
     * @return [TokenResponse]
     */
    @POST("auth/refresh")
    suspend fun refreshToken(@Body refreshTokenRequest: RefreshTokenRequest): Response<TokenResponse>

    /**
     * Register a device push token for the authenticated user
     * Upserts an APNs (iOS) or FCM (Android) device token so the user receives comedian-arrival push notifications. iOS APNs hex tokens are stored lowercased; Android FCM tokens are stored verbatim.
     * Responses:
     *  - 200: Push token registered
     *  - 400: Invalid request body (token length / platform)
     *  - 401: Missing or invalid Bearer token
     *  - 422: Authenticated user has no UserProfile row
     *  - 429: Rate limit exceeded
     *
     * @param pushTokenRegisterRequest 
     * @return [PushTokenRegisterResponse]
     */
    @POST("me/push-tokens")
    suspend fun registerMePushToken(@Body pushTokenRegisterRequest: PushTokenRegisterRequest): Response<PushTokenRegisterResponse>

    /**
     * Revoke the current native session refresh token
     * Requires a valid Bearer access token. Current native clients provide their refresh token and sanitized client context so only that session is revoked. For compatibility, an omitted request body retains the legacy behavior of revoking every active refresh token for the caller. Clients should still clear local credentials after the call completes.
     * Responses:
     *  - 200: Tokens revoked
     *  - 400: Malformed nonempty request body or invalid client context
     *  - 401: Missing or invalid Bearer token
     *  - 422: Authenticated user has no UserProfile row
     *  - 429: Rate limit exceeded
     *
     * @param signoutRequest Current native session details. Omitted only by legacy clients. (optional)
     * @return [SignoutResponse]
     */
    @POST("auth/signout")
    suspend fun signout(@Body signoutRequest: SignoutRequest? = null): Response<SignoutResponse>

    /**
     * Update authenticated user profile state
     * Updates durable profile state for the authenticated user. iOS clients use this to mark comedian onboarding complete after the user finishes or skips onboarding.
     * Responses:
     *  - 200: Profile state updated
     *  - 400: Invalid request body
     *  - 401: Missing or invalid Bearer token
     *  - 422: Authenticated user has no UserProfile row
     *  - 429: Rate limit exceeded
     *
     * @param meUpdateRequest 
     * @return [MeUpdateResponse]
     */
    @PATCH("me")
    suspend fun updateMe(@Body meUpdateRequest: MeUpdateRequest): Response<MeUpdateResponse>

}
