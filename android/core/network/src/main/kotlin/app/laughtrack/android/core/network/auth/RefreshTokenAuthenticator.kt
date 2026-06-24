package app.laughtrack.android.core.network.auth

import app.laughtrack.android.core.network.generated.api.AuthApi
import app.laughtrack.android.core.network.generated.model.RefreshTokenRequest
import kotlinx.coroutines.runBlocking
import okhttp3.Authenticator
import okhttp3.Request
import okhttp3.Response
import okhttp3.Route
import java.time.Clock

class RefreshTokenAuthenticator(
    private val tokenStore: TokenStore,
    private val refreshApi: AuthApi,
    private val clock: Clock = Clock.systemUTC(),
) : Authenticator {
    override fun authenticate(route: Route?, response: Response): Request? {
        if (responseCount(response) >= MAX_AUTH_ATTEMPTS) return null

        val currentTokens = runBlocking { tokenStore.read() } ?: return null
        val tokenResponse = runBlocking {
            refreshApi.refreshToken(
                RefreshTokenRequest(refreshToken = currentTokens.refreshToken),
            )
        }

        if (!tokenResponse.isSuccessful) {
            runBlocking { tokenStore.clear() }
            return null
        }

        val refreshed = tokenResponse.body() ?: return null
        val newTokens = SessionTokens(
            accessToken = refreshed.accessToken,
            refreshToken = refreshed.refreshToken,
            expiresAtEpochSeconds = clock.instant().epochSecond + refreshed.expiresIn,
        )
        runBlocking { tokenStore.save(newTokens) }

        return response.request.newBuilder()
            .header("Authorization", "Bearer ${newTokens.accessToken}")
            .build()
    }

    private fun responseCount(response: Response): Int {
        var result = 1
        var prior = response.priorResponse
        while (prior != null) {
            result += 1
            prior = prior.priorResponse
        }
        return result
    }

    private companion object {
        const val MAX_AUTH_ATTEMPTS = 2
    }
}

