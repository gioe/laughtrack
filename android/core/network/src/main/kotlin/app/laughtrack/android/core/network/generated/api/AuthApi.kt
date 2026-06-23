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
import app.laughtrack.android.core.network.generated.model.NotificationsSeenResponse
import app.laughtrack.android.core.network.generated.model.RefreshTokenRequest
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
     * Revoke every active refresh token for the authenticated user
     * Requires a valid Bearer access token. Marks every non-revoked refresh_token row for the caller as revoked. iOS clients should still clear local keychain entries after the call completes.
     * Responses:
     *  - 200: Tokens revoked
     *  - 401: Missing or invalid Bearer token
     *  - 422: Authenticated user has no UserProfile row
     *  - 429: Rate limit exceeded
     *
     * @return [SignoutResponse]
     */
    @POST("auth/signout")
    suspend fun signout(): Response<SignoutResponse>

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
