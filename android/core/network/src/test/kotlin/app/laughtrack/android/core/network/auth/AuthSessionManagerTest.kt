package app.laughtrack.android.core.network.auth

import app.laughtrack.android.core.network.generated.api.AuthApi
import app.laughtrack.android.core.network.generated.model.AccountDeletionResponse
import app.laughtrack.android.core.network.generated.model.MeResponse
import app.laughtrack.android.core.network.generated.model.MeUpdateRequest
import app.laughtrack.android.core.network.generated.model.MeUpdateResponse
import app.laughtrack.android.core.network.generated.model.NotificationListResponse
import app.laughtrack.android.core.network.generated.model.NotificationsSeenResponse
import app.laughtrack.android.core.network.generated.model.RefreshTokenRequest
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
    fun handleCallbackStoresTokenPairWhenStateMatches() = runTest {
        val store = InMemoryTokenStore()
        val manager = newManager(store)
        val state = extractState(manager.buildSignInUrl(AuthProvider.GOOGLE))

        val result = manager.handleCallback(
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
    fun handleCallbackRejectsMismatchedStateWithoutStoringTokens() = runTest {
        val store = InMemoryTokenStore()
        val manager = newManager(store)
        manager.buildSignInUrl(AuthProvider.GOOGLE)

        val result = manager.handleCallback(
            "laughtrack://auth/callback?provider=google&state=attacker-chosen" +
                "&accessToken=injected&refreshToken=injected&expiresIn=900",
        )

        assertEquals(AuthCallbackResult.Error("state_mismatch"), result)
        assertEquals(null, store.read())
    }

    @Test
    fun handleCallbackRejectsCallbackWithNoStateParam() = runTest {
        val store = InMemoryTokenStore()
        val manager = newManager(store)
        manager.buildSignInUrl(AuthProvider.GOOGLE)

        val result = manager.handleCallback(
            "laughtrack://auth/callback?provider=google" +
                "&accessToken=injected&refreshToken=injected&expiresIn=900",
        )

        assertEquals(AuthCallbackResult.Error("state_mismatch"), result)
        assertEquals(null, store.read())
    }

    @Test
    fun handleCallbackRejectsTokensWhenNoSignInWasInitiated() = runTest {
        val store = InMemoryTokenStore()
        val manager = newManager(store)

        // No buildSignInUrl() first -> no pending nonce -> a hostile deep link
        // invoked directly is rejected.
        val result = manager.handleCallback(
            "laughtrack://auth/callback?provider=google&state=anything" +
                "&accessToken=injected&refreshToken=injected&expiresIn=900",
        )

        assertEquals(AuthCallbackResult.Error("state_mismatch"), result)
        assertEquals(null, store.read())
    }

    @Test
    fun handleCallbackReturnsErrorWithoutStoringTokens() = runTest {
        val store = InMemoryTokenStore()
        val manager = AuthSessionManager(
            tokenStore = store,
            authApi = UnsupportedAuthApi,
            websiteBaseUrl = "https://www.laugh-track.com",
            clock = clock,
        )

        val result = manager.handleCallback(
            "laughtrack://auth/callback?provider=apple&error=OAuthCallback",
        )

        assertEquals(AuthCallbackResult.Error("OAuthCallback"), result)
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
    private fun extractState(signInUrl: String): String =
        decodeCallbackUrl(signInUrl).substringAfter("state=")

    private object UnsupportedAuthApi : AuthApi {
        override suspend fun deleteMe(): Response<AccountDeletionResponse> = unsupported()
        override suspend fun exchangeToken(): Response<TokenResponse> = unsupported()
        override suspend fun getMe(): Response<MeResponse> = unsupported()
        override suspend fun getMeNotifications(): Response<NotificationListResponse> = unsupported()
        override suspend fun markMeNotificationsSeen(): Response<NotificationsSeenResponse> = unsupported()
        override suspend fun refreshToken(
            refreshTokenRequest: RefreshTokenRequest,
        ): Response<TokenResponse> = unsupported()
        override suspend fun signout(): Response<SignoutResponse> = unsupported()
        override suspend fun updateMe(meUpdateRequest: MeUpdateRequest): Response<MeUpdateResponse> = unsupported()

        private fun unsupported(): Nothing = error("not used in this test")
    }
}
