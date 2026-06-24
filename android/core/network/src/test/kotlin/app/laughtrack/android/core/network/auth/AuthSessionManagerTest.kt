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
import org.junit.Assert.assertTrue
import org.junit.Test
import retrofit2.Response
import java.time.Clock
import java.time.Instant
import java.time.ZoneOffset

class AuthSessionManagerTest {
    private val clock = Clock.fixed(Instant.ofEpochSecond(1_700_000_000), ZoneOffset.UTC)

    @Test
    fun buildSignInUrlTargetsNativeCallback() {
        val manager = AuthSessionManager(
            tokenStore = InMemoryTokenStore(),
            authApi = UnsupportedAuthApi,
            websiteBaseUrl = "https://www.laugh-track.com",
            clock = clock,
        )

        val expectedCallback =
            "https%3A%2F%2Fwww.laugh-track.com%2Fapi%2Fv1%2Fauth%2Fnative%2Fcallback%3Fprovider%3Dgoogle"
        assertEquals(
            "https://www.laugh-track.com/?nativeAuthProvider=google&callbackUrl=$expectedCallback",
            manager.buildSignInUrl(AuthProvider.GOOGLE),
        )
    }

    @Test
    fun handleCallbackStoresTokenPair() = runTest {
        val store = InMemoryTokenStore()
        val manager = AuthSessionManager(
            tokenStore = store,
            authApi = UnsupportedAuthApi,
            websiteBaseUrl = "https://www.laugh-track.com",
            clock = clock,
        )

        val result = manager.handleCallback(
            "laughtrack://auth/callback?provider=google" +
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
