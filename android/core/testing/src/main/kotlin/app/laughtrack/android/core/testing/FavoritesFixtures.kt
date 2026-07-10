package app.laughtrack.android.core.testing

import app.laughtrack.android.core.data.auth.LoginPromptController
import app.laughtrack.android.core.data.favorites.FavoriteEntity
import app.laughtrack.android.core.data.favorites.FavoriteQueue
import app.laughtrack.android.core.data.favorites.FavoritesRepository
import app.laughtrack.android.core.network.auth.AuthSessionManager
import app.laughtrack.android.core.network.auth.SessionTokens
import app.laughtrack.android.core.network.auth.TokenStore
import app.laughtrack.android.core.network.generated.api.AuthApi
import app.laughtrack.android.core.network.generated.api.FavoritesApi
import java.time.Clock

/** [FavoriteQueue] that drops every enqueue, for tests that never replay offline writes. */
object NoOpQueue : FavoriteQueue {
    override fun enqueue(
        entity: FavoriteEntity,
        id: String,
        isFavorite: Boolean,
    ) = Unit
}

/** [TokenStore] with no stored session, so the auth session restores to signed-out. */
object NullTokenStore : TokenStore {
    override suspend fun read(): SessionTokens? = null

    override suspend fun save(tokens: SessionTokens) = Unit

    override suspend fun clear() = Unit
}

/**
 * Real [FavoritesRepository] over a signed-out auth session: no stored tokens, no
 * offline queue, and an [AuthApi] that must never be called. Pass [favoritesApi]
 * when the test drives refresh flows; the default throws on any use. Signed-out
 * describes only the repository's auth session — ViewModels that take their own
 * signedIn flag (e.g. LibraryViewModel.refresh) drive refreshes independently of
 * it, so this fixture backs those signed-in-flow tests too.
 */
fun signedOutFavoritesRepository(favoritesApi: FavoritesApi = throwingApi()): FavoritesRepository =
    FavoritesRepository(
        favoritesApi = favoritesApi,
        offlineQueue = NoOpQueue,
        authSessionManager =
            AuthSessionManager(
                tokenStore = NullTokenStore,
                authApi = throwingApi<AuthApi>(),
                websiteBaseUrl = "https://www.laugh-track.com",
                clock = Clock.systemUTC(),
            ),
        loginPromptController = LoginPromptController(),
    )
