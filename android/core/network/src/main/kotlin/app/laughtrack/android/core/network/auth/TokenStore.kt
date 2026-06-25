package app.laughtrack.android.core.network.auth

interface TokenStore {
    suspend fun read(): SessionTokens?

    suspend fun save(tokens: SessionTokens)

    suspend fun clear()
}
