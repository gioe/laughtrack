package app.laughtrack.android.core.network.auth

import app.laughtrack.android.core.network.generated.api.AuthApi
import app.laughtrack.android.core.network.generated.model.AccountDeletionResponse
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
import kotlinx.coroutines.test.runTest
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import retrofit2.Response
import java.net.URLDecoder
import java.nio.charset.StandardCharsets
import java.time.Clock
import java.time.Instant
import java.time.ZoneOffset

class AuthSessionManagerTest {
    private val clock = Clock.fixed(Instant.ofEpochSecond(1_700_000_000), ZoneOffset.UTC)

    @Test
    fun buildSignInUrlTargetsNativeCallbackWithRandomState() {
        val manager = newManager()

        val state = extractState(manager.buildSignInUrl(AuthProvider.GOOGLE))
        val decodedCallback = decodeCallbackUrl(manager.buildSignInUrl(AuthProvider.GOOGLE))

        // The inner callbackUrl points at the native callback for the provider
        // and carries the per-flow state nonce.
        assertTrue(
            decodedCallback.startsWith(
                "https://www.laugh-track.com/api/v1/auth/native/callback?provider=google&state=",
            ),
        )
        assertTrue(state.isNotBlank())
        // Each sign-in attempt mints a fresh nonce.
        assertNotEquals(
            extractState(manager.buildSignInUrl(AuthProvider.GOOGLE)),
            extractState(manager.buildSignInUrl(AuthProvider.GOOGLE)),
        )
    }

    @Test
    fun buildSignInUrlCarriesEmailProviderForMagicLink() {
        val manager = newManager()

        val signInUrl = manager.buildSignInUrl(AuthProvider.EMAIL)

        // The outer page picks the magic-link form via nativeAuthProvider=email...
        assertTrue(signInUrl.contains("nativeAuthProvider=email"))
        // ...and the inner native callback is stamped with provider=email so the
        // web completion redirects tokens back to laughtrack://auth/callback.
        assertTrue(
            decodeCallbackUrl(signInUrl).startsWith(
                "https://www.laugh-track.com/api/v1/auth/native/callback?provider=email&state=",
            ),
        )
    }

    @Test
    fun handleCallbackStoresTokenPairWhenStateMatches() =
        runTest {
            val store = InMemoryTokenStore()
            val manager = newManager(store)
            val state = extractState(manager.buildSignInUrl(AuthProvider.GOOGLE))

            val result =
                manager.handleCallback(
                    "laughtrack://auth/callback?provider=google&state=$state" +
                        "&accessToken=access-jwt&refreshToken=refresh-token&expiresIn=900",
                )

            assertTrue(result is AuthCallbackResult.Authenticated)
            assertEquals(
                SessionTokens(
                    accessToken = "access-jwt",
                    refreshToken = "refresh-token",
                    expiresAtEpochSeconds = 1_700_000_900,
                ),
                store.read(),
            )
        }

    @Test
    fun handleCallbackRejectsMismatchedStateWithoutStoringTokens() =
        runTest {
            val store = InMemoryTokenStore()
            val manager = newManager(store)
            manager.buildSignInUrl(AuthProvider.GOOGLE)

            val result =
                manager.handleCallback(
                    "laughtrack://auth/callback?provider=google&state=attacker-chosen" +
                        "&accessToken=injected&refreshToken=injected&expiresIn=900",
                )

            assertEquals(AuthCallbackResult.Error("state_mismatch"), result)
            assertEquals(null, store.read())
        }

    @Test
    fun handleCallbackRejectsCallbackWithNoStateParam() =
        runTest {
            val store = InMemoryTokenStore()
            val manager = newManager(store)
            manager.buildSignInUrl(AuthProvider.GOOGLE)

            val result =
                manager.handleCallback(
                    "laughtrack://auth/callback?provider=google" +
                        "&accessToken=injected&refreshToken=injected&expiresIn=900",
                )

            assertEquals(AuthCallbackResult.Error("state_mismatch"), result)
            assertEquals(null, store.read())
        }

    @Test
    fun handleCallbackRejectsTokensWhenNoSignInWasInitiated() =
        runTest {
            val store = InMemoryTokenStore()
            val manager = newManager(store)

            // No buildSignInUrl() first -> no pending nonce -> a hostile deep link
            // invoked directly is rejected.
            val result =
                manager.handleCallback(
                    "laughtrack://auth/callback?provider=google&state=anything" +
                        "&accessToken=injected&refreshToken=injected&expiresIn=900",
                )

            assertEquals(AuthCallbackResult.Error("state_mismatch"), result)
            assertEquals(null, store.read())
        }

    @Test
    fun handleCallbackReturnsErrorWithoutStoringTokens() =
        runTest {
            val store = InMemoryTokenStore()
            val manager =
                AuthSessionManager(
                    tokenStore = store,
                    authApi = UnsupportedAuthApi,
                    websiteBaseUrl = "https://www.laugh-track.com",
                    clock = clock,
                )

            val result =
                manager.handleCallback(
                    "laughtrack://auth/callback?provider=apple&error=OAuthCallback",
                )

            assertEquals(AuthCallbackResult.Error("OAuthCallback"), result)
            assertEquals(null, store.read())
        }

