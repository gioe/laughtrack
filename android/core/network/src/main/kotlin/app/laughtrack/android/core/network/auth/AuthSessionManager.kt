package app.laughtrack.android.core.network.auth

import app.laughtrack.android.core.network.generated.api.AuthApi
import app.laughtrack.android.core.network.generated.model.MeResponse
import java.net.URI
import java.net.URLDecoder
import java.net.URLEncoder
import java.nio.charset.StandardCharsets
import java.time.Clock

class AuthSessionManager(
    private val tokenStore: TokenStore,
    private val authApi: AuthApi,
    private val websiteBaseUrl: String,
    private val clock: Clock = Clock.systemUTC(),
) {
    fun buildSignInUrl(provider: AuthProvider): String {
        val callbackUrl = "$websiteBaseUrl/api/v1/auth/native/callback?provider=${provider.id}"
        return "$websiteBaseUrl/?nativeAuthProvider=${provider.id}&callbackUrl=${encode(callbackUrl)}"
    }

    suspend fun restoreSession(): SessionTokens? = tokenStore.read()

    suspend fun handleCallback(callbackUrl: String): AuthCallbackResult {
        val uri = runCatching { URI(callbackUrl) }.getOrNull()
            ?: return AuthCallbackResult.Ignored

        if (
            uri.scheme != DEEP_LINK_SCHEME ||
            uri.host != DEEP_LINK_HOST ||
            uri.path != DEEP_LINK_PATH
        ) {
            return AuthCallbackResult.Ignored
        }

        val query = parseQuery(uri.rawQuery)
        query["error"]?.let { return AuthCallbackResult.Error(it) }

        val accessToken = query["accessToken"]
        val refreshToken = query["refreshToken"]
        if (accessToken.isNullOrBlank() || refreshToken.isNullOrBlank()) {
            return AuthCallbackResult.Error("missing_token")
        }

        val expiresIn = query["expiresIn"]?.toLongOrNull() ?: DEFAULT_ACCESS_TOKEN_TTL_SECONDS
        val tokens = SessionTokens(
            accessToken = accessToken,
            refreshToken = refreshToken,
            expiresAtEpochSeconds = clock.instant().epochSecond + expiresIn,
        )
        tokenStore.save(tokens)
        return AuthCallbackResult.Authenticated(tokens)
    }

    suspend fun getMe(): Result<MeResponse> = runCatching {
        val response = authApi.getMe()
        if (!response.isSuccessful) {
            error("GET /me failed with HTTP ${response.code()}")
        }
        response.body() ?: error("GET /me returned an empty body")
    }

    suspend fun signOut(): Boolean {
        val response = runCatching { authApi.signout() }.getOrNull()
        tokenStore.clear()
        return response?.isSuccessful == true
    }

    suspend fun deleteAccount(): Boolean {
        val response = runCatching { authApi.deleteMe() }.getOrNull()
        if (response?.isSuccessful == true) {
            tokenStore.clear()
        }
        return response?.isSuccessful == true
    }

    private fun parseQuery(rawQuery: String?): Map<String, String> {
        if (rawQuery.isNullOrBlank()) return emptyMap()
        return rawQuery.split("&")
            .mapNotNull { part ->
                val separator = part.indexOf("=")
                if (separator < 0) return@mapNotNull null
                val key = decode(part.substring(0, separator))
                val value = decode(part.substring(separator + 1))
                key to value
            }
            .toMap()
    }

    private fun encode(value: String): String =
        URLEncoder.encode(value, StandardCharsets.UTF_8.name())

    private fun decode(value: String): String =
        URLDecoder.decode(value, StandardCharsets.UTF_8.name())

    companion object {
        private const val DEEP_LINK_SCHEME = "laughtrack"
        private const val DEEP_LINK_HOST = "auth"
        private const val DEEP_LINK_PATH = "/callback"
        private const val DEFAULT_ACCESS_TOKEN_TTL_SECONDS = 900L

        /**
         * True when [url] is the OAuth callback (`laughtrack://auth/callback`), as
         * opposed to an entity navigation deep link (`laughtrack://show/123`, …)
         * handled by core:navigation. Lets MainActivity dispatch the shared scheme.
         */
        fun isAuthCallback(url: String): Boolean {
            val uri = runCatching { URI(url) }.getOrNull() ?: return false
            return uri.scheme == DEEP_LINK_SCHEME &&
                uri.host == DEEP_LINK_HOST &&
                uri.path == DEEP_LINK_PATH
        }
    }
}

enum class AuthProvider(val id: String) {
    GOOGLE("google"),
    APPLE("apple"),
}

sealed interface AuthCallbackResult {
    data class Authenticated(val tokens: SessionTokens) : AuthCallbackResult
    data class Error(val code: String) : AuthCallbackResult
    data object Ignored : AuthCallbackResult
}
