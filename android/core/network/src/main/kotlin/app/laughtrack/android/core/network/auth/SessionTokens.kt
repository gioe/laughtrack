package app.laughtrack.android.core.network.auth

data class SessionTokens(
    val accessToken: String,
    val refreshToken: String,
    val expiresAtEpochSeconds: Long,
)