    @Test
    fun signOutSendsCurrentRefreshTokenAndSanitizedClientContext() =
        runTest {
            val store =
                InMemoryTokenStore(
                    SessionTokens(
                        accessToken = "access-jwt",
                        refreshToken = "current-refresh-token",
                        expiresAtEpochSeconds = 1_700_000_900,
                    ),
                )
            val authApi = RecordingAuthApi()
            val manager =
                AuthSessionManager(
                    tokenStore = store,
                    authApi = authApi,
                    websiteBaseUrl = "https://www.laugh-track.com",
                    appVersion = "2.17.0+57",
                    clock = clock,
                )

            val succeeded = manager.signOut()

            assertTrue(succeeded)
            assertEquals(
                SignoutRequest(
                    refreshToken = "current-refresh-token",
                    platform = SignoutRequest.Platform.ANDROID,
                    appVersion = "2.17.0+57",
                    source = SignoutRequest.Source.PROFILE,
                ),
                authApi.signoutRequest,
            )
            assertEquals(null, store.read())
        }

    @Test
    fun signOutRetriesWithRotatedRefreshTokenWhenInitialRevocationMisses() =
        runTest {
            val store =
                InMemoryTokenStore(
                    SessionTokens(
                        accessToken = "stale-access-token",
                        refreshToken = "initial-refresh-token",
                        expiresAtEpochSeconds = 1_700_000_900,
                    ),
                )
            val authApi = RotatingSignoutAuthApi(store)
            val manager =
                AuthSessionManager(
                    tokenStore = store,
                    authApi = authApi,
                    websiteBaseUrl = "https://www.laugh-track.com",
                    appVersion = "2.17.0+57",
                    clock = clock,
                )

            val succeeded = manager.signOut()

            assertTrue(succeeded)
            assertEquals(
                listOf("initial-refresh-token", "rotated-refresh-token"),
                authApi.signoutRequests.map { it.refreshToken },
            )
            assertEquals(null, store.read())
        }

    private fun newManager(store: TokenStore = InMemoryTokenStore()): AuthSessionManager =
        AuthSessionManager(
            tokenStore = store,
            authApi = UnsupportedAuthApi,
            websiteBaseUrl = "https://www.laugh-track.com",
            clock = clock,
        )

    /** Decode the inner `callbackUrl` param the app embeds in the web sign-in URL. */
    private fun decodeCallbackUrl(signInUrl: String): String =
        URLDecoder.decode(signInUrl.substringAfter("callbackUrl="), StandardCharsets.UTF_8.name())

    /** Pull the per-flow `state` nonce out of a built sign-in URL. */
    private fun extractState(signInUrl: String): String = decodeCallbackUrl(signInUrl).substringAfter("state=")

    private object UnsupportedAuthApi : AuthApi {
        override suspend fun deleteMe(): Response<AccountDeletionResponse> = unsupported()

        override suspend fun deleteMePushToken(
            pushTokenRegisterRequest: PushTokenRegisterRequest,
        ): Response<PushTokenDeleteResponse> = unsupported()

        override suspend fun exchangeToken(): Response<TokenResponse> = unsupported()

        override suspend fun getMe(): Response<MeResponse> = unsupported()

        override suspend fun getMeNotifications(): Response<NotificationListResponse> = unsupported()

        override suspend fun markMeNotificationsSeen(): Response<NotificationsSeenResponse> = unsupported()

        override suspend fun patchMeLocation(
            profileLocationUpdateRequest: ProfileLocationUpdateRequest,
        ): Response<ProfileLocationUpdateResponse> = unsupported()

        override suspend fun patchMeNotifications(
            notificationPreferenceUpdateRequest: NotificationPreferenceUpdateRequest,
        ): Response<NotificationPreferenceUpdateResponse> = unsupported()

        override suspend fun refreshToken(refreshTokenRequest: RefreshTokenRequest): Response<TokenResponse> =
            unsupported()

        override suspend fun registerMePushToken(
            pushTokenRegisterRequest: PushTokenRegisterRequest,
        ): Response<PushTokenRegisterResponse> = unsupported()

        override suspend fun signout(signoutRequest: SignoutRequest?): Response<SignoutResponse> = unsupported()

        override suspend fun updateMe(meUpdateRequest: MeUpdateRequest): Response<MeUpdateResponse> = unsupported()

        private fun unsupported(): Nothing = error("not used in this test")
    }

    private class RecordingAuthApi : AuthApi by UnsupportedAuthApi {
        var signoutRequest: SignoutRequest? = null
            private set

        override suspend fun signout(signoutRequest: SignoutRequest?): Response<SignoutResponse> {
            this.signoutRequest = signoutRequest
            return Response.success(SignoutResponse(revoked = 1))
        }
    }

    private class RotatingSignoutAuthApi(
        private val tokenStore: TokenStore,
    ) : AuthApi by UnsupportedAuthApi {
        val signoutRequests = mutableListOf<SignoutRequest>()

        override suspend fun signout(signoutRequest: SignoutRequest?): Response<SignoutResponse> {
            val request = requireNotNull(signoutRequest)
            signoutRequests += request
            return if (signoutRequests.size == 1) {
                tokenStore.save(
                    SessionTokens(
                        accessToken = "rotated-access-token",
                        refreshToken = "rotated-refresh-token",
                        expiresAtEpochSeconds = 1_700_001_800,
                    ),
                )
                Response.success(SignoutResponse(revoked = 0))
            } else {
                Response.success(SignoutResponse(revoked = 1))
            }
        }
    }
}
