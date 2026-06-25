package app.laughtrack.android.core.network.auth

import app.laughtrack.android.core.network.generated.api.AuthApi
import app.laughtrack.android.core.network.generated.model.RefreshTokenRequest
import kotlinx.coroutines.runBlocking
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
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
    // OkHttp invokes authenticate() concurrently for every in-flight request that
    // gets a 401. The backend rotates refresh tokens single-use and treats reuse
    // as theft (revoking the whole token family), so two threads refreshing with
    // the same old token would irrecoverably sign the user out. Serialize refresh
    // and let losers of the race retry with the token the winner already stored.
    private val refreshMutex = Mutex()

    override fun authenticate(
        route: Route?,
        response: Response,
    ): Request? {
        if (responseCount(response) >= MAX_AUTH_ATTEMPTS) return null

        return runBlocking {
            refreshMutex.withLock {
                val current = tokenStore.read() ?: return@withLock null

                // If another thread already refreshed while we waited for the lock,
                // the stored access token differs from the one our failed request
                // used — just retry with the current token instead of refreshing.
                val currentBearer = "Bearer ${current.accessToken}"
                if (response.request.header("Authorization") != currentBearer) {
                    return@withLock retryWith(response, current.accessToken)
                }

                val tokenResponse =
                    refreshApi.refreshToken(
                        RefreshTokenRequest(refreshToken = current.refreshToken),
                    )
                if (!tokenResponse.isSuccessful) {
                    tokenStore.clear()
                    return@withLock null
                }

                val refreshed = tokenResponse.body() ?: return@withLock null
                val newTokens =
                    SessionTokens(
                        accessToken = refreshed.accessToken,
                        refreshToken = refreshed.refreshToken,
                        expiresAtEpochSeconds = clock.instant().epochSecond + refreshed.expiresIn,
                    )
                tokenStore.save(newTokens)
                retryWith(response, newTokens.accessToken)
            }
        }
    }

    private fun retryWith(
        response: Response,
        accessToken: String,
    ): Request =
        response.request.newBuilder()
            .header("Authorization", "Bearer $accessToken")
            .build()

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
