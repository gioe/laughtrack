package app.laughtrack.android.core.network.auth

import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock

class InMemoryTokenStore(
    initialTokens: SessionTokens? = null,
) : TokenStore {
    private val mutex = Mutex()
    private var tokens = initialTokens

    override suspend fun read(): SessionTokens? = mutex.withLock { tokens }

    override suspend fun save(tokens: SessionTokens) {
        mutex.withLock {
            this.tokens = tokens
        }
    }

    override suspend fun clear() {
        mutex.withLock {
            tokens = null
        }
    }
}

